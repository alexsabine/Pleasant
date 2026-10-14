# Pleasant Crescent — Claude Code implementation and research starter

**Prepared 14 October 2026 | Proposed for Del Norte County / Crescent City family-resource mapping**

This is a **code-and-design starter kit**, not a deployed website and **not a bundle of downloaded geospatial imagery**. No Google tiles, county-owned GIS data, protected-species observations, private records or API secrets are included. All maps intended for local use must first pass the per-layer rights checklist. The `data/` directory contains only synthetic examples and a dataset manifest.

## What is inside

* `CLAUDE.md` — project instructions for Claude Code, including delivery constraints.
* `docs/` — scope, sequencing, ethical rules, roles, mobile experience, pricing and success conditions.
* `licenses/` — source-by-source rights matrix and approval checklist for a **self-contained atlas**.
* `architecture/` — layered map specification, data flow, provenance, event history and optional H3.
* `phoenix_selected/` — **positive, actionable, accurately qualified** components selected from the Phoenix repository. Includes exact short excerpts, adaptation notes and provenance to source documents. This does **not** assert a CRR-specific Bayes-optimal theorem or verified AI compute savings.
* `research/` — Bayesian decision theory, Free Energy Principle (FEP), Active Inference (AIF), and constrained optimization; specific test protocols.
* `backend/pc_core/` — executable, dependency-free Python reference implementation of belief updating, value of information, bounded attention policies, Fisher–Rao diagnostics, and lossless historical event retention.
* `backend/tests/` — unit tests. Run `PYTHONPATH=backend python -m unittest discover -s backend/tests -v` from repo root.
* `backend/examples/` — executable synthetic scenario and sample data, never published as genuine listings.
* `infrastructure/` — a small PostgreSQL/PostGIS Compose environment and starter schema.
* `frontend/` — a MapLibre layer adapter outline for *your* locally hosted map tiles; not production client code.
* `integrations/` — Daniel Friedman GIS compatibility questionnaire, export/import contracts, optional messaging strategy.

### Added 14 October 2026, third pass: real nodes, fine H3, palette v2, living crescent

* **No fictional nodes.** 58 real listings (schools, early years, libraries, college, youth programmes, parks, beaches, playgrounds, museums, visitor centres, trails) summarised from official websites by two research sweeps, placed only from authoritative coordinates (state school directory, official page coordinates, named features in our own OSM tiles, or a logged address geocode) and published with the badge "Checked online". 16 candidates without an authoritative geolocation are held back in `data/verified/unplaced.json`. Method and caveats in `audit/verified_nodes.md`.
* **Family-group map layers.** Kim's nine launch groups drive the map switches and colours; technical layers moved under "Map details"; overlapping points cluster with counts, and co-located listings open one combined popup.
* **Fine H3.** Every public venue stores its exact containing cell at resolutions 8 to 12; the map draws the cell at a selectable resolution with a one-step halo. H3 nesting is only approximate (about 7% of points have a mismatched parent), so each resolution is stored, not derived. People-related and sensitive data remain coarse and k-anonymous.
* **Palette v2** (`web/tools/palette.py`): river, redwood and ocean hues fixed in OKLCH, lightness solved for WCAG 2.2 contrast targets, map fills checked for perceptual separation, light and dark variants, contrast ratios written into `tokens.json`.
* **Living crescent** (`backend/pc_core/crescent.py`): the logo's lit fraction is the mean P(current) of the directory; its terminator sits at the Fisher–Rao coordinate of that belief; breathing amplitude is the week's belief path length; ring marks count the week's changes. Explained on the About page; checks LOGO-1..4.
* Offline geocoder from our own tiles (`backend/ingest/geocode_local.py`), validated against the state school directory (median offset 121 m); zoom-15 tiles for the whole county.
* 36 mathematical checks and 31 reference unit tests pass; 12 Django tests pass.

### Added 14 October 2026, second pass: the first running platform

* `web/` — Django 6 + Wagtail 8 + GeoDjango site with the Explore list and map, This week, Local help, About, resource pages, a read-only JSON API, PMTiles served with HTTP Range support, a Wagtail admin with drafts, revisions and a Moderators-approval workflow, a hash-chained audit log, per-category hazard settings, and the embedded **Crescent Compass** agent (`web/compass/`). Run instructions in `web/README.md`. Screenshots in `design/screenshots/platform/`.
* `backend/ingest/` — logged, reproducible acquisition of the self-hosted basemap: Protomaps OSM build extracted by bounding box (ODbL), USGS 3DEP terrain via Terrain Tiles (public domain), Census TIGER 2025 boundaries (public domain). Tiles stay out of Git; `data/ingest_log.json` records URL, bytes, SHA-256, licence and attribution for every download.
* `web/static/style/` — the basemap style is generated from `tokens.json` by `web/tools/build_style.js`; glyphs, sprites and the three JavaScript libraries are vendored so browsing makes zero off-origin requests (verified by the screenshot run).
* `backend/examples/math_checks.py` now has 30 checks: a new `[AGT]` section for Compass (published recommendation threshold, grounding validator, bounded working memory, trust calibration over time, eleven-field decision records) and H3 sizing on the real Census county polygon.

