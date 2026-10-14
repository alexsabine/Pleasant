# H3 and basemap optimisation: what was checked, what was changed

Third iteration (October 2026). Companion to `research/06_landmapping_report.md` (generated), `research/07_compass_tuning.md` (generated) and `research/08_trust_check.md` (generated).

## 1. The land data the H3 grid was checked against

| Layer | Source | Why it is the most robust available | Used for |
|---|---|---|---|
| County polygon (06015) with ALAND/AWATER | U.S. Census TIGER/Line 2025 | Legal boundary; official land and water areas | L1 containment, L6 coverage |
| Place polygons (Crescent City city limits) | TIGER/Line 2025 | Legal city boundary (small; most "Crescent City" addresses are outside it) | L2 |
| Elevation | USGS 3DEP via AWS Terrain Tiles (terrarium, z7–z13) | 10 m lidar-derived DEM, public domain | L4 water/pier sanity, L5 cell footprint, L6 land/water share |
| Roads, paths, names | OpenStreetMap via Protomaps (ODbL), our own tiles | Only source with trail geometry at this scale | geocoding and display |

Aerial imagery (NAIP) is logged as available but not used for placement: nothing is placed from image recognition (CLAUDE.md rule 5).

## 2. Results (58 live venues, 6/6 checks)

- Every venue lies inside the county polygon. Nineteen of the 33 "Crescent City" venues lie inside the city limits; the other 14 are within 10 km (schools, state-park trails and overlooks with Crescent City postal addresses). The report lists them so the community label can be discussed with Kim.
- Every stored H3 cell (res 8–12) is the exact containing cell of the venue point, and every point lies within its res-11 cell's own circumradius (largest offset/circumradius 0.88).
- Elevations are plausible everywhere: the only sub-zero reading is B Street Pier, which stands over water. River sites sit within 30 m of their local valley floor (Panther Flat is 161 m above sea level because the Smith River is; "near sea level" was the wrong test and was replaced).
- The median elevation range across a res-11 cell is 2 m; the largest is 42 m at Crescent Beach Overlook, which is the sea bluff itself.
- Res-9 cells covering the county total 3,180 km² against TIGER's 3,185 km² (0.1 % off); 16.5 % of sampled cell centres are at or below sea level against TIGER's 18.2 % water share (the county extends three nautical miles offshore).

## 3. Resolution choices, with the numbers behind them

| Use | Res | Cell size (edge / area) | Reason |
|---|---|---|---|
| Public aggregates, sensitive places | ≤ 8 (sensitive ≤ 6) | res 8 ≈ 461 m / 0.74 km² | k-anonymity (k ≥ 5); cannot single out a house |
| County coverage, cache keys | 9 | ≈ 174 m / 0.105 km² | 31,156 cells cover the county; matches official area to 0.1 % |
| Map "venue cell" at z ≥ 13 | 11 | ≈ 25 m / 2,150 m² | Faithful footprint (median 2 m elevation range) without implying survey accuracy |
| Exact containment record | 8–12 stored separately | res 12 ≈ 9.4 m | H3 nesting is approximate (~7 % of a child's area lies outside its parent), so each resolution is computed from the point, never derived by parent/child |

## 4. What was optimised in this pass

1. **Database indexes** on `h3_res_8`, on the public-projection filter (`live, visibility, is_sensitive`) and on the facet pair (`category, community`) (migration 0006). On PostGIS the same migration applies unchanged.
2. **Landmapping check script** (`backend/examples/landmapping_checks.py`) now encodes the real geography: pier allowance, valley-floor test for river and beach sites, bluff allowance, water share compared with TIGER rather than assumed.
3. **Basemap** unchanged in content; the audit stands (own-origin PMTiles, zero off-origin requests, verified again by trust check T8). The corridor z15 extract remains the fine-detail source for Crescent City and the Smith River corridor; the county-wide extract stops at z14.
4. **Compass** tuned from the repository mathematics: per-category hazard priors in two declared classes (places, programmes), the show rule cross-checked against the exact finite-horizon POMDP over Compass's own actions, a derived steward workload (3.3 checks/week keeps every listing recommendable), and a 34-question intent sweep with keyword fixes (tide pools no longer parse as a swimming pool; "after school programs" no longer returns schools).

## 5. Still open

- Community labels for the 14 out-of-city "Crescent City" venues (Kim's call: postal area or nearest community).
- Human verification: 0 of 40; the review queue orders the work.
- Tsunami Lanes and several programme-type places from Kim's draft have no official page we could find; they stay out until a source exists.
