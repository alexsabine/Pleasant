# Front-end system: a list-first, map-optional atlas

The owner supplies the aesthetics: palette, photography, crescent branding, typography. This document fixes the *system* underneath so that any palette produces a coherent, accessible, fast product. Visual examples are in `design/basemap_examples.html` (self-contained, no network) and `design/screenshots/`.

## 1. Principles

1. **List first, map second.** Every map interaction has a list or form equivalent. The map is a view of the same filtered result set, never the only way to reach a listing.
2. **Calm basemap, loud facts.** The basemap is low-contrast and desaturated so that the directory pins, cost, age band, access status and last-verified date are the brightest things on screen.
3. **Freshness is visible.** Every card and pin shows "verified 12 days ago" (from `last_verified_at`) and the P(current) band in words: *recently verified*, *verified this season*, *needs re-check*. Never a fake percentage on scant data.
4. **Unknown is a state, not a gap.** Accessibility `unknown` renders as a distinct neutral token, never as "accessible" and never hidden.
5. **One optional question at a time.** No gates, no forced login, no location permission prompt on arrival.
6. **Attribution is part of the layout**, not an afterthought: a persistent, legible credit strip with dataset vintages.

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
