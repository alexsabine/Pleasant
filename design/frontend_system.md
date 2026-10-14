# Front-end system: a list-first, map-optional atlas

The owner supplies the aesthetics: palette, photography, crescent branding, typography. This document fixes the *system* underneath so that any palette produces a coherent, accessible, fast product. Visual examples are in `design/basemap_examples.html` (self-contained, no network) and `design/screenshots/`.

## 1. Principles

1. **List first, map second.** Every map interaction has a list or form equivalent. The map is a view of the same filtered result set, never the only way to reach a listing.
2. **Calm basemap, loud facts.** The basemap is low-contrast and desaturated so that the directory pins, cost, age band, access status and last-verified date are the brightest things on screen.
3. **Freshness is visible.** Every card and pin shows "verified 12 days ago" (from `last_verified_at`) and the P(current) band in words: *recently verified*, *verified this season*, *needs re-check*. Never a fake percentage on scant data.
4. **Unknown is a state, not a gap.** Accessibility `unknown` renders as a distinct neutral token, never as "accessible" and never hidden.
5. **One optional question at a time.** No gates, no forced login, no location permission prompt on arrival.
6. **Attribution is part of the layout**, not an afterthought: a persistent, legible credit strip with dataset vintages.

## 2a. Palette v2: river, redwoods, ocean (14 October 2026)

The palette is generated, not hand-picked, by `web/tools/palette.py`. Hue and chroma anchors are fixed in OKLCH (river teal 192°, river emerald 160°, Pacific 236°, redwood bark 32°, redwood needle 145°, sand 80°, fog 215°, kelp 120°) and lightness is solved by bisection so that every text/background pair meets its WCAG 2.2 target: primary text 10.5:1, secondary 5.5:1, links and buttons 4.5:1 on white and white on the accent, map labels 4.5:1 on land. Map fills are checked for perceptual separation (ΔE_OK ≥ 0.04 between land, water, park and road), with water the only blue family and parks the only green family. A dark variant is solved the same way. The resulting contrast ratios are written into `tokens.json` so a reviewer can read them without running anything.

## 2b. The living crescent

The logo is a gauge. Its lit fraction is the directory's mean estimate that listings are still current; the terminator sits at the Fisher–Rao coordinate θ = 2·asin(√p) of that belief (the angle Phoenix/CRR integrates on the Bernoulli family), so the arc between two states is the information distance between them. A gentle 14-second breathing animation spans the distance the belief moved over the last week; small marks on the ring count publications and verifications in that week. It is rendered server-side as inline SVG (`backend/pc_core/crescent.py`, cached ten minutes), respects reduced-motion, carries its three numbers in its accessible name, and is available at `/logo.svg`. Checks LOGO-1..4 verify it is faithful (lit fraction equals p to 1e-16, area monotone, no external references).

## 2d. Family-group layers and clustering (Kim's categories)

The map's main switches are Kim's launch groups, in her order: parks and playgrounds; pools and indoor recreation; attractions; rivers and beaches; hiking and nature; learning and STEM; arts; libraries and family services; programs, events and people to call. Every listing category maps to exactly one group (`CATEGORY_GROUP` in `atlas/models.py`) and each group has a solved colour (nine hues, lightness varied, pairwise ΔE_OK ≥ 0.07, each at least 3.2:1 on white) used for points, venue cells, list tags and the legend. Technical layers (H3 cells and their resolution, terrain, county and city limits, Tribal boundaries, the k-anonymous aggregate) sit under a collapsed "Map details" section.

Points cluster when they would overlap (MapLibre clustering, radius 34 px, up to zoom 15). Clicking a cluster zooms to separate it; if its members share one point (several programmes at one address) or the map is already at street zoom, a combined popup lists them instead. Venue cells appear from zoom 13.

Why nodes bunch: several listings legitimately share a point or a block. The Del Norte Child Care Council, its Wonder Bus and the Mary Peacock after-school programme are one organisation at one address; Del Norte High, Bess Maxwell, Del Norte Community School and Castle Rock Charter share one campus block on El Dorado Street; the library, Pyke Field, the Recreation Department, Crescent Elk Middle and Joe Hamilton Elementary sit within two blocks downtown; the Hiouchi visitor centre, the Jedediah Smith day-use area and the Nature River Trail are one site. That is the town's real geography, not a placement error, and the combined popup makes it legible.

## 2c. H3 venue mapping

