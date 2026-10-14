"""Append-only ingest log: every acquisition of source data is recorded with
URL, bytes, SHA-256, vintage, licence and attribution, per
licenses/RIGHTS_CHECKLIST.md. The log is committed; the data is not."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "data" / "ingest_log.json"
BBOX = {"min_lon": -124.45, "min_lat": 41.35, "max_lon": -123.45, "max_lat": 42.05}  # padded Del Norte extent, NOT a legal boundary


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(entry: dict) -> None:
    entries = json.loads(LOG.read_text()) if LOG.exists() else []
    entry = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **entry}
    entries.append(entry)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(entries, indent=2) + "\n")
    print("ingest_log:", json.dumps(entry)[:300])
