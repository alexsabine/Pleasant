"""Small discrete POMDP toy expected-free-energy policy scorer (standard form).

Not a generic FEP implementation; policy scores are meaningful only under the
specified state distribution, likelihood, and outcome preferences.
"""
from math import log
from pc_core.bayes import binary_entropy


def binary_risk_ambiguity(p_state_true: float, p_obs_pos_if_true: float,
                          p_obs_pos_if_false: float, p_prefer_pos: float) -> tuple[float,float,float]:
    """G = KL(q(o)||pref(o)) + E_s H[p(o|s)] for a one-step binary model.

    All probabilities must be strictly interior where preference logs used.
    """
    x = (p_state_true, p_obs_pos_if_true, p_obs_pos_if_false)
    if any(not 0 <= p <= 1 for p in x) or not 0 < p_prefer_pos < 1:
        raise ValueError("invalid probability")
    p_pos = p_state_true*p_obs_pos_if_true+(1-p_state_true)*p_obs_pos_if_false
    risk = 0.0
    if p_pos > 0: risk += p_pos*log(p_pos/p_prefer_pos)
    if p_pos < 1: risk += (1-p_pos)*log((1-p_pos)/(1-p_prefer_pos))
    ambiguity = (p_state_true*binary_entropy(p_obs_pos_if_true)
                 +(1-p_state_true)*binary_entropy(p_obs_pos_if_false))
    return (risk+ambiguity, risk, ambiguity)
