"""Executable mathematical checks for Pleasant Crescent.

Run from repo root:
    PYTHONPATH=backend python backend/examples/math_checks.py [--report research/05_math_check_report.md]

Each check states (a) the public source of the mathematics, (b) what is being
verified numerically, (c) PASS/FAIL. Every number printed is from a declared
synthetic model. None is a measurement of real Crescent City listings.
Paradigms: [BDT] Bayesian decision theory, [AIF] Active Inference / FEP,
[PHX] Phoenix / CRR information geometry, [MEM] memory + governance techniques,
[H3] derived spatial index.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from math import asin, exp, isclose, log, sqrt, cos, sin, atan2, radians

from pc_core.bayes import (BetaEvidence, FamilyQuery, Resource, choose_binary_action,
                           eligible_resources, expected_value_of_sample_information,
                           posterior_given_binary_test)
from pc_core.geometry import (fisher_information_bernoulli, fisher_rao_bernoulli,
                              fisher_rao_bernoulli_via_bhattacharyya, kl_bernoulli,
                              surplus_on_bernoulli_path, arc_from_probabilities)
from pc_core.history import exponential_working_summary
from pc_core.pomdp import (exact_posterior, freshness_pomdp, kalman_predict, kalman_update,
                           propagate_with_gaps, softmax_policy, variational_free_energy)
from pc_core.freshness import GammaRate, brier_decomposition, log_loss, prob_current, review_priority
from pc_core.audit_chain import AuditChain
from pc_core.closure import (Claim, PublishedFact, check_operational_closure,
                             simulate_verification_loop)

RESULTS: list[tuple[str, str, bool, str]] = []  # (paradigm, name, passed, detail)


def check(paradigm: str, name: str, passed: bool, detail: str) -> None:
    RESULTS.append((paradigm, name, bool(passed), detail))
    print(f"[{paradigm}] {'PASS' if passed else 'FAIL'}  {name}\n        {detail}")


# =============================================================================
# [BDT] Bayesian decision theory
# =============================================================================
def bdt_checks() -> None:
    m = freshness_pomdp()
    # A1: exact DP value equals best over ALL enumerated depth-2 policy trees
    worst_gap, n_trees, n_beliefs = 0.0, 0, 0
    agree = True
    for p in [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]:
        b = [p, 1 - p]
        v_dp, a_dp = m.value_dp(b, 2)
        best = max(m.all_policy_trees(2), key=lambda t: m.value_of_policy_tree(b, t))
        v_best = m.value_of_policy_tree(b, best)
        n_trees = sum(1 for _ in m.all_policy_trees(2))
        worst_gap = max(worst_gap, abs(v_dp - v_best))
        agree &= best[0] == a_dp or isclose(v_dp, v_best, abs_tol=1e-12)
        n_beliefs += 1
    check("BDT", "Bayes act = best of all enumerated policy trees (exact DP, horizon 2)",
          worst_gap < 1e-12 and agree,
          f"{n_beliefs} beliefs x {n_trees} policy trees; max |V_dp - V_best| = {worst_gap:.2e}. "
          "Optimality holds FOR THE DECLARED model (T, A, R); that is the whole claim.")

    # A2: value of information is nonnegative (Jensen); zero for an uninformative test; EVPI >= EVSI
    viol = 0
    for p in [i / 20 for i in range(1, 20)]:
        for sens in [0.5, 0.7, 0.9, 1.0]:
            for spec in [0.5, 0.7, 0.9, 1.0]:
                evsi = expected_value_of_sample_information(p, sens, spec, verification_cost=0.0)
                # EVPI: perfect information
                evpi = p * max(1.0, 0.0) + (1 - p) * max(-3.0, 0.0) - choose_binary_action(p)[1]
                if evsi < -1e-12 or evsi > evpi + 1e-12:
                    viol += 1
    e_uninf = expected_value_of_sample_information(0.5, 0.5, 0.5, verification_cost=0.0)
    check("BDT", "0 <= EVSI <= EVPI on a grid; uninformative test has EVSI = 0",
          viol == 0 and abs(e_uninf) < 1e-12, f"violations={viol}; EVSI(sens=spec=0.5)={e_uninf:.1e}")

    # A3: conjugate Beta: sequential == batch; order-invariant; duplicates inflate confidence
    seq = BetaEvidence().update(2, 0).update(1, 1).update(0, 2)
    batch = BetaEvidence().update(3, 3)
    one_obs = BetaEvidence(1, 1).update(1, 0)
    triple_dup = BetaEvidence(1, 1).update(3, 0)  # WRONG: same bytes counted 3x
    check("BDT", "Beta conjugacy: sequential == batch; duplicate bytes must not be re-counted",
          seq == batch and one_obs.mean < triple_dup.mean,
          f"seq={seq} batch={batch}; mean after 1 real obs={one_obs.mean:.3f}, "
          f"if the same ETag is counted 3x={triple_dup.mean:.3f} (overconfident)")

    # A4: proper scoring: truthful probability minimises expected log loss and Brier
    rng = random.Random(1)
    p_true = 0.3
    ys = [1 if rng.random() < p_true else 0 for _ in range(20000)]
    losses = {q: log_loss([q] * len(ys), ys) for q in [0.1, 0.2, 0.3, 0.4, 0.5, 0.7]}
    best_q = min(losses, key=losses.get)
    levels = [(i + 0.5) / 10 for i in range(10)]  # discrete forecast levels (one per bin)
    probs = [rng.choice(levels) for _ in range(5000)]
    outs = [1 if rng.random() < p else 0 for p in probs]
    bd = brier_decomposition(probs, outs)
    cont = brier_decomposition([rng.random() for _ in range(5000)], outs)
    check("BDT", "Proper scoring rules: truthful p minimises log loss; Murphy Brier decomposition exact for binned forecasts",
          best_q == 0.3 and abs(bd["identity_gap"]) < 1e-12 and abs(cont["identity_gap"]) > 1e-6,
          f"argmin_q logloss = {best_q}; Brier={bd['brier']:.4f} = rel {bd['reliability']:.4f} "
          f"- res {bd['resolution']:.4f} + unc {bd['uncertainty']:.4f} (gap {bd['identity_gap']:.1e}). "
          f"With continuous forecasts the 3-term identity leaves a within-bin residual ({cont['identity_gap']:.1e}): "
          "publish calibration with the binning stated (Stephenson, Coelho & Jolliffe 2008).")

    # A5: hard constraints are lexicographic: no score can promote an 'unknown' accessibility item
    items = [Resource("x", "Popular unknown access", 0, 18, 0, "unknown", True, 0.999),
             Resource("y", "Verified accessible", 0, 18, 0, "verified_yes", True, 0.5)]
    got = [r.identifier for r in eligible_resources(items, FamilyQuery(6, 10, requires_accessibility=True))]
    check("BDT", "Safety/accessibility are hard constraints, not weighted scores",
          got == ["y"], f"eligible under requires_accessibility: {got} (popular 'unknown' excluded)")


# =============================================================================
# [AIF] Active Inference / Free Energy Principle
# =============================================================================
def aif_checks() -> None:
    rng = random.Random(3)
    # B1: variational free energy bounds -log p(o); minimised exactly at the Bayesian posterior
    prior = [0.6, 0.4]
    lik = [0.9, 0.2]
    post = exact_posterior(prior, lik)
    neg_log_evidence = -log(sum(p * l for p, l in zip(prior, lik)))
    f_post = variational_free_energy(post, prior, lik)
    worst = 0.0
    for _ in range(2000):
        q0 = rng.random()
        f = variational_free_energy([q0, 1 - q0], prior, lik)
        worst = min(worst, f - neg_log_evidence)
    check("AIF", "Variational free energy F[q] >= -log p(o), equality iff q = exact posterior",
          worst >= -1e-12 and abs(f_post - neg_log_evidence) < 1e-12,
          f"min over 2000 random q of (F + log p(o)) = {worst:.1e}; F[posterior] - (-log p(o)) = "
          f"{f_post - neg_log_evidence:.1e}. 'Bayes-optimal perception' = exact inference.")

    # B2: EFE decomposition identity risk+ambiguity == -(epistemic) - (pragmatic)
    m = freshness_pomdp()
    gap = 0.0
    for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
        for a in m.actions:
            g = m.efe([p, 1 - p], a)
            gap = max(gap, abs(g["G_risk_ambiguity"] - g["G_epistemic_pragmatic"]))
    g = m.efe([0.5, 0.5], "verify")
    check("AIF", "EFE identity: risk + ambiguity == -epistemic value - pragmatic value",
          gap < 1e-12,
          f"max gap over beliefs x actions = {gap:.1e}; e.g. verify@0.5: risk={g['risk']:.3f} "
          f"ambiguity={g['ambiguity']:.3f} epistemic={g['epistemic']:.3f} pragmatic={g['pragmatic']:.3f}")

    # B3: EFE is NOT the same criterion as expected utility; multi-step EU with VOI recovers
    # the information-seeking choice. (Honesty check on 'Bayes-optimal in all paradigms'.)
    diverge, recover = [], []
    for p in [i / 20 for i in range(1, 20)]:
        b = [p, 1 - p]
        a_efe = m.efe_policy(b)
        a_eu1 = m.value_dp(b, 1)[1]
        a_eu2 = m.value_dp(b, 2)[1]
        if a_efe != a_eu1:
            diverge.append(round(p, 2))
        if a_efe == "verify" and a_eu2 == "verify":
            recover.append(round(p, 2))
    check("AIF", "EFE argmin differs from 1-step expected utility (so it is a different criterion); "
                 "2-step EU with value-of-information also chooses 'verify' where EFE does",
          len(diverge) > 0 and len(recover) > 0,
          f"beliefs where EFE != myopic EU: {diverge}; beliefs where both EFE and 2-step EU verify: {recover}. "
          "Conclusion: epistemic value is already inside Bayesian decision theory via VOI; EFE is an "
          "alternative one-step scorer with an explicit information term.")

    # B4: missing observation = propagate only; stale repeats must not shrink variance
    q, r = 0.5, 1.0
    mean, var = 0.0, 1.0
    _, var3 = kalman_predict(mean, var, q)
    _, var3 = kalman_predict(_, var3, q)
    _, var3 = kalman_predict(_, var3, q)
    stream_bad = [(2.0, "etag-A"), (2.0, "etag-A"), (2.0, "etag-A")]
    m_ok, v_ok, n_ok = propagate_with_gaps(0.0, 1.0, q, r, stream_bad)
    # naive: treat each repeat as a fresh observation
    mn, vn = 0.0, 1.0
    for y, _e in stream_bad:
        mn, vn = kalman_predict(mn, vn, q)
        mn, vn = kalman_update(mn, vn, y, r)
    check("AIF", "Missing-observation Kalman rule: variance grows by Q per gap; repeated ETag counts once",
          isclose(var3, 1.0 + 3 * q) and n_ok == 1 and v_ok > vn,
          f"3 gaps: var {var3:.2f} = 1 + 3Q; same bytes x3 -> real updates={n_ok}, var={v_ok:.3f}; "
          f"naive re-counting var={vn:.3f} (falsely confident). This is the P14 'stale world' reduction.")

    # B5: precision is an explicit published knob; gamma -> inf recovers argmin EFE
    scores = {a: -m.efe([0.5, 0.5], a)["G_risk_ambiguity"] for a in m.actions}
    soft = softmax_policy(scores, 1.0)
    hard = softmax_policy(scores, 200.0)
    best = max(scores, key=scores.get)
    check("AIF", "Policy precision gamma is explicit; gamma->inf gives deterministic argmin-EFE",
          hard[best] > 0.999 and 0 < soft[best] < 1,
          f"gamma=1: {({k: round(v, 3) for k, v in soft.items()})}; gamma=200: best={best} p={hard[best]:.4f}")


# =============================================================================
# [PHX] Phoenix / CRR information geometry
# =============================================================================
def phx_checks() -> None:
    rng = random.Random(11)
    # C1: closed form == numerical geodesic integral == Bhattacharyya form; metric axioms
    try:
        from scipy.integrate import quad
        have_scipy = True
    except ImportError:  # pragma: no cover
        have_scipy = False
    max_gap_int, max_gap_bh, tri_viol = 0.0, 0.0, 0
    for _ in range(300):
        p, q, r = (rng.uniform(0.01, 0.99) for _ in range(3))
        d = fisher_rao_bernoulli(p, q)
        if have_scipy:
            num, _err = quad(lambda x: sqrt(fisher_information_bernoulli(x)), min(p, q), max(p, q))
            max_gap_int = max(max_gap_int, abs(num - d))
        max_gap_bh = max(max_gap_bh, abs(fisher_rao_bernoulli_via_bhattacharyya(p, q) - d))
        if d > fisher_rao_bernoulli(p, r) + fisher_rao_bernoulli(r, q) + 1e-12:
            tri_viol += 1
    check("PHX", "Fisher-Rao(Bernoulli): closed form == integral of sqrt(g) == 2*Bhattacharyya angle; "
                 "symmetric; triangle inequality",
          max_gap_int < 1e-8 and max_gap_bh < 1e-9 and tri_viol == 0,
          f"max |integral - closed| = {max_gap_int:.1e} (scipy={'yes' if have_scipy else 'no'}); "
          f"max |Bhattacharyya - closed| = {max_gap_bh:.1e}; triangle violations = {tri_viol}/300")

    # C2: Fisher information = Hessian of KL at q=p; d_FR^2 ~ 2 KL for small moves
    p = 0.3
    h = 1e-4
    hess = (kl_bernoulli(p, p + h) - 2 * kl_bernoulli(p, p) + kl_bernoulli(p, p - h)) / h ** 2
    ratios = []
    for delta in [0.1, 0.03, 0.01, 0.003]:
        ratios.append(fisher_rao_bernoulli(p, p + delta) ** 2 / (2 * kl_bernoulli(p, p + delta)))
    check("PHX", "Fisher information g(p) = Hessian of KL at p; d_FR^2 -> 2 KL as the move shrinks",
          abs(hess - fisher_information_bernoulli(p)) / fisher_information_bernoulli(p) < 1e-4
          and abs(ratios[-1] - 1) < 2e-3,
          f"finite-difference Hessian {hess:.4f} vs g(0.3)={fisher_information_bernoulli(p):.4f}; "
          f"d^2/(2KL) for delta=.1,.03,.01,.003: {[round(x, 4) for x in ratios]} -> 1. "
          "So the CRR distance is the standard local KL geometry; nothing exotic is needed to explain it.")

    # C3: path surplus S = C - d >= 0 always; out-and-back has S = C
    viol = 0
    for _ in range(300):
        pts = [rng.uniform(0.02, 0.98) for _ in range(rng.randint(2, 7))]
        if surplus_on_bernoulli_path(pts) < -1e-12:
            viol += 1
    oab = [0.2, 0.8, 0.2]
    check("PHX", "Path surplus S = path length - geodesic >= 0 (triangle inequality); out-and-back S = C",
          viol == 0 and isclose(surplus_on_bernoulli_path(oab), arc_from_probabilities(oab)),
          f"violations={viol}/300; S([.2,.8,.2]) = {surplus_on_bernoulli_path(oab):.4f} = C. "
          "S carries no information beyond (C, d); it is not a new observable.")

    # C4: EMA working memory is lossy: many histories, one state; event log is not
    q = 0.5
    target = exponential_working_summary([0.0, 1.0], q)
    same = []
    for _ in range(5000):
        a = rng.random()
        # solve for b such that q*(q*0 + (1-q)*a) + (1-q)*b == target
        b = (target - q * (1 - q) * a) / (1 - q)
        if 0 <= b <= 1 and isclose(exponential_working_summary([a, b], q), target):
            same.append((round(a, 3), round(b, 3)))
    check("PHX", "Exponential working summary is many-to-one (lossy); cannot serve as the archive",
          len(same) > 100, f"{len(same)} distinct 2-event histories collapse to the same state {target:.3f}; "
                           f"examples {same[:3]}. Keep the event log; derive summaries from it.")

    # C5: two clocks: chronological age, material-change count N, belief path C diverge
    histories = {
        "3 identical re-verifications": [0.9, 0.9, 0.9, 0.9],
        "one material change": [0.9, 0.9, 0.2, 0.2],
        "flip-flopping reports": [0.9, 0.2, 0.9, 0.2],
    }
    rows = []
    for name, beliefs in histories.items():
        n_changes = sum(1 for a, b in zip(beliefs, beliefs[1:]) if abs(a - b) > 0.3)
        rows.append((name, len(beliefs) - 1, n_changes, round(arc_from_probabilities(beliefs), 3)))
    distinct = len({(r[1], r[2], r[3]) for r in rows}) == 3 and rows[0][3] == 0.0 and rows[2][2] > rows[1][2]
    check("PHX", "Two clocks: elapsed steps, material-change count N and belief path length C are different",
          distinct, "; ".join(f"{n}: steps={s}, N={c}, C={cc}" for n, s, c, cc in rows))

    # C6: no universal Fisher-distance threshold: cost-optimal threshold moves with base rate and cost
    def best_threshold(base_rate: float, miss_cost: float, n: int = 4000) -> float:
        rr = random.Random(int(base_rate * 1000) + int(miss_cost))
        samples = []
        for _ in range(n):
            changed = rr.random() < base_rate
            before = rr.uniform(0.6, 0.95)
            after = rr.uniform(0.05, 0.5) if changed else max(0.01, min(0.99, before + rr.gauss(0, 0.08)))
            samples.append((changed, fisher_rao_bernoulli(before, after)))
        best_t, best_c = None, float("inf")
        for t in [i / 50 for i in range(0, 80)]:
            cost = sum((miss_cost if (ch and d <= t) else 0) + (1.0 if (not ch and d > t) else 0)
                       for ch, d in samples)
            if cost < best_c:
                best_t, best_c = t, cost
        return best_t
    t_a = best_threshold(0.05, 2.0)
    t_b = best_threshold(0.40, 2.0)
    t_c = best_threshold(0.05, 20.0)
    check("PHX", "Fisher-distance change trigger has NO universal threshold: optimum depends on base rate and costs",
          not (t_a == t_b == t_c),
          f"cost-optimal threshold: base 5%/miss x2 -> {t_a}; base 40%/miss x2 -> {t_b}; base 5%/miss x20 -> {t_c}. "
          "Thresholds must be fitted on validation data and published, per phoenix_selected/03.")


# =============================================================================
# [MEM] memory architecture, governance and the agent interface
# =============================================================================
def mem_checks() -> None:
    rng = random.Random(5)
    # D1: Gamma-exponential survival: closed form == Monte Carlo; age widens, never 'confirms'
    prior = GammaRate(2.0, 200.0)
    age = 90.0
    closed = prior.survival(age)
    mc = 0
    N = 200000
    for _ in range(N):
        lam = rng.gammavariate(prior.shape, 1 / prior.rate)
        if rng.expovariate(lam) > age:
            mc += 1
    mc_p = mc / N
    post = prior.update(changes=0, exposure=365.0)  # a year of quiet exposure
    check("MEM", "Freshness survival P(still current | age) closed form == Monte Carlo; quiet exposure lowers hazard",
          abs(closed - mc_p) < 0.005 and post.mean_hazard < prior.mean_hazard and prob_current(prior, 0) == 1.0,
          f"P(current|90d) closed={closed:.4f} MC={mc_p:.4f}; mean hazard prior={prior.mean_hazard:.4f} "
          f"-> after 365d no change {post.mean_hazard:.4f}; P(current|age 0)=1.")

    # D2: review priority (EVSI) is model-driven, not a fixed schedule
    ages = list(range(0, 1500))
    pr = [review_priority(prior, a, 0.95, 0.95) for a in ages]
    hot = GammaRate(2.0, 20.0)  # a volatile category (events) has 10x the hazard
    pr_hot = [review_priority(hot, a, 0.95, 0.95) for a in ages]
    peak, peak_hot = ages[pr.index(max(pr))], ages[pr_hot.index(max(pr_hot))]
    pr_rep = [review_priority(prior, a, 0.95, 0.95, repair_value=1.0) for a in ages]
    check("MEM", "Review priority (pure EVSI): zero at age 0, peaks, then falls once 'abstain' is already the Bayes act; "
                 "volatile categories peak at a smaller age; adding repair value removes the starvation of old listings",
          pr[0] < 0 and max(pr) > 0 and pr[-1] < 0 and peak_hot < peak and pr_rep[-1] > 0,
          f"stable: EVSI(0d)={pr[0]:.2f}, peak {max(pr):.2f} at {peak} d, EVSI(1499d)={pr[-1]:.2f}; "
          f"volatile: peak {max(pr_hot):.2f} at {peak_hot} d; with repair_value=1: priority(1499d)={pr_rep[-1]:.2f} > 0. "
          "Finding: the objective must value restored coverage or the Bayes-optimal policy lets old listings rot.")

    # D3: hash-chained audit log detects tampering; lawful redaction keeps the chain valid
    chain = AuditChain()
    for i in range(5):
        chain.append({"request_id": f"r{i}", "retrieval_sources": ["published"], "source_versions": {"v": i},
                      "policy_version": "p1", "assumptions": [], "confidence_type": "model",
                      "action_proposed": "show", "user_approval": None, "action_result": "ok",
                      "timestamp": f"2026-10-14T00:0{i}:00Z", "limitations": "synthetic"},
                     require_decision_fields=True)
    ok0, _ = chain.verify()
    chain.entries[2].payload["action_result"] = "tampered"
    ok1, bad = chain.verify()
    chain.entries[2].payload["action_result"] = "ok"
    chain.redact(1, "lawful deletion request")
    ok2, _ = chain.verify()
    try:
        chain.append({"request_id": "x"}, require_decision_fields=True)
        strict = False
    except ValueError:
        strict = True
    check("MEM", "Hash-chained decision log: valid -> tamper detected at the right index -> redaction keeps chain valid; "
                 "decision records must carry all 11 provenance fields",
          ok0 and not ok1 and bad == 2 and ok2 and strict,
          f"verify fresh={ok0}; after edit={ok1} at index {bad}; after redaction={ok2}; incomplete record rejected={strict}")

    # D4: operational closure of publication
    chain2 = AuditChain()
    h_ok = chain2.append({"event": "verify", "claim": "c1", "by": "editor"}).hash
    claims = {
        "c1": Claim("c1", "park-1", "opening_hours", "reported", "editor", h_ok),
        "c2": Claim("c2", "park-1", "accessibility", "generated", "editor", h_ok),   # LLM text
        "c3": Claim("c3", "park-2", "cost", "observed", None, None),                 # unverified
        "c4": Claim("c4", "park-3", "cost", "observed", "editor", "deadbeef"),       # not in audit
    }
    facts_ok = [PublishedFact("park-1", "opening_hours", ("c1",))]
    facts_bad = facts_ok + [PublishedFact("park-1", "accessibility", ("c2",)),
                            PublishedFact("park-2", "cost", ("c3",)),
                            PublishedFact("park-3", "cost", ("c4",)),
                            PublishedFact("park-4", "name", ())]
    rep_ok = check_operational_closure(facts_ok, claims, {e.hash for e in chain2.entries})
    rep_bad = check_operational_closure(facts_bad, claims, {e.hash for e in chain2.entries})
    check("MEM", "Operational closure: every published fact traces to a verified observed/reported claim in the audit chain; "
                 "generated, unverified, un-audited and unsupported facts are rejected",
          rep_ok.ok and not rep_bad.ok and len(rep_bad.violations) == 4,
          f"clean projection ok={rep_ok.ok}; 4 bad facts -> {len(rep_bad.violations)} violations: "
          + " | ".join(v.split(': ')[1] for v in rep_bad.violations))

    # D5: homeostasis: the verification loop bounds staleness; without it staleness -> 1
    none = simulate_verification_loop(policy="none", checks_per_day=0)
    oldest = simulate_verification_loop(policy="oldest", checks_per_day=4)
    evsi = simulate_verification_loop(policy="evsi", checks_per_day=4)
    evsi_r = simulate_verification_loop(policy="evsi_repair", checks_per_day=4)
    tail = lambda r: sum(r.stale_fraction_over_time[-90:]) / 90
    check("MEM", "Homeostasis under the declared model: a bounded review budget keeps the stale fraction bounded; "
                 "no loop -> staleness drifts toward 1; pure myopic EVSI starves old listings (synthetic)",
          tail(none) > 0.9 and tail(oldest) < 0.3 and tail(evsi_r) < 0.3 and tail(evsi) > tail(oldest),
          f"mean stale fraction, last 90 of 365 days: no loop={tail(none):.3f}; oldest-first (4 checks/day of 200)="
          f"{tail(oldest):.3f}; pure EVSI={tail(evsi):.3f} (worse: it stops checking listings it has given up on); "
          f"EVSI + repair value 3={tail(evsi_r):.3f} (= oldest-first: with ONE shared hazard, oldest-first IS the Bayes "
          "policy; EVSI only adds value when categories have different hazards). repair value 1 leaves a hump at 31 d "
          "and starves middle-aged listings (0.445). No policy is claimed best for real data: that is Study A in research/03.")


# =============================================================================
# [H3] derived spatial index
# =============================================================================
def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(a), sqrt(1 - a))


def h3_checks() -> None:
    try:
        from pc_core import h3_index as hx
        import h3  # noqa: F401
    except Exception as e:  # pragma: no cover
        check("H3", "h3 package available", False, f"optional dependency missing: {e}")
        return
    rng = random.Random(2)
    lat0, lon0 = 41.755, -124.20  # approximate public centre of Crescent City (demo only)
    # E1: cell areas at each resolution; neighbour count 1+3k(k+1); parent containment
    areas = {r: round(hx.cell_area_km2(hx.cell_for(lat0, lon0, r)), 3) for r in range(5, 11)}
    c8 = hx.cell_for(lat0, lon0, 8)
    import h3 as _h3
    ring_ok = all(len(_h3.grid_disk(c8, k)) == 1 + 3 * k * (k + 1) for k in range(0, 4))
    parent_ok = hx.parent(c8, 6) == hx.cell_for(lat0, lon0, 6)
    check("H3", "Cell areas by resolution at Crescent City; k-ring size 1+3k(k+1); parent containment",
          ring_ok and parent_ok and areas[7] > areas[8] > areas[9],
          f"km^2 by res: {areas}; k-ring sizes ok={ring_ok}; parent(res8)->res6 matches={parent_ok}")

    # E2: county-scale sizing: cells covering an APPROXIMATE Del Norte bounding polygon (not a legal boundary)
    bbox = [(41.38, -124.42), (41.38, -123.52), (42.01, -123.52), (42.01, -124.42)]
    sizes = {r: len(hx.cells_covering(bbox, r)) for r in (5, 6, 7, 8, 9)}
    check("H3", "Approximate county bbox coverage sizes (storage/aggregate planning only; bbox is NOT the county boundary)",
          sizes[8] > sizes[7] > sizes[6],
          f"cells by res: {sizes} (res 8 ~ {sizes[8]} cells is trivial for PostGIS or a JSON cache)")

    # E3: grid distance is not a geographic distance, let alone a travel time
    pts = [(lat0 + rng.uniform(-0.15, 0.15), lon0 + rng.uniform(-0.2, 0.2)) for _ in range(400)]
    cells = [hx.cell_for(a, b, 8) for a, b in pts]
    by_gd: dict[int, list[float]] = {1: [], 2: [], 3: []}
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            gd = hx.grid_distance(cells[i], cells[j])
            if gd in by_gd:
                by_gd[gd].append(_haversine_km(*pts[i], *pts[j]))
    rng_txt = {k: (round(min(v), 2), round(max(v), 2)) for k, v in by_gd.items() if v}
    overlap = by_gd[1] and by_gd[2] and max(by_gd[1]) > min(by_gd[2])
    check("H3", "Hex grid distance ranges overlap in km: a cell index is not a distance or travel-time proxy",
          bool(overlap), f"km range of pairs at grid distance 1/2/3: {rng_txt} (ranges overlap -> use PostGIS/routing)")

    # E4: k-anonymity suppression and sensitive coarsening
    pts2 = [(lat0 + rng.uniform(-0.01, 0.01), lon0 + rng.uniform(-0.01, 0.01), False) for _ in range(12)]
    pts2 += [(lat0 + 0.08, lon0 + 0.08, False)]            # lone point -> suppressed
    pts2 += [(lat0 - 0.05, lon0 - 0.05, True)] * 6         # sensitive cluster -> coarse cell
    agg = hx.public_aggregate(pts2, res=8, k=5)
    suppressed = [c for c in agg if c.suppressed]
    coarse = [c for c in agg if _h3.get_resolution(c.cell) == hx.SENSITIVE_MAX_RES]
    try:
        hx.public_aggregate(pts2, res=10, k=5)
        too_fine_blocked = False
    except ValueError:
        too_fine_blocked = True
    check("H3", "Public aggregates: counts < k suppressed; sensitive points only at coarse resolution; res > 8 refused",
          len(suppressed) >= 1 and all(c.count == 0 for c in suppressed) and len(coarse) == 1 and too_fine_blocked,
          f"cells={len(agg)}, suppressed={len(suppressed)}, coarse sensitive cells={len(coarse)}, res10 refused={too_fine_blocked}")


# =============================================================================
def write_report(path: str, elapsed: float) -> None:
    n_pass = sum(1 for r in RESULTS if r[2])
    lines = ["# Mathematical check report (generated)", "",
             f"Generated by `backend/examples/math_checks.py` on {time.strftime('%Y-%m-%d')} in {elapsed:.1f}s. "
             f"**{n_pass}/{len(RESULTS)} checks passed.** All numbers come from declared synthetic models; "
             "none is a measurement of real Crescent City listings.", "",
             "| Paradigm | Check | Result | Detail |", "|---|---|---|---|"]
    for par, name, ok, detail in RESULTS:
        lines.append(f"| {par} | {name} | {'PASS' if ok else 'FAIL'} | {detail.replace('|', '/')} |")
    lines += ["", "Paradigm key: BDT = Bayesian decision theory; AIF = Active Inference / FEP; "
              "PHX = Phoenix / CRR information geometry; MEM = memory, governance and agent interface; "
              "H3 = derived hexagonal index.", "",
              "See `research/04_mathematics_register.md` for the public sources and the interpretation of each row."]
    with open(path, "w", encoding="utf8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\nReport written to {path}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=None, help="write a Markdown report to this path")
    args = ap.parse_args(argv)
    t0 = time.time()
    bdt_checks()
    aif_checks()
    phx_checks()
    mem_checks()
    h3_checks()
    elapsed = time.time() - t0
    n_pass = sum(1 for r in RESULTS if r[2])
    print(f"\n{n_pass}/{len(RESULTS)} checks passed in {elapsed:.1f}s")
    if args.report:
        write_report(args.report, elapsed)
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
