"""Compatibility check: Crescent Compass's decision maths vs GNN (Generalized Notation Notation).

GNN (Active Inference Institute, Daniel Friedman; CC BY-NC-SA 4.0) is a plain-text notation for
active-inference generative models. Conventions used here come from its public docs
(docs/gnn/gnn_syntax.md "B-tensor orientation", docs/gnn/reference/gnn_syntax.md "C vector semantics")
and its examples; no GNN code is copied or run. The GNN file written below is our own.

Checks
  G1  our freshness POMDP translates into GNN's conventions: B[next, prev, action] column-stochastic,
      A[obs, state...] column-stochastic, C as log-preferences (consumers apply softmax), D a distribution;
      the action-dependent observations are expressed losslessly with a second "checked" state factor.
  G2  round trip: rebuilding our model from the GNN arrays reproduces exact DP values/actions and EFE.
  G3  preferences: softmax(C_gnn) equals our C, so our risk term equals the KL risk GNN's consumers use.
  G4  decision criteria: with utilities written as log-preferences C = lambda * U, the one-step EFE rule shows
      a listing iff lambda * E[U] + H(p) > 0. It recommends MORE often than the Bayes-optimal rule
      (threshold 0.75) at low lambda and converges to it as lambda grows. Production keeps the Bayes rule.
Writes research/gnn/freshness_pomdp.gnn.md and research/10_gnn_compatibility.md.
Run: PYTHONPATH=backend python backend/examples/gnn_compat.py
"""
from __future__ import annotations

import sys
from math import exp, log
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from pc_core.bayes import choose_binary_action  # noqa: E402
from pc_core.pomdp import POMDP, freshness_pomdp  # noqa: E402

RESULTS = []


def check(name, ok, detail):
    RESULTS.append((name, bool(ok), detail))
    print(f"[GNN] {'PASS' if ok else 'FAIL'}  {name}\n        {detail}")


def softmax(v):
    m = max(v)
    w = [exp(x - m) for x in v]
    z = sum(w)
    return [x / z for x in w]


def to_gnn(m: POMDP):
    """Our model -> GNN arrays. Factor 0 = freshness {current, stale}; factor 1 = checked {no, yes}."""
    S, O, U = len(m.states), len(m.observations), m.actions
    checked = {a: (1 if m.A[a][0][2] < 1.0 else 0) for a in U}  # an action that can yield pos/neg is a check
    B_f0 = [[[m.T[a][p][n] for a in U] for p in range(S)] for n in range(S)]            # [next][prev][action]
    B_f1 = [[[1.0 if n == checked[a] else 0.0 for a in U] for p in range(2)] for n in range(2)]
    verify = next(a for a in U if checked[a])
    quiet = next(a for a in U if not checked[a])
    A_m0 = [[[m.A[quiet][s][o], m.A[verify][s][o]] for s in range(S)] for o in range(O)]  # [obs][fresh][checked]
    C_m0 = [log(c) for c in m.C]
    return {"B_f0": B_f0, "B_f1": B_f1, "A_m0": A_m0, "C_m0": C_m0, "checked": checked}


def from_gnn(g, template: POMDP) -> POMDP:
    U, S, O = template.actions, len(template.states), len(template.observations)
    T = {a: [[g["B_f0"][n][p][U.index(a)] for n in range(S)] for p in range(S)] for a in U}
    A = {a: [[g["A_m0"][o][s][g["checked"][a]] for o in range(O)] for s in range(S)] for a in U}
    return POMDP(states=template.states, actions=U, observations=template.observations, T=T, A=A,
                 R=template.R, C=softmax(g["C_m0"]))


def fmt(x):
    if abs(x) < 1e-12:
        return "0.0"
    t = f"{x:.4f}".rstrip("0")
    return t + "0" if t.endswith(".") else t


