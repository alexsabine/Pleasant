"""Place a verified listing on the map from authoritative sources, in order:

1. coordinates stated on an official page (recorded by the researcher as geo_source);
2. the California Department of Education school directory (schools);
3. a named feature in OUR OWN basemap tiles (OpenStreetMap via Protomaps), matched
   category-aware (a museum must match a museum, a trail a path, and so on);
4. a logged, ingest-time geocode of the official STREET ADDRESS via OSM Nominatim
   (usage policy: identified User-Agent, one request per second, light use), kept
   only if the result lies inside Del Norte County and, for Crescent City addresses,
   inside the city area. Directions-only entries are never geocoded.

Everything is logged to data/verified/geocode_log.json. Nothing is guessed.
"""
from __future__ import annotations

import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFIED = ROOT / "data" / "verified"
LOG = VERIFIED / "geocode_log.json"
COUNTY_BBOX = (-124.50, 41.35, -123.40, 42.05)
CITY_BBOX = (-124.27, 41.69, -124.08, 41.83)
KIND_FOR_CATEGORY = {
    "school": {"school", "college", "kindergarten"}, "preschool": {"kindergarten", "school", "childcare", "community_centre"},
    "childcare": {"childcare", "kindergarten", "school"}, "college": {"college", "university", "school"},
    "library": {"library"}, "museum": {"museum", "memorial"}, "attraction": {"memorial", "aquarium", "attraction", "viewpoint", "garden", "lighthouse", "pier", "recreation_ground", "zoo", "information"},
    "visitor_center": {"information", "visitor_centre"}, "park": {"park", "nature_reserve", "recreation_ground", "picnic_site", "camp_site", "protected_area"},
    "playground": {"playground", "park", "recreation_ground"}, "beach": {"beach", "picnic_site", "viewpoint"},
    "trail": {"path", "trailhead", "other"}, "sport": {"pitch", "sports_centre", "swimming_pool", "park", "recreation_ground", "stadium"},
    "family_service": {"social_facility", "community_centre", "office"}, "after_school": {"school", "community_centre", "social_facility"},
    "class": {"community_centre", "school", "information"}, "arts": {"arts_centre", "community_centre"},
}
COMMUNITY_CENTRE = {"crescent_city": (41.756, -124.200), "smith_river": (41.928, -124.150), "gasquet": (41.846, -123.970),
                    "klamath": (41.527, -124.038), "fort_dick": (41.868, -124.150), "hiouchi": (41.793, -124.072)}
COMMUNITY_MAX_KM = {"crescent_city": 9, "smith_river": 10, "gasquet": 15, "klamath": 14, "fort_dick": 10, "hiouchi": 12}
STOP = {"the", "and", "of", "at", "in", "a", "main", "del", "norte", "crescent", "city", "smith", "river", "klamath", "gasquet", "hiouchi", "memorial", "regional", "county", "day", "use", "area", "trail", "park", "playground",
        "state", "national", "recreation", "center", "centre", "visitor", "program", "school", "elementary", "middle", "high", "services",
        "redwoods", "redwood", "parks", "sp", "nra", "dnusd", "dncoe", "frc"}


def norm(t: str) -> str:
    t = re.sub(r"\([^)]*\)", " ", t or "")
    t = re.sub(r"[^a-z0-9 ]", " ", t.lower().replace("'", ""))
    return re.sub(r"\s+", " ", t).strip()


def tokens(t: str) -> list[str]:
    return [w for w in norm(t).split() if w not in STOP and len(w) > 2]