### Added 14 October 2026 (stage one: audit, mathematics, system design)

* `audit/gis_basemap_audit.md` — desk audit of 38 basemap sources for Del Norte County with licence findings, offline fit, rights gate and a recommended zero-external-call stack. `licenses/layer_rights_matrix.csv` and `data/layer_manifest.json` were extended to match.
* `design/basemap_examples.html` — self-contained visual examples (six basemap styles, light and dark, and the list-first phone interface) on synthetic geometry; makes no network requests. Screenshots in `design/screenshots/`.
* `design/frontend_system.md` and `design/backend_system.md` — the coherent front-end and back-end system around Wagtail, PostGIS, MapLibre/PMTiles, the four memory layers, the review queue and the read-only agent.
* `research/04_mathematics_register.md` — every formula in use, its public source, its evidential status, what "Bayes-optimal" means in each of the three paradigms, the governance/transparency note, and the honest upper limits.
* `research/05_math_check_report.md` — generated by `backend/examples/math_checks.py` (25 numerical checks across Bayesian decision theory, Active Inference/FEP, Phoenix/CRR geometry, memory/governance techniques and H3).
* `backend/pc_core/` gained `pomdp.py` (exact small POMDP, EFE, VFE, Kalman gaps), `freshness.py` (survival model, review priority, calibration), `audit_chain.py` (hash-chained decision log), `h3_index.py` (guarded derived index), `closure.py` (operational closure and homeostasis). Tests in `backend/tests/test_math_checks.py`.

## Most important decisions

1. **Kim's contract is the baseline**: accessible mobile-first site, >= 40 **human-verified** entries, CMS, events, map or approved fallback, two organization-controlled admins, moderation, documentation, videos, two trainings and handoff. Eight weeks, $10,000 fixed planning envelope. Do not silently replace this with experimental AI research.
2. **MapLibre + Wagtail/Django + PostGIS** are the base. H3 is a derived spatial index for future aggregates, not a source of geography or road/travel time.
3. **No external map fetch per view**: produce your own properly licensed map tiles (vector roads + hydrography, raster orthophotos, terrain). Fetch data when *you choose* to ingest/update it; users view locally served tiles. Optionally provide Google View as a separate, officially integrated online-only tab, never cached/rehosted.
4. **Don't publish county GIS data without permission**: the county says its shared data are county-owned. Viewing or querying an ArcGIS service does not automatically grant redistribution rights.
5. **A small family directory is not a continual-learning GPU problem**. The LLM (if approved later) reads verified records; never retrains on user/private data by default.
6. **Bayes-optimal is conditional** on a declared prior, likelihood, feasible actions and utility. FEP/AIF is an optional normative decision formulation, not a proven improvement or unconditional guarantee.
7. **Keep event evidence** separately from compact working memories. An average can erase differences. Retention and deletion are governed by policy; never claim immutable storage is always appropriate.
8. **No child geolocation tracking or identifiable child profiles** in the proposed launch. Adults browse and filter resources by relevant age bands. Sensitive wildlife coordinates are protected.

## Suggested first Claude Code task

> Read `CLAUDE.md`, `docs/01_client_scope.md`, `licenses/layer_rights_matrix.csv`, `architecture/01_base_map.md`, and `architecture/02_data_and_memory.md`. Create a working Django/Wagtail/PostGIS/MapLibre vertical slice with **five clearly fictional** directory items and a public map; a contributor suggests an edit; an editor approves it; an admin checks the audit log. All writes must be server-authorized. First run the supplied reference unit tests, then run framework migrations and workflow tests. Document risks, licensing gaps, and what still needs the client to decide. Make no external GIS download or paid API call without explicit approval.

## Run reference checks

```bash
cd pleasant_crescent_code_pack
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
PYTHONPATH=backend python backend/examples/demo_decisions.py
PYTHONPATH=backend python backend/examples/math_checks.py --report research/05_math_check_report.md
```
Optional for the H3 checks: `python -m pip install h3` (pin the version in your lockfile).

## Documentation/source status

This package selects **actionable positive contributions** from Phoenix but keeps required scope limitations. It distinguishes:
- source-verified fact;
- derived mathematical identity;
- proposed implementable design rule;
- experiment yet to be tested.

All source URLs and licence checkpoints appear in `licenses/` and `phoenix_selected/SOURCE_INDEX.md`.
