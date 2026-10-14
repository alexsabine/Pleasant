"""Fetch Terrarium-encoded elevation tiles for the Del Norte bbox and pack them
into a local raster PMTiles for MapLibre hillshade (raster-dem, encoding terrarium).

Source: AWS Open Data "Terrain Tiles" (Mapzen/Tilezen), s3://elevation-tiles-prod
https://registry.opendata.aws/terrain-tiles/  US content is USGS 3DEP (public domain).
Attribution per Tilezen: "Terrain Tiles: Mapzen/Tilezen; elevation data courtesy USGS 3DEP".

Usage: python backend/ingest/fetch_terrain.py --minzoom 7 --maxzoom 13
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_protomaps import tiles_in_bbox  # noqa: E402
from ingest_log import BBOX, ROOT, record, sha256_of  # noqa: E402

BASE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium"


def fetch(zxy):
    z, x, y = zxy
    req = urllib.request.Request(f"{BASE}/{z}/{x}/{y}.png", headers={"User-Agent": "pleasant-crescent-ingest/0.1"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return zxy, r.read()
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--minzoom", type=int, default=7)
    ap.add_argument("--maxzoom", type=int, default=13)
    ap.add_argument("--out", default=str(ROOT / "data" / "tiles" / "delnorte_terrain.pmtiles"))
    args = ap.parse_args(argv)
    todo = list(tiles_in_bbox(BBOX, args.minzoom, args.maxzoom))
    print(f"{len(todo)} terrain tiles z{args.minzoom}-{args.maxzoom}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with out.open("wb") as fh:
        w = Writer(fh)
        results = {}
        with ThreadPoolExecutor(max_workers=8) as ex:
            for zxy, data in ex.map(fetch, todo):
                results[zxy_to_tileid(*zxy)] = data
        for tid in sorted(results):
            w.write_tile(tid, results[tid])
        header = {"tile_type": TileType.PNG, "tile_compression": Compression.NONE,
                  "min_zoom": args.minzoom, "max_zoom": args.maxzoom,
                  "min_lon_e7": int(BBOX["min_lon"] * 1e7), "min_lat_e7": int(BBOX["min_lat"] * 1e7),
                  "max_lon_e7": int(BBOX["max_lon"] * 1e7), "max_lat_e7": int(BBOX["max_lat"] * 1e7),
                  "center_zoom": 10, "center_lon_e7": int(-124.2 * 1e7), "center_lat_e7": int(41.75 * 1e7)}
        w.finalize(header, {"name": "Pleasant Crescent terrain (Terrarium) Del Norte bbox",
                            "encoding": "terrarium",
                            "attribution": "Terrain Tiles: Mapzen/Tilezen on AWS Open Data; elevation data courtesy USGS 3DEP"})
    print(f"wrote {len(results)} tiles to {out} ({out.stat().st_size/1e6:.1f} MB) in {time.time()-t0:.0f}s")
    record({"id": "TERRAIN_TILES_3DEP", "source_url": BASE, "product": "AWS Open Data Terrain Tiles (terrarium PNG); US content USGS 3DEP",
            "licence": "Public domain (3DEP); Terrain Tiles attribution requested", "attribution": "Mapzen/Tilezen Terrain Tiles; USGS 3DEP",
            "bbox": BBOX, "zoom": [args.minzoom, args.maxzoom], "tiles": len(results), "output": str(out.relative_to(ROOT)),
            "bytes": out.stat().st_size, "sha256": sha256_of(out), "decision": "approved_with_attribution"})


if __name__ == "__main__":
    main(sys.argv[1:])