def in_bbox(lon, lat, bb):
    return bb[0] <= lon <= bb[2] and bb[1] <= lat <= bb[3]


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class Placer:
    def __init__(self, cde: dict | None = None, osm: dict | None = None, allow_network: bool = True):
        self.cde = cde or self._load_cde()
        self.osm = osm or self._load_osm()
        self.allow_network = allow_network
        self.log: list[dict] = json.loads(LOG.read_text()) if LOG.exists() else []
        self._last_net = 0.0

    @staticmethod
    def _load_cde():
        p = VERIFIED / "cde_schools.json"
        out = {}
        if p.exists():
            for s in json.loads(p.read_text())["schools"]:
                if s["School"] != "No Data" and s["Latitude"] not in ("", "No Data"):
                    out[norm(s["School"])] = s
        return out

    @staticmethod
    def _load_osm():
        p = VERIFIED / "osm_names.json"
        return json.loads(p.read_text())["names"] if p.exists() else {}

    def save_log(self):
        LOG.write_text(json.dumps(self.log, indent=1) + "\n")

    # ---- strategies ----
    def place(self, e: dict) -> tuple[float, float, str] | tuple[None, None, None]:
        for fn in (self._official, self._cde_match, self._osm_exact):
            res = fn(e)
            if res[0] is not None and in_bbox(res[0], res[1], COUNTY_BBOX):
                self.log.append({"name": e["name"], "lon": res[0], "lat": res[1], "source": res[2]})
                return res
        # An address geocode and a fuzzy named-feature match are both weaker evidence.
        # If both exist and disagree by more than 300 m, the named feature of the right
        # kind wins (a museum POI beats an address that resolves to a different building).
        addr = self._address_geocode(e)
        fuzzy = self._osm_fuzzy(e)
        chosen = None
        if addr[0] is not None and fuzzy[0] is not None:
            d = haversine_m(addr[1], addr[0], fuzzy[1], fuzzy[0])
            chosen = fuzzy if d > 300 else addr
            self.log.append({"name": e["name"], "note": f"address and named-feature candidates {d:.0f} m apart; chose {'named feature' if chosen is fuzzy else 'address'}"})
        elif addr[0] is not None:
            chosen = addr
        elif fuzzy[0] is not None:
            chosen = fuzzy
        if chosen and in_bbox(chosen[0], chosen[1], COUNTY_BBOX):
            self.log.append({"name": e["name"], "lon": chosen[0], "lat": chosen[1], "source": chosen[2]})
            return chosen
        self.log.append({"name": e["name"], "lon": None, "lat": None, "source": "unplaced"})
        return None, None, None

    def _official(self, e):
        if e.get("lat") is not None and e.get("lon") is not None and e.get("geo_source"):
            return float(e["lon"]), float(e["lat"]), f"official page: {e['geo_source']}"
        return None, None, None

    def _cde_match(self, e):
        if e.get("category") not in ("school", "college"):
            return None, None, None
        n = norm(e["name"]).replace(" school", "")
        best = None
        for key, s in self.cde.items():
            k = key.replace(" school", "")
            if k == n or (k and k in n) or (n and n in k):
                best = s
                break
        if best is None:
            tn = set(tokens(e["name"]))
            for key, s in self.cde.items():
                if tn and tn <= set(tokens(key)) or (set(tokens(key)) and set(tokens(key)) <= tn):
                    best = s
                    break
        if best:
            return float(best["Longitude"]), float(best["Latitude"]), f"California Department of Education school directory (CDS {best['CDSCode']})"
        return None, None, None

    def _community_ok(self, e, lon, lat):
        c = e.get("community")
        if c not in COMMUNITY_CENTRE:
            return True
        clat, clon = COMMUNITY_CENTRE[c]
        return haversine_m(clat, clon, lat, lon) / 1000 <= COMMUNITY_MAX_KM[c]

    def _osm_exact(self, e):
        return self._osm_match(e, min_score=95)

    def _osm_fuzzy(self, e):
        return self._osm_match(e, min_score=70)

    def _osm_match(self, e, min_score=70):
        kinds = KIND_FOR_CATEGORY.get(e.get("category", ""), set())
        q = norm(e["name"])
        tq = tokens(e["name"])
        cands = []
        for name, ents in self.osm.items():
            if len(name) < 4:
                continue
            nn = norm(name)
            tn = tokens(name)
            if nn == q:
                score = 100
            elif q and (q in nn or nn in q) and len(nn) >= 8 and tn and tn[0] in tq:
                score = 85   # containment only counts when the feature name has a distinctive token the query shares
            elif tq and tn and tq[0] in tn and len(set(tq) & set(tn)) / len(set(tq)) >= 0.6:
                score = 70   # the most distinctive (first) token must match and most tokens must overlap
            else:
                continue
            for ent in ents:
                kind_ok = (ent["kind"] in kinds) if kinds else True
                cands.append((score + (10 if kind_ok else -30), ent, kind_ok))
        if not cands:
            return None, None, None
        cands.sort(key=lambda c: -c[0])
        score, ent, kind_ok = cands[0]
        if score < min_score or not kind_ok:
            return None, None, None
        if not self._community_ok(e, ent["lon"], ent["lat"]):
            return None, None, None
        return ent["lon"], ent["lat"], f"OpenStreetMap feature '{ent['name']}' ({ent['kind']}) in our basemap tiles"

    def _address_geocode(self, e):
        addr = (e.get("address") or "").strip()
        m = re.match(r"^\s*(\d{1,6}[A-Za-z]?)\s+([^,]+?),\s*([A-Za-z .']+?),\s*CA\s*(\d{5})?", addr)
        if not m or not self.allow_network:
            return None, None, None
        number, street, city, zipc = m.group(1), m.group(2), m.group(3).strip(), m.group(4) or ""
        params = {"street": f"{number} {street}", "city": city, "state": "California", "country": "USA", "format": "jsonv2", "limit": 1, "countrycodes": "us"}
        if zipc:
            params["postalcode"] = zipc
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
        data = None
        for attempt in range(3):
            wait = 2.2 - (time.time() - self._last_net)
            if wait > 0:
                time.sleep(wait)
            self._last_net = time.time()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "pleasant-crescent-ingest/0.1 (private family atlas; one-off address geocoding)"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode("utf8"))
                break
            except Exception as ex:
                if "429" in str(ex) and attempt < 2:
                    time.sleep(8)
                    continue
                self.log.append({"name": e["name"], "error": f"nominatim: {ex}"})
                return None, None, None
        if not data:
            return None, None, None
        lon, lat = float(data[0]["lon"]), float(data[0]["lat"])
        # Reject street-level fallbacks that are only a town centroid
        if data[0].get("addresstype") in ("city", "town", "village", "hamlet", "county", "state"):
            return None, None, None
        if not self._community_ok(e, lon, lat):
            return None, None, None
        return lon, lat, f"OSM Nominatim geocode of the official street address '{number} {street}, {city}' ({data[0].get('addresstype', '')}), logged at ingest"
