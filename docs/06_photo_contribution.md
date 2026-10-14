# Photo upload -> optional location suggestion -> human confirmation -> publication

## What can be automated
1. Adult authorised contributor uploads a photo in the CMS, not via arbitrary execution tools.
2. The backend validates file size, MIME/type and malware risk as appropriate; quarantines original in restricted storage.
3. If GPS EXIF is present, it produces an **unpublished location suggestion**. If no GPS exists, don't infer exact coordinates from background scenery or an LLM caption.
4. Contributor reviews map point, source, public/private choice and map sensitivity; edits or declines geotagging.
5. Optional LLM proposes a brief caption with explicit "AI draft" status. It can describe what's visible but must not claim verified species/people/land access.
6. Moderation checks public suitability, copyright, privacy, wildlife sensitivity, age appropriateness and factual claims. Staff approves.
7. Public derivative strips EXIF/private metadata; writes an approved `resource_claim`, revision and new public map projection. Retain only the authorised original as policy permits.
8. Later corrections make new versions; remove unlawful/withdrawn personal content and dependent cached summaries.

## Example
User submits a sand-dollar photo. The agent may draft: "Photograph shows a sand-dollar-like marine specimen. Species and exact collection location not verified." It may ask the user to place a pin manually or confirm EXIF coordinates. A sensitive observation remains private or is coarsened under a documented rule. Never auto-publish an ecological observation with exact location solely because image metadata exists.

## What compaction may and may not do
Summaries can merge repeated routine descriptions while **preserving source references, timestamps and contradictory exemplars**. Do not average geographically or semantically distinct accounts into "the community thinks X". The official published projection is human-curated and contestable.
