"""API contract tests: the public JSON/GeoJSON surface Kim's acceptance criteria and the
map client depend on. Every listing field the brief requires is present; hard filters are
hard; drafts, restricted and sensitive records never leave; Compass's contract is stable."""
import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import Point
from django.test import Client, TestCase
from django.utils import timezone

from compass.tools import ALLOW_LIST

from .models import Event, ProjectionVersion, Resource

REQUIRED_LISTING_FIELDS = ("name", "category", "category_label", "min_age", "max_age", "cost_status", "lon", "lat", "community",
                           "accessibility_status", "access_notes", "website_url", "phone_public", "last_verified_at",
                           "verification_method", "p_current", "freshness_band", "public_source_url")
COUNTY_BBOX = (-124.45, 41.38, -123.50, 42.01)


def make(name, publish=True, **kw):
    d = dict(category="playground", community="crescent_city", min_age=0, max_age=18, cost_status="free",
             accessibility_status="unknown", location=Point(-124.2, 41.75, srid=4326), website_url="https://example.invalid/x",
             last_verified_at=timezone.now() - timedelta(days=2), verification_method="official_online")
    d.update(kw)
    r = Resource.objects.create(name=name, **d)
    if publish:
        r.save_revision().publish()
    return r


class ApiContract(TestCase):
    def setUp(self):
        self.c = Client()
        self.park = make("Kid Town", category="playground", min_age=2, max_age=12, accessibility_status="verified_yes")
        self.pool = make("Fred Endert Pool", category="sport", cost_status="priced", cost_usd=5, min_age=3, max_age=18)
        self.clinic = make("Countywide Family Service", category="family_service", community="countywide")
        self.draft = make("Draft Only", publish=False)
        self.sensitive = make("Quiet Nesting Site", category="trail", is_sensitive=True, location=Point(-124.1, 41.8, srid=4326))
        self.restricted = make("Restricted Record", visibility="restricted")

    # -- listings -------------------------------------------------------------------
    def test_resources_json_carries_every_field_the_brief_requires(self):
        d = self.c.get("/api/resources.json").json()
        self.assertEqual(d["projection_version"], ProjectionVersion.current())
        self.assertEqual({i["name"] for i in d["items"]}, {"Kid Town", "Fred Endert Pool", "Countywide Family Service"})
        for item in d["items"]:
            for f in REQUIRED_LISTING_FIELDS:
                self.assertIn(f, item, f)
            self.assertIn(item["accessibility_status"], ("verified_yes", "verified_no", "unknown"))
            self.assertIsNotNone(item["last_verified_at"])
            self.assertTrue(item["website_url"] or item["phone_public"], "link or contact required")

    def test_hidden_records_never_leave_any_endpoint(self):
        hidden = {self.draft.pk, self.sensitive.pk, self.restricted.pk}
        for url in ("/api/resources.json", "/api/resources.geojson", "/api/h3_venues.geojson", "/api/resources.geojson?group=outdoors"):
            body = self.c.get(url).json()
            ids = {i["id"] for i in body.get("items", [])} | {f["properties"]["id"] for f in body.get("features", [])}
            self.assertFalse(ids & hidden, url)
            self.assertNotIn("Quiet Nesting", json.dumps(body))

    def test_geojson_is_valid_and_inside_the_county(self):
        d = self.c.get("/api/resources.geojson").json()
        self.assertEqual(d["type"], "FeatureCollection")
        for f in d["features"]:
            self.assertEqual(f["geometry"]["type"], "Point")
            x, y = f["geometry"]["coordinates"]
            self.assertTrue(COUNTY_BBOX[0] <= x <= COUNTY_BBOX[2] and COUNTY_BBOX[1] <= y <= COUNTY_BBOX[3], f["properties"]["name"])
            self.assertEqual(f["properties"]["h3_res_11"][:1], "8")

    def test_filters_are_hard_where_the_brief_says_so(self):
        names = lambda url: {i["name"] for i in self.c.get(url).json()["items"]}
        self.assertEqual(names("/api/resources.json?access=1"), {"Kid Town"})            # unknown is never accessible
        self.assertEqual(names("/api/resources.json?free=1"), {"Kid Town", "Countywide Family Service"})
        self.assertEqual(names("/api/resources.json?age=1"), {"Countywide Family Service"})
        self.assertEqual(names("/api/resources.json?age=14"), {"Fred Endert Pool", "Countywide Family Service"})
        self.assertEqual(names("/api/resources.json?community=smith_river"), {"Countywide Family Service"})  # countywide serves everyone
        self.assertEqual(names("/api/resources.json?category=sport"), {"Fred Endert Pool"})
        self.assertEqual(names("/api/resources.json?q=town"), {"Kid Town"})

    def test_h3_endpoints_respect_resolution_limits_and_k_anonymity(self):
        v = self.c.get("/api/h3_venues.geojson?res=15").json()
        self.assertEqual(v["res"], 12)
        v = self.c.get("/api/h3_venues.geojson?res=3&halo=0").json()
        self.assertEqual(v["res"], 8)
        self.assertEqual({f["properties"]["role"] for f in v["features"]}, {"venue"})
        for f in v["features"]:
            ring = f["geometry"]["coordinates"][0]
            self.assertEqual(ring[0], ring[-1])
        a = self.c.get("/api/h3.geojson?res=12&k=5").json()
        self.assertLessEqual(a["res"], 8)                       # never finer than the public ceiling
        for f in a["features"]:
            self.assertTrue(f["properties"]["suppressed"] or f["properties"]["count"] >= 5)

    def test_events_exclude_past_and_draft(self):
        now = timezone.now()
        e1 = Event.objects.create(title="Story time", start_at=now + timedelta(days=2), cost_status="free")
        e1.save_revision().publish()
        Event.objects.create(title="Draft event", start_at=now + timedelta(days=3))
        e3 = Event.objects.create(title="Gone", start_at=now - timedelta(days=3))
        e3.save_revision().publish()
        titles = {e["title"] for e in self.c.get("/api/events.json").json()["items"]}
        self.assertEqual(titles, {"Story time"})

    def test_manifest_and_boundaries(self):
        m = self.c.get("/api/manifest.json").json()
        self.assertIn("layers", m); self.assertIn("ingest", m)
        for layer in m["layers"]:
            self.assertTrue(layer.get("licence_status") and layer.get("official_url"), f"{layer.get('id')} lacks rights/source fields")
        for entry in m["ingest"]:
            for key in ("licence", "attribution", "source_url", "fetched_at"):
                self.assertIn(key, entry, f"{entry.get('id')} lacks {key}")
        self.assertEqual(self.c.get("/api/boundaries/nope.geojson").status_code, 404)
        if (Path(settings.BOUNDARIES_DIR) / "county.geojson").exists():
            r = self.c.get("/api/boundaries/county.geojson")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(json.loads(b"".join(r.streaming_content))["type"], "FeatureCollection")

    def test_pmtiles_served_with_byte_ranges_from_our_origin(self):
        path = Path(settings.TILES_DIR) / "delnorte_terrain.pmtiles"
        if not path.exists():
            self.skipTest("tiles not present in this checkout")
        r = self.c.get("/tiles/delnorte_terrain.pmtiles", HTTP_RANGE="bytes=0-6")
        self.assertEqual(r.status_code, 206)
        self.assertEqual(b"".join(r.streaming_content), b"PMTiles")
        self.assertEqual(self.c.get("/tiles/../etc.pmtiles").status_code, 404)
        self.assertEqual(self.c.get("/tiles/missing_file.pmtiles").status_code, 404)

    def test_logo_is_a_gauge_of_the_live_projection(self):
        r = self.c.get("/logo.svg?size=96")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"<svg", r.content)

    # -- Compass contract ---------------------------------------------------------------
    def test_compass_contract(self):
        d = self.c.post("/compass/ask", data=json.dumps({"question": "a free playground for a 4 year old"}), content_type="application/json").json()
        for k in ("request_id", "action", "text", "items", "events", "provenance"):
            self.assertIn(k, d)
        p = d["provenance"]
        for k in ("policy_version", "projection_version", "tools", "allow_list", "audit_index", "audit_hash", "llm_used", "intent", "limitations"):
            self.assertIn(k, p)
        self.assertTrue(set(p["tools"]) <= set(ALLOW_LIST))
        self.assertEqual(tuple(p["allow_list"]), tuple(ALLOW_LIST))
        self.assertEqual([i["name"] for i in d["items"]], ["Kid Town"])
        self.assertEqual(p["projection_version"], ProjectionVersion.current())
        for item in d["items"]:
            self.assertIn("last_verified_at", item)
        self.assertNotIn("Draft Only", json.dumps(d)); self.assertNotIn("Quiet Nesting", json.dumps(d))

    def test_compass_rejects_bad_input_and_never_invents(self):
        self.assertEqual(self.c.post("/compass/ask", data="nope", content_type="application/json").status_code, 400)
        self.assertEqual(self.c.post("/compass/ask", data=json.dumps({"question": ""}), content_type="application/json").status_code, 400)
        d = self.c.post("/compass/ask", data=json.dumps({"question": "a trampoline centre"}), content_type="application/json").json()
        self.assertEqual(d["action"], "explain_unknown")
        self.assertEqual(d["items"], [])

    def test_stale_listing_is_withheld_not_recommended(self):
        make("Old Listing", category="class", last_verified_at=timezone.now() - timedelta(days=400))
        d = self.c.post("/compass/ask", data=json.dumps({"question": "a class"}), content_type="application/json").json()
        self.assertEqual(d["action"], "show_low_confidence")
        self.assertEqual([i["name"] for i in d["withheld"]], ["Old Listing"])


