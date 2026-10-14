# Pleasant Crescent — binding instructions for Claude Code

## Mission
Build an accessible, mobile-first Del Norte County activities and resources atlas for **caregivers of children aged 0–18**, local organizations and newcomers. Website is an intuitive directory first, conversational agent second. Allow the owner to guide visual/aesthetic design directly.

## Client acceptance (do not omit)
- >=40 sourced, human-verified family activity/resource listings. Required: name, type, age suitability, price/free, location, access notes (including UNKNOWN), link/contact, last-verified timestamp.
- Category, age, cost and community filters, usable without an interactive map; responsive across devices.
- One-off and recurring calendar events with expiry/archival controls and map/directions links.
- CMS: two independent organizational admins plus editor and moderated contributor roles. Public submissions never auto-publish.
- Geo mapping feasibility memo with Daniel Friedman or project rep; no assumed access. GIS display, CSV, GeoJSON and service integration options; offline/fallback.
- WCAG 2.2 AA review, keyboard navigation, functional accessibility, privacy/contact information and basic analytics.
- Editable manual + PDF, 3–5 short tutorial videos, two practical trainings and organization-controlled account/assets inventory and handoff.
- $10,000 fixed delivery planning envelope, eight weeks, milestones and written client acceptance. Recurring allowance $500–$1,000/year; premium paid services require approval.

## Chosen architecture (subject to approved changes)
Django/Wagtail CMS + PostgreSQL/PostGIS + MapLibre + self-hosted licensed terrain/vector/raster tiles. Optional H3 index. Object storage for photos. Claude API agent behind feature flag, **read-only initially**.

## Rules
1. Never claim an unverified activity is current. Label fixtures and unverified content as such; do not count them toward 40 accepted records.
2. Do not ingest third-party GIS assets until data rights are logged as `approved`. ArcGIS REST export capability does not imply republishing rights. Never rehost Google/Esri provider tiles without specific permission.
3. Store attribution, source URL, licence, acquisition date, CRS and data version for every layer. Permit offline browsing of our **own** licensed tiles without live external GIS requests.
4. Maintain separate layers for: original evidence, versions/claims, current approved projection, compressed task context. Classify claims as `observed`, `reported`, `inferred`, `generated`, or `simulated` and do not conflate them.
5. Never invent location accuracy from image recognition: EXIF GPS may propose a private location; users must confirm; absent EXIF ask for location. Strip GPS metadata from published thumbnails. Do not expose children's homes/locations or sensitive species sites.
6. Enforce role/object permissions in backend; no LLM-authored policy overrides. Publishing, third-party messaging, location sharing and role grants need server enforcement and, where appropriate, user approval.
7. Do not automatically rank popularity as worth. Respect hard preferences, uncertainty and underrepresented resource categories. No optimisation to manufacture synchronicity.
8. User-controlled attention, mute/abstain, and optional personal settings. No covert location collection. Support anonymous public browsing and accessible list-based alternatives to maps.
9. Each development slice: test -> review -> capture screenshots -> report acceptance status -> commit, never silently deploy to production.
10. Treat Phoenix/FEP/Active Inference as research guidance, not an excuse to replace proved existing methods. All algorithm claims need a native baseline and defined metric.

## Work order
First get a 5-item **synthetic** vertical slice operating end-to-end. Then verify 40 real listings with humans. Then polish CMS and accessibility. Keep advanced AI, WhatsApp, private fog, global network and CL/GPU as separate optional projects.

## Source links
See `phoenix_selected/SOURCE_INDEX.md`, `licenses/layer_rights_matrix.csv`, `docs/01_client_scope.md`.
