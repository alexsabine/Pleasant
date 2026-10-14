# Basemap source audit for Del Norte County and Crescent City

**Status:** desk audit, verified 2026-10-14 by reading licence and landing pages only. Nothing was downloaded. This is an engineering rights assessment, not legal advice. Every row below should be re-checked against the exact product file before an importer is unlocked (see `licenses/RIGHTS_CHECKLIST.md`).

**Goal of the basemap:** a calm, family-oriented map of Del Norte County served entirely from Pleasant Crescent's own storage. Browsing must make zero live calls to source agencies. Data is fetched only when an administrator chooses to ingest or refresh it, with a logged approval per layer.

## 1. Recommended minimum viable stack (zero external calls)

| Role | Source | Licence | Gate |
|---|---|---|---|
| Streets, paths, labels, water, land use, POIs | OpenStreetMap via Geofabrik `norcal` extract, built with Planetiler into PMTiles. Alternative: Protomaps daily build, extracted by bounding box with `pmtiles extract`. | ODbL 1.0, "© OpenStreetMap contributors" | approved_with_attribution; ODbL share-alike applies to any derivative *database* we publish, so the civic directory is kept in a separate database |
| Low zooms (z0 to z6) | Natural Earth (bundled by Planetiler) | Public domain, no credit required | approved_with_metadata |
| County, city, Tribal land boundaries | US Census TIGER/Line 2025 (county 06015, Crescent City place, AIANNH) | US Government work, cite Census | approved_with_attribution; AIANNH are statistical, not legal, boundaries |
| Rivers, lakes, coast | USGS National Hydrography / 3DHP plus NOAA CUSP shoreline | Public domain, credit USGS and NOAA | approved_with_attribution |
| Parks and open space | CPAD (GreenInfo Network) | CC BY per CNRA/data.gov catalogue; GreenInfo's own site states no licence | **conditional**: confirm the licence file inside the 2026a release before import |
| Federal trails and recreation | NPS boundaries and trails (Redwood NSP), USFS FSGeodata (Six Rivers NF, Smith River NRA), BLM California | Public domain, credit requested | approved_with_attribution; NPS trails item needs a per-item metadata check |
| State park units inside Redwood NSP | California State Parks GIS | Attribution mandatory; commercial use needs prior approval; "may not be sold or altered" | **conditional**: a short permission email to geodata@parks.ca.gov; otherwise CPAD plus OSM for those units |
| Terrain and hillshade | USGS 3DEP 1/3 arc-second seamless, 1 m where lidar exists, converted locally to terrain-RGB with GDAL / rio-rgbify | Public domain, credit USGS | approved_with_attribution |
| Optional aerial | USDA NAIP, California 2022 vintage, 60 cm, via AWS `naip-visualization` COGs (requester-pays) or EarthExplorer | Public domain, credit USDA-FSA | approved_with_attribution; size the storage and egress before acquisition |
| Optional highway shields and bike routes | Caltrans GIS open data | CC BY 4.0 by policy (policy document is internally inconsistent; read the per-dataset licence field) | approved_with_attribution |

Styling: Protomaps "light" or "grayscale" theme, or VersaTiles "muted" or "gray" (CC0 / MIT), edited in Maputnik to the owner's palette. The style files carry no attribution burden; the tile data does.

## 2. Full source register

Legend for *gate*: `approved_with_metadata` (public domain, record provenance), `approved_with_attribution` (open, credit required), `conditional_*` (usable after a named human decision), `needs_written_permission`, `blocked`, `unknown`.

### Existing matrix rows, re-verified

| id | Source | What it gives us | Licence finding | Offline fit | Gate |
|---|---|---|---|---|---|
| NAIP_USGS | USDA NAIP via USGS EROS | Aerial raster | Public domain. CA 2022 InPort record: "The USDA-FSA Aerial Photography Field Office asks to be credited in derived products." No 2024 CA release confirmed. | yes | approved_with_attribution |
| 3DEP_USGS | USGS 3DEP | DEM, hillshade | "All 3DEP products are available, free of charge and without use restrictions." | yes | approved_with_attribution |
| OSM_NORCAL | Geofabrik Northern California | Vector base | ODbL 1.0; near-daily; `.osm.pbf` about 623 MB | yes | approved_with_attribution (ODbL) |
| CPAD | California Protected Areas Database | Park polygons | CC BY only in catalogue metadata; GreenInfo site shows only a copyright line; current release 2026a (June 2026) | conditional | conditional_confirm_licence |
| NPS_TRAILS | NPS open data | Trails, boundaries | "generally considered in the public domain"; credit appreciated; Arrowhead logo needs permission | yes | approved (boundaries) / conditional_verify_item (trails) |
| COUNTY_GIS | Del Norte County GIS | Parcels, addresses | No licence. Verbatim: "The shared data are a dataset owned and maintained by the County of Del Norte." No download offered. | no | needs_written_permission |
| CGS_TSUNAMI | CGS Tsunami Hazard Area | Hazard polygons | "intended for local jurisdictional, coastal evacuation planning uses only"; "not legal documents"; © State of California | conditional | conditional_purpose_statement (overlay only, with verbatim disclaimer) |
| CDFW_BIOS | CDFW BIOS | Biological layers | No blanket licence; per-layer, some password-protected | conditional | conditional_per_layer; none for basemap |
| INAT | iNaturalist | Observations | Default CC BY-NC; per-observer | conditional | conditional_nc_only; none for basemap |
| CALFLORA | Calflora | Plant observations | Non-image data dedicated to public domain, but TOS §4.1(a) bars reproducing "a significant portion of the ... underlying database" | conditional | conditional_bulk_restriction; none for basemap |
| DWR_LAND | DWR land use via CNRA | Land-use polygons | CNRA: "considered public and may be distributed or copied. Use of appropriate credit is requested." | yes | approved_with_attribution |
| GOOGLE | Google Maps Platform | Provider tiles | Terms page not machine-readable this session; policy is no caching or bulk download | no | blocked (optional live Google tab only) |
| CALTRANS_QUICKMAP | Caltrans QuickMap | Live traffic | Feeds via CWWP under Caltrans Conditions of Use; embedding "not recommended" | no | conditional_feeds_only; link out, never cache as current |
| FRIEDMAN | Partner system | Unknown | Unknown | unknown | needs_written_permission |

