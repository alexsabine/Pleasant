"""Crescent Compass decision policy: constrained expected utility with value of
information, over the published projection only.

Actions: show, ask (one optional question), explain_unknown, abstain.
Hard constraints (age, accessibility, cost) are filters, never scores.
Every answer is grounded in record ids; the phrasing layer (honesty.py) cannot add facts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from django.conf import settings

from pc_core.bayes import choose_binary_action

from . import tools

AGE_RE = re.compile(r"(\d{1,2})\s*(?:-|to)?\s*(?:year|yr|y/o|yo)|(?:age|aged|ages)\s*(\d{1,2})|(\d{1,2})\s*(?:year|yr)s?\s*old|toddler|baby|teen", re.I)
EVENT_WORDS = {"whats", "what", "happening", "event", "events", "this", "week", "weekend", "today", "tomorrow", "coming"}
WORD_AGES = {"toddler": 2, "baby": 0, "teen": 14, "teenager": 14, "preschooler": 4}


@dataclass
class Intent:
    age: int | None = None
    free_only: bool = False
    max_cost: float | None = None
    requires_accessibility: bool = False
    categories: list[str] = field(default_factory=list)
    community: str | None = None
    wants_events: bool = False
    text: str = ""
    source: str = "rules"  # or "llm"
    age_span: tuple | None = None   # from saved age bands (adult choice), used only when no age is asked

    def as_dict(self):
        d = self.__dict__.copy()
        d["age_span"] = list(d["age_span"]) if d.get("age_span") else None
        return d


def parse_intent_rules(question: str) -> Intent:
    q = question.lower()
    it = Intent()
    m = AGE_RE.search(q)
    if m:
        for g in m.groups():
            if g and g.isdigit():
                it.age = int(g)
                break
        if it.age is None:
            for w, a in WORD_AGES.items():
                if w in m.group(0).lower():
                    it.age = a
    if it.age is None:
        for w, a in WORD_AGES.items():
            if w in q:
                it.age = a
                break
    if re.search(r"\bfree\b|no cost|cheap|budget|don't want to pay", q):
        it.free_only = True
    m2 = re.search(r"under\s*\$?(\d+)|less than\s*\$?(\d+)|\$(\d+)", q)
    if m2:
        it.max_cost = float(next(g for g in m2.groups() if g))
    if re.search(r"wheelchair|accessible|pushchair|stroller|step-free|mobility", q):
        it.requires_accessibility = True
    for cat, words in tools.KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(w) + r"s?\b", q) for w in words):
            it.categories.append(cat)
    for key, label in (("smith_river", "smith river"), ("gasquet", "gasquet"), ("klamath", "klamath"), ("fort_dick", "fort dick"), ("hiouchi", "hiouchi"), ("crescent_city", "crescent city")):
        if label in q:
            it.community = key
            break
    if re.search(r"this week|weekend|today|tomorrow|event|what's on|whats on|happening", q):
        it.wants_events = True
    return it


@dataclass
class Decision:
    action: str                     # show | ask | explain_unknown | abstain
    intent: Intent
    shown: list[dict]               # records the policy is willing to recommend
    withheld: list[dict]            # records that exist but fail the show test (shown separately, lower confidence)
    events: list[dict]
    question: str | None = None
    reason: str = ""
    tool_calls: list[str] = field(default_factory=list)
    projection_version: int | None = None
    broadened: list[str] = field(default_factory=list)   # which constraints were relaxed to find anything


def _structured(intent: Intent) -> bool:
    return any([intent.age is not None, intent.free_only, intent.max_cost is not None, intent.requires_accessibility,
                intent.categories, intent.community])


def decide(intent: Intent, max_items: int = 4) -> Decision:
    u = settings.COMPASS_UTILITIES
    calls = []
    text = "" if _structured(intent) else intent.text
    leftover = [t for t in re.findall(r"[a-z]{4,}", (text or "").lower()) if t not in tools.STOPWORDS and t not in EVENT_WORDS]
    events_only = intent.wants_events and not _structured(intent) and not leftover
    kwargs = dict(age=intent.age, free_only=intent.free_only, max_cost=intent.max_cost,
                  requires_accessibility=intent.requires_accessibility, categories=intent.categories or None,
                  community=intent.community, text=text, age_span=intent.age_span)
    if events_only:
        res = {"count": 0, "items": [], "projection_version": tools.ProjectionVersion.current()}
    else:
        res = tools.search_published_resources(**kwargs)
        calls.append("search_published_resources")
    broadened = []
    # Broaden one soft constraint at a time (category, then community, then cost). Hard
    # constraints (age band, accessibility) are never relaxed by the policy.
    for key, label in (("categories", "type of activity"), ("community", "community"), ("free_only", "cost")):
        if events_only or res["count"] or not kwargs.get(key):
            continue
        kwargs[key] = None if key != "free_only" else False
        res = tools.search_published_resources(**kwargs)
        calls.append("search_published_resources")
        broadened.append(label)
    events = []
    if intent.wants_events:
        events = tools.search_events(free_only=intent.free_only, age=intent.age)["items"]
        calls.append("search_events")

    shown, withheld = [], []
    for d in res["items"]:
        p = d["p_current"]
        if p is None:
            withheld.append({**d, "why": "no verification on record"})
            continue
        act, _ = choose_binary_action(p, u["show_true"], u["show_false"], u["abstain"])
        (shown if act == "show" else withheld).append({**d, "why": "" if act == "show" else f"P(current)={p:.2f} below the show threshold under the published utilities"})

    # Value-of-information rule for ONE optional question: ask for age only if the
    # result set would change with it (candidates span disjoint age bands).
    question = None
    if intent.age is None and len(shown) >= 2:
        bands = {(d["min_age"], d["max_age"]) for d in shown}
        if len(bands) > 1 and any(a[1] < b[0] or b[1] < a[0] for a in bands for b in bands):
            question = "How old is your child? I can narrow this to the right age band (optional)."

    if not shown and not events and withheld:
        action, reason = "show_low_confidence", "matches exist but none is recently verified; shown with their status, not recommended"
    elif not shown and not events:
        action, reason = "explain_unknown", "no published listing matches; nothing is invented"
    elif question and len(shown) > 3:
        action, reason = "ask", "age would change which safe suggestions apply"
    else:
        action, reason = "show", f"{len(shown)} listing(s) pass the Bayes show test"
    if broadened and action == "show":
        reason += f"; no exact match, so {', '.join(broadened)} was relaxed"
    return Decision(action=action, intent=intent, shown=shown[:max_items], withheld=withheld[:max_items], events=events[:max_items],
                    question=question, reason=reason, tool_calls=calls, projection_version=res["projection_version"],
                    broadened=broadened)
