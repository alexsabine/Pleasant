# Bayesian constrained decision making for an atlas

## The actual claim
For a fixed, auditable state model `p(x|D)`, utility `U(a,x)` and feasible action set `A_safe`, selecting

`a*(D)=argmax_{a in A_safe} E_{x~p(x|D)} U(a,x)`

is Bayes-optimal **for that model and those objectives**. This is a standard decision-theory result, not proof that the model corresponds perfectly to families' desires or that the utility function is morally adequate.

## Five action types
1. `show` published verified suitable resources with sources and freshness visible.
2. `ask` one optional clarification that could change the feasible set; default to broad non-sensitive answers if not needed.
3. `verify` a high-impact uncertain source; cost includes staff effort and latency.
4. `suggest_correction` as draft, no auto-publish.
5. `abstain` (no unsolicited output) or `explain_unknown` when evidence insufficient.

Privacy/child safety/accessibility requirements are **hard constraints**, not weighted scores that a sufficiently popular result can override.

## Verification belief example
For a narrowly defined binary event such as "this event schedule matches the current authoritative source", model an unknown rate `theta` with Beta(a,b), when independent comparable verified checks exist. Posterior `Beta(a+s,b+f)`; mean `(a+s)/(a+b+s+f)`.

**Do not count duplicated cached responses as independent successes.** **Do not interpret this mean as the guaranteed probability that *this* event is on** unless the sampling process and model justify that interpretation. For individual listings with scant data, show `unverified` rather than fictitious high-confidence percentages.

## Value of information
Before spending a human editor's time, evaluate whether checking a source is likely to change which safe recommendation should be given. For a properly modelled outcome `o`:

`EVSI(check) = E_o[max_a E[U(a,x)|D,o]] - max_a E[U(a,x)|D] - check_cost`.

This provides a decision-theoretic basis for review queues—rather than checking every stable playground on an arbitrary fixed schedule.

## Personalisation
Preferences belong to the adult account as explicit choices: minimum/maximum age bands, price cap, preferred categories, accessibility requirements and notification level. No sensitive latent personality labels. Information capacity represented by user-selected `few / standard / all`, not inferred psychological vulnerability.

## Constraints and feedback loops
Track when public recommendations shift attention toward promoted sites. Hold out/surface diverse eligible resource types when useful and fair, and test under-represented groups. Avoid optimizing clicks, notification volume or artificially reported synchronicity.
