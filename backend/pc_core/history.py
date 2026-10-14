"""Versioned factual events and a separately derived lossy working summary.

Reference data structures only; a production system must enforce DB transactions,
row-level authorization, retention and encryption using established patterns.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

Kind = Literal["observed", "reported", "inferred", "generated", "simulated"]


@dataclass(frozen=True)
class EvidenceEvent:
    event_id: str
    resource_id: str
    source_id: str
    provenance_type: Kind
    attribute: str
    value: str
    recorded_at: datetime
    verified: bool = False
    source_revision: str | None = None
    permission: str = "internal"

    def __post_init__(self):
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must have timezone")


@dataclass
class EventStore:
    events: dict[str, EvidenceEvent] = field(default_factory=dict)

    def append(self, event: EvidenceEvent) -> bool:
        """Idempotent by event ID; never count same event as fresh confirmation."""
        old = self.events.get(event.event_id)
        if old:
            if old != event:
                raise ValueError("event ID collision with differing content")
            return False
        self.events[event.event_id] = event
        return True

    def approved_projection(self, resource_id: str) -> dict[str, str]:
        # Illustrates one publishing policy: last VERIFIED observed/reported
        # event by timestamp; real production requires approved revision links.
        sorted_evs = sorted((e for e in self.events.values()
                            if e.resource_id == resource_id and e.verified
                            and e.provenance_type in ("observed", "reported")),
                            key=lambda e: (e.recorded_at, e.event_id))
        return {e.attribute: e.value for e in sorted_evs}

    def source_events(self, resource_id: str) -> list[EvidenceEvent]:
        return sorted((e for e in self.events.values() if e.resource_id == resource_id),
                      key=lambda e: (e.recorded_at, e.event_id))


def exponential_working_summary(contents: list[float], q: float, m0: float = 0.0) -> float:
    """Lossy derived state; do not substitute for event log."""
    if not 0 <= q < 1:
        raise ValueError("0 <= q < 1")
    m = m0
    for phi in contents:
        m = q * m + (1 - q) * phi
    return m


def example_event(event_id="evt-1") -> EvidenceEvent:
    return EvidenceEvent(event_id=event_id, resource_id="fictional-park",
                         source_id="human-confirmed-demo", provenance_type="reported",
                         attribute="opening_hours", value="example_only",
                         recorded_at=datetime(2026, 10, 14, tzinfo=timezone.utc), verified=True)
