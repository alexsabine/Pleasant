# Verified nodes: how every real listing was checked and placed

**Date:** 14 October 2026. **Method:** official web sources read by an automated assistant, then placed from authoritative coordinate sources. **Not** a human site visit. Every listing shows the badge "Checked online" and its geolocation source on the site. Nothing without an authoritative geolocation is published.

## Sources

- **Educational providers** (`data/verified/education.json`): 36 entries researched from dnusd.org, school sites, tolowa.gov, yuroktribe.org, Del Norte Child Care Council, Family Resource Center of the Redwoods, UC Cooperative Extension, College of the Redwoods, the California State Library's library-location file. 12 candidates were dropped for lack of an official page (for example the SDA and Foursquare Christian schools, Del Norte Reads, First 5 Del Norte whose site returns 404). There is no Boys & Girls Club in the county.
- **Attractions and trails** (`data/verified/attractions.json`): 41 entries from nps.gov, parks.ca.gov, fs.usda.gov, wildlife.ca.gov, co.del-norte.ca.us, crescentcity.org, delnortehistory.org, oceanworldonline.com, treesofmystery.net, northcoastmmc.org and ccharbor.com. 11 dropped (no official page, or covered by another entry).
- **Zoom-15 tiles** were extracted for the Crescent City to Hiouchi and Klamath corridor so that more named parks, viewpoints and trails could be matched offline (Klamath River Overlook was placed this way).
- **Coordinates**: the California Department of Education public school directory (`data/verified/cde_schools.json`, 15 active Del Norte schools with coordinates), official page coordinates where the researcher found them (State Parks map links, Forest Service, City of Crescent City), and named features in our own OpenStreetMap-derived basemap tiles (`data/verified/osm_names.json`, built by `backend/ingest/geocode_local.py`).

## Placement rules (`backend/ingest/placer.py`)

Order of authority: official page coordinates → state school directory → exact named feature in our tiles of the right kind → logged geocode of the official street address (OSM Nominatim, identified user agent, one request per two seconds) → fuzzy named feature of the right kind. A fuzzy match must contain the listing's most distinctive word and most of its words; place names (Del Norte, Crescent City, Smith River, Klamath) count for nothing. Every candidate must fall within the listing's community radius. When an address geocode and a named feature disagree by more than 300 m, the named feature of the right kind wins (that is how the Historical Society museum was kept at its building rather than at the lighthouse the address resolved to). Every decision is logged in `data/verified/geocode_log.json`.

The offline geocoder was validated against the state directory: for the six schools present in both, the median offset is 121 m and the largest 252 m (check GEO-1).

## Result

58 listings published and mapped with exact H3 cells at resolutions 8 to 12; 16 unplaced, written to `data/verified/unplaced.json` and **not** shown on the map:

| Unplaced | Why |
|---|---|
| Sunset Early Head Start Center; Northcoast Children's Services Infant Toddler Center; Harmony & Me (Wonder Forge); Tolowa Dee-ni' Howonquet Early Learning; Yurok Head Start (Klamath) | Street address did not resolve to a building in OpenStreetMap; needs a human to confirm the point |
| Fraser Park; Peterson Park skate park; Florence Keller Regional Park; Ruby Van Deventer County Park; Lake Earl Wildlife Area | Not named in our tiles and no official coordinates; county pages give only cross-streets or directions. (Ruby Van Deventer matched a feature named only "County park" and was rejected by the distinctive-token rule.) |
| Lagoon Creek; False Klamath Cove; Howland Hill Road; Stout Memorial Grove Trail; Enderts Beach / Coastal Trail sections | NPS pages give directions, not coordinates; the trail or feature is not named in our tiles even at zoom 15 (Stout Grove appears only as a service road, which the trail rule does not accept) |

These are the first candidates for a human verifier with a phone: standing at the entrance and recording the point takes a minute each and upgrades the listing to "Visited".

## Caveats recorded by the researchers

- The CDE school directory website blocked the researcher after a few pages; grade spans for district schools were inferred from school pages and should be checked against the directory file we hold (it has `GSoffered` for every school).
- The Del Norte County Library District website was unreachable (503) during research; library hours are unconfirmed.
- NPS no longer publishes visitor centre hours on its pages; both say to call.
- Trees of Mystery admission and the pool fees change; both carry their check date.
- Current NPS conditions on 14 October 2026: Stout Grove seasonal footbridges removed; Boy Scout Tree Trail blocked by a fallen tree 1.75 miles in; Damnation Creek trailhead closed; Mill Creek day-use area closed on weekdays. These are stated on the listings as warnings, not as live status.
- Tribal boundaries are drawn from Census AIANNH data for reference only; names of Tribal nations and any content about their programmes should be confirmed with each Nation before public launch.

## What a human verifier does next

For each listing: open the official page linked on the listing, confirm the facts shown, visit or phone, and mark the claims verified in the admin (Atlas → Claims). The verification method then changes to "Visited" and the listing counts toward the 40 human-verified records in the contract. None of the 58 online-checked listings counts yet.
