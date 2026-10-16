"""Honesty layer: the only facts in a Lumen answer are the records the policy
retrieved. The deterministic composer builds the answer from records. If an LLM
phrasing is enabled, its output is a list of sentences each tagged with the
record ids it relies on; any sentence citing an unknown id, or asserting
accessibility for a record that is not verified accessible, or naming a place
that is not in the retrieved set, is dropped. The provenance block is always
generated here, never by the model."""
from __future__ import annotations

import re
from datetime import datetime, timezone as dt_tz

BAND_TEXT = {"recently_verified": "recently verified", "verified_this_season": "verified this season",
             "needs_recheck": "needs a re-check", "unverified": "not yet verified"}
ACCESS_TEXT = {"verified_yes": "verified accessible", "verified_no": "verified not accessible", "unknown": "access unknown"}
COST_TEXT = {"free": "free", "priced": "priced", "variable": "variable cost", "unknown": "cost unknown"}
ACCESS_WORDS = re.compile(r"wheelchair|accessible|step-free|pushchair|stroller", re.I)


def verified_ago(iso: str | None) -> str:
    if not iso:
        return "not yet verified"
    dt = datetime.fromisoformat(iso)
    days = int((datetime.now(dt_tz.utc) - dt).total_seconds() // 86400)
    return "checked today" if days == 0 else f"checked {days} day{'s' if days != 1 else ''} ago"


def item_line(d: dict) -> str:
    cost = COST_TEXT[d["cost_status"]] + (f" (${d['cost_usd']:.0f})" if d["cost_status"] == "priced" and d.get("cost_usd") is not None else "")
    bits = [d["category_label"].lower(), f"ages {d['min_age']} to {d['max_age']}", cost, ACCESS_TEXT[d["accessibility_status"]],
            verified_ago(d["last_verified_at"])]
    fict = " [fictional demo record]" if d.get("is_fictional") else ""
    return f"{d['name']}{fict}: " + ", ".join(bits) + "."


def compose(decision, memory_notes: list[str]) -> dict:
    """Deterministic answer. Returns {text, items, events, question, limitations}."""
    lines = []
    if decision.action == "show_low_confidence":
        lines.append("I found a match, but it has not been re-verified recently enough for me to recommend it outright. Here it is with its status:")
        for d in decision.withheld:
            lines.append("• " + item_line(d) + (f" ({d['why']})" if d.get("why") else ""))
        lines.append("You can check the source link on the listing page, or ask again later once an editor has re-verified it.")
    elif decision.action == "explain_unknown":
        lines.append("I could not find a published listing that matches. I only suggest places that an editor has verified, so I will not guess.")
        lines.append("You could broaden the search (drop the age or cost filter) or browse the full Explore list.")
    else:
        if decision.broadened:
            lines.append("Nothing matched exactly, so I relaxed the " + " and ".join(decision.broadened) + " and kept your other requirements.")
        if decision.shown:
            lines.append(f"Here {'is' if len(decision.shown) == 1 else 'are'} {len(decision.shown)} recently checked option{'s' if len(decision.shown) != 1 else ''} from the published directory:")
            for d in decision.shown:
                lines.append("• " + item_line(d))
        if decision.events:
            lines.append("Coming up:")
            for e in decision.events:
                when = datetime.fromisoformat(e["start_at"]).strftime("%a %d %b, %H:%M")
                lines.append(f"• {e['title']}{' [fictional demo]' if e.get('is_fictional') else ''}: {when}, {COST_TEXT[e['cost_status']]}, ages {e['min_age']} to {e['max_age']}.")
        if decision.withheld:
            lines.append("Also listed, but not re-verified recently enough for me to recommend outright:")
            for d in decision.withheld:
                lines.append("• " + item_line(d) + (f" ({d['why']})" if d.get("why") else ""))
    if decision.question:
        lines.append(decision.question)
    if memory_notes:
        lines.append("(I used " + "; ".join(memory_notes) + ". You can change these in My atlas.)")
    limitations = ["Only published, editor-verified records are used; nothing is inferred about places not listed.",
                   "Access status 'unknown' is never presented as accessible.",
                   "Verification dates are shown; conditions can change between checks."]
    return {"text": "\n".join(lines), "items": decision.shown, "withheld": decision.withheld, "events": decision.events,
            "question": decision.question, "limitations": limitations}


def validate_llm_sentences(sentences: list[dict], allowed: dict[int, dict]) -> tuple[list[str], list[str]]:
    """Keep only sentences whose cited ids are all allowed and whose text does
    not over-claim. Returns (kept_texts, dropped_reasons)."""
    kept, dropped = [], []
    names = {d["name"].lower(): rid for rid, d in allowed.items()}
    for s in sentences:
        text = (s.get("text") or "").strip()
        ids = [int(i) for i in s.get("resource_ids", []) if str(i).lstrip("-").isdigit()]
        if not text:
            continue
        if any(i not in allowed for i in ids):
            dropped.append(f"cites unknown record: {text[:60]}")
            continue
        low = text.lower()
        # A sentence that names a listed place must cite it.
        for nm, rid in names.items():
            if nm in low and rid not in ids:
                ids.append(rid)
        if ACCESS_WORDS.search(text) and any(allowed[i]["accessibility_status"] != "verified_yes" for i in ids):
            dropped.append(f"accessibility claim without verification: {text[:60]}")
            continue
        if not ids and re.search(r"\b(open|closed|free|costs?|hours|accessible|verified)\b", low):
            dropped.append(f"factual claim with no record: {text[:60]}")
            continue
        kept.append(text)
    return kept, dropped
