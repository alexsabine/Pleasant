"""One-year running-cost model for Pleasant Crescent with 20 onboarded people.

Everything is an explicit, editable assumption; nothing is measured yet. Prices were gathered
on 2026-10-16 (Anthropic from its published model table; others from provider pages and price
aggregators, which disagree by up to ~20%). Re-run after changing any number:

    python backend/examples/cost_model.py

Writes research/09_cost_model.md and design/cost_model.json (the data the explainer page uses).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PEOPLE, WEEKS, BUDGET = 20, 52, 1500

# ---- how much people use it (per onboarded person per week) --------------------------------
USAGE = {
    "light":   {"label": "Light",   "questions": 5,  "suggestions": 0.25},
    "typical": {"label": "Typical", "questions": 15, "suggestions": 1},
    "heavy":   {"label": "Heavy",   "questions": 40, "suggestions": 3},
}

# ---- token profiles (estimates from compass/adapter.py; output includes the model's reasoning) --
CALL = {
    "intent":     (700, 300),     # turn the question into filters (schema-constrained)
    "phrase":     (2600, 600),    # reword the checked answer from up to 8 public records
    "agent":      (12000, 1800),  # conversational agent: ~3 model turns per question, growing context
    "suggestion": (1500, 500),    # tidy a person's suggestion into a draft for a steward
}
GATED_SHARE = 0.20  # share of questions the rules cannot parse (the 34-question sweep parsed 33; real phrasing is messier)

# AI modes: model calls per question, plus whether suggestions use the model
MODES = {
    "A": {"label": "Rules only (today's default)", "per_question": {}, "suggestions": False},
    "B": {"label": "AI only when the rules are stuck", "per_question": {"intent": GATED_SHARE}, "suggestions": True},
    "C": {"label": "AI words every answer", "per_question": {"intent": 1, "phrase": 1}, "suggestions": True},
    "D": {"label": "Conversational agent", "per_question": {"agent": 1}, "suggestions": True},
}

# steward helpers per year (modes B-D): weekly submissions digest, monthly governance report,
# and a summary for each re-check the review queue asks for (~3.3 per week, research/07)
STEWARD = [(52, 6000, 800), (12, 30000, 3000), (172, 10000, 800)]

# ---- model prices, US$ per million tokens (input, output) ------------------------------------
PROVIDERS = [
    # key, label, family, in, out, where the data goes, note
    ("opus",     "Claude Opus 5.5",            "Anthropic",  4.00, 20.00, "Anthropic (US)", "Most capable Claude for this job"),
    ("sonnet",   "Claude Sonnet 5.5",          "Anthropic",  2.00, 10.00, "Anthropic (US)", "Strong, half the price of Opus"),
    ("haiku",    "Claude Haiku 5.5",           "Anthropic",  0.10,  0.50, "Anthropic (US)", "Small, fast; ample for wording checked facts"),
    ("gem_lite", "Gemini 2.5 Flash-Lite",      "Google",     0.10,  0.40, "Google (US)", "Very cheap"),
    ("gem_fl",   "Gemini 3 Flash",             "Google",     0.50,  3.00, "Google (US)", "Mid-price"),
    ("gpt_nano", "GPT-5 nano",                 "OpenAI",     0.05,  0.40, "OpenAI (US)", "Cheapest listed; snapshot retiring Dec 2026"),
    ("gpt_mini", "GPT-5 mini",                 "OpenAI",     0.25,  2.00, "OpenAI (US)", "Mid-price"),
    ("mistral",  "Mistral Small 4",            "Mistral",    0.15,  0.60, "Mistral (EU)", "Open-weight family, EU company"),
    ("deepseek", "DeepSeek V4.1 Flash",        "DeepSeek",   0.30,  1.20, "DeepSeek (China)", "Cheap; data leaves the US, not recommended for a family service"),
    ("oss_host", "gpt-oss-120B (Groq/Together)", "Open model, hosted", 0.15, 0.60, "Groq/Together (US)", "Open model without owning hardware"),
]

# ---- running the website itself (per year) ---------------------------------------------------
HOSTING = {
    "static": {"label": "Static preview on GitHub Pages (no accounts, no AI)", "year": 15,
               "parts": "domain name $15"},
    "small":  {"label": "Small server we manage", "year": 22 * 12 + 5 * 12 + 15,
               "parts": "4 GB virtual server ~$22/mo, backups and photo storage ~$5/mo, domain $15"},
    "managed": {"label": "Managed server and database", "year": (24 + 15 + 5) * 12 + 15,
                "parts": "4 GB server $24/mo, managed PostgreSQL $15/mo, storage $5/mo, domain $15"},
}

# ---- our own AI box: hardware amortised over 3 years + electricity at 26 c/kWh (Del Norte average) --
KWH = 0.26
LOCAL = [
    # key, label, hardware $, average watts (24/7), what it can run
    ("mac",  "Mac mini (M5 Pro, 64 GB)", 2300, 40,  "20-30B open models (Qwen, gpt-oss-20b, Mistral Small) at chat speed"),
    ("3090", "PC with a used RTX 3090 (24 GB)", 1800, 120, "Same class of models, faster, louder, more power"),
    ("5090", "Workstation with an RTX 5090 (32 GB)", 9000, 180, "Larger models; far beyond this project's needs"),
]
RENTED = [
    ("pod",  "Rented cloud GPU, always on (RTX 4090)", 0.34 * 24 * 365, "Community-tier pod at $0.34/hour"),
    ("srv",  "Rented serverless GPU (about 2 busy hours a day)", 66 * 12, "Pay per second; 10-60 s cold starts"),
]


def tokens_per_year(usage: dict, mode: dict) -> tuple[float, float, int]:
    q = PEOPLE * WEEKS * usage["questions"]
    s = PEOPLE * WEEKS * usage["suggestions"]
    tin = tout = 0.0
    calls = 0.0
    for kind, per in mode["per_question"].items():
        i, o = CALL[kind]
        tin += q * per * i; tout += q * per * o; calls += q * per
    if mode["suggestions"]:
        i, o = CALL["suggestion"]
        tin += s * i; tout += s * o; calls += s
    if mode["per_question"]:
        for n, i, o in STEWARD:
            tin += n * i; tout += n * o; calls += n
    return tin, tout, round(calls)


def cost(tin: float, tout: float, p_in: float, p_out: float) -> float:
    return tin / 1e6 * p_in + tout / 1e6 * p_out


def main():
    rows = []
    for ukey, u in USAGE.items():
        for mkey, m in MODES.items():
            tin, tout, calls = tokens_per_year(u, m)
            for key, label, fam, pin, pout, where, note in PROVIDERS:
                rows.append({"usage": ukey, "mode": mkey, "provider": key, "calls": calls,
                             "tokens_in": round(tin), "tokens_out": round(tout), "ai_cost": round(cost(tin, tout, pin, pout), 2)})
    local = []
    for key, label, hw, watts, runs in LOCAL:
        elec = watts * 24 * 365 / 1000 * KWH
        local.append({"key": key, "label": label, "hardware": hw, "electricity_year": round(elec), "amortised_year": round(hw / 3 + elec),
                      "first_year_cash": round(hw + elec), "runs": runs})
    rented = [{"key": k, "label": l, "year": round(y), "note": n} for k, l, y, n in RENTED]

    # the daily cap that turns a yearly AI allowance into a guarantee
    def cap(ai_allowance: float, provider: str, mode: str = "C") -> int:
        p = next(x for x in PROVIDERS if x[0] == provider)
        per_q = sum(cost(CALL[k][0] * n, CALL[k][1] * n, p[3], p[4]) for k, n in MODES[mode]["per_question"].items())
        return int(ai_allowance / 365 / per_q) if per_q else 0

    data = {"generated": "2026-10-16", "people": PEOPLE, "weeks": WEEKS, "budget": BUDGET, "usage": USAGE,
            "modes": {k: {"label": v["label"]} for k, v in MODES.items()}, "calls": CALL, "gated_share": GATED_SHARE,
            "providers": [{"key": k, "label": l, "family": f, "in": pi, "out": po, "where": w, "note": n} for k, l, f, pi, po, w, n in PROVIDERS],
            "hosting": HOSTING, "local": local, "rented": rented, "rows": rows,
            "caps": {p: cap(BUDGET - HOSTING["small"]["year"], p) for p in ("opus", "sonnet", "haiku")}}
    (ROOT / "design" / "cost_model.json").write_text(json.dumps(data, indent=1))

    # markdown report
    def ai(u, m, p):
        return next(r for r in rows if r["usage"] == u and r["mode"] == m and r["provider"] == p)
    L = ["# One-year running-cost model (generated)", "",
         f"Generated by `backend/examples/cost_model.py` on {data['generated']}. {PEOPLE} onboarded people for {WEEKS} weeks; Kim's ceiling ${BUDGET}/year. "
         "All figures are estimates from stated assumptions; prices change and aggregators disagree by up to ~20%.", "",
         "## Usage scenarios (per person per week)", "", "| Scenario | Compass questions | Suggestions or corrections |", "|---|---|---|"]
    for u in USAGE.values():
        L.append(f"| {u['label']} | {u['questions']} | {u['suggestions']} |")
    L += ["", "## AI cost per year (US$), typical use", "", "| Model | " + " | ".join(f"{k}: {m['label']}" for k, m in MODES.items()) + " |", "|---" * (len(MODES) + 1) + "|"]
    for key, label, *_ in PROVIDERS:
        L.append(f"| {label} | " + " | ".join(f"{ai('typical', mk, key)['ai_cost']:,.2f}" for mk in MODES) + " |")
    L += ["", "## AI cost per year (US$), heavy use", "", "| Model | " + " | ".join(f"{k}" for k in MODES) + " |", "|---" * (len(MODES) + 1) + "|"]
    for key, label, *_ in PROVIDERS:
        L.append(f"| {label} | " + " | ".join(f"{ai('heavy', mk, key)['ai_cost']:,.2f}" for mk in MODES) + " |")
    L += ["", "## Running the website", "", "| Option | Per year | Made of |", "|---|---|---|"]
    for h in HOSTING.values():
        L.append(f"| {h['label']} | ${h['year']:,} | {h['parts']} |")
    L += ["", "## Our own AI hardware (plus website hosting, which is still needed)", "", "| Option | Hardware | Electricity/yr | Per year over 3 years | First-year cash |", "|---|---|---|---|---|"]
    for x in local:
        L.append(f"| {x['label']} | ${x['hardware']:,} | ${x['electricity_year']:,} | ${x['amortised_year']:,} | ${x['first_year_cash']:,} |")
    for x in rented:
        L.append(f"| {x['label']} | none | included | ${x['year']:,} | ${x['year']:,} |")
    L += ["", "## Daily caps that guarantee the ceiling (AI mode C, small server)", ""]
    for p, n in data["caps"].items():
        L.append(f"- {p}: at most {n} AI-worded answers a day keeps the year under ${BUDGET}.")
    (ROOT / "research" / "09_cost_model.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
