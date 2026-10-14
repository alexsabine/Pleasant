"""Offline geocoder: index named features from OUR OWN basemap tiles (OSM via
Protomaps, ODbL) so that verified listings can be placed without any live
external geocoding request.

Builds data/verified/osm_names.json: {name_lower: [{"name","kind","layer","lon","lat","z","tile"}]}
from the `pois`, `places`, `landuse`, `natural`, `water` and `buildings`
layers at z14 (and `places` at z12) of data/tiles/delnorte_basemap.pmtiles.

Usage: python backend/ingest/geocode_local.py            # build index
       python backend/ingest/geocode_local.py "Battery Point Lighthouse"   # lookup
"""
from __future__ import annotations

import gzip
import json
import math
import sys
from pathlib import Path

import mapbox_vector_tile
from pmtiles.reader import MmapSource, Reader
from pmtiles.tile import tileid_to_zxy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_log import ROOT  # noqa: E402

TILES = [ROOT / "data" / "tiles" / "delnorte_basemap.pmtiles", ROOT / "data" / "tiles" / "crescent_city_z15.pmtiles"]
OUT = ROOT / "data" / "verified" / "osm_names.json"
LAYERS = {"pois", "places", "landuse", "natural", "water", "buildings", "physical_point", "roads"}
EXTENT = 4096


def tile_to_lonlat(z, x, y, px, py):
    n = 2 ** z
    lon = (x + px / EXTENT) / n * 360.0 - 180.0
    # decoded with y_coord_down=True: py is measured from the TOP of the tile
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (y + py / EXTENT) / n)))
    return lon, math.degrees(lat_rad)


def centroid(geom):
    t = geom["type"]
    c = geom["coordinates"]
    if t == "Point":
        return c
    pts = []
    def walk(v):
        if isinstance(v[0], (int, float)):
            pts.append(v)
        else:
            for u in v:
                walk(u)
    walk(c)
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]


def build():
    index: dict[str, list] = {}
    n_tiles = n_feats = 0
    from pmtiles.reader import all_tiles
    for tiles_path in TILES:
      if not tiles_path.exists():
        continue
      with open(tiles_path, "rb") as fh:
        src = MmapSource(fh)
        for zxy, data in all_tiles(src):
            z, x, y = zxy if isinstance(zxy, tuple) else tileid_to_zxy(zxy)
            if z not in (12, 14, 15):
                continue
            n_tiles += 1
            raw = gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
            tile = mapbox_vector_tile.decode(raw, default_options={"y_coord_down": True})
            for lname, layer in tile.items():
                if lname not in LAYERS:
                    continue
                if z == 12 and lname != "places":
                    continue
                for f in layer["features"]:
                    props = f.get("properties", {})
                    name = props.get("name") or props.get("name:en")
                    if not name:
                        continue
                    if lname == "roads" and props.get("kind") not in ("path", "other"):
                        continue  # only named paths/trails, not streets
                    cx, cy = centroid(f["geometry"])
                    lon, lat = tile_to_lonlat(z, x, y, cx, cy)
                    index.setdefault(name.lower(), []).append({
                        "name": name, "layer": lname, "kind": props.get("kind") or props.get("kind_detail") or "",
                        "lon": round(lon, 6), "lat": round(lat, 6), "z": z, "tile": f"{z}/{x}/{y}"})
                    n_feats += 1
    # dedupe near-identical points per name
    for k, v in index.items():
        seen, out = set(), []
        for e in v:
            key = (round(e["lon"], 4), round(e["lat"], 4), e["layer"])
            if key not in seen:
                seen.add(key)
                out.append(e)
        index[k] = out
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": "data/tiles/delnorte_basemap.pmtiles (OpenStreetMap via Protomaps, ODbL)",
                               "built_from_tiles": n_tiles, "features": n_feats, "names": index}, indent=0))
    print(f"indexed {n_feats} named features from {n_tiles} tiles into {OUT.relative_to(ROOT)} ({len(index)} distinct names)")


def lookup(query: str, limit: int = 8):
    idx = json.loads(OUT.read_text())["names"]
    q = query.lower()
    toks = [t for t in q.replace("'", "").split() if len(t) > 2]
    scored = []
    for name, entries in idx.items():
        if q == name:
            score = 100
        elif q in name or name in q:
            score = 80
        else:
            hits = sum(1 for t in toks if t in name)
            score = 60 * hits / max(1, len(toks)) if hits else 0
        if score >= 40:
            for e in entries:
                scored.append((score, e))
    scored.sort(key=lambda s: -s[0])
    return [dict(score=s, **e) for s, e in scored[:limit]]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for r in lookup(" ".join(sys.argv[1:])):
            print(r)
    else:
        build()