### Additional candidates

| id | Source | What it gives us | Licence finding | Offline fit | Gate |
|---|---|---|---|---|---|
| OVERTURE | Overture Maps Foundation | Buildings, places, divisions, transportation (GeoParquet on S3/Azure; `overturemaps download --bbox`) | Per theme: base/buildings/divisions/transportation ODbL; places mostly CDLA-Permissive-2.0; addresses permissive. Monthly releases. | yes | approved_with_attribution (per-theme credit lines) |
| PROTOMAPS | Protomaps basemap builds | Complete OSM basemap as PMTiles; `pmtiles extract --bbox` | Tiles ODbL; code BSD-3; design CC0; "hotlinking ... discouraged" so copy to own storage | yes | approved_with_attribution |
| OPENFREEMAP | OpenFreeMap | OSM vector tiles, OpenMapTiles schema | MIT code, ODbL data; attribution required; needs a dedicated Ubuntu server and planet-scale files | conditional | approved_with_attribution, but not suited to a county extract |
| OPENMAPTILES_PLANETILER | OpenMapTiles schema; Planetiler | Build pipeline Geofabrik → PMTiles | OpenMapTiles code BSD-3, design CC BY 4.0 ("must visibly credit OpenMapTiles"); Planetiler Apache-2.0 | yes | approved_with_attribution |
| OPEN_STYLES | OSM Americana, Protomaps themes, VersaTiles styles | MapLibre style JSON | Americana CC0; Protomaps design CC0; VersaTiles MIT, icons CC0 | yes | approved_with_metadata |
| TIGER | US Census TIGER/Line 2025 | County, place, road, AIANNH boundaries | US Government work; cite Census; 2025 vintage released 2025-09-23 | yes | approved_with_attribution |
| USGS_TNM | USGS National Map (NHD/3DHP, GNIS, NBD, NTD, US Topo) | Hydrography, names, boundaries, transportation, topo quads | Public domain; TNM Downloader, staged products | yes | approved_with_attribution |
| NAIP_AWS_PC | NAIP on AWS; Microsoft Planetary Computer | Tile-ready RGB COGs | AWS "Public Domain with Attribution", requester-pays; PC STAC licence field reads "proprietary" while linking "Public Domain"; cite USDA, not PC | yes | approved_with_attribution |
| SENTINEL_LANDSAT | Copernicus Sentinel-2; USGS Landsat 8/9 | Coarse satellite fallback | Sentinel: EU legal notice, "Contains modified Copernicus Sentinel data [Year]" (not CC BY-SA, despite common claims); Landsat: no restrictions | yes | approved_with_attribution; north-coast cloud and 10 m resolution limit use to low zooms |
| GLO30_TERRAINTILES | Copernicus GLO-30; Mapzen/Tilezen Terrain Tiles on AWS | Terrain alternatives | GLO-30 free but with a long mandatory notice and liability sentence; Terrain Tiles US content is 3DEP | yes | approved_with_attribution; prefer 3DEP directly |
| NOAA | NOAA CUSP shoreline, ENC, SLR data, tide station 9419750 "Crescent City" | Shoreline, harbour, sea-level context, tide station POI | Access constraints "None"; credit NOAA requested; "not for use in litigation" | yes | approved_with_attribution; tide predictions pre-computed, never shown as live |
| FEMA_NFHL | FEMA National Flood Hazard Layer | Flood polygons | Federal product; county download via Map Service Center; record effective date | yes | approved_with_metadata; overlay only, not for determinations |
| CALFIRE_FRAP | CAL FIRE FRAP perimeters; Fire Hazard Severity Zones | Hazard overlays | Perimeters CC BY ("No restrictions on public use"), version firep25_1; FHSZ licence unverified (portal blocked by WAF) | yes | approved_with_attribution (perimeters) / unknown (FHSZ) |
| CA_STATE_PARKS | California State Parks GIS | Park boundaries, routes, campgrounds (monthly) | Attribution mandatory; non-commercial/public-sector free; commercial needs approval; "may not be sold or altered" | conditional | conditional_noncommercial_or_permission |
| CALTRANS_GIS | Caltrans GIS open data | Highways, bridges, bike routes | DGP-05 names CC BY 4.0 as default in one place and CC0 in another; site content "considered in the public domain" | yes | approved_with_attribution; read per-dataset field |
| USFS | FSGeodata Clearinghouse | NF boundary, roads, trails, recreation sites | "considered public information and may be distributed or copied"; credit requested | yes | approved_with_attribution |
| BLM_CA | BLM California | Surface management agency | US public domain label | yes | approved_with_metadata |
| TRIBAL_BOUNDARIES | Census AIANNH; BIA LAR | Tribal land boundaries (Tolowa Dee-ni' Nation, Elk Valley Rancheria, Resighini Rancheria, Yurok Reservation) | TIGER public; BIA licence unverified, REST only | yes (TIGER) | approved_with_attribution (TIGER) / unknown (BIA). Boundaries only. Any cultural content only through consultation with each Nation; naming per each Nation's preference. |
| RCTA_GTFS | Redwood Coast Transit GTFS | Transit stops and routes | Official feed carries no licence; Cal-ITP archive copy is CC BY 4.0 but stale (2022 flex feed) | conditional | conditional_confirm_licence; email RCTA |
| CRESCENT_CITY | City of Crescent City | None published | No GIS or open-data section | no | needs_written_permission; use TIGER place polygon for city limits |
| CCED | California Conservation Easement Database | Easements | No licence on site; request form | conditional | conditional_confirm_licence; not needed for basemap |
| NATURAL_EARTH | Natural Earth | Low-zoom land, ocean, boundaries | Public domain; "Crediting the authors is unnecessary" | yes | approved_with_metadata |
| BUILDINGS | Microsoft US Building Footprints; Google Open Buildings | Building fills | Microsoft ODbL, California 11.5 M buildings; Google does not cover the US mainland | yes (MS) / no (Google) | approved_with_attribution / blocked-no-coverage; Overture buildings already merge OSM and Microsoft |
| CPH_ARCHIVE | Cal Poly Humboldt GIS Data Archive | Regional misc. | No terms; Humboldt Bay focus; nothing Del Norte-specific found | unknown | unknown |

## 3. Notable findings

- **Pages that could not be read this session** (JavaScript-only or blocked): shoreline.noaa.gov, fire.ca.gov/FRAP, gis.data.ca.gov terms, Caltrans hub, BLM hub, NPS hub, BIA hub, NAIP hub, Planetary Computer page, iNaturalist terms, transit.land operator page, NOAA data-licensing page. Licence findings for those rest on fetched PDFs, data.gov catalogue records or sibling policy pages and are flagged in the table. A human should open them in a browser before approval.
- **CPAD is the biggest surprise.** It is the obvious parks layer, yet its CC BY status exists only in catalogue metadata. Confirm with the licence file inside the 2026a zip or by email before marking approved.
- **California State Parks data is not fully open.** For Jedediah Smith, Del Norte Coast, Tolowa Dunes and Pelican State Beach it is the authoritative boundary and route source, so a permission email is the cleanest path. The "may not be altered" clause may be read to cover re-tiling.
- **Protomaps plus `pmtiles extract`** is the lowest-effort fully offline basemap and its own documentation tells users to copy tiles to their own storage, which matches our zero-external-call rule exactly.
- **Overture** is now a credible single download for buildings, places and administrative divisions, but each theme carries its own licence and credit line.
- **Sentinel data** is governed by an EU legal notice, not CC BY-SA 3.0 IGO as commonly repeated. The mandatory text is "Contains modified Copernicus Sentinel data [Year]".
- **NAIP:** latest confirmed California vintage is 2022 at 60 cm. Do not cite Planetary Computer as the licence authority; its STAC record is inconsistent.
- **Transit:** a Redwood Coast Transit GTFS feed exists but has no licence statement anywhere official. One email settles it.
- **Written permission is required for:** Del Norte County GIS, City of Crescent City, California State Parks (if the atlas is read as commercial or tiling as alteration), the partner dataset, and any Tribal content beyond TIGER boundaries.

## 4. What this audit does not do

It does not clear any layer for import. The importer stays locked until the eight-item checklist in `licenses/RIGHTS_CHECKLIST.md` is complete for that layer and a named person has recorded the decision. It does not estimate storage or egress; that is done at ingest-planning time for NAIP and 3DEP once the owner decides whether aerial imagery is in the first release.

## 5. Decisions for the owner

1. Approve the minimum viable stack in section 1 for ingest planning (no downloads yet).
2. Decide whether to send the three permission emails now: CPAD licence confirmation, California State Parks, Redwood Coast Transit.
3. Decide whether aerial imagery is in the first release or deferred until the storage estimate exists.
4. Confirm the naming convention for Tribal land boundaries with the four Nations before any label is published.
