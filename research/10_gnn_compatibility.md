# GNN compatibility check (generated)

`backend/examples/gnn_compat.py`. **4/4 checks passed.** GNN conventions from its public docs; no GNN code copied or run.

| Check | Result | Detail |
|---|---|---|
| G1 our model fits GNN's conventions: B[next, prev, action] and A[obs, freshness, checked] column-stochastic, action-dependent observations carried by a second 'checked' factor | PASS | B columns sum to 1: True; A columns sum to 1: True; file written to research/gnn/freshness_pomdp.gnn.md |
| G2 round trip through the GNN arrays reproduces our exact DP (horizons 1-3) and EFE on 99 beliefs | PASS | max value difference 0.0e+00; identical actions: True; max EFE difference 4.4e-16 |
| G3 GNN's log-preference C, after the softmax its consumers apply, equals our preference distribution (and adding a constant changes nothing) | PASS | max difference 2.8e-17; after +5 shift 2.8e-17 |
| G4 one-step EFE with utilities as log-preferences shows a listing iff lambda*E[U] + H(p) > 0: it recommends below the Bayes threshold 0.75 at low precision and converges to it as lambda grows | PASS | lambda=1: EFE shows from P(current)=0.580 (Bayes 0.751, formula 0.580); lambda=2: EFE shows from P(current)=0.671 (Bayes 0.751, formula 0.671); lambda=5: EFE shows from P(current)=0.721 (Bayes 0.751, formula 0.721); lambda=10: EFE shows from P(current)=0.736 (Bayes 0.751, formula 0.736); lambda=20: EFE shows from P(current)=0.743 (Bayes 0.751, formula 0.743); lambda=50: EFE shows from P(current)=0.748 (Bayes 0.751, formula 0.748); lambda=100: EFE shows from P(current)=0.749 (Bayes 0.751, formula 0.749) |

## What this means

- Our freshness model can be published in GNN notation without losing anything; the file is `research/gnn/freshness_pomdp.gnn.md`.
- GNN's preference vector C is over observations only. Our +1/-3/0 utilities depend on state and action, so they are stated in the Equations section; GNN has no native slot for them.
- GNN's standard agent chooses by expected free energy over one step. That criterion includes an entropy bonus H(p): written with utilities as log-preferences, it shows a listing when lambda*E[U] + H(p) > 0. At low preference precision it would recommend listings that are only ~58% likely current, which our trust rule forbids. It matches the Bayes-optimal rule only as precision grows (within 0.01 by lambda=50).
- Lumen's live decision therefore stays Bayesian decision theory (threshold 0.75; exact DP when a check is possible). A GNN/PyMDP rendering is useful offline as a documented comparison baseline, as CLAUDE.md rule 10 requires.
