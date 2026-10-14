"""Public views and read-only JSON API. Only live, public projections leave the
server; private claims, contributor identities and restricted coordinates never do."""
from __future__ import annotations

import json
import os
import re
from datetime import timedelta

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import CATEGORIES, CATEGORY_GROUP, COMMUNITIES, GROUPS, Event, ProjectionVersion, Resource, Submission


def _public_resources():
    # Sensitive places never appear individually; only in coarse k-anonymous aggregates.
    return Resource.objects.filter(live=True, visibility="public", is_sensitive=False)


def _apply_filters(qs, params):
    cat = params.get("category")
    if cat:
        qs = qs.filter(category=cat)
    grp = params.get("group")
    if grp:
        qs = qs.filter(category__in=[c for c, g in CATEGORY_GROUP.items() if g == grp])
    com = params.get("community")
    if com:
        qs = qs.filter(community__in=[com, "countywide"])
    if params.get("free") in ("1", "true", "on"):
        qs = qs.filter(cost_status="free")
    if params.get("access") in ("1", "true", "on"):
        qs = qs.filter(accessibility_status="verified_yes")  # hard filter: unknown is never "accessible"
    age = params.get("age")
    if age and age.isdigit():
        a = int(age)
        qs = qs.filter(min_age__lte=a, max_age__gte=a)
    q = params.get("q", "").strip()
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(description__icontains=q)
    return qs


def _common_ctx(request):
    return {"categories": CATEGORIES, "communities": COMMUNITIES, "groups": GROUPS, "params": request.GET,
            "projection_version": ProjectionVersion.current()}


def explore(request):
    qs = _apply_filters(_public_resources(), request.GET)
    items = sorted(qs, key=lambda r: (-(r.p_current or 0), r.name))
    ctx = _common_ctx(request)
    ctx.update({"items": items, "count": len(items), "view": request.GET.get("view", "list")})
    return render(request, "atlas/explore.html", ctx)


def resource_detail(request, slug):
    r = get_object_or_404(_public_resources(), slug=slug)
    history = [e for e in r.revisions.order_by("-created_at")[:10]]
    ctx = _common_ctx(request)
    ctx.update({"r": r, "claims": r.verified_claims(), "history": history,
                "events": r.events.filter(live=True, start_at__gte=timezone.now() - timedelta(days=1))[:5]})
    return render(request, "atlas/resource_detail.html", ctx)


def this_week(request):
    now = timezone.now()
    upcoming = Event.objects.filter(live=True, start_at__gte=now - timedelta(hours=3), start_at__lte=now + timedelta(days=14)).order_by("start_at")
    expired = Event.objects.filter(live=True, start_at__lt=now - timedelta(hours=3), archived_at__isnull=True).order_by("-start_at")[:5]
    ctx = _common_ctx(request)
    ctx.update({"upcoming": upcoming, "expired": expired})
    return render(request, "atlas/this_week.html", ctx)


def local_help(request):
    qs = _public_resources().filter(category__in=("family_service", "health", "food", "childcare"))
    ctx = _common_ctx(request)
    ctx.update({"items": qs})
    return render(request, "atlas/local_help.html", ctx)


def about(request):
    ingest = []
    if settings.INGEST_LOG.exists():
        ingest = json.loads(settings.INGEST_LOG.read_text())
    ctx = _common_ctx(request)
    ctx.update({"ingest": ingest})
    return render(request, "atlas/about.html", ctx)


# ---- JSON API -----------------------------------------------------------------
@require_GET
def api_resources(request):
    qs = _apply_filters(_public_resources(), request.GET)
    items = sorted((r.public_dict() for r in qs), key=lambda d: (-(d["p_current"] or 0), d["name"]))
    return JsonResponse({"projection_version": ProjectionVersion.current(), "count": len(items), "items": items})


@require_GET
def api_resources_geojson(request):
    qs = _apply_filters(_public_resources(), request.GET)
    feats = []
    for r in qs:
        if r.location is None or r.is_sensitive:
            continue  # sensitive places only ever appear in coarse aggregates
        d = r.public_dict()
        feats.append({"type": "Feature", "id": r.pk, "geometry": {"type": "Point", "coordinates": [r.location.x, r.location.y]},
                      "properties": d})
    return JsonResponse({"type": "FeatureCollection", "projection_version": ProjectionVersion.current(), "features": feats})


@require_GET
def api_events(request):
    now = timezone.now()
    qs = Event.objects.filter(live=True, start_at__gte=now - timedelta(hours=3), start_at__lte=now + timedelta(days=30)).order_by("start_at")
    return JsonResponse({"items": [e.public_dict() for e in qs]})


@require_GET
def api_h3_aggregate(request):
    """k-anonymous counts per H3 cell; res clamp and suppression in pc_core.h3_index."""
    try:
        from pc_core import h3_index as hx
        import h3
    except Exception:
        return JsonResponse({"type": "FeatureCollection", "features": [], "note": "h3 not installed"})
    res = max(hx.PUBLIC_MIN_RES, min(hx.PUBLIC_MAX_RES, int(request.GET.get("res", 7))))
    k = max(2, int(request.GET.get("k", 2)))
    pts = [(r.location.y, r.location.x, r.is_sensitive) for r in Resource.objects.filter(live=True, visibility="public") if r.location is not None]
    feats = []
    for c in hx.public_aggregate(pts, res=res, k=k):
        ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(c.cell)]
        ring.append(ring[0])
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": {"cell": c.cell, "count": c.count, "suppressed": c.suppressed, "res": h3.get_resolution(c.cell)}})
    return JsonResponse({"type": "FeatureCollection", "res": res, "k": k, "features": feats,
                         "note": "Derived index; counts below k are suppressed; no distances or travel times."})


