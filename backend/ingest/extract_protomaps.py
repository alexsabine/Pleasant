"""Extract a bounding box from a Protomaps daily OSM basemap build into a local
PMTiles file using HTTP range requests (the same thing `pmtiles extract` does).

Source: https://build.protomaps.com/<YYYYMMDD>.pmtiles  (ODbL; © OpenStreetMap
contributors; design CC0; Protomaps asks that builds be copied, not hotlinked).

Usage (from repo root):
    python backend/ingest/extract_protomaps.py --build 20261013 --maxzoom 14
Output: data/tiles/delnorte_basemap.pmtiles  (git-ignored) and an ingest log entry.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pmtiles.reader import Reader
from pmtiles.tile import zxy_to_tileid
from pmtiles.writer import Writer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_log import BBOX, ROOT, record, sha256_of  # noqa: E402


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def tiles_in_bbox(bbox: dict, minzoom: int, maxzoom: int):
    for z in range(minzoom, maxzoom + 1):
        x0, y0 = lonlat_to_tile(bbox["min_lon"], bbox["max_lat"], z)
        x1, y1 = lonlat_to_tile(bbox["max_lon"], bbox["min_lat"], z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                yield z, x, y


class RangeSource:
    """get_bytes(offset, length) over HTTP with a small cache for directories."""

    def __init__(self, url: str):
        self.url = url
        self.cache: dict[tuple[int, int], bytes] = {}
        self.requests = 0

    def __call__(self, offset: int, length: int) -> bytes:
        key = (offset, length)
        if key in self.cache:
            return self.cache[key]
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={offset}-{offset + length - 1}",
                                                        "User-Agent": "pleasant-crescent-ingest/0.1"})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                break
            except Exception as e:  # pragma: no cover
                if attempt == 4:
                    raise
                time.sleep(1.5 * (attempt + 1))
        self.requests += 1
        if length < 300_000:  # directories and small tiles are worth caching
            self.cache[key] = data
        return data


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="20261013")
    ap.add_argument("--minzoom", type=int, default=0)
    ap.add_argument("--maxzoom", type=int, default=14)
    ap.add_argument("--out", default=str(ROOT / "data" / "tiles" / "delnorte_basemap.pmtiles"))
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(argv)

    url = f"https://build.protomaps.com/{args.build}.pmtiles"
    src = RangeSource(url)
    reader = Reader(src)
    header = reader.header()
    metadata = reader.metadata()
    print("source header:", {k: header[k] for k in ("tile_type", "tile_compression", "min_zoom", "max_zoom")})
    print("source metadata name/attribution:", metadata.get("name"), "|", metadata.get("attribution"))

    todo = list(tiles_in_bbox(BBOX, args.minzoom, min(args.maxzoom, header["max_zoom"])))
    print(f"{len(todo)} candidate tiles in bbox z{args.minzoom}-{args.maxzoom}")

    def fetch(zxy):
        z, x, y = zxy
        return zxy, reader.get(z, x, y)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    n_written = 0
    with out.open("wb") as fh:
        w = Writer(fh)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            results = {}
            for (zxy, data) in ex.map(fetch, todo):
                if data:
                    results[zxy_to_tileid(*zxy)] = data
        for tid in sorted(results):  # clustered order for an efficient file
            w.write_tile(tid, results[tid])
            n_written += 1
        h = dict(header)
        h.update({"min_zoom": args.minzoom, "max_zoom": min(args.maxzoom, header["max_zoom"]),
                  "min_lon_e7": int(BBOX["min_lon"] * 1e7), "min_lat_e7": int(BBOX["min_lat"] * 1e7),
                  "max_lon_e7": int(BBOX["max_lon"] * 1e7), "max_lat_e7": int(BBOX["max_lat"] * 1e7),
                  "center_zoom": 10, "center_lon_e7": int(-124.2 * 1e7), "center_lat_e7": int(41.75 * 1e7)})
        md = dict(metadata)
        md["name"] = f"Pleasant Crescent basemap extract (Protomaps build {args.build}, Del Norte bbox)"
        md["attribution"] = metadata.get("attribution") or '<a href="https://openstreetmap.org">© OpenStreetMap contributors</a>'
        md["pleasant_crescent_extract"] = {"source_url": url, "bbox": BBOX, "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        w.finalize(h, md)
    dt = time.time() - t0
    print(f"wrote {n_written} tiles to {out} ({out.stat().st_size/1e6:.1f} MB) in {dt:.0f}s with {src.requests} range requests")
    record({"id": "OSM_PROTOMAPS_EXTRACT", "source_url": url, "product": f"Protomaps daily build {args.build} (OpenStreetMap)",
            "licence": "ODbL 1.0 (data); design CC0", "attribution": "© OpenStreetMap contributors",
            "bbox": BBOX, "zoom": [args.minzoom, args.maxzoom], "tiles": n_written,
            "output": str(out.relative_to(ROOT)), "bytes": out.stat().st_size, "sha256": sha256_of(out),
            "range_requests": src.requests, "decision": "approved_with_attribution",
            "note": "Private-use first iteration; ODbL share-alike applies only to a publicly distributed derived database."})


if __name__ == "__main__":
    main(sys.argv[1:])