def write_gnn_file(g, m: POMDP):
    U = m.actions
    nest3 = lambda arr: "{\n" + ",\n".join("  ( " + ", ".join("(" + ",".join(fmt(x) for x in inner) + ")" for inner in mid) + " )" for mid in arr) + "\n}"
    text = f"""# GNN file: Crescent Compass freshness model (our own file, written in GNN notation)
# Source of truth: backend/pc_core/pomdp.py freshness_pomdp(); regenerate with backend/examples/gnn_compat.py
# Active Inference is research guidance here. Lumen's live decision is the Bayes-optimal rule
# (expected utility, exact finite-horizon DP); this file documents the model for governance and comparison.

## GNNSection
CrescentCompassFreshness

## GNNVersionAndFlags
GNN v1

## ModelName
Crescent Compass listing freshness (show, abstain, verify)

## ModelAnnotation
Is a published listing still current? Hidden factor 0 is freshness (current, stale); hidden factor 1 records
whether a human check was made this step (no, yes), so observations depend on the action without
needing action-dependent likelihoods. Observations: pos (looks current), neg (looks stale), none (no check).
Utilities are not observation preferences and cannot be written in C; they are stated in Equations.

## StateSpaceBlock
s_f0[2,1,type=float]     # freshness: current, stale
s_f1[2,1,type=float]     # checked this step: no, yes
o_m0[3,1,type=int]       # pos, neg, none
u[3,1,type=int]          # actions: {", ".join(U)}
A_m0[3,2,2,type=float]   # obs x freshness x checked
B_f0[2,2,3,type=float]   # next freshness x previous freshness x action (column-stochastic per action)
B_f1[2,2,3,type=float]   # next checked x previous checked x action
C_m0[3,type=float]       # log-preferences over observations
D_f0[2,type=float]       # prior over freshness
D_f1[2,type=float]       # prior over checked
G[π,type=float]          # expected free energy (comparison only)
t[1,type=int]

## Connections
D_f0>s_f0
D_f1>s_f1
(s_f0, u)>B_f0
B_f0>s_f0
(s_f1, u)>B_f1
B_f1>s_f1
(s_f0, s_f1)>A_m0
A_m0>o_m0
C_m0>G
G>u

## InitialParameterization
# Literals nest in the declared index order (outermost index first).
A_m0={nest3(g["A_m0"])}
B_f0={nest3(g["B_f0"])}
B_f1={nest3(g["B_f1"])}
C_m0={{({", ".join(fmt(c) for c in g["C_m0"])})}}
D_f0={{(0.8,0.2)}}
D_f1={{(1.0,0.0)}}

## Equations
# Utilities (state x action), published constants: U(show, current)=+1, U(show, stale)=-3, U(abstain, .)=0,
# U(verify, .)=-{fmt(-m.R['verify'][0])} (cost of a steward's check).
# Live decision rule (Bayesian decision theory): show iff P(current) * 1 + (1 - P(current)) * (-3) > 0,
# i.e. P(current) > 0.75; with verify available, exact finite-horizon dynamic programming over beliefs.
# P(current) comes from a Gamma-exponential survival model per category (backend/pc_core/freshness.py).
# Comparison rule (Active Inference): G(a) = KL(q(o|a) || softmax(C)) + E_q(s'|a) H[p(o|s')].

## Time
Dynamic
Discrete
ModelTimeHorizon=3

## ActInfOntologyAnnotation
A_m0=LikelihoodMatrix
B_f0=TransitionMatrix
B_f1=TransitionMatrix
C_m0=LogPreferenceVector
D_f0=PriorOverHiddenStates
D_f1=PriorOverHiddenStates
s_f0=HiddenState
s_f1=HiddenState
o_m0=Observation
u=Action
G=ExpectedFreeEnergy

## ModelParameters
num_hidden_states_factors: [2, 2]
num_obs_modalities: [3]
num_actions: 3

## Footer
Crescent Compass, research/gnn/freshness_pomdp.gnn.md

## Signature
Generated by backend/examples/gnn_compat.py from pc_core.pomdp.freshness_pomdp()
"""
    out = ROOT / "research" / "gnn" / "freshness_pomdp.gnn.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    return out


