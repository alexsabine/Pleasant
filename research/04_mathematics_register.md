# Mathematics register: what Pleasant Crescent uses, where it comes from, and what it can honestly claim

**Purpose.** Every formula that influences what the atlas shows, asks, verifies or withholds is listed here with its public source, the check that verifies it (`backend/examples/math_checks.py`, report in `05_math_check_report.md`), and its evidential status. A governance body should be able to read this file, run the checks, and change a declared number without touching code.

**Status legend.** `source-verified fact` (textbook or peer-reviewed, reproduced numerically here) · `derived identity` (follows algebraically; checked numerically) · `design rule` (our choice, publicly stated, revisable) · `to be tested` (needs the controlled study in `03_controlled_research_plan.md` before any claim).

Every number in the checks comes from a declared synthetic model. None is a measurement of real listings.

---

## 1. What "Bayes-optimal" means here, in all three paradigms

The owner asked for the system to be Bayes-optimal in Bayesian decision theory, in Active Inference / FEP, and in the Phoenix / CRR framing. The honest answer, verified by the checks, is:

| Paradigm | What is optimal, and relative to what | Check |
|---|---|---|
| **Bayesian decision theory (BDT)** | For a declared state model p(x\|D), utility U(a,x) and feasible set A_safe, the action a* = argmax E[U] is optimal *for that model and that utility*. Verified by exact enumeration of all 81 depth-2 policy trees against belief-space dynamic programming: zero gap. | BDT-1 |
| **Active Inference / FEP (AIF)** | Perception: minimising variational free energy F[q] recovers the exact Bayesian posterior, F ≥ −log p(o) with equality iff q is the posterior. Action: minimising expected free energy G is a *different* criterion from maximising expected utility: its argmin disagreed with myopic expected utility at every belief tested, because G carries an explicit information-gain term. A two-step expected-utility planner, which includes the value of information, chose the same information-seeking action. | AIF-1, AIF-3 |
| **Phoenix / CRR** | The Fisher–Rao distance used by Phoenix is the length of the geodesic of the Fisher metric, which is the Hessian of KL divergence. It is a correct way to measure *how much a belief moved*. It is not a decision rule and does not by itself make anything optimal; the threshold that turns it into a trigger has no universal value (the cost-optimal threshold moved with base rate and miss cost). | PHX-1, PHX-2, PHX-6 |

**Reconciliation.** There is one production decision rule: constrained expected utility with value of information (BDT). EFE is kept as an alternative scorer because its two-term decomposition (risk + ambiguity, or equivalently −epistemic − pragmatic) is a readable explanation of *why* an action was chosen. Fisher–Rao distance is a monitor feature feeding the review queue. All three are mathematically consistent with each other; none is a magic ingredient. The claim "Bayes-optimal" is always conditional on the published model and utility, which is exactly why the model and utility must be published.

---

## 2. Register of formulas

