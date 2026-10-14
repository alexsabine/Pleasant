# Daniel Friedman mapping-system interoperability: discovery only

Do not assume credentials, permission, format or guaranteed availability.

## Questions for the system owner
1. Who owns/controls geospatial layers, service access and onward redistribution?
2. Is there a REST/ArcGIS FeatureServer/WFS/WMS/OGC API, GeoJSON, GPKG or CSV export? Exact documented endpoints?
3. CRS / axis order / coordinate precision? Source geometry authority? Point/line/polygon?
4. Which identifiers are stable? How are deletions, revisions and conflicts communicated?
5. Authentication, rate limits, token rotations, service uptime, security model?
6. Which layers are public versus confidential (e.g. ecology, minors, private residences)? Who can publish?
7. Are one-way extracts permitted for local rendering? Are caching, offline access and commercial/funder use permitted?
8. What version/time fields and validation metadata exist?
9. How would a change made in Wagtail synchronize? One-way import safest for initial pilot; no unagreed bi-directional writes.
10. Who maintains the integration and how will failures be shown to editors?

## Integration approval gates
- `A` documented REST/GeoJSON pull with permission and import log.
- `B` authorised scheduled CSV/GeoPackage import with schema mapping.
- `C` embed/link to partner viewer if only display rights.
- `D` **fallback**: independent PostGIS-based atlas, so Kim's 8-week acceptance is not blocked.

## Data contract example
Input: `{source_id, title, geometry, category, description, last_updated, licence, sensitivity, source_url}`.
Output: approved map `Feature`/directory entry with fields mapped explicitly. Rejected: missing provenance, disallowed licence, unmatched CRS, protected precise location, conflicting update without review.

## Test cases
- Coordinate reference: known test point round-trips within declared tolerance.
- Deleted or renamed record not silently resurrected.
- Repeated import of same revision is idempotent.
- Restricted data never appears in public tiles/API.
- Partner outage leaves independently hosted family directory functional.
