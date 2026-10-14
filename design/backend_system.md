# Back-end system: evidence, projection, context and a read-only agent

Stack as approved: Django + Wagtail CMS, PostgreSQL 16 + PostGIS, self-hosted PMTiles, object storage for photos, optional H3 as a derived index, Claude API agent behind a feature flag and read-only. This document describes the system that keeps the front end smooth, the publication loop operationally closed, and the decision rules Bayes-optimal *for the published model*. The mathematics is in `research/04_mathematics_register.md`; the executable checks are in `backend/examples/math_checks.py`.

## 1. Django apps

| App | Responsibility | Key models (mirrors `infrastructure/schema_reference.sql`) |
|---|---|---|
| `sources` | Rights-gated layer manifest, attribution, vintage, approval receipts | `GisSource` (permission_status, evidence_of_approval, last_reviewed_at) |
| `evidence` | Append-only events and claims; epistemic type; idempotency by event id and source revision | `EvidenceEvent`, `ResourceClaim` |
| `directory` | Resources, published projection, typed timestamps, P(current) | `Resource`, `ResourceRevision` |
| `events` | One-off and recurring events with expiry and archival | `CommunityEvent` |
| `review` | Submissions, moderation, review queue with published priority | `ContentSubmission`, `ReviewTask` |
| `provenance` | Hash-chained decision log, eleven-field decision records, redaction | `AuditEntry` |
| `tiles` | Tile build jobs, manifest, cache invalidation on publish | `TileBuild`, `ProjectionSnapshot` |
| `agent` | Feature-flagged read-only tools, allow-list, request budget | `AgentRequest` |

Wagtail provides authentication, groups, page revisions and the admin shell. Object-level permissions use `django-guardian` or Wagtail's own group/collection permissions; nothing custom.

## 2. The four memory layers and their rules

```
EVIDENCE (append-only, hash-chained) --verify--> CLAIMS (typed) --approve--> PROJECTION (one per resource)
                                                                          |
                                                                   WORKING CONTEXT (per request, lossy, discarded)
```

1. **Evidence events** are never edited. Identical bytes from a partner (same ETag or content hash) are stored once and do not update confidence (math check AIF-4). Deletion for lawful reasons is a redaction entry that preserves the chain (MEM-3).
2. **Claims** carry `epistemic_type` in {observed, reported, inferred, generated, simulated}. Only observed and reported claims verified by an editor, steward or admin can support publication. A database constraint and the closure test (MEM-4) enforce this.
3. **Projection** is the human-approved revision with `approved_claim_ids`, typed timestamps (`observed_at`, `submitted_at`, `approved_at`, `last_verified_at`, `last_material_change_at`, `archived_at`) and a computed `p_current` from the category hazard model (MEM-1). Publishing writes a revision, bumps the projection version and invalidates the pin GeoJSON cache.
4. **Working context** is assembled per request from the projection and permitted claims, bounded by the user's chosen dosage (few / standard / all), and never written back.

## 3. Freshness and the review queue

- Each category has a declared hazard prior `Gamma(shape, rate)` stored in a table editable by admins, with its history. Posterior updates come only from verification outcomes (change / no change over exposure), never from elapsed time.
- `p_current(age)` is the posterior-predictive survival. It is rendered as a band, never as a precise percentage when the category has fewer than a published minimum of verification outcomes.
- Review priority = EVSI + P(stale)·specificity·repair_value − cost, with every constant in the same admin table. Finding 8.2 in the register explains why `repair_value` exists: without it the Bayes act lets old listings rot.
- Events expire by clock time regardless of agent activity or network state (the stale-world rule).
- The queue page shows the explanation in words: "checked next because it is 41 days old in a category that changes about every 100 days, and a check would change the decision to show it".

## 4. Publication workflow (server-enforced)

contributor submits → draft claim (`reported`, unverified) → editor verifies (claim marked verified, audit entry with eleven fields) → editor or admin approves revision → projection version increments → pin cache invalidated → public list and map update. Public submissions never auto-publish; an LLM-drafted caption is a `generated` claim that can never support a fact.

Photos: upload → quarantine → MIME sniff, size limit, scan → EXIF GPS becomes an unpublished location suggestion only → contributor confirms or declines → moderation → public derivative with EXIF stripped.

## 5. Tile pipeline (authorised offline ingest)

```
ingest/<layer>/   (outside Git; .gitignore already excludes rasters, pbf, pmtiles)
  1. check_rights(layer)  -> refuses unless GisSource.permission_status is approved/conditional-with-receipt
  2. download original product (logged: URL, checksum, vintage, CRS)
  3. transform (ogr2ogr / gdalwarp to EPSG:4326 source, EPSG:3857 display)
  4. build tiles: Planetiler (OSM) | tippecanoe (GeoJSON overlays) | gdal2tiles + rio-rgbify (raster, terrain)
  5. write manifest entry: attribution text, vintage, licence, build date, checksum
  6. publish to object storage behind our origin; style JSON references only our origin
```

A CI test parses the MapLibre style and fails if any source URL is off-origin. A second test asserts every layer in the style has a manifest entry with attribution.

## 6. H3 as a derived index

`Resource.h3_res_8` is computed on save from the PostGIS point and may be null. Uses: cache keys for pin GeoJSON by viewport cell; k-anonymous aggregate counts for an optional "resources per area" overlay at res 5–8; coarse res ≤ 6 for sensitive categories. Prohibited by code and test: any distance, travel time or person-location inference (H3-3, H3-4).

## 7. Agent (feature flag, read-only)

- Tools: `search_published_resources`, `search_events`, `get_public_map_feature`, `explain_source_and_freshness`. Each tool reads the projection only; no SQL, no private claims, no external calls.
- Decision rule: constrained expected utility with `abstain` and `explain_unknown` always available at utility 0; one optional question allowed per request when its EVSI is positive.
- Every answer writes a decision record (request id, retrieval sources, source versions, policy version, assumptions, confidence type, action proposed, user approval, result, timestamp, limitations) into the hash chain. Records lacking a field are rejected.
- Optional EFE explanation (risk, ambiguity) attached for governance reading; it does not choose.
- Budget: requests per day and tokens per request capped in settings; the flag defaults to off; costs are reported monthly against the $500–$1,000 annual envelope.

## 8. API surface (public, read-only)

`GET /api/resources?category&age&cost&community&access&page` → list with `p_current_band`, `last_verified_at`, `source_url`, attribution. `GET /api/resources.geojson?version=` → pins for the published projection. `GET /api/events?from&to`. `GET /api/manifest` → layer credits and vintages. No endpoint returns private claims, restricted coordinates or contributor identities.

## 9. Operations

Separate staging and production; migrations and tests in GitHub Actions against a PostGIS service container; backups restored on a schedule and the restore logged; admin MFA; minimum-privilege database role; rate limits; log retention policy; monthly governance report generated from the audit chain (counts of publications, corrections, redactions, agent abstentions).

## 10. Development environment note

The cloud sandbox used for this stage has no Docker daemon. The vertical slice will therefore run locally against SQLite + SpatiaLite for the fictional five records, with PostGIS exercised in CI and on staging. The `infrastructure/docker-compose.yml` remains the local developer path where Docker is available.
