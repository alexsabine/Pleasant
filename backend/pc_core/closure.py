"""Operational closure and homeostasis checks ("autopoiesis-informed").

Autopoiesis (Maturana & Varela 1972/1980) describes a system whose organisation
is a network of processes that produce the components which regenerate that
same network. We do not claim the atlas *is* autopoietic in the biological
sense. We take two testable engineering consequences:

1. **Operational closure of publication.** Every published fact must be
   produced by the system's own verification process (a verified claim,
   verified by an authorised principal, recorded in the audit chain). Nothing
   enters the published projection from outside that loop: not an LLM
   summary, not a raw partner feed, not a cached duplicate.

2. **Homeostasis of accuracy.** The verification loop is the regulator that
   keeps the fraction of stale published listings bounded under a stationary
   change process. Without the loop the stale fraction drifts to 1. This is a
   simulation under the declared model; it says nothing about real staleness
   rates until measured.

The Markov-blanket reading used by the Free Energy Principle (Friston 2013,
"Life as we know it", J. R. Soc. Interface, open access) maps cleanly onto the
layered data model: internal states = evidence/claims/projection; sensory
states = submissions, verifications, partner imports; active states =
publications, recommendations, notifications; external states = the community
and places. That mapping is a design discipline, not a theorem about the atlas.
Python stdlib only.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from pc_core.freshness import GammaRate, review_priority

EPISTEMIC_PUBLISHABLE = {"observed", "reported"}
VERIFIER_ROLES = {"editor", "steward", "admin"}


@dataclass(frozen=True)
class Claim:
    claim_id: str
    resource_id: str
    attribute: str
    epistemic_type: str
    verified_by_role: str | None  # None = unverified
    audit_entry: str | None       # hash of the audit entry that recorded verification


@dataclass(frozen=True)
class PublishedFact:
    resource_id: str
    attribute: str
    supporting_claim_ids: tuple[str, ...]


@dataclass
class ClosureReport:
    ok: bool
    violations: list[str] = field(default_factory=list)


def check_operational_closure(facts: list[PublishedFact], claims: dict[str, Claim],
                              audit_hashes: set[str]) -> ClosureReport:
    """Every published fact traces to >=1 claim that is observed/reported,
    verified by an authorised role, and whose verification is in the audit chain."""
    v: list[str] = []
    for f in facts:
        if not f.supporting_claim_ids:
            v.append(f"{f.resource_id}.{f.attribute}: published with no supporting claim")
            continue
        ok_any = False
        for cid in f.supporting_claim_ids:
            c = claims.get(cid)
            if c is None:
                v.append(f"{f.resource_id}.{f.attribute}: unknown claim {cid}")
                continue
            if c.epistemic_type not in EPISTEMIC_PUBLISHABLE:
                v.append(f"{f.resource_id}.{f.attribute}: claim {cid} is '{c.epistemic_type}', not publishable evidence")
                continue
            if c.verified_by_role not in VERIFIER_ROLES:
                v.append(f"{f.resource_id}.{f.attribute}: claim {cid} not verified by an authorised role")
                continue
            if c.audit_entry not in audit_hashes:
                v.append(f"{f.resource_id}.{f.attribute}: claim {cid} verification missing from audit chain")
                continue
            ok_any = True
        if not ok_any and not any(s.startswith(f"{f.resource_id}.{f.attribute}") for s in v):
            v.append(f"{f.resource_id}.{f.attribute}: no valid supporting claim")
    return ClosureReport(ok=not v, violations=v)


@dataclass
class HomeostasisResult:
    stale_fraction_over_time: list[float]
    final_stale_fraction: float
    checks_made: int


def simulate_verification_loop(n_listings: int = 200, days: int = 365, daily_change_prob: float = 0.01,
                               checks_per_day: int = 0, policy: str = "evsi", seed: int = 7,
                               sensitivity: float = 0.95, specificity: float = 0.95) -> HomeostasisResult:
    """Listings go stale at a constant hazard; a bounded review budget repairs them.

    policy: 'none' (no loop), 'oldest' (fixed-age schedule), 'evsi' (pure myopic
    value of information under the declared Gamma-rate prior; starves old
    listings), 'evsi_repair' (value of information plus the declared value of
    restoring a stale listing to current).
    Returns the daily stale fraction among published listings.
    """
    rng = random.Random(seed)
    stale = [False] * n_listings
    age = [0.0] * n_listings  # days since last verification
    prior = GammaRate(2.0, 2.0 / daily_change_prob)  # prior mean hazard matches the world
    series: list[float] = []
    checks = 0
    for _ in range(days):
        for i in range(n_listings):
            if not stale[i] and rng.random() < daily_change_prob:
                stale[i] = True
            age[i] += 1
        if checks_per_day > 0 and policy != "none":
            if policy == "oldest":
                order = sorted(range(n_listings), key=lambda i: -age[i])
            elif policy == "evsi":
                order = sorted(range(n_listings),
                               key=lambda i: -review_priority(prior, age[i], sensitivity, specificity))
            elif policy == "evsi_repair":
                order = sorted(range(n_listings),
                               key=lambda i: -review_priority(prior, age[i], sensitivity, specificity,
                                                              repair_value=3.0))
            else:
                raise ValueError("unknown policy")
            for i in order[:checks_per_day]:
                checks += 1
                # editor check: detects staleness with `specificity`; repairs it
                if stale[i] and rng.random() < specificity:
                    stale[i] = False
                age[i] = 0.0
        series.append(sum(stale) / n_listings)
    return HomeostasisResult(series, series[-1], checks)
