"""Freshness as a survival process: 'is this listing still current?'

Public, textbook mathematics:
- Exponential time-to-change with a Gamma prior on the rate is conjugate
  (Gelman et al., *Bayesian Data Analysis* 3e, ch. 2; the posterior-predictive
  survival function is the Lomax / Pareto-II tail).
- Review priority is the expected value of sample information (Raiffa &
  Schlaifer 1961; Howard 1966 "Information value theory").

The hazard is per category and per declared unit of time. Nothing here is a
claim about real listings; it is the DECLARED model that a governance body can
read and change. Python stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, log

from pc_core.bayes import choose_binary_action, posterior_given_binary_test


@dataclass(frozen=True)
class GammaRate:
    """Gamma(shape, rate) prior/posterior on an exponential change hazard lambda."""
    shape: float = 2.0
    rate: float = 100.0  # e.g. days of 'exposure' worth of prior belief

    def __post_init__(self):
        if self.shape <= 0 or self.rate <= 0:
            raise ValueError("Gamma parameters must be positive")

    @property
    def mean_hazard(self) -> float:
        return self.shape / self.rate

    def update(self, changes: int, exposure: float) -> "GammaRate":
        """changes = number of material changes observed over total exposure time."""
        if changes < 0 or exposure < 0:
            raise ValueError("counts and exposure must be nonnegative")
        return GammaRate(self.shape + changes, self.rate + exposure)

    def survival(self, age: float) -> float:
        """Posterior predictive P(no material change within `age`) = (b/(b+t))^a."""
        if age < 0:
            raise ValueError("age must be nonnegative")
        return (self.rate / (self.rate + age)) ** self.shape

    def survival_known_rate(self, age: float, hazard: float) -> float:
        return exp(-hazard * age)


def prob_current(prior: GammaRate, age_since_verification: float) -> float:
    """P(listing still current | verified `age` ago, no reports since).

    Time passing is NOT evidence of change; it only widens the predictive
    distribution. Repeated identical cached responses are not observations.
    """
    return prior.survival(age_since_verification)


def review_priority(prior: GammaRate, age: float, sensitivity: float, specificity: float,
                    utility_true: float = 1.0, utility_false: float = -3.0,
                    utility_abstain: float = 0.0, check_cost: float = 0.1,
                    repair_value: float = 0.0) -> float:
    """Net value of a human check for one listing under the declared utilities.

    = EVSI (value of the information for the show/abstain decision)
      + P(stale) * specificity * repair_value   (value of restoring coverage)
      - check_cost.

    `repair_value` is the declared worth of turning a stale published listing
    back into a current one (future shows, trust). With repair_value = 0 the
    priority is pure myopic EVSI and, once a listing is old enough that
    'abstain' is already the Bayes act, it stops being worth checking: old
    listings are starved. That is a property of the objective, not a bug in
    the mathematics; see math_checks D2/D5. The exact multi-step version is
    pc_core.pomdp.POMDP.value_dp with a longer horizon.
    """
    if repair_value < 0:
        raise ValueError("repair_value must be nonnegative")
    p = prob_current(prior, age)
    base = choose_binary_action(p, utility_true, utility_false, utility_abstain)[1]
    p_pos = p * sensitivity + (1 - p) * (1 - specificity)
    after = 0.0
    for positive, p_out in ((True, p_pos), (False, 1 - p_pos)):
        if p_out > 0:
            post = posterior_given_binary_test(p, positive, sensitivity, specificity)
            after += p_out * choose_binary_action(post, utility_true, utility_false, utility_abstain)[1]
    return after - base + (1 - p) * specificity * repair_value - check_cost


def brier_decomposition(probs: list[float], outcomes: list[int], bins: int = 10) -> dict[str, float]:
    """Murphy (1973) decomposition: Brier = reliability - resolution + uncertainty."""
    if len(probs) != len(outcomes) or not probs:
        raise ValueError("probs and outcomes must be same nonzero length")
    n = len(probs)
    base = sum(outcomes) / n
    brier = sum((p - y) ** 2 for p, y in zip(probs, outcomes)) / n
    groups: dict[int, list[int]] = {}
    for i, p in enumerate(probs):
        k = min(bins - 1, int(p * bins))
        groups.setdefault(k, []).append(i)
    rel = res = 0.0
    for idx in groups.values():
        nk = len(idx)
        pk = sum(probs[i] for i in idx) / nk
        ok = sum(outcomes[i] for i in idx) / nk
        rel += nk * (pk - ok) ** 2
        res += nk * (ok - base) ** 2
    unc = base * (1 - base)
    return {"brier": brier, "reliability": rel / n, "resolution": res / n,
            "uncertainty": unc, "identity_gap": brier - (rel / n - res / n + unc)}


def log_loss(probs: list[float], outcomes: list[int]) -> float:
    eps = 1e-12
    return -sum(y * log(max(p, eps)) + (1 - y) * log(max(1 - p, eps))
                for p, y in zip(probs, outcomes)) / len(probs)