@require_GET
def api_h3_venues(request):
    """Exact H3 cells of public venues (res 8..12) with a 1-ring halo at the chosen res.
    Public places only; sensitive records are excluded at model level (h3_cells empty)."""
    try:
        from pc_core import h3_index as hx
    except Exception:
        return JsonResponse({"type": "FeatureCollection", "features": []})
    res = max(8, min(12, int(request.GET.get("res", 11))))
    halo = request.GET.get("halo", "1") == "1"
    feats = []
    for r in _apply_filters(_public_resources(), request.GET):
        cell = (r.h3_cells or {}).get(str(res))
        if not cell:
            continue
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [hx.cell_polygon(cell)]},
                      "properties": {"id": r.pk, "slug": r.slug, "name": r.name, "cell": cell, "res": res, "role": "venue",
                                     "category": r.category, "group": r.group, "freshness_band": r.freshness_band}})
        if halo:
            for nb in hx.venue_neighbourhood(cell, 1):
                if nb != cell:
                    feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [hx.cell_polygon(nb)]},
                                  "properties": {"id": r.pk, "cell": nb, "res": res, "role": "halo", "group": r.group}})
    return JsonResponse({"type": "FeatureCollection", "res": res, "features": feats,
                         "note": "Exact containing cells for public venues; a halo is one grid step, not a distance."})


@require_GET
def logo_svg(request):
    from .context_processors import living_logo
    size = max(16, min(512, int(request.GET.get("size", 128))))
    svg = living_logo(request, size=size, animate=request.GET.get("static") != "1")["logo_svg"]
    resp = HttpResponse(svg, content_type="image/svg+xml")
    resp["Cache-Control"] = "public, max-age=600"
    return resp


@require_GET
def api_manifest(request):
    layers = json.loads(settings.LAYER_MANIFEST.read_text()) if settings.LAYER_MANIFEST.exists() else []
    ingest = json.loads(settings.INGEST_LOG.read_text()) if settings.INGEST_LOG.exists() else []
    return JsonResponse({"layers": layers, "ingest": ingest, "private_mode": settings.PC_PRIVATE_MODE})


@require_GET
def api_boundary(request, name):
    if name not in ("county", "places", "aiannh"):
        raise Http404
    path = settings.BOUNDARIES_DIR / f"{name}.geojson"
    if not path.exists():
        raise Http404
    return FileResponse(open(path, "rb"), content_type="application/geo+json")


# ---- PMTiles with HTTP Range support (dev server; production uses object storage/nginx) ----
_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


@require_GET
def serve_pmtiles(request, name):
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise Http404
    path = settings.TILES_DIR / f"{name}.pmtiles"
    if not path.exists():
        raise Http404
    size = os.path.getsize(path)
    rng = request.headers.get("Range")
    if not rng:
        resp = FileResponse(open(path, "rb"), content_type="application/octet-stream")
        resp["Accept-Ranges"] = "bytes"
        resp["Content-Length"] = str(size)
        return resp
    m = _RANGE_RE.fullmatch(rng.strip())
    if not m:
        return HttpResponse(status=416)
    start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2)))
    end = int(m.group(2)) if m.group(2) and m.group(1) else size - 1
    end = min(end, size - 1)
    if start > end or start >= size:
        resp = HttpResponse(status=416)
        resp["Content-Range"] = f"bytes */{size}"
        return resp
    length = end - start + 1

    def stream():
        with open(path, "rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(1 << 16, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    resp = StreamingHttpResponse(stream(), status=206, content_type="application/octet-stream")
    resp["Content-Range"] = f"bytes {start}-{end}/{size}"
    resp["Content-Length"] = str(length)
    resp["Accept-Ranges"] = "bytes"
    resp["Cache-Control"] = "public, max-age=3600"
    return resp


# ---- Public contribution form (Kim 3.3): suggestions are moderated, never auto-published ----
def contribute(request):
    from django import forms

    class SuggestForm(forms.Form):
        kind = forms.ChoiceField(choices=[("new", "Suggest a new place or programme"), ("correction", "Correct an existing listing")], widget=forms.RadioSelect, initial="new")
        resource = forms.ModelChoiceField(queryset=_public_resources(), required=False, label="Listing to correct (if any)")
        name = forms.CharField(max_length=160, required=False, label="Name of the place or programme")
        details = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}), label="What should we know? (hours, cost, ages, access, what changed)")
        source_url = forms.URLField(required=False, label="Official website or source (helps us verify)")
        contact = forms.EmailField(required=False, label="Your email (optional, only if you want a reply)")
        honey = forms.CharField(required=False, widget=forms.HiddenInput)  # spam trap

    form = SuggestForm(request.POST or None)
    sent = False
    if request.method == "POST" and form.is_valid() and not form.cleaned_data.get("honey"):
        d = form.cleaned_data
        Submission.objects.create(
            target_resource=d.get("resource"), submitter=request.user if request.user.is_authenticated else None,
            proposed_payload={"attribute": "suggestion" if d["kind"] == "new" else "correction", "kind": d["kind"], "name": d.get("name", ""),
                              "details": d["details"], "source_url": d.get("source_url", ""), "contact": d.get("contact", "")})
        sent = True
        form = SuggestForm()
    ctx = _common_ctx(request)
    ctx.update({"form": form, "sent": sent})
    return render(request, "atlas/contribute.html", ctx)
