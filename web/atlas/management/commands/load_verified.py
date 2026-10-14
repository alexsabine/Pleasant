"""Load online-verified real listings from data/verified/*.json.

Sources, in order of authority for coordinates:
1. an official page that states coordinates (recorded by the researcher as geo_source);
2. the California Department of Education school directory (data/verified/cde_schools.json);
3. a named feature in OUR OWN basemap tiles (OpenStreetMap via Protomaps, data/verified/osm_names.json).
Anything without one of those is NOT published; it is written to data/verified/unplaced.json for a human.

Each listing gets: a `reported` claim per fact with the official source URL, verified by the
system user `web_verifier` (role Editors) with verification_method = official_online, an audit
entry, and the exact H3 cell hierarchy (res 8..12). is_fictional is False. Nothing here is a
human site visit and the public label says so.

Usage: python manage.py load_verified [--replace-fictional]
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone as dt_tz

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from atlas.models import CategoryHazard, Claim, Resource

import sys as _sys
_sys.path.insert(0, str(settings.REPO_ROOT / "backend" / "ingest"))
from placer import Placer, tokens as _tokens  # noqa: E402

VERIFIED = settings.REPO_ROOT / "data" / "verified"
CATEGORY_MAP = {"after_school": "after_school", "visitor_center": "visitor_center", "park": "park", "beach": "beach",
                "attraction": "attraction", "museum": "museum", "playground": "playground", "sport": "sport", "trail": "trail",
                "school": "school", "preschool": "preschool", "childcare": "childcare", "college": "college", "library": "library",
                "class": "class", "arts": "arts", "family_service": "family_service"}
COUNTY_BBOX = (-124.50, 41.35, -123.40, 42.05)


def inside_county(lon, lat):
    return COUNTY_BBOX[0] <= lon <= COUNTY_BBOX[2] and COUNTY_BBOX[1] <= lat <= COUNTY_BBOX[3]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


class Command(BaseCommand):
    help = "Load online-verified real listings; never publishes anything without an authoritative geolocation."

    def add_arguments(self, parser):
        parser.add_argument("--replace-fictional", action="store_true", help="unpublish and delete fictional demo records first")
        parser.add_argument("--offline", action="store_true", help="no address geocoding requests")
        parser.add_argument("--reset-verified", action="store_true", help="delete previously loaded online-verified listings and reload")

    def handle(self, *args, **opts):
        User = get_user_model()
        verifier, created = User.objects.get_or_create(username="web_verifier", defaults={"is_staff": False, "email": "verifier@example.invalid"})
        if created:
            verifier.set_unusable_password(); verifier.save()
        editors, _ = Group.objects.get_or_create(name="Editors")
        verifier.groups.add(editors)
        if opts["replace_fictional"]:
            n = Resource.objects.filter(is_fictional=True).count()
            for r in Resource.objects.filter(is_fictional=True):
                if r.live:
                    r.unpublish()
                r.delete()
            from atlas.models import Event
            Event.objects.filter(is_fictional=True).delete()
            self.stdout.write(f"removed {n} fictional demo resources")

        if opts.get("reset_verified"):
            qs = Resource.objects.filter(verification_method="official_online")
            n = qs.count()
            for r in qs:
                if r.live:
                    r.unpublish()
                r.delete()
            self.stdout.write(f"reset: removed {n} previously loaded online-verified listings")
            from placer import LOG as _LOG
            if _LOG.exists():
                _LOG.unlink()
        cde = {}
        cde_path = VERIFIED / "cde_schools.json"
        if cde_path.exists():
            for s in json.loads(cde_path.read_text())["schools"]:
                if s["School"] != "No Data" and s["Latitude"] not in ("", "No Data"):
                    cde[norm(s["School"])] = s
        osm = {}
        osm_path = VERIFIED / "osm_names.json"
        if osm_path.exists():
            osm = json.loads(osm_path.read_text())["names"]

        entries = []
        for fname in ("education.json", "attractions.json"):
            p = VERIFIED / fname
            if p.exists():
                data = json.loads(p.read_text())
                for e in data.get("entries", []):
                    e["_file"] = fname
                    entries.append(e)
        self.stdout.write(f"{len(entries)} candidate entries from researchers")

        # Dedupe: an education entry that merely re-describes an attraction venue (same core name) is skipped.
        attraction_tokens = [set(_tokens(e["name"])) for e in entries if e["_file"] == "attractions.json"]
        deduped = []
        for e in entries:
            if e["_file"] == "education.json":
                if "junior ranger" in e["name"].lower():
                    self.stdout.write(f"  fold programme into its venue entry: {e['name']}")
                    continue
                te = set(_tokens(e["name"]))
                if any(ta and ta <= te and len(ta) >= 2 for ta in attraction_tokens):
                    self.stdout.write(f"  skip duplicate venue from education list: {e['name']}")
                    continue
            deduped.append(e)
        entries = deduped

        placer = Placer(allow_network=not opts.get("offline"))
        placed, unplaced = [], []
        for e in entries:
            lon, lat, src = placer.place(e)
            if lon is None:
                unplaced.append({"name": e["name"], "reason": "no authoritative geolocation", "address": e.get("address", "")})
                continue
            placed.append((e, lon, lat, src))
        placer.save_log()

        now = timezone.now()
        n_new = 0
        for e, lon, lat, src in placed:
            cat = CATEGORY_MAP.get(e.get("category", ""), "attraction")
            if cat == "park" and ("river" in e["name"].lower() or "swimming hole" in (e.get("summary") or "").lower()):
                cat = "river"
            CategoryHazard.for_category(cat)
            slug = slugify(e["name"])[:160]
            if Resource.objects.filter(slug=slug).exists():
                continue
            vdate = datetime.strptime(e.get("verified_on", "2026-10-14"), "%Y-%m-%d").replace(tzinfo=dt_tz.utc)
            r = Resource(name=e["name"][:160], slug=slug, description=e.get("summary", "")[:2000], category=cat,
                         community=e.get("community") or "crescent_city", min_age=int(e.get("min_age") or 0), max_age=int(e.get("max_age") or 18),
                         cost_status=e.get("cost_status") or "unknown", cost_note=(e.get("cost_note") or "")[:300],
                         accessibility_status=e.get("accessibility_status") or "unknown", access_notes=(e.get("access_notes") or "")[:300],
                         location=Point(lon, lat, srid=4326), geo_source=src[:200], website_url=(e.get("official_url") or "")[:200],
                         phone_public=(e.get("phone_public") or "")[:40], public_source_url=(e.get("official_url") or "")[:200],
                         source_note="Summarised from the official website; not a site visit.", address=(e.get("address") or "")[:300],
                         hours_note=(e.get("hours_note") or "")[:300], last_verified_at=vdate, verification_method="official_online",
                         is_fictional=False, trail_info=e.get("trail") or None)
            r.save()
            # one reported claim per fact, all pointing at the official source
            facts = {"summary": e.get("summary", ""), "ages": [r.min_age, r.max_age], "cost_status": r.cost_status,
                     "accessibility_status": r.accessibility_status, "hours": r.hours_note, "address": r.address,
                     "location": {"lon": lon, "lat": lat, "source": src}}
            for attr, val in facts.items():
                if val in ("", None, []):
                    continue
                c = Claim.objects.create(resource=r, attribute=attr, raw_value=val, epistemic_type="reported",
                                         source_uri=(e.get("official_url") or "")[:200], source_revision=f"web-{e.get('verified_on')}-{slug}-{attr}",
                                         source_observed_at=vdate, submitted_by=verifier, access_level="public")
                c.verify(verifier, note=f"checked against official source(s): {', '.join(e.get('source_urls', [])[:3])}")
            r.save_revision(user=verifier).publish(user=verifier)
            n_new += 1

        (VERIFIED / "unplaced.json").write_text(json.dumps({"generated": now.isoformat(), "unplaced": unplaced}, indent=1) + "\n")
        self.stdout.write(self.style.SUCCESS(
            f"published {n_new} new listings ({len(placed)} placed, {len(unplaced)} unplaced written to data/verified/unplaced.json); "
            f"live total {Resource.objects.filter(live=True).count()}"))

    def _locate(self, e, cde, osm):
        """Return (lon, lat, source) or (None, None, None)."""
        if e.get("lat") is not None and e.get("lon") is not None and e.get("geo_source"):
            return float(e["lon"]), float(e["lat"]), f"official: {e['geo_source']}"
        n = norm(e["name"])
        # CDE directory for schools: exact or containment match on the school name
        for key, s in cde.items():
            if key and (key == n or key in n or n in key or key.replace(" elementary", "") == n.replace(" elementary school", "").replace(" elementary", "")):
                return float(s["Longitude"]), float(s["Latitude"]), f"CDE public school directory ({s['CDSCode']})"
        # our own OSM tiles: exact name, then containment with a single unambiguous hit
        cands = osm.get(n.lower()) or osm.get((e["name"] or "").lower())
        if not cands:
            toks = [t for t in n.split() if len(t) > 3 and t not in ("park", "trail", "beach", "state", "county", "school", "center", "centre", "the")]
            hits = []
            for name, ents in osm.items():
                if all(t in name for t in toks) and toks:
                    hits.extend(ents)
            if len({(round(h["lon"], 3), round(h["lat"], 3)) for h in hits}) == 1:
                cands = hits[:1]
        if cands:
            c = cands[0]
            return c["lon"], c["lat"], f"OpenStreetMap feature '{c['name']}' ({c['kind']}) in our basemap tiles"
        return None, None, None
