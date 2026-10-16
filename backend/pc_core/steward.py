"""Steward trust: how much a steward's entry can be relied on when it is made.

Textbook pieces only (Python stdlib):
- Beta-binomial reliability with a pooled (empirical-Bayes, hierarchical) prior, so a new
  steward starts at the group's record, not at a coin flip (Gelman et al., BDA3 ch. 5).
- Recency weights: an outcome's weight halves every `half_life_days`.
- Joined to the freshness model: P(current | entered by s, age t) = r_s * S(t), where S is the
  Gamma-exponential survival in pc_core.freshness. The show/abstain decision stays the same
  Bayes act (show iff p > 0.75 under +1/-3/0), so trust changes HOW LONG a listing is
  recommended before re-check, never who may contribute.
- Fair blame: when a re-check finds a listing different, only the share explained by "wrong
  when entered" counts against the steward; the rest is ordinary change, which updates the
  category hazard instead.

The numbers are private to the steward and the stewards, never public, never ranked, and
never grant or remove a role on their own (rules 6 and 7).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, lgamma, log

from pc_core.freshness import GammaRate

SHOW_THRESHOLD = 0.75  # Bayes act under utilities +1 / -3 / 0
OUTCOMES = ("still_right", "changed_since", "wrong_at_entry", "cant_tell")


def recency_weight(age_days: float, half_life_days: float = 365.0) -> float:
    return 0.5 ** (max(0.0, age_days) / half_life_days)


@dataclass(frozen=True)
class Record:
    """Recency-weighted counts of a steward's checked entries."""
    right: float = 0.0
    wrong: float = 0.0

    def add(self, right: float = 0.0, wrong: float = 0.0, age_days: float = 0.0, half_life_days: float = 365.0) -> "Record":
        w = recency_weight(age_days, half_life_days)
        return Record(self.right + w * right, self.wrong + w * wrong)


@dataclass(frozen=True)
class PooledPrior:
    """Beta(m * p, m * (1 - p)): the group's reliability p, worth m entries of evidence."""
    p: float = 0.9
    strength: float = 10.0

    @classmethod
    def from_records(cls, records: list[Record], strength: float = 10.0, fallback: "PooledPrior | None" = None) -> "PooledPrior":
        """Empirical Bayes: pool everyone's (weighted) outcomes; the declared fallback fills in while data is thin."""
        fb = fallback or cls()
        right = sum(r.right for r in records) + fb.p * fb.strength
        wrong = sum(r.wrong for r in records) + (1 - fb.p) * fb.strength
        return cls(right / (right + wrong), strength)

    @property
    def alpha(self) -> float:
        return self.p * self.strength

    @property
    def beta(self) -> float:
        return (1 - self.p) * self.strength


def reliability(rec: Record, prior: PooledPrior) -> float:
    """Posterior mean P(an entry by this steward is right when made). The Bayes act uses this mean."""
    return (prior.alpha + rec.right) / (prior.alpha + prior.beta + rec.right + rec.wrong)


def prob_current(r: float, hazard: GammaRate, age: float) -> float:
    return r * hazard.survival(age)


def shelf_life(r: float, hazard: GammaRate, threshold: float = SHOW_THRESHOLD) -> float:
    """Days until r * S(t) falls to the threshold; 0 if it starts below. S(t) = (b / (b + t))^a."""
    if r <= threshold:
        return 0.0
    return hazard.rate * ((r / threshold) ** (1 / hazard.shape) - 1)


def blame_share(r: float, hazard: GammaRate, age: float) -> float:
    """P(wrong when entered | found different at age t) = (1 - r) / ((1 - r) + r * (1 - S(t)))."""
    wrong_then = 1 - r
    changed_since = r * (1 - hazard.survival(age))
    total = wrong_then + changed_since
    return wrong_then / total if total > 0 else 0.0


def record_outcome(rec: Record, outcome: str, r: float, hazard: GammaRate, age_at_check: float,
                   evidence_dated: bool = False, days_ago: float = 0.0) -> tuple[Record, float]:
    """Update a steward's record from one re-check. Returns (new record, share counted as change).

    still_right    -> one right.
    wrong_at_entry -> one wrong (the checker has dated evidence it was wrong when entered).
    changed_since  -> with dated evidence of a later change: no blame, all change.
                      Without it: split by blame_share, so a stale old listing is not held against anyone.
    cant_tell      -> no update.
    """
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown outcome {outcome!r}")
    if outcome == "still_right":
        return rec.add(right=1, age_days=days_ago), 0.0
    if outcome == "wrong_at_entry":
        return rec.add(wrong=1, age_days=days_ago), 0.0
    if outcome == "changed_since":
        if evidence_dated:
            return rec.add(right=1, age_days=days_ago), 1.0
        b = blame_share(r, hazard, age_at_check)
        return rec.add(right=1 - b, wrong=b, age_days=days_ago), 1 - b
    return rec, 0.0


# --- cautious lower bound, used only for INVITATION eligibility (a governance choice) ----------

def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the regularised incomplete beta (Numerical Recipes, Lentz)."""
    tiny, qab, qap, qam = 1e-300, a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c if abs(1 + aa / c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = 1 / (d if abs(d) > tiny else tiny)
        c = 1 + aa / c if abs(1 + aa / c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-12:
            break
    return h


def beta_cdf(x: float, a: float, b: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = exp(lgamma(a + b) - lgamma(a) - lgamma(b) + a * log(x) + b * log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1 - front * _betacf(b, a, 1 - x) / b


def beta_lower(a: float, b: float, q: float = 0.05) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if beta_cdf(mid, a, b) < q else (lo, mid)
    return (lo + hi) / 2
