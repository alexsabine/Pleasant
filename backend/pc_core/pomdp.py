"""Tiny exact discrete POMDP for the listing-freshness decision.

Everything here is textbook and publicly documented:
- Bayesian filtering (Kaelbling, Littman & Cassandra 1998, "Planning and acting
  in partially observable stochastic domains", Artificial Intelligence 101).
- Finite-horizon belief-space dynamic programming (same source).
- Variational free energy bound (Bishop, Pattern Recognition and Machine
  Learning 2006, ch. 10; Blei, Kucukelbir & McAuliffe 2017, JASA).
- Expected free energy, risk+ambiguity and epistemic+pragmatic forms
  (Parr, Pezzulo & Friston, *Active Inference*, MIT Press 2022, open access,
  ch. 2 and appendix; Smith, Friston & Whyte 2022 tutorial, PMC8956124).

The model is deliberately small so that every quantity can be enumerated
exactly; the point is auditability, not scale. Nothing here is a calibrated
claim about real Crescent City listings. Python stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from math import log

Belief = list[float]


def _normalise(v: list[float]) -> list[float]:
    s = sum(v)
    if s <= 0:
        raise ValueError("cannot normalise a zero vector")
    return [x / s for x in v]


def entropy(p: list[float]) -> float:
    return -sum(x * log(x) for x in p if x > 0)


def kl(p: list[float], q: list[float]) -> float:
    out = 0.0
    for a, b in zip(p, q):
        if a > 0:
            if b <= 0:
                raise ValueError("KL undefined: q has zero mass where p does not")
            out += a * log(a / b)
    return out


@dataclass
class POMDP:
    """Discrete POMDP with action-dependent transitions and observations.

    states: names; actions: names; observations: names.
    T[a][s][s']  transition probability.
    A[a][s'][o]  observation probability after action a lands in s'.
    R[a][s]      immediate reward for taking a in s.
    C[o]         prior preference over observations (for EFE), strictly > 0.
    """
    states: list[str]
    actions: list[str]
    observations: list[str]
    T: dict[str, list[list[float]]]
    A: dict[str, list[list[float]]]
    R: dict[str, list[float]]
    C: list[float] = field(default_factory=list)

    def __post_init__(self):
        n, m = len(self.states), len(self.observations)
        for a in self.actions:
            for row in self.T[a]:
                if abs(sum(row) - 1) > 1e-9 or len(row) != n:
                    raise ValueError(f"T[{a}] rows must be distributions over states")
            for row in self.A[a]:
                if abs(sum(row) - 1) > 1e-9 or len(row) != m:
                    raise ValueError(f"A[{a}] rows must be distributions over observations")
        if self.C and (len(self.C) != m or any(c <= 0 for c in self.C)):
            raise ValueError("C must be a strictly positive distribution over observations")

    # ---- Bayesian filtering -------------------------------------------------
    def predict(self, b: Belief, a: str) -> Belief:
        """Prior over next state after action a (no observation yet)."""
        n = len(self.states)
        return [sum(b[s] * self.T[a][s][s2] for s in range(n)) for s2 in range(n)]

    def obs_prob(self, b_pred: Belief, a: str, o: int) -> float:
        return sum(b_pred[s2] * self.A[a][s2][o] for s2 in range(len(self.states)))

    def update(self, b: Belief, a: str, o: int | None) -> Belief:
        """Posterior after action a and observation o.

        o=None means NO observation arrived: propagate only (missing-observation
        rule). This is the rule the Phoenix P14 run reduces to, and the one that
        'stale repeated bytes' must map onto.
        """
        bp = self.predict(b, a)
        if o is None:
            return bp
        post = [bp[s2] * self.A[a][s2][o] for s2 in range(len(self.states))]
        return _normalise(post)

    # ---- Expected utility (Bayesian decision theory) -------------------------
    def expected_reward(self, b: Belief, a: str) -> float:
        return sum(b[s] * self.R[a][s] for s in range(len(self.states)))

    def value_dp(self, b: Belief, horizon: int) -> tuple[float, str]:
        """Exact finite-horizon belief-space dynamic programming."""
        if horizon <= 0:
            return 0.0, ""
        best_v, best_a = -float("inf"), ""
        for a in self.actions:
            v = self.expected_reward(b, a)
            if horizon > 1:
                bp = self.predict(b, a)
                for o in range(len(self.observations)):
                    po = self.obs_prob(bp, a, o)
                    if po > 0:
                        v += po * self.value_dp(self.update(b, a, o), horizon - 1)[0]
            if v > best_v + 1e-12:
                best_v, best_a = v, a
        return best_v, best_a

    def value_of_policy_tree(self, b: Belief, tree) -> float:
        """Evaluate an explicit depth-k policy tree (a, {o: subtree})."""
        a, children = tree
        v = self.expected_reward(b, a)
        if children:
            bp = self.predict(b, a)
            for o, sub in children.items():
                po = self.obs_prob(bp, a, o)
                if po > 0:
                    v += po * self.value_of_policy_tree(self.update(b, a, o), sub)
        return v

    def all_policy_trees(self, depth: int):
        """Enumerate every deterministic policy tree of the given depth."""
        if depth == 1:
            for a in self.actions:
                yield (a, {})
            return
        subtrees = list(self.all_policy_trees(depth - 1))
        m = len(self.observations)
        for a in self.actions:
            for combo in product(subtrees, repeat=m):
                yield (a, dict(zip(range(m), combo)))

    # ---- Expected free energy (Active Inference) -----------------------------
    def efe(self, b: Belief, a: str) -> dict[str, float]:
        """One-step expected free energy in both standard decompositions.

        risk      = KL( q(o|a) || C(o) )
        ambiguity = E_{q(s'|a)} H[ p(o|s') ]
        epistemic = E_{q(o|a)} KL( q(s'|o,a) || q(s'|a) )   (expected info gain)
        pragmatic = E_{q(o|a)} log C(o)
        Identity: risk + ambiguity == -epistemic - pragmatic.
        """
        if not self.C:
            raise ValueError("preferences C required for EFE")
        bp = self.predict(b, a)
        m = len(self.observations)
        qo = [self.obs_prob(bp, a, o) for o in range(m)]
        risk = kl(qo, self.C)
        ambiguity = sum(bp[s2] * entropy(self.A[a][s2]) for s2 in range(len(self.states)))
        epistemic = 0.0
        for o in range(m):
            if qo[o] > 0:
                post = self.update(b, a, o)
                epistemic += qo[o] * kl(post, bp)
        pragmatic = sum(qo[o] * log(self.C[o]) for o in range(m) if qo[o] > 0)
        return {"G_risk_ambiguity": risk + ambiguity, "risk": risk, "ambiguity": ambiguity,
                "G_epistemic_pragmatic": -epistemic - pragmatic,
                "epistemic": epistemic, "pragmatic": pragmatic}

    def efe_policy(self, b: Belief) -> str:
        return min(self.actions, key=lambda a: self.efe(b, a)["G_risk_ambiguity"])


def variational_free_energy(q: list[float], prior: list[float], likelihood: list[float]) -> float:
    """F[q] = E_q[ log q(s) - log p(o,s) ] for a fixed observation.

    likelihood[s] = p(o|s). F >= -log p(o) with equality iff q == p(s|o).
    """
    joint = [prior[s] * likelihood[s] for s in range(len(prior))]
    f = 0.0
    for s in range(len(prior)):
        if q[s] > 0:
            if joint[s] <= 0:
                return float("inf")
            f += q[s] * (log(q[s]) - log(joint[s]))
    return f


def exact_posterior(prior: list[float], likelihood: list[float]) -> list[float]:
    return _normalise([prior[s] * likelihood[s] for s in range(len(prior))])


def softmax_policy(scores: dict[str, float], precision: float) -> dict[str, float]:
    """Boltzmann policy over NEGATIVE EFE (or utility); precision is a published knob."""
    if precision < 0:
        raise ValueError("precision must be nonnegative")
    from math import exp
    mx = max(scores.values())
    w = {a: exp(precision * (s - mx)) for a, s in scores.items()}
    z = sum(w.values())
    return {a: v / z for a, v in w.items()}


def freshness_pomdp(hazard: float = 0.10, sensitivity: float = 0.9, specificity: float = 0.9,
                    show_true: float = 1.0, show_false: float = -3.0,
                    verify_cost: float = 0.3, prefer_current_obs: float = 0.85) -> POMDP:
    """The declared model for 'is this listing still current?'.

    States: current, stale. Actions: show, abstain, verify.
    verify asks a human editor; if the editor finds the listing stale it is
    corrected, so verify can move stale -> current. show/abstain do not act on
    the world except through the staleness hazard.
    Observations: pos (looks current), neg (looks stale), none (no check made).
    """
    T_noop = [[1 - hazard, hazard], [0.0, 1.0]]
    # verify: current may still go stale during the step; stale gets corrected
    # with probability equal to the editor's sensitivity at spotting staleness
    # (specificity applies to the "stale" detection here, symmetric toy choice).
    T_verify = [[1 - hazard, hazard], [specificity, 1 - specificity]]
    A_noop = [[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]
    A_verify = [[sensitivity, 1 - sensitivity, 0.0], [1 - specificity, specificity, 0.0]]
    # Preferences over observations: we prefer to see "pos"; "none" is neutral.
    C = _normalise([prefer_current_obs, (1 - prefer_current_obs) / 2, (1 - prefer_current_obs) / 2])
    return POMDP(states=["current", "stale"], actions=["show", "abstain", "verify"],
                 observations=["pos", "neg", "none"],
                 T={"show": T_noop, "abstain": T_noop, "verify": T_verify},
                 A={"show": A_noop, "abstain": A_noop, "verify": A_verify},
                 R={"show": [show_true, show_false], "abstain": [0.0, 0.0],
                    "verify": [-verify_cost, -verify_cost]}, C=C)


# ---- Scalar Kalman filter: the missing-observation rule ----------------------
# Kalman (1960); any filtering textbook (e.g. Särkkä, *Bayesian Filtering and
# Smoothing*, CUP 2013, open access, ch. 4). A random walk x_{t+1} = x_t + w,
# w ~ N(0, Q), observed y = x + v, v ~ N(0, R).
def kalman_predict(mean: float, var: float, q: float) -> tuple[float, float]:
    if var < 0 or q < 0:
        raise ValueError("variances must be nonnegative")
    return mean, var + q


def kalman_update(mean: float, var: float, y: float, r: float) -> tuple[float, float]:
    if var < 0 or r <= 0:
        raise ValueError("prior variance nonnegative, observation noise positive")
    k = var / (var + r)
    return mean + k * (y - mean), (1 - k) * var


def propagate_with_gaps(mean: float, var: float, q: float, r: float,
                        stream: list[tuple[float | None, str | None]]) -> tuple[float, float, int]:
    """Run the filter over (value, etag) pairs.

    value None  -> no observation this step: predict only.
    Repeated etag -> identical bytes re-delivered: treated as NO new observation.
    Returns (mean, var, n_real_updates).
    """
    seen: set[str] = set()
    n = 0
    for y, etag in stream:
        mean, var = kalman_predict(mean, var, q)
        if y is None or (etag is not None and etag in seen):
            continue
        if etag is not None:
            seen.add(etag)
        mean, var = kalman_update(mean, var, y, r)
        n += 1
    return mean, var, n