def main():
    m = freshness_pomdp()
    g = to_gnn(m)

    # G1 conventions
    col_ok = all(abs(sum(B[n][p][a] for n in range(2)) - 1) < 1e-12 for B in (g["B_f0"], g["B_f1"]) for p in range(2) for a in range(3))
    a_ok = all(abs(sum(g["A_m0"][o][s][c] for o in range(3)) - 1) < 1e-12 for s in range(2) for c in range(2))
    path = write_gnn_file(g, m)
    check("G1 our model fits GNN's conventions: B[next, prev, action] and A[obs, freshness, checked] column-stochastic, "
          "action-dependent observations carried by a second 'checked' factor",
          col_ok and a_ok, f"B columns sum to 1: {col_ok}; A columns sum to 1: {a_ok}; file written to {path.relative_to(ROOT)}")

    # G2 round trip
    m2 = from_gnn(g, m)
    worst_v, act_same, worst_g = 0.0, True, 0.0
    for i in range(1, 100):
        b = [i / 100, 1 - i / 100]
        for h in (1, 2, 3):
            v1, a1 = m.value_dp(b, h)
            v2, a2 = m2.value_dp(b, h)
            worst_v = max(worst_v, abs(v1 - v2)); act_same &= a1 == a2
        for a in m.actions:
            worst_g = max(worst_g, abs(m.efe(b, a)["G_risk_ambiguity"] - m2.efe(b, a)["G_risk_ambiguity"]))
    check("G2 round trip through the GNN arrays reproduces our exact DP (horizons 1-3) and EFE on 99 beliefs",
          worst_v < 1e-12 and act_same and worst_g < 1e-12,
          f"max value difference {worst_v:.1e}; identical actions: {act_same}; max EFE difference {worst_g:.1e}")

    # G3 preferences
    diff = max(abs(x - y) for x, y in zip(softmax(g["C_m0"]), m.C))
    shift = max(abs(x - y) for x, y in zip(softmax([c + 5.0 for c in g["C_m0"]]), m.C))
    check("G3 GNN's log-preference C, after the softmax its consumers apply, equals our preference distribution "
          "(and adding a constant changes nothing)", diff < 1e-12 and shift < 1e-12, f"max difference {diff:.1e}; after +5 shift {shift:.1e}")

    # G4 decision criteria: utilities as log-preferences over outcomes
    U = [1.0, -3.0, 0.0]  # good show, bad show, nothing
    rows = []
    for lam in (1, 2, 5, 10, 20, 50, 100):
        C = softmax([lam * u for u in U])
        out = POMDP(states=["current", "stale"], actions=["show", "abstain"], observations=["good", "bad", "nothing"],
                    T={"show": [[1, 0], [0, 1]], "abstain": [[1, 0], [0, 1]]},
                    A={"show": [[1, 0, 0], [0, 1, 0]], "abstain": [[0, 0, 1], [0, 0, 1]]},
                    R={"show": [1.0, -3.0], "abstain": [0.0, 0.0]}, C=C)
        thr = next(i / 1000 for i in range(1, 1000) if out.efe_policy([i / 1000, 1 - i / 1000]) == "show")
        bayes = next(i / 1000 for i in range(1, 1000) if choose_binary_action(i / 1000, 1.0, -3.0, 0.0)[0] == "show")
        # closed form: show iff lam*(4p-3) + H(p) > 0  (H in nats)
        H = lambda q: -(q * log(q) + (1 - q) * log(1 - q))
        formula = next(i / 1000 for i in range(1, 1000) if lam * (4 * i / 1000 - 3) + H(i / 1000) > 0)
        rows.append((lam, thr, bayes, formula))
    converges = (abs(rows[-1][1] - 0.75) <= 0.002 and all(r[1] < 0.75 for r in rows)
                 and all(rows[i][1] <= rows[i + 1][1] for i in range(len(rows) - 1)) and all(r[1] == r[3] for r in rows))
    check("G4 one-step EFE with utilities as log-preferences shows a listing iff lambda*E[U] + H(p) > 0: it recommends "
          "below the Bayes threshold 0.75 at low precision and converges to it as lambda grows",
          converges, "; ".join(f"lambda={l}: EFE shows from P(current)={t:.3f} (Bayes {b:.3f}, formula {f:.3f})" for l, t, b, f in rows))

    n_pass = sum(r[1] for r in RESULTS)
    L = ["# GNN compatibility check (generated)", "",
         f"`backend/examples/gnn_compat.py`. **{n_pass}/{len(RESULTS)} checks passed.** GNN conventions from its public docs; no GNN code copied or run.", "",
         "| Check | Result | Detail |", "|---|---|---|"]
    L += [f"| {n} | {'PASS' if ok else 'FAIL'} | {d.replace('|', '/')} |" for n, ok, d in RESULTS]
    L += ["", "## What this means", "",
          "- Our freshness model can be published in GNN notation without losing anything; the file is `research/gnn/freshness_pomdp.gnn.md`.",
          "- GNN's preference vector C is over observations only. Our +1/-3/0 utilities depend on state and action, so they are stated in the Equations section; "
          "GNN has no native slot for them.",
          "- GNN's standard agent chooses by expected free energy over one step. That criterion includes an entropy bonus H(p): written with utilities as "
          "log-preferences, it shows a listing when lambda*E[U] + H(p) > 0. At low preference precision it would recommend listings that are only ~58% likely "
          "current, which our trust rule forbids. It matches the Bayes-optimal rule only as precision grows (within 0.01 by lambda=50).",
          "- Lumen's live decision therefore stays Bayesian decision theory (threshold 0.75; exact DP when a check is possible). A GNN/PyMDP rendering is useful "
          "offline as a documented comparison baseline, as CLAUDE.md rule 10 requires."]
    (ROOT / "research" / "10_gnn_compatibility.md").write_text("\n".join(L) + "\n")
    print(f"\n{n_pass}/{len(RESULTS)} GNN compatibility checks passed")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
