# Local/offline basemap acquisition: rights gate

**This is an engineering rights assessment, not a legal opinion.** Source rules can change; verify terms on the exact data product and obtain written licences where needed.

## Allowed in principle, with notices
- USGS National Map 3DEP, hydrography and NAIP **original downloadable** products: public domain. Maintain agency/source/acquisition date and ground resolution. Download source files via USGS/EarthExplorer rather than copying arbitrary web map service images.
- OSM downloadable underlying roads/paths/place data via Geofabrik: ODbL. Show mandatory attribution and be prepared to comply with requirements for OSM-derived databases. Prefer self-created vector map tiles, not bulk cached tiles from OpenStreetMap.org.
- CPAD California Protected Areas Database: state portal lists Creative Commons Attribution, unrestricted public use. Preserve attribution, dataset version and access-type caveats.
- NPS public maps/trails: NPS generally public domain, subject to specific sources/metadata exceptions. Do not rely solely on these for backcountry navigation or current trail safety.
- CA Department of Water Resources public historical land-use data: individual surveys public domain, but check availability for Del Norte.

## Conditional / restricted
- County-maintained Del Norte GIS: county asserts dataset ownership; obtain redistribution/self-hosting permission **for each layer** before ingestion. An ArcGIS REST export link does not settle licensing.
- California Geological Survey tsunami hazard shapefiles: downloadable; examine product notices, attribution and limitations. Static cached hazard polygons are not live alerts.
- CDFW BIOS: some public, some restricted to authorised partners. Sensitive species locations should be omitted, generalised only by authorised rules or limited to private stewards.
- iNaturalist: observation fields and photos/audio have **separate licences**, frequently CC BY-NC or all-rights-reserved. Geoprivacy and taxon obscuration must never be reversed or made falsely precise.
- Calflora: public observation data may be CC0 under the terms, but photos are excluded and service access has separate conditions.
- Daniel Friedman GIS: no assumed right to read or redistribute data; pending formal compatibility and approval.

## Not approved for self-hosting
- Google Maps/Earth/Street View/Places tiles/data from standard Maps Platform: do not download, mirror, cache or rehost. Optional Google View is a separate live API view with displayed attributions and user privacy choices.
- Caltrans QuickMap live road conditions: without separately approved feed rights cannot present a cache as current. Link to official live service.

## Require for every layer before importer unlock
- [ ] Official dataset landing page saved.
- [ ] Named custodian and product-specific download licence captured.
- [ ] Licence checked for: copying, processing, redistribution, attribution, offline tiles and derivative databases.
- [ ] Spatial extent, units/CRS, acquisition/vintage, update schedule known.
- [ ] Attribution text and source link visibly displayed on map.
- [ ] Location sensitivity reviewed, especially people, children, Indigenous or wildlife data.
- [ ] Import approval recorded with decision maker and date; immutable audit *metadata* only as law/policy permits.
- [ ] Refresh route, expiry indicators and deletion/withdrawal mechanism specified.

## Sources verified 2026-10-14
USGS: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer
USGS downloader: https://www.usgs.gov/tools/download-data-maps-national-map
OSM licence: https://osmfoundation.org/wiki/Licence/Licence_and_Legal_FAQ
OSM attribution: https://osmfoundation.org/wiki/Attribution_Guidelines
Geofabrik: https://download.geofabrik.de/north-america/us/california/norcal.html
CPAD: https://data.ca.gov/@california-natural-resources-agency/california-protected-areas-database
County: https://www.co.del-norte.ca.us/GIS
NPS: https://www.nps.gov/subjects/gisandmapping/data-sources-and-accuracy.htm
CDFW: https://wildlife.ca.gov/Data/BIOS/Submitting-Data
iNat: https://help.inaturalist.org/en/support/solutions/articles/151000175695
Tsunami: https://www.conservation.ca.gov/cgs/tsunami/maps
Google: https://developers.google.com/maps/documentation/tile/policies
Calflora: https://www.calflora.org/tos.html
