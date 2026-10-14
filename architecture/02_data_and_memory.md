# Database history, provenance and compact working memory

## Data is not just a pin
For each resource: stable ID, public visibility state, geospatial point/boundary, categorical facets (type, min/max ages, price class, accessibility status including unknown), verified source, verified timestamp, revision, audit record, and moderation status.

Maintain three **separate** representations:

1. **Source observations and claims**: licence, identity/role of reviewer where permitted, direct evidence/capture date, original contradictory reports.
2. **Published projection**: one clear user-facing entry chosen by human editorial rule, pointing back to supporting claims and including unresolved uncertainty.
3. **Working context**: small, revocable cache assembled for one user request. Not an evidence store. Rebuild from source records when needed.

Historical summaries are not lossless. Different episodes can yield the same weighted average, so do not use rolling averages as a legal/audit archive. Do not retain all personal content forever; implement deletion/retention and consent controls.

## Causal timeline
`observed_at` (source observation); `submitted_at`; `approved_at`; `valid_from`; `last_verified`; `last_changed`; `archived_at` each answer distinct questions. Directory conditions can change while the server receives no reports: time itself is not sufficient evidence of a change. An agent should not confuse a repeated stale record with new observation.

## Decision provenance
Each consequential recommendation or agent write intent logs at minimum:
`request_id`, `retrieval_sources`, `source_versions`, `policy_version`, `assumptions`, `confidence_type`, `action_proposed`, `user_approval`, `action_result`, `timestamp` and `limitations`. Logs minimised and access-restricted.

## Provisional cognitive-memory policy
- Compress task histories into short summaries for efficient context, retaining links to permitted source records.
- Use deterministic change events (verified price, opening hours, age range) to invalidate cached projections.
- Optional Fisher–Rao distance between suitably **specified probability distributions** can measure belief change; this does NOT make resource histories into literal circles, determine a universal threshold or establish a new physics.
- Reconcile concurrent edits with version checks and approval queues; never allow chat summaries to become trusted CMS content automatically.
- User attention/notification budgets are explicit with `no-action` as a valid choice.

## Geospatial layering and H3
Precise spatial decisions in PostGIS (ST_DWithin, ST_Intersects, geography distance and actual road routing where available). H3 cells are **derived** indexes for coarser aggregate grouping. No implicit cell -> person location inference and no inference of precise travel time from neighbours.
