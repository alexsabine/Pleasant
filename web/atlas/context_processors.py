import json
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _tokens():
    with open(settings.BASE_DIR / "static" / "style" / "tokens.json", encoding="utf8") as fh:
        return json.load(fh)


def site_tokens(request):
    static_export = request.META.get("HTTP_X_PC_STATIC") == "1"   # set only by manage.py export_static
    return {"tokens": _tokens(), "private_mode": settings.PC_PRIVATE_MODE, "static_export": static_export,
            "static_config": json.dumps({"base": settings.PC_STATIC_BASE, "reviewEmail": settings.PC_REVIEW_EMAIL}),
            "map_center": settings.PC_MAP_CENTER, "map_zoom": settings.PC_MAP_ZOOM}


def living_logo(request, size: int = 36, animate: bool = True):
    """Crescent phase = Fisher-Rao coordinate of mean P(current); breathing = belief path
    length over the last 7 daily snapshots (approximated from audit entries); marks = changes."""
    from django.core.cache import cache
    from pc_core.crescent import CrescentState, crescent_svg, fr_theta
    key = f"living_logo:{size}:{int(animate)}"
    svg = cache.get(key)
    if svg is None:
        from atlas.models import AuditEntry, Resource
        from django.utils import timezone
        from datetime import timedelta
        live = [r for r in Resource.objects.filter(live=True, visibility="public") if r.p_current is not None]
        p = sum(r.p_current for r in live) / len(live) if live else 0.5
        week = timezone.now() - timedelta(days=7)
        changes = AuditEntry.objects.filter(created_at__gte=week, payload__event__in=["published", "unpublished", "claim_verified"]).count()
        # path length: compare today's mean belief with what it was a week ago (no new verifications -> only ageing)
        p_week_ago = (sum(max(0.0, r.p_current) for r in live) / len(live)) if live else 0.5
        try:
            from pc_core.freshness import prob_current
            from atlas.models import CategoryHazard
            vals = []
            for r in live:
                age = max(0.0, (r.age_days or 0) - 7)
                vals.append(prob_current(CategoryHazard.for_category(r.category).posterior(), age))
            p_week_ago = sum(vals) / len(vals) if vals else p
        except Exception:
            pass
        state = CrescentState(p=p, path_c=abs(fr_theta(p) - fr_theta(p_week_ago)) + 0.03 * min(changes, 10), changes_n=changes, n_listings=len(live))
        svg = crescent_svg(state, _tokens()["logo"], size=size, animate=animate)
        cache.set(key, svg, 600)
    return {"logo_svg": svg}