class PlanPages(TestCase):
    """The For Kim pages render, carry their key content, and use the new names."""

    def test_every_tab_renders(self):
        c = Client()
        expect = {"/plan/": "What each part does", "/plan/at-a-glance/": "Lumen's limits", "/plan/system/": "What never leaves our server",
                  "/plan/costs/": "How an AI call works", "/plan/ethics/": "who may be missing", "/plan/future/": "The map is never the territory",
                  "/plan/legal/": "The check: where we stand"}
        for url, text in expect.items():
            r = c.get(url)
            self.assertEqual(r.status_code, 200, url)
            body = r.content.decode()
            self.assertIn(text, body, url)
            self.assertIn("Crescent Compass", body)
            self.assertNotIn("Pleasant Crescent", body)
        self.assertEqual(c.get("/plan/nope/").status_code, 404)
        summary = c.get("/plan/").content.decode()
        self.assertIn("Kim, Sasha, Daniel and Bill", summary)
        self.assertIn("at any time through Lumen", summary)
        self.assertIn("Coordinating a group event", summary)
        self.assertIn("never the single source of truth", c.get("/plan/ethics/").content.decode())
        self.assertIn("Thirteen simple T-charts", c.get("/plan/at-a-glance/").content.decode())
        legal = c.get("/plan/legal/").content.decode()
        for text in ("Legal considerations", "The contract between Alex and Kim", "Group meetups", "Information Commission"):
            self.assertIn(text, legal)
        privacy = c.get("/privacy/").content.decode()
        self.assertIn("aged 18 and over", privacy)
        self.assertIn("Do Not Track", privacy)
        self.assertIn('href="/privacy/"', c.get("/about/").content.decode())

    def test_costs_come_from_the_model_and_fit_the_ceiling(self):
        body = Client().get("/plan/costs/").content.decode()
        d = json.loads((Path(settings.REPO_ROOT) / "design" / "cost_model.json").read_text())
        for k in ("light", "typical", "heavy"):
            total = d["lumen"]["scenarios"][k]["total"]
            self.assertLess(total, d["budget"])
            self.assertIn(f"${round(total):,}".replace(",", ""), body.replace(",", ""))
