# From member to steward: a trust pathway (proposal, not built)

Prompted by GEO_INFER's civic-participation module (`GEO-INFER-CIV/src/geo_infer_civ/core/participation.py`,
Active Inference Institute, CC BY-NC-SA 4.0; ideas only, no code copied).

## What GEO_INFER computes

- **Representation index** per group: share of participants from the group divided by the group's share of the
  population. Below 0.8 is under-represented, above 1.2 over-represented. An overall score is 1 minus the standard
  deviation of the indices.
- **Engagement score**: a fixed blend of method mix (0.35), evenness over time (0.20), variety of methods
  (0.20, normalised Shannon entropy) and reach (0.25).

## What we take, and what we leave

| Take | Leave |
|---|---|
| The representation index, applied to **communities** (Crescent City, Smith River, Gasquet, Klamath, Fort Dick, Hiouchi) using public Census population shares, never to individuals or demographics | Demographic groups and participant locations: we collect neither |
| Use it to steer outreach, invitations and which listings to add next | Engagement score on people: it rewards volume, which is popularity, not reliability (rule 7) |
| Evenness over time, as one condition of tenure | Hand-picked weights with no stated basis |

One mathematical improvement to discuss with Daniel: the overall score uses an unweighted standard deviation of
ratios, so a very small community moves it as much as a large one. A population-weighted distance between the
contributor distribution p and the population distribution q, such as total variation `TV = 1/2 * sum |p_c - q_c|`,
is bounded, weights communities by size, and is 0 exactly when contributors mirror the county.
(Note the identity `sum_c q_c * r_c = 1` for representation indices r_c = p_c / q_c.)

## Proposed ladder, with its maths

Each step is an **invitation** from the stewards, accepted by the member, enforced by the server and sealed in the
log. Lumen never grants a role (rule 6). The numbers only decide who becomes *eligible to be invited*.

Track record: each of a member's contributions ends approved or rejected by a steward. Model the member's
acceptance rate with a Beta posterior, `Beta(1 + a, 1 + r)`, where approved `a` and rejected `r` are counted with
recency weights (an item's weight halves every 12 months), so old mistakes and old successes both fade.
Eligibility uses the **lower 5% credible bound** L of that rate, which is cautious with small samples.

| Step | Can do | Eligible to be invited when |
|---|---|---|
| Member | Ask Lumen, add places and photos, send corrections | Joins (adult confirmation) |
| Contributor | Draft listings directly in the review queue | at least 5 approved items and L >= 0.70 |
| Editor (verifier) | Check evidence and mark it verified; cannot publish | at least 20 approved items, L >= 0.85, active across at least 6 months, items in at least 3 of the 9 groups |
| Steward | Approve publication, monthly round, rules | Editor for at least 12 months, invited by the existing stewards; representation index guides who is asked first |

Worked figures for L, the lower 5% bound of Beta(1 + a, 1 + r):
- 20 approved, 0 rejected: L ~ 0.87
- 20 approved, 2 rejected: L ~ 0.75
- 50 approved, 3 rejected: L ~ 0.86

So volume alone never qualifies anyone; reliability does, and a small number of rejections is forgiven over time.

## Safeguards

- A member's track record is private to them and the stewards; it is never shown publicly or ranked.
- Anyone can decline or step down at any time.
- Roles can be removed by two stewards, with the reason sealed in the log.
- Stewards review the community representation index each quarter; an index below 0.8 prompts outreach in that
  community, not a lower bar.
