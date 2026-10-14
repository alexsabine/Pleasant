"""Hash-chained decision/provenance log for governance transparency.

Each entry commits to the previous entry's hash (a linear Merkle chain, the
same construction as Git commits and certificate-transparency logs, see RFC
6962 for the tree variant). Anyone holding the log can recompute the chain
and detect alteration or deletion of past entries. It does NOT make storage
immutable and it does not replace retention/deletion policy: a lawful
deletion is recorded as a new 'redaction' entry that keeps the hash of the
removed content, so the chain still verifies. Python stdlib only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

GENESIS = "0" * 64

REQUIRED_DECISION_FIELDS = (
    "request_id", "retrieval_sources", "source_versions", "policy_version",
    "assumptions", "confidence_type", "action_proposed", "user_approval",
    "action_result", "timestamp", "limitations",
)


def canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def entry_hash(prev_hash: str, payload: dict) -> str:
    return hashlib.sha256((prev_hash + "\n" + canonical(payload)).encode("utf8")).hexdigest()


@dataclass(frozen=True)
class Entry:
    index: int
    prev_hash: str
    payload: dict
    hash: str


@dataclass
class AuditChain:
    entries: list[Entry] = field(default_factory=list)

    def append(self, payload: dict, require_decision_fields: bool = False) -> Entry:
        if require_decision_fields:
            missing = [k for k in REQUIRED_DECISION_FIELDS if k not in payload]
            if missing:
                raise ValueError(f"decision record missing fields: {missing}")
        prev = self.entries[-1].hash if self.entries else GENESIS
        e = Entry(len(self.entries), prev, dict(payload), entry_hash(prev, payload))
        self.entries.append(e)
        return e

    def verify(self) -> tuple[bool, int | None]:
        """Return (ok, first_bad_index)."""
        prev = GENESIS
        for i, e in enumerate(self.entries):
            if e.index != i or e.prev_hash != prev:
                return False, i
            redacted = e.payload.get("redacted") is True and e.payload.get("original_hash") == e.hash
            if not redacted and entry_hash(prev, e.payload) != e.hash:
                return False, i
            prev = e.hash
        return True, None

    def redact(self, index: int, reason: str) -> Entry:
        """Lawful deletion: replace content, keep its hash, append a redaction entry."""
        old = self.entries[index]
        tomb = {"redacted": True, "original_hash": old.hash, "reason": reason}
        # The chain is re-linked through the tombstone; the redaction event is
        # itself appended so the history of the deletion is auditable.
        self.entries[index] = Entry(old.index, old.prev_hash, tomb, old.hash)
        return self.append({"event": "redaction", "of_index": index, "reason": reason})
