"""One-year running cost for Pleasant Crescent: 100 onboarded members, Claude Opus 5.5.

Scenario (owner's brief, 2026-10-16):
- the map and listings are public; only onboarded members can use Crescent Compass (the API);
- members can send corrections, suggestions and photographs of places they visited;
- stewards approve all "write" items once a month by asking Compass for the monthly digest;
- every listing's official web page is checked monthly; soft integration with quadruplicate.org;
- the full trust system runs on every answer (show rule, honesty check, sealed log, closure, k-anonymity);
- no offline/own AI computer, no WhatsApp.

Every number below is an editable assumption. Re-run:  python backend/examples/cost_model.py
Writes research/09_cost_model.md and design/cost_model.json (data for the explainer page).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEMBERS, WEEKS, MONTHS, BUDGET = 100, 52, 12, 1500
IN, OUT = 4.00, 20.00          # Claude Opus 5.5, US$ per million tokens (Anthropic model table, 2026-10)
BATCH = 0.5                    # Message Batches API: 50% off for jobs that can wait a few hours

USAGE = {   # per onboarded member
    "light":   {"label": "Light",   "questions_wk": 3,  "suggestions_mo": 0.5, "photos_mo": 0.5},
    "typical": {"label": "Typical", "questions_wk": 8,  "suggestions_mo": 1,   "photos_mo": 2},
    "heavy":   {"label": "Heavy",   "questions_wk": 20, "suggestions_mo": 3,   "photos_mo": 5},
}
LISTINGS = 150          # average live listings over the year (58 today, growing)
PAGE_CHANGED = 0.35     # share of official pages whose text changed since last month
RULES_STUCK = 0.20      # share of questions the rules cannot parse
CACHE_HIT = 0.25        # share of questions answered from the checked-answer cache

# tokens (input, output); output includes Opus's reasoning at low effort
T = {
    "intent":        (700, 300),    # turn a question the rules could not read into filters
    "phrase_full":   (2600, 600),   # as built: full public records sent for wording
    "phrase_lean":   (1200, 450),   # optimised: only the 8 fields an answer uses, at most 4 listings
    "suggestion":    (1500, 500),   # tidy a member's correction into a steward-ready draft
    "photo":         (1900, 300),   # vision check: people, children, private homes, readable signs, matches place
    "page_compare":  (4500, 500),   # changed official page vs the listing's claims
    "digest_item":   (1200, 250),   # one line of the steward's monthly digest with a recommendation
    "digest_summary": (10000, 1500),  # "What needs approving this month?" overview
    "steward_followup": (4000, 600),  # a steward's follow-up question (10 a month)
    "quadruplicate": (9000, 1500),  # sort ~50 new Quadruplicate calendar events for family relevance
    "governance":    (15000, 2000),  # monthly trust and audit summary for the stewards
}

FIXED = [  # US$ per year
    ("Server for the website, database and Compass (4 GB virtual server, $24/month)", 288),
    ("Off-site backups and photo storage (object storage, about $6/month)", 72),
    ("Domain name, e.g. crescentcompass.ca", 20),
    ("Email for sign-up and password resets (pay-per-use service)", 5),
    ("GitHub Pro for the code owner: private code, public preview site ($4/month)", 48),
    ("Anthropic API account: pay as you go, no subscription", 0),
    ("Security certificate (Let's Encrypt), uptime and error alerts (free tiers)", 0),
    ("Map: our own tiles from public data, no map subscription", 0),
    ("Trust system: runs as code on our server, no AI tokens", 0),
]


# Suggested hybrid: public pages served free by GitHub Pages (static export), members' features on a
# smaller 2 GB server ($12/month) because public traffic no longer reaches it.
HYBRID_SERVER = 144
SINGLE_SERVER = 288


def usd(tokens, batch=False):
    i, o = tokens
    return (i * IN + o * OUT) / 1e6 * (BATCH if batch else 1)


def jobs(u: dict, optimised: bool) -> list[dict]:
    q = MEMBERS * WEEKS * u["questions_wk"]
    sug = MEMBERS * MONTHS * u["suggestions_mo"]
    pho = MEMBERS * MONTHS * u["photos_mo"]
    pages = LISTINGS * MONTHS * PAGE_CHANGED
    b = optimised  # batch the jobs that can wait
    if optimised:
        per_q = RULES_STUCK * usd(T["intent"]) + (1 - CACHE_HIT) * usd(T["phrase_lean"])
        q_note = "intent only when the rules are stuck; lean records; checked-answer cache"
    else:
        per_q = usd(T["intent"]) + usd(T["phrase_full"])
        q_note = "intent and wording on every question; full records"
    items = sug + pho + pages
    rows = [
        {"job": "Compass answers for members", "count": q, "unit": "questions", "per": per_q, "note": q_note},
        {"job": "Corrections and suggestions drafted", "count": sug, "unit": "drafts", "per": usd(T["suggestion"])},
        {"job": "Photo checks before a steward sees them", "count": pho, "unit": "photos", "per": usd(T["photo"], b)},
        {"job": "Monthly check of official web pages", "count": pages, "unit": "changed pages", "per": usd(T["page_compare"], b),
         "note": f"{LISTINGS} pages fetched by our code each month; only the ~{int(PAGE_CHANGED*100)}% that changed go to Opus"},
        {"job": "Steward digest: one line per item", "count": items, "unit": "items", "per": usd(T["digest_item"], b)},
        {"job": "Steward asks: what needs approving?", "count": MONTHS, "unit": "months", "per": usd(T["digest_summary"])},
        {"job": "Steward follow-up questions", "count": 10 * MONTHS, "unit": "questions", "per": usd(T["steward_followup"])},
        {"job": "Quadruplicate events sorted", "count": MONTHS, "unit": "months", "per": usd(T["quadruplicate"], b)},
        {"job": "Monthly trust and audit summary", "count": MONTHS, "unit": "months", "per": usd(T["governance"], b)},
    ]
    for r in rows:
        r["year"] = r["count"] * r["per"]
    return rows


def main():
    fixed = sum(v for _, v in FIXED)
    out = {"generated": "2026-10-16", "members": MEMBERS, "budget": BUDGET, "price": {"in": IN, "out": OUT, "batch": BATCH},
           "fixed": [{"item": k, "year": v} for k, v in FIXED], "fixed_total": fixed, "usage": USAGE, "tokens": T,
           "assumptions": {"listings": LISTINGS, "page_changed": PAGE_CHANGED, "rules_stuck": RULES_STUCK, "cache_hit": CACHE_HIT},
           "scenarios": {}}
    for k, u in USAGE.items():
        s = {}
        for mode in ("as_built", "optimised"):
            rows = jobs(u, mode == "optimised")
            ai = sum(r["year"] for r in rows)
            s[mode] = {"rows": [{**r, "per": round(r["per"], 5), "year": round(r["year"], 2), "count": round(r["count"])} for r in rows],
                       "ai": round(ai, 2), "total": round(ai + fixed, 2)}
        # daily cap on worded answers that guarantees the ceiling (optimised)
        rows = s["optimised"]["rows"]
        other = sum(r["year"] for r in rows[1:])
        per_q = rows[0]["per"]
        s["optimised"]["daily_cap"] = max(0, int((BUDGET - fixed - other) / 365 / per_q))
        out["scenarios"][k] = s
    (ROOT / "design" / "cost_model.json").write_text(json.dumps(out, indent=1))

    L = ["# One-year running cost (generated)", "",
         f"`backend/examples/cost_model.py`, {out['generated']}. {MEMBERS} onboarded members, Claude Opus 5.5 at ${IN}/${OUT} per million tokens "
         f"(batch jobs at {int(BATCH*100)}%). Ceiling ${BUDGET}/year. Estimates from stated assumptions.", "",
         "## Fixed costs per year", "", "| Item | US$ |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in FIXED] + [f"| **Total** | **{fixed}** |", "", "## Totals", "",
          "| Use | Questions/member/week | AI as built | AI optimised | Total optimised | Daily cap on worded answers |", "|---|---|---|---|---|---|"]
    for k, u in USAGE.items():
        s = out["scenarios"][k]
        L.append(f"| {u['label']} | {u['questions_wk']} | ${s['as_built']['ai']:,.0f} | ${s['optimised']['ai']:,.0f} | ${s['optimised']['total']:,.0f} | {s['optimised']['daily_cap']} |")
    L += ["", "## Typical use, optimised, by job", "", "| Job | Count/year | US$ each | US$/year |", "|---|---|---|---|"]
    for r in out["scenarios"]["typical"]["optimised"]["rows"]:
        L.append(f"| {r['job']} | {r['count']:,} {r['unit']} | {r['per']:.4f} | {r['year']:,.2f} |")
    hyb = fixed - SINGLE_SERVER + HYBRID_SERVER
    out["hybrid_fixed"] = hyb
    for k in USAGE:
        out["scenarios"][k]["optimised"]["hybrid_total"] = round(out["scenarios"][k]["optimised"]["ai"] + hyb, 2)
    (ROOT / "design" / "cost_model.json").write_text(json.dumps(out, indent=1))
    L += ["", "## Suggested hybrid hosting", "",
          f"Public pages on GitHub Pages (covered by GitHub Pro), members' features on a 2 GB server: fixed ${hyb}/year.", "",
          "| Use | Total optimised, hybrid |", "|---|---|"]
    L += [f"| {u['label']} | ${out['scenarios'][k]['optimised']['hybrid_total']:,.0f} |" for k, u in USAGE.items()]
    (ROOT / "research" / "09_cost_model.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