Every public venue stores its exact containing H3 cell at resolutions 8 to 12 (about 460 m, 175 m, 65 m, 25 m and 9 m across). H3 hexagons are only approximately nested, and about 7% of points have a resolution-11 cell whose parent is not the point's own resolution-10 cell, so each resolution is stored independently rather than derived. The map draws the exact cell at the chosen resolution with a one-step halo; a selector switches resolution live. Sensitive places and anything about people never get fine cells; they appear only in the coarse k-anonymous aggregate.

## 2. Design tokens (the owner changes values, not structure)

```
--pc-bg            page background
--pc-surface       cards, sheets
--pc-ink           primary text (contrast >= 7:1 on bg)
--pc-ink-2         secondary text (>= 4.5:1)
--pc-accent        one brand colour for primary actions and selected pins
--pc-free          "free" badge
--pc-unknown       neutral token for unknown access/cost
--pc-verified      verified-recently indicator
--pc-stale         needs-re-check indicator
--pc-map-land / -water / -park / -road / -road-casing / -label / -hillshade
--pc-radius, --pc-shadow, --pc-space-1..6, --pc-font-ui, --pc-font-display
```

Light and dark variants are required; the map style is generated from the same tokens so the basemap and the UI never disagree. A single JSON token file is the contract between the owner's palette and both the CSS and the MapLibre style (Maputnik-editable).

## 3. Information architecture (from `docs/03_mobile_experience.md`)

| Tab | Default view | Map role |
|---|---|---|
| Explore | filtered list, 12 per page, "Show on map" toggle | pins for the current page of results only |
| This week | date-grouped event list with expiry state | optional pins with directions link |
| For my family | age band, budget, access needs, "few / standard / all" dosage | none |
| Local help | services list with source and contact | optional |
| About / feedback | licences, governance, correction form | credits and dataset vintages |

## 4. Components

- **ResourceCard**: name, type chip, age band, cost token, access token, distance-from-chosen-place (never from covert location), verified-ago, source link. Compact and detailed variants.
- **FilterBar**: category, age band, cost, community, access. Chips are real `<button aria-pressed>` elements; state lives in the URL so results are shareable and keyboard-reachable.
- **MapPanel**: MapLibre GL with the PMTiles protocol, local style, layer switches as a checkbox list (`<fieldset>`), keyboard-navigable pin list mirrored beside the map, "list view" always one tap away.
- **LayerSwitcher**: streets (default on), terrain, aerial (if licensed), parks and trails, hazards (off, with disclaimer), H3 aggregate (off, debug). Each switch shows its attribution and vintage inline.
- **FreshnessBadge**: three states from P(current) bands, with the verification date as the accessible name.
- **CreditStrip**: generated from the layer manifest; never hidden on mobile, collapsible to one line.
- **Editor components** (Wagtail admin): claim panel with epistemic type, map point picker with coordinate display and EXIF-suggested point requiring confirmation, review queue ordered by the published priority with the EVSI explanation shown in words.

## 5. Map rendering rules

- Sources are `pmtiles://` URLs on our own origin. No tile URL may point off-origin; a CI test asserts this against the style JSON.
- Basemap vector tiles from OSM (Planetiler or Protomaps extract) at z0–z14; terrain-RGB from 3DEP at z8–z13; optional NAIP raster at z12–z17.
- Directory pins come from a small GeoJSON per published projection version, not from the tile build, so publishing never requires re-tiling the basemap. Cache key = projection version plus H3 res-7 cell of the viewport.
- Default zoom shows Crescent City at z13; the county at z10. Labels never fall below 14 px on phones.
- Reduced-motion users get no fly-to animations. All controls have 44 px touch targets.
- Hazard layers render with a dashed boundary and a visible "planning map, dated YYYY, not an alert" label on the map itself.

## 6. Offline and resilience

- A service worker caches the app shell, the style, the tokens, and tiles the user has viewed (own origin only, bounded storage). Last-seen listings render from cache with a "viewed offline, verified on DATE" banner.
- Partner outages, API outages and tile outages each degrade to the list view with a plain message. No spinner longer than 2 s without text.

## 7. Accessibility acceptance (WCAG 2.2 AA)

Keyboard path through every filter, card and map pin list; focus visible; form labels and errors; alt text on photos (AI draft labelled as draft, human-approved before publish); contrast tokens validated in CI; no information conveyed by colour alone (freshness and access tokens carry icons and text); target size 24 px minimum, 44 px on primary actions; reduced-motion respected; a text-only mode toggle.

## 8. What is deliberately not built

No child profiles, no route tracking, no notification storms, no popularity ranking, no "nearby now" without an explicit chosen place, no photo implying current access without a verified claim.
