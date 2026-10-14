"""Fetch US Census TIGER/Line 2025 boundaries and clip to the Del Norte bbox.

Public domain (US Government work); cite "U.S. Census Bureau". AIANNH boundaries
are for statistical purposes and are not legal land descriptions.

Outputs (small, committed): data/boundaries/county.geojson, places.geojson, aiannh.geojson
Usage: python backend/ingest/fetch_tiger.py
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import shapefile  # pyshp

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_log import BBOX, ROOT, record  # noqa: E402

FILES = {
    "county": ("https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip",
               lambda r: r["GEOID"] == "06015"),
    "places": ("https://www2.census.gov/geo/tiger/TIGER2025/PLACE/tl_2025_06_place.zip",
               lambda r: True),  # filtered by bbox below
    "aiannh": ("https://www2.census.gov/geo/tiger/TIGER2025/AIANNH/tl_2025_us_aiannh.zip",
               lambda r: True),
}
OUT = ROOT / "data" / "boundaries"


def bbox_overlaps(b):
    return not (b[2] < BBOX["min_lon"] or b[0] > BBOX["max_lon"] or b[3] < BBOX["min_lat"] or b[1] > BBOX["max_lat"])


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "pleasant-crescent-ingest/0.1"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (url, keep) in FILES.items():
        t0 = time.time()
        raw = download(url)
        z = zipfile.ZipFile(io.BytesIO(raw))
        stem = [n for n in z.namelist() if n.endswith(".shp")][0][:-4]
        sf = shapefile.Reader(shp=io.BytesIO(z.read(stem + ".shp")), dbf=io.BytesIO(z.read(stem + ".dbf")),
                              shx=io.BytesIO(z.read(stem + ".shx")))
        fields = [f[0] for f in sf.fields[1:]]
        feats = []
        for sr in sf.iterShapeRecords():
            rec = dict(zip(fields, sr.record))
            if not keep(rec):
                continue
            if not bbox_overlaps(sr.shape.bbox):
                continue
            keep_props = {k: rec[k] for k in ("GEOID", "NAME", "NAMELSAD", "ALAND", "AWATER", "INTPTLAT", "INTPTLON", "LSAD", "CLASSFP", "AIANNHCE", "COMPTYP") if k in rec}
            feats.append({"type": "Feature", "properties": keep_props, "geometry": sr.shape.__geo_interface__})
        gj = {"type": "FeatureCollection", "name": f"tiger2025_{name}",
              "attribution": "U.S. Census Bureau TIGER/Line 2025 (public domain)", "features": feats}
        path = OUT / f"{name}.geojson"
        path.write_text(json.dumps(gj, separators=(",", ":")) + "\n")
        print(f"{name}: {len(feats)} features kept of {len(sf)} in {time.time()-t0:.0f}s -> {path.relative_to(ROOT)} ({path.stat().st_size/1e3:.0f} kB)")
        import hashlib
        record({"id": f"TIGER_{name.upper()}", "source_url": url, "product": f"TIGER/Line 2025 {stem}",
                "licence": "US Government work (public domain)", "attribution": "U.S. Census Bureau",
                "source_bytes": len(raw), "source_sha256": hashlib.sha256(raw).hexdigest(),
                "features_kept": len(feats), "output": str(path.relative_to(ROOT)), "decision": "approved_with_attribution",
                "note": "AIANNH boundaries are statistical, not legal land descriptions; names to be confirmed with each Nation." if name == "aiannh" else ""})


if __name__ == "__main__":
    main()
