"""Constrained Bayesian decisions, compact and auditable. Python stdlib only.

These functions demonstrate decision mathematics; they are NOT calibrated family
resource probabilities. Permission checks live in the authenticated backend.
"""
from dataclasses import dataclass
from math import log


def binary_entropy(p: float) -> float:
    if not 0 <= p <= 1:
        raise ValueError("probability outside [0,1]")
    if p == 0 or p == 1:
        return 0.0
    return -(p * log(p) + (1 - p) * log(1 - p))


@dataclass(frozen=True)
class BetaEvidence:
    alpha: float = 1.0
    beta: float = 1.0

    def __post_init__(self):
        if self.alpha <= 0 or self.beta <= 0:
            raise ValueError("Beta parameters must be positive")

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def update(self, successes=0, failures=0) -> "BetaEvidence":
        if successes < 0 or failures < 0:
            raise ValueError("counts must be nonnegative")
        return BetaEvidence(self.alpha + successes, self.beta + failures)


def posterior_given_binary_test(p_true: float, observation_positive: bool,
                                sensitivity: float, specificity: float) -> float:
    """P(true | test result) for a one-off conditionally independent test.

    Do not treat repeated cached/same-origin messages as independent tests.
    """
    for p in (p_true, sensitivity, specificity):
        if not 0 <= p <= 1:
            raise ValueError("probability outside [0,1]")
    if observation_positive:
        numerator = p_true * sensitivity
        denom = numerator + (1 - p_true) * (1 - specificity)
    else:
        numerator = p_true * (1 - sensitivity)
        denom = numerator + (1 - p_true) * specificity
    if denom == 0:
        raise ValueError("impossible observation under specified model")
    return numerator / denom


def binary_test_information_gain(p_true, sensitivity, specificity) -> float:
    """Expected mutual information I(S;O), measured in nats, for a binary test."""
    p_pos = p_true * sensitivity + (1 - p_true) * (1 - specificity)
    h_before = binary_entropy(p_true)
    h_after = 0
    for is_pos, p_out in ((True, p_pos), (False, 1 - p_pos)):
        if p_out:
            p_post = posterior_given_binary_test(p_true, is_pos, sensitivity, specificity)
            h_after += p_out * binary_entropy(p_post)
    return max(0.0, h_before - h_after)  # protect floating round-off only


@dataclass(frozen=True)
class Resource:
    identifier: str
    name: str
    min_age: int
    max_age: int
    cost_usd: float | None
    accessibility: str  # verified_yes / verified_no / unknown
    verified: bool
    prob_current_model: float | None = None  # illustrative calibrated probability


@dataclass(frozen=True)
class FamilyQuery:
    child_age: int
    max_cost_usd: float | None
    requires_accessibility: bool = False
    max_results: int = 3


def eligible_resources(items: list[Resource], query: FamilyQuery) -> list[Resource]:
    """Hard filters: no inferred accessible status, no guessed prices."""
    if query.max_results < 0:
        raise ValueError("max_results must be >= 0")
    matches = []
    for it in items:
        if not it.verified or not (it.min_age <= query.child_age <= it.max_age):
            continue
        if query.max_cost_usd is not None and (it.cost_usd is None or it.cost_usd > query.max_cost_usd):
            continue
        if query.requires_accessibility and it.accessibility != "verified_yes":
            continue
        matches.append(it)
    return sorted(matches, key=lambda it: (-float(it.prob_current_model or 0.0), it.name))[:query.max_results]


def choose_binary_action(p_true: float, utility_show_if_true: float = 1.0,
                         utility_show_if_false: float = -3.0,
                         utility_abstain: float = 0.0) -> tuple[str, float]:
    """Bayes act for two actions, CONDITIONAL on the caller's utilities/prior."""
    if not 0 <= p_true <= 1:
        raise ValueError("probability outside [0,1]")
    u_show = p_true * utility_show_if_true + (1 - p_true) * utility_show_if_false
    return ("show", u_show) if u_show > utility_abstain else ("abstain", utility_abstain)


def expected_value_of_sample_information(p_true, sensitivity, specificity,
                                         utility_true=1.0, utility_false=-3.0,
                                         utility_abstain=0.0, verification_cost=0.1):
    """Net EVSI for binary check, assuming user-consented verification is allowed."""
    base = choose_binary_action(p_true, utility_true, utility_false, utility_abstain)[1]
    p_pos = p_true * sensitivity + (1 - p_true) * (1 - specificity)
    after = 0.0
    for positive, p_out in ((True, p_pos), (False, 1-p_pos)):
        if p_out > 0:
            posterior = posterior_given_binary_test(p_true, positive, sensitivity, specificity)
            after += p_out * choose_binary_action(posterior, utility_true, utility_false, utility_abstain)[1]
    return after - base - verification_cost
