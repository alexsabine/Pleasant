# Active Inference / FEP: mathematical guide, kept separate from Phoenix

## Scope
FEP and Active Inference are established theoretical frameworks with multiple formulations and debated interpretive claims. They are **not identical to Bayes-optimal reward control**. This package uses a tiny discrete POMDP to show an optional policy-score calculation; it does not claim to derive civic ethics, agency or child welfare from a physical FEP.

## A generative model
Let hidden state `s_t` describe whether an activity's published schedule is currently correct. Actions `a_t` may be show, ask, check source, or abstain. Observation `o_t` may be human verification, trusted API status, or user report.

`P(s_0), P(o_t|s_t), P(s_{t+1}|s_t,a_t)` plus prior preferences over outcomes `P_pref(o_t)` define a discrete model. Bayesian filtering:

`q_t(s) ∝ P(o_t|s_t) sum_{s'} P(s_t|s',a_{t-1}) q_{t-1}(s')`.

**Careful**: missing observation means propagate state without a fake likelihood update. Repeated stale responses are not independent evidence.

## One standard expected-free-energy expression
Under a specified predictive model and assumptions, one useful "risk + ambiguity" expression for expected free energy of policy `π` is

`G(π) = KL(q(o|π) || P_pref(o)) + E_{q(s|π)}[ H(P(o|s)) ]`.

Risk compares predicted outcomes to preferred outcome probabilities. Ambiguity is the expected conditional observation entropy. Related factorizations describe pragmatic value and epistemic value (expected information gain). Not all decompositions are literally interchangeable without their assumptions; choose and test one.

Given expected outcomes and a precise `P_pref`, one may consider policies with lower `G(π)` preferable, subject to **hard safeguarding and authorization constraints**. A more direct civic policy might use constrained expected utility and `EVSI` instead; that should be the baseline.

## What FEP does *not* license
- Inferring that an unspoken family preference exists.
- Publishing guesses as facts.
- Maximising social surprise, felt synchronicity or emotional intensity.
- Automatically contacting a person to improve a model's information gain.
- Claiming global Bayes optimality without a correct generative model and objective.
- Declaring CRR's circular cut or `Omega=1` an empirically calibrated FEP precision.

## Potential hybrid use
- Native constrained Bayesian ranking/review actions for production.
- Optional EFE scorer for **same** synthetic decisions, compared with expected-utility baseline.
- Phoenix-inspired process layer documents provenance, history and consent, and proposes when to consolidate context.
- Reward is externally audited task completion, clarity, accuracy and user agency, not time spent with the app.

References:
- Smith et al., "A step-by-step tutorial on active inference and its application to empirical data": https://pmc.ncbi.nlm.nih.gov/articles/PMC8956124/
- Friston et al., "Active inference and epistemic value" (2015): https://doi.org/10.1080/17588928.2015.1020053
- Wei, "Value of Information and Reward Specification in Active Inference and POMDPs": https://arxiv.org/abs/2408.06542
