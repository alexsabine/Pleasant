# Cost, scaling and known project risks

## Separate capital and operations
- Kim's contractual **development** planning envelope: $10,000 fixed across five accepted milestones.
- Her **annual operations** allowance: $500–$1,000 ($42–$83/month). This is a constraint, not a validated vendor quote.
- H3, PostGIS, Wagtail, Django and MapLibre have no software license charge under their respective open-source licences.
- Hosting a modest server, domain, backups, email and basic object storage may fit the envelope if self-managed. Paid AI calls, commercial GIS and high-resolution imagery **egress/storage** may push beyond it; get written approval.
- Source-code and software deployment on GitHub; private observations, photos and huge rasters in database/object storage, NOT committed to Git.

## Risks
- 40 listing verifications, tutorials, training and staff testing are a larger schedule risk than adding an H3 grid.
- County data are county-owned: public viewing does not imply permission for offline reproduction.
- High-resolution aerial imagery requires selection of *downloadable source products*, clipping, tile production and adequate storage. Compute size before acquisition.
- OSM extract share-alike/attribution for derivative databases: maintain boundary between OSM-derived roads and separately sourced community directory.
- Locally cached emergency data go stale: surface timestamp and link to the authoritative live source for safety-critical decisions.
- AI hallucination, prompt injection and unsafe publication: keep the LLM read-only and human review for writes in pilot.
- Image EXIF may expose a child's home or sensitive wildlife location. Require confirmation and selective publication.

## Governance and maintenance
A working site does not maintain itself: budget staff time for expired-event checks, directory reviews, accessibility regression, patch updates, backup restores and security.
