"""The Compass tool allow-list. Every tool reads the published projection only.
No SQL, no private claims, no external calls, no writes. The LLM, when enabled,
never calls these directly: the policy runs them deterministically and hands the
model the results to phrase."""
from __future__ import annotations

import re
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from atlas.models import Event, ProjectionVersion, Resource

STOPWORDS = {"with", "that", "this", "what", "where", "there", "have", "want", "need", "near", "like", "some", "ideas", "things", "place", "places", "good", "best", "around", "kids", "child", "children", "family", "take", "year", "years", "old", "can", "could", "would", "should", "anything", "something", "today", "week", "weekend", "free", "cheap"}
ALLOW_LIST = ("search_published_resources", "search_events", "get_public_map_feature", "explain_source_and_freshness")

KEYWORDS = {
    "indoor_play": ["indoor", "rainy", "rain", "soft play", "inside"],
    "library": ["library", "story", "books", "storytime", "rainy", "rain", "indoor"],
    "arts": ["art", "museum", "craft", "music", "paint", "rainy", "rain"],
    "playground": ["playground", "swings", "slide", "kidtown", "kid's town"],
    "trail": ["trail", "walk", "hike", "dunes", "redwood", "grove"],
    "sport": ["swim", "pool", "sport", "soccer", "football", "basketball", "skate"],
    "class": ["class", "club", "lesson"],
    "family_service": ["help", "support", "service", "advice", "parenting"],
    "health": ["health", "clinic", "doctor", "wellbeing", "dentist"],
    "food": ["food", "meal", "pantry", "hungry"],
    "childcare": ["childcare", "daycare", "nursery", "infant", "toddler care"],
    "preschool": ["preschool", "head start", "pre-k", "early learning"],
    "school": ["school", "elementary", "middle school", "high school", "charter", "academy"],
    "college": ["college", "community college"],
    "after_school": ["after school", "after-school", "youth program", "4-h", "summer program"],
    "museum": ["museum", "history", "historical"],
    "beach": ["beach", "tidepool", "tide pool", "sand"],
    "park": ["park", "picnic", "campground", "day use"],
    "visitor_center": ["visitor center", "visitor centre", "information center", "ranger"],
    "attraction": ["aquarium", "sea lion", "seal", "pier", "attraction", "trees of mystery", "overlook", "lighthouse"],
}


def _public():
    return Resource.objects.filter(live=True, visibility="public", is_sensitive=False)


def search_published_resources(*, age: int | None = None, free_only: bool = False, max_cost: float | None = None,
                               requires_accessibility: bool = False, categories: list[str] | None = None,
                               community: str | None = None, text: str = "", limit: int = 20, age_span=None) -> dict:
    qs = _public()
    if age is not None:
        qs = qs.filter(min_age__lte=age, max_age__gte=age)
    elif age_span:
        lo, hi = age_span
        qs = qs.filter(min_age__lte=hi, max_age__gte=lo)  # overlaps any chosen band
    if free_only:
        qs = qs.filter(cost_status="free")
    if max_cost is not None:
        qs = qs.filter(cost_status__in=("free", "priced")).filter(cost_usd__lte=max_cost) | qs.filter(cost_status="free")
    if requires_accessibility:
        qs = qs.filter(accessibility_status="verified_yes")  # hard constraint: unknown is never accessible
    if categories:
        qs = qs.filter(category__in=categories)
    if community:
        qs = qs.filter(community__in=[community, "countywide"])  # countywide services serve every community
    if text:
        # token search over name/description, stopwords removed; never the whole question
        toks = [t for t in re.findall(r"[a-z]{4,}", text.lower()) if t not in STOPWORDS]
        if toks:
            q = Q()
            for t in toks:
                q |= Q(name__icontains=t) | Q(description__icontains=t)
            qs = qs.filter(q)
    items = [r.public_dict() for r in qs.distinct()]
    items.sort(key=lambda d: (-(d["p_current"] or 0.0), d["name"]))
    return {"tool": "search_published_resources", "projection_version": ProjectionVersion.current(),
            "count": len(items), "items": items[:limit]}


def search_events(*, days: int = 7, free_only: bool = False, age: int | None = None, limit: int = 10) -> dict:
    now = timezone.now()
    qs = Event.objects.filter(live=True, start_at__gte=now - timedelta(hours=3), start_at__lte=now + timedelta(days=days))
    if free_only:
        qs = qs.filter(cost_status="free")
    if age is not None:
        qs = qs.filter(min_age__lte=age, max_age__gte=age)
    items = [e.public_dict() for e in qs.order_by("start_at")[:limit] if not e.is_past]
    return {"tool": "search_events", "count": len(items), "items": items}


def get_public_map_feature(resource_id: int) -> dict:
    r = _public().filter(pk=resource_id).first()
    if r is None or r.is_sensitive or r.location is None:
        return {"tool": "get_public_map_feature", "feature": None}
    return {"tool": "get_public_map_feature", "feature": {"type": "Feature", "geometry": {"type": "Point", "coordinates": [r.location.x, r.location.y]}, "properties": r.public_dict()}}


def explain_source_and_freshness(resource_id: int) -> dict:
    r = _public().filter(pk=resource_id).first()
    if r is None:
        return {"tool": "explain_source_and_freshness", "found": False}
    claims = [{"attribute": c.attribute, "epistemic_type": c.epistemic_type, "verified_at": c.verified_at.isoformat() if c.verified_at else None,
               "source_uri": c.source_uri, "audit_hash": c.audit_hash[:12]} for c in r.verified_claims()[:10]]
    return {"tool": "explain_source_and_freshness", "found": True, "resource": r.public_dict(), "verified_claims": claims,
            "model": {"category": r.category, "p_current": r.p_current, "band": r.freshness_band,
                      "explanation": "P(still current) = posterior-predictive survival under the published category hazard; "
                                     "elapsed time widens uncertainty, it is not evidence of change."}}
