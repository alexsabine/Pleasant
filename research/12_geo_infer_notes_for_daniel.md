# GEO_INFER and GNN: notes for the conversation with Daniel Friedman (October 2026)

Both repositories are by the Active Inference Institute (Daniel Friedman, Director) and licensed CC BY-NC-SA 4.0.
Crescent Compass takes ideas and writes its own code, or agrees terms first. Items marked "verified" were checked
directly in the source; the rest come from a read-only review.

## Ideas Crescent Compass would like to adopt

1. Per-layer rights and provenance records with source query, hashes of raw and output files, use constraints and an
   explicit "unresolved" list (`GEO-INFER-PLACE/.../cascadia/config/cascadia_layers.provenance.json`). Extends our
   `licenses/layer_rights_matrix.csv`.
2. Feed-health states ok / empty / unavailable / stale with a checked-at time (`GEO-INFER-BAYES/.../geo_observations.py`),
   for a safety banner that never shows "no alerts" when a feed is down.
3. Strict timestamps: reject naive times and bare epochs, never silently re-sort (`GEO-INFER-TIME/.../timestamps.py`).
4. "Every stated number traces to a measured value" documentation contracts (`GEO-INFER-TEST/.../documentation_contracts.py`),
   a pattern for Lumen's honesty check.
5. Honest experiment reporting with a reference condition, ablations and censoring (`GEO-INFER-ACT/docs/cascadia_seed_study_20261012.md`),
   a template for our rule that Active Inference needs a native baseline and metric.
6. Representation index (`GEO-INFER-CIV/.../participation.py`), applied to communities to guide steward invitations;
   see research/11_stewardship_pathway.md.

## Public data sources named in GEO_INFER that we could read directly

NOAA CO-OPS tides station 9419750 (Crescent City); NWS alerts zone CAZ006 and Eureka marine forecast; USGS earthquake
feeds and NWIS; NDBC buoys; Census ACS. Federal sources are public domain; state sources need their own licence check.

## Questions to ask

- May we cite the municipal-code mapping in the Crescent City civic-intel contract, and is it reviewed against the official code?
- Is the Smith River salmon model meant for any local use or outreach?
- How does the Institute want GNN files written by others to be credited, given the non-commercial licence and a paid delivery?
- Would the Institute like Crescent Compass's GNN file and compatibility check (research/gnn/, research/10_gnn_compatibility.md)?

## Small fixes we can offer back (friendly, verified in source)

- `GEO-INFER-NORMS/src/geo_infer_norms/core/normative_inference.py` lines ~362-374: both branches of the Bayesian update
  reduce to `c*p / (c*p + (1-c)(1-p))`, so a non-compliant verdict gives the same probability as a compliant one.
  With no observations the function returns `(False, 0.0)`, which yields compliance probability 0: missing data is
  read as certain non-compliance. (verified)
- `GEO-INFER-PLACE/.../del_norte_county/config/analysis_config.yaml` line 18 labels EPSG:2227 as California State Plane
  Zone I; EPSG:2227 is Zone III (Zone I is EPSG:2225). (verified)
- `GEO-INFER-PLACE/.../del_norte_county/coastal_resilience_analyzer.py` lines ~668-670 carry fixed figures
  (population at risk 8,500; 12 operational sirens) without a source, and line ~787 stamps data_quality "high" with
  `last_updated = now()`, so stored figures look freshly checked. (verified)
- Reported, not yet checked by us: an environment switch that disables TLS certificate checks in the Cascadia downloader,
  and a tribal-territory point for the Tolowa Dee-ni' Nation without a consent note.

## GNN compatibility (summary of research/10_gnn_compatibility.md)

Our freshness model writes into GNN notation losslessly (two state factors) and round-trips exactly. GNN's standard
one-step expected-free-energy choice differs from our Bayes-optimal show rule: with utilities as log-preferences it shows
a listing iff lambda*E[U] + H(p) > 0, which recommends below the 0.75 threshold at low preference precision and converges
to it as precision grows. Live decisions stay Bayesian; GNN serves documentation and an offline baseline.