| ID | Formula | Used for | Public source | Status | Check |
|---|---|---|---|---|---|
| F1 | Bayes rule, discrete: q(s\|o) ∝ p(o\|s) q(s) | Updating belief that a listing is current | Any probability text; Kaelbling, Littman & Cassandra 1998 (POMDPs) | source-verified fact | AIF-1 |
| F2 | Beta–Binomial conjugacy: Beta(a,b) → Beta(a+s, b+f) | Verification success rates per source | Gelman et al., *Bayesian Data Analysis* 3e ch. 2 (free PDF from authors) | source-verified fact | BDT-3 |
| F3 | Expected utility: a* = argmax_a Σ_x p(x\|D) U(a,x), subject to hard constraints | Show / ask / verify / abstain decisions | Berger, *Statistical Decision Theory* 1985; Raiffa & Schlaifer 1961 | source-verified fact | BDT-1, BDT-5 |
| F4 | EVSI = E_o[max_a E[U\|D,o]] − max_a E[U\|D] − cost; 0 ≤ EVSI ≤ EVPI | Review-queue priority; whether to ask the user one question | Howard 1966 "Information value theory"; Raiffa & Schlaifer 1961 | source-verified fact | BDT-2, MEM-2 |
| F5 | Finite-horizon belief DP: V_k(b) = max_a [ r(b,a) + Σ_o p(o\|b,a) V_{k−1}(b') ] | Exact optimal plan in the small freshness model | Kaelbling et al. 1998 | source-verified fact | BDT-1 |
| F6 | Proper scoring: log loss and Brier; Murphy decomposition Brier = REL − RES + UNC | Publishing calibration of our own probabilities | Murphy 1973; Gneiting & Raftery 2007 (JASA); Stephenson, Coelho & Jolliffe 2008 for the within-bin terms | source-verified fact | BDT-4 |
| F7 | Variational free energy F[q] = E_q[log q(s) − log p(o,s)] ≥ −log p(o) | Shows "Bayes-optimal perception" is exact inference | Bishop, *PRML* 2006 ch. 10; Blei, Kucukelbir & McAuliffe 2017 | source-verified fact | AIF-1 |
| F8 | Expected free energy G(π) = KL(q(o\|π) ‖ C(o)) + E_q(s\|π) H[p(o\|s)] = −E[info gain] − E[log C(o)] | Alternative, explainable action scorer | Parr, Pezzulo & Friston, *Active Inference*, MIT Press 2022 (open access) ch. 2 and appendix; Smith, Friston & Whyte 2022, PMC8956124 | derived identity (verified to 4e-16) | AIF-2 |
| F9 | Boltzmann policy π(a) ∝ exp(−γ G(a)) with precision γ | Makes "how deterministic" an explicit, published knob | Same as F8 | design rule | AIF-5 |
| F10 | Kalman predict-only step for a missing observation: P ← P + Q; identical bytes (same ETag) are not a new observation | Partner feed ingestion; stale-world handling | Kalman 1960; Särkkä, *Bayesian Filtering and Smoothing* 2013 (open access) ch. 4; Phoenix P14 reduces to this | source-verified fact | AIF-4 |
| F11 | Fisher–Rao distance on Bernoulli: d = 2\|asin√p − asin√q\| = 2·arccos(√(pq) + √((1−p)(1−q))) = ∫√(1/(x(1−x))) dx | Monitor feature: how far a belief moved between verifications | Amari & Nagaoka 2000; Bhattacharyya 1943; Phoenix `CORE/MATHEMATICS.md` | source-verified fact; two public formulas agree to 1e-13 | PHX-1 |
| F12 | Fisher information g(p) = ∂²KL(p‖q)/∂q² at q=p; d² → 2·KL for small moves | Shows F11 is standard local KL geometry | Cover & Thomas 2e ch. 11 | source-verified fact | PHX-2 |
| F13 | Path surplus S = C − d ≥ 0 | Phoenix's "surplus"; carries no information beyond (C, d) | Triangle inequality | derived identity | PHX-3 |
| F14 | Exponential working summary m_{n+1} = q m_n + (1−q) φ_n | Compact task context only; many-to-one, so never the archive | Phoenix `MATHEMATICS.md`; it is an EMA | source-verified fact (lossiness demonstrated) | PHX-4 |
| F15 | Two clocks: elapsed time t, material-change count N, belief path length C are distinct | Typed timestamps in the data model | Phoenix `FOUNDATIONS/TWO_CLOCKS.md` | design rule, backed by a numerical demonstration | PHX-5 |
| F16 | Change trigger d_FR > τ: τ has no universal value | τ must be fitted on validation data and published | Phoenix `03_math_selected.md` caveat; standard ROC/cost analysis | design rule | PHX-6 |
| F17 | Exponential survival with Gamma prior on hazard: P(current \| age t) = (b/(b+t))^a; posterior Gamma(a+n, b+T) | "Is this still current?" without pretending time is evidence | Gelman et al. 3e ch. 2 (Gamma–Poisson/exponential); Lomax tail | source-verified fact (closed form = Monte Carlo) | MEM-1 |
| F18 | Review priority = EVSI + P(stale)·spec·repair_value − cost | Which listing an editor checks next | F4 plus a declared coverage value | design rule; see finding 8.2 | MEM-2, MEM-5 |
| F19 | SHA-256 hash chain: h_i = H(h_{i−1} ‖ canonical(payload_i)) | Tamper-evident decision and provenance log | RFC 6962 (Certificate Transparency); Git object model | source-verified fact | MEM-3 |
| F20 | Operational closure invariant: every published fact ← verified observed/reported claim ← authorised role ← audit entry | The "autopoiesis-informed" publication rule | Maturana & Varela 1980 (concept); Friston 2013 "Life as we know it" (Markov blanket reading, open access) | design rule, enforced as a test | MEM-4 |
| F21 | Homeostasis: bounded review budget keeps stale fraction bounded under a stationary hazard | Why the verification loop is the system's regulator | Elementary queueing/renewal argument; simulated | design rule, demonstrated under the declared model only | MEM-5 |
| F22 | H3 cell area by resolution; k-ring size 1+3k(k+1); parent containment | Aggregate cells, cache keys | H3 docs (Apache-2.0), h3geo.org | source-verified fact | H3-1, H3-2 |
| F23 | Grid distance is not geographic distance (km ranges at grid distance 1 and 2 overlap) | Forbids using H3 for travel time | Demonstrated numerically | derived (demonstration) | H3-3 |
| F24 | k-anonymity suppression (count < k → 0) and coarsening of sensitive points to res ≤ 6 | Public aggregate maps | Sweeney 2002 (k-anonymity) | design rule | H3-4 |

---

## 3. Memory architecture, in mathematical terms

Four layers, each with its own mathematics (see `architecture/02_data_and_memory.md` for the data model):

1. **Evidence events** are the archive. Idempotent by event id (F10's ETag rule), hash-chained (F19). Nothing is ever averaged here.
2. **Claims** carry an epistemic class: `observed`, `reported`, `inferred`, `generated`, `simulated`. Only the first two can support publication (F20).
3. **Published projection** is one human-chosen entry per resource. It carries P(current) from F17 and the typed timestamps from F15. Calibration of that probability is published with its binning (F6).
4. **Working context** for one request is an exponential summary or a retrieval result (F14), explicitly lossy, rebuilt from layer 1 on demand, never written back as fact.

The missing-observation rule (F10) is the hinge between layers 1 and 3: time passing widens uncertainty in layer 3 (F17) but creates no event in layer 1.

---

## 4. The agentic interface, in mathematical terms

- The agent's action set is the published allow-list (`integrations/agent_messaging_future.md`); A_safe in F3 is literally that list, intersected with object-level permissions enforced by the backend.
- `abstain` and `explain_unknown` are always in A_safe with utility 0, so the agent needs a positive expected-utility reason to speak (BDT-5 shows popularity cannot override a hard constraint).
- Asking the user one optional question is an EVSI decision (F4): ask only when the answer could change which safe recommendation is given.
- Every consequential response logs the eleven provenance fields required by `architecture/02` into the hash chain (F19, MEM-3 rejects an incomplete record).
- EFE's decomposition (F8) is used to *explain* a choice in two human-readable numbers: how far the expected outcome is from what the user asked for (risk) and how uncertain the evidence would be (ambiguity). It is not the production chooser.

---

## 5. What H3 is licensed to do

Derived index only (F22–F24): cache keys for map projections, k-anonymous aggregate counts at resolution 5–8, coarse cells (≤ 6) for sensitive categories, and sizing (about 7,300 res-8 cells cover the approximate county bounding box). Not licensed: any distance, any travel time, any inference of a person's location from a cell, any resolution above 8 for people-related data. Precise spatial questions go to PostGIS (`ST_DWithin`, geography distance) and, if ever needed, a routing engine.

---

## 6. Transparency and governance: what Phoenix, FEP and Active Inference actually offer

This is the clear note the owner asked for. Three things in these frameworks are genuinely useful for making a mapping system legible to a future governance body; none of them requires accepting any contested claim.

1. **A declared generative model is a readable policy.** In Active Inference the whole decision apparatus is four published objects: the transition matrix T (how listings go stale), the likelihood A (how reliable each verification channel is), the preference vector C (what outcomes the organisation wants) and the precision γ. A board can inspect, argue about and vote on each of them. They are the `freshness_pomdp()` arguments. Changing a number changes behaviour, with no code change and a diff in version control.
2. **Two-term explanations.** The EFE identity (F8) means every candidate action has an auditable "risk" and "ambiguity" score. Likewise EVSI (F4) states, in utility units, why an editor's hour was spent on one listing rather than another. These are explanations a non-specialist can read.
3. **Provenance as a type, not a comment.** Phoenix's `OBSERVED ≠ GENERATED ≠ INFERRED ≠ SIMULATED` (PX-01) becomes a database constraint and the closure test (F20). Phoenix's instruction to mark every explanation with source, confidence, intervention status, version and failure modes maps onto the eleven-field decision record in the hash chain (F19). The two clocks (F15) give the typed timestamps that let an auditor ask "when was this last *seen*, not merely re-sent?"

What they do **not** offer: any evidence that the atlas will perform better than a plain verified directory; any threshold for "meaningful change"; any licence to infer a family's unstated preferences, to contact people for information gain, or to treat the published map as the territory. Those limits are stated in `02_active_inference_and_fep.md` and `phoenix_selected/03_math_selected.md`, and the checks here confirm the mathematical reasons behind them.

---

## 7. Upper limits: an honest review

**What I can build here.** The full Django/Wagtail/PostGIS/MapLibre stack, the tile build pipeline (Planetiler or `pmtiles extract`, GDAL for terrain-RGB), the CMS workflow, the API, the tests and CI, the accessibility review tooling, the hash-chained audit log, the freshness model, the review queue, and a feature-flagged read-only agent over the allow-list. All of that is standard engineering with mature libraries.

**What I cannot do, and should not pretend to.** Obtain licences or permissions (three emails and one county conversation need a human sender). Verify the 40 listings (human eyes, by contract). Make a legal determination about CPAD, State Parks or ODbL share-alike. Measure real staleness rates before the site has a history. Run a PostGIS container in this sandbox (Docker daemon is absent; the vertical slice will run against SQLite/SpatiaLite locally and PostGIS in CI and staging).

**Upper limit of Active Inference / FEP for this project.** It provides a consistent, explainable scoring of a handful of actions over a two-state model. It does not provide calibration, which needs data; it does not provide a utility, which needs the owner; and its empirical advantage over expected utility with VOI is, by the checks, nil on this model because the two agree wherever information matters. Its value is governance legibility (section 6), which is real.

**Upper limit of Phoenix / CRR.** Its mathematics reduces, on inspection and by numerical check, to standard information geometry (F11–F13), standard Kalman handling of missing data (F10) and an EMA (F14). Its process grammar (provenance types, two clocks, map ≠ territory) is the valuable part and is adopted as design rules. No Phoenix result is cited as evidence that the atlas works.

**Upper limit of "Bayes-optimal".** Optimal relative to a declared model and utility. The model will be wrong in ways that only data reveals; the utility is a value judgement. Both are published so that they can be corrected.

---

## 8. Findings from running the checks

Three checks failed on first run. Each failure was informative and is recorded rather than hidden.

- **8.1 Brier decomposition is exact only for binned forecasts.** With continuous probabilities the three-term identity leaves a within-bin residual. Rule adopted: publish calibration with the bin edges stated.
- **8.2 Pure value-of-information starves old listings.** Under the kit's utilities (show-if-true +1, show-if-false −3, abstain 0, check cost 0.1), EVSI peaks at 31 days for a stable category and falls to −0.1 for very old listings, because once "abstain" is already the Bayes act, checking cannot change the decision. In simulation that policy left 45% of listings stale versus 25% for oldest-first. Adding a declared *repair value* ≥ 3 (the worth of restoring a stale listing to current) makes the priority monotone in age and matches oldest-first. **Design consequence:** the review objective must include the value of restored coverage, and with one shared hazard, oldest-first is already the Bayes policy. EVSI earns its place only when categories have different hazards (events versus playgrounds). That is Study A in `03_controlled_research_plan.md`, now with a concrete reason to run it.
- **8.3 "Volatile categories" peak earlier, not higher.** The hump for a 10× hazard category sits at 3 days rather than 31; its height is about the same. Review cadence, not review intensity, is what differs by category.

Everything else passed on the first run, including the identities that tie Phoenix's distance to KL geometry and EFE to expected utility.

---

## 8b. Crescent Compass: what the checks verify about the running agent

Five further checks (`[AGT]` in the report) run against the actual Compass modules in `web/compass/`:

- The recommendation threshold is a published number, p* = 0.75 under the utilities (+1, −3, 0). A board changes behaviour by changing those three numbers in the admin.
- The grounding validator drops any model-phrased sentence that cites a record not retrieved, asserts accessibility for a record not verified accessible, or states a fact with no record behind it.
- Working memory is bounded to six turns, holds only record ids and parsed preferences, folds older turns into preferences, is rebuilt when the published projection changes, and is cleared on request.
- Trust calibrates: on a synthetic world whose true change rate is four times the prior's, 300 verification outcomes move the posterior toward the truth and improve the Brier score of P(current) from 0.34 to 0.21. The site should publish this score monthly.
- Every answer writes an eleven-field decision record into the hash chain; an incomplete record is refused.

Twelve end-to-end Django tests (`web/compass/tests.py`) add the invariants that need a database: unknown access is never shown as accessible; unpublished, private and sensitive records never leave the server; stale matches are shown as low confidence rather than recommended; a true no-match is an honest unknown; expired events are never returned; memory carries preferences only until the projection changes or the user says "forget that"; the LLM is off by default and tools stay inside the allow-list; a `generated` claim can never be verified as evidence.

## 8c. Palette, logo and fine H3 (second iteration)

| ID | Formula | Used for | Public source | Status | Check |
|---|---|---|---|---|---|
| F25 | OKLCH ↔ sRGB conversion; WCAG 2.2 contrast = (L1+0.05)/(L2+0.05); ΔE_OK Euclidean in OKLab | Palette solved for contrast targets by bisection on lightness | Ottosson 2020 (OKLab); W3C WCAG 2.2 §1.4.3/1.4.11 | source-verified fact | tokens.json `contrast_checks` |
| F26 | Moon lit fraction (1 − cos θ)/2 with θ = 2·asin(√p) ⇒ lit fraction = p | The living crescent is a faithful gauge of the mean P(current) | Standard trigonometry; F11 | derived identity | LOGO-1..3 |
| F27 | Breathing amplitude = FR path length over the window, capped at 0.35 rad; marks = min(N, 24) | Two clocks on the logo: belief movement C and change count N | F15 | design rule | LOGO-4 |
| F28 | H3 parent/child nesting is approximate: P(parent(cell_r(x)) ≠ cell_{r−1}(x)) ≈ 0.07 | Store the exact containing cell at each resolution 8..12 | H3 docs (hierarchy approximation) | source-verified fact (measured) | H3-2b |

## 9. Other techniques considered

| Technique | Verdict for this project |
|---|---|
| Conformal prediction for honest "unverified" bands | Useful later for calibrated uncertainty on P(current) without distributional assumptions; needs a few hundred verification outcomes first. To be tested. |
| Thompson sampling over review categories | A cheap way to learn category hazards while scheduling; a candidate challenger in Study A. To be tested. |
| Differential privacy on aggregates | Not needed while aggregates are k-anonymous counts of *places*, not people. Revisit if any per-user aggregate is ever published. |
| CRDTs for concurrent editing | Over-engineering for two admins and a few editors; Wagtail revisions plus optimistic version checks suffice. |
| Full belief-space POMDP solvers | Unnecessary at two states and three actions; exact enumeration is cheaper and more auditable. |
| GPU continual learning | Out of scope by contract and by design; the agent reads verified records, it does not train on them. |
