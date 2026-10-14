"""Correct conditional information geometry; not a universal CRR event mechanism."""
from math import asin, sqrt, isfinite


def fisher_rao_bernoulli(p: float, q: float) -> float:
    """Intrinsic Fisher-Rao geodesic distance along Bernoulli family in radians."""
    if not (0 <= p <= 1 and 0 <= q <= 1):
        raise ValueError("Bernoulli parameters must lie in [0,1]")
    return 2 * abs(asin(sqrt(p)) - asin(sqrt(q)))


def arc_from_probabilities(points: list[float], sigma: float = 1.0) -> float:
    """Cumulative discrete FR arc divided by independently fixed sigma.

    This is sample-dependent path length, not a continuous theorem or circle.
    """
    if sigma <= 0 or not isfinite(sigma):
        raise ValueError("sigma must be positive and finite")
    return sum(fisher_rao_bernoulli(a, b) for a, b in zip(points, points[1:])) / sigma


def surplus_on_bernoulli_path(points: list[float], sigma: float = 1.0) -> float:
    """Path - endpoint geodesic; does NOT implement canonical circular rotor."""
    if not points:
        return 0.0
    c = arc_from_probabilities(points, sigma)
    d = fisher_rao_bernoulli(points[0], points[-1]) / sigma
    return max(0.0, c - d)  # round-off


def significant_belief_change(before: float, after: float, threshold: float) -> bool:
    """Proposed monitor feature, threshold selected separately from evaluation."""
    if threshold < 0:
        raise ValueError("threshold nonnegative")
    return fisher_rao_bernoulli(before, after) > threshold


# ---- Public identities that tie Fisher-Rao to textbook quantities -----------
# Sources: Amari & Nagaoka, *Methods of Information Geometry* (2000), ch. 2-3;
# Cover & Thomas, *Elements of Information Theory* 2e, ch. 11 (KL, Fisher
# information as the Hessian of KL); Bhattacharyya (1943) angle.
from math import acos, log


def kl_bernoulli(p: float, q: float) -> float:
    """KL(Bern(p) || Bern(q)) in nats."""
    for x in (p, q):
        if not 0 <= x <= 1:
            raise ValueError("probability outside [0,1]")
    if q in (0.0, 1.0) and p != q:
        return float("inf")
    out = 0.0
    if p > 0:
        out += p * log(p / q)
    if p < 1:
        out += (1 - p) * log((1 - p) / (1 - q))
    return out


def fisher_information_bernoulli(p: float) -> float:
    """g(p) = 1 / (p (1-p)); the metric whose geodesic length is fisher_rao_bernoulli."""
    if not 0 < p < 1:
        raise ValueError("Fisher information of Bernoulli is defined on the open interval")
    return 1.0 / (p * (1 - p))


def fisher_rao_bernoulli_via_bhattacharyya(p: float, q: float) -> float:
    """Same distance as fisher_rao_bernoulli, written as 2 * Bhattacharyya angle.

    d = 2 * arccos( sqrt(p q) + sqrt((1-p)(1-q)) ). Two public formulas, one number.
    """
    if not (0 <= p <= 1 and 0 <= q <= 1):
        raise ValueError("Bernoulli parameters must lie in [0,1]")
    bc = sqrt(p * q) + sqrt((1 - p) * (1 - q))
    return 2 * acos(max(-1.0, min(1.0, bc)))
