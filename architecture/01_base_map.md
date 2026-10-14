# A fully self-hosted Del Norte basemap (normal operation)

## Core architecture

**Data acquisition is not map browsing.** An administrator downloads legitimately licensed original products periodically, normalises/tiles them, and serves the results locally. Once built, mobile browsers request only Pleasant Crescent's own static vector/raster tiles and service API—not source agencies' servers. This reduces latency, external coupling and unexpected cost, but creates a data freshness obligation.

```
AUTHORISED OFFLINE INGEST (occasional, logged)
USGS NAIP  ────────>  reproject/clip/COG  ────> aerial raster tiles
USGS 3DEP ────────>  DEM and contours   ────> hillshade / terrain
OSM extract ──────>  clip + vectorize  ────> roads, labels, POI tiles (ODbL)
CPAD / NPS ───────>  validate + clip    ────> parks, trails, access polygons
County GIS ───────>  LICENCE GATE      ────> approved layers ONLY
CDFW/observations -> rights/privacy gate -> approved coarse public overlays

        OWN STORAGE (image tiles / PMTiles / object store)
                    |
          MapLibre on mobile web
                    |
    PostGIS directory pins and event filtering
                    |
          Wagtail editing and approvals
                    |
        optional read-only API guide
```

## Default layer switches
- Streets & labels (**start here for children/families**): locally generated OSM road and path vectors, civic resource directory points, waterways. Do not display every commercial business automatically.
- Aerial imagery: licensed downloaded USGS NAIP source with a visible acquisition date.
- Terrain/topography: 3DEP hillshade, contours, slope; road/label overlay always legible.
- Public parks, trail networks & access (CPAD + approved NPS public trails); access conditions are not guarantees.
- Family resources: verified directory, age, cost, accessibility, category, date and community; list view equivalent.
- Events: recurring schedules, expired state and source links.
- Biodiversity: reviewed habitat/observation points, with endangered species/precise locations suppressed and community stewardship highlighted.
- Heritage/land use: public heritage and available historical land use, not invented future land-use predictions.
- Hazards (optional): CGS static tsunami planning map clearly labelled; external live official alerts are linked, not replicated.
- H3: disabled by default; optional debug/aggregate cells at suitable resolution, no implied journey/travel time.
- Google View: separate optional live tab, NEVER part of offline basemap.

## Practical tooling (proposed, not run here)
- Download source files to a rights-checked local ingress area.
- QGIS/GDAL `ogr2ogr` import for GeoJSON, GPKG and ESRI shapefiles. `gdalwarp` / `gdal_translate` for rasters, conversions to Cloud Optimized GeoTIFF as useful.
- `tippecanoe` or Martin/other vector tile generator for layers. For prototype, low-volume GeoJSON from PostGIS is enough.
- Make static PMTiles/MBTiles/vector tiles and raster image tiles, exposed from organisation-controlled hosting with attribution.
- Decide whether raster tiling of whole county is economical. **Never add gigabyte imagery to Git commits**. For cheap launch use local street/vector/parks tiles and add local aerophotos incrementally.
- Reprojection: store authoritative source CRS, ingest to EPSG:4326 geometries (display project to Web Mercator EPSG:3857); avoid losing original coordinates/accuracy metadata.
- Bboxes alone are not legal county boundaries. Obtain a licensed authoritative county polygon or manually declare prototype bounding box as approximate and NEVER assert precise property/permit boundaries.

## Scientific and ethical mapping
The map changes behaviour: it draws visitors to featured places and can expose wildlife or communities. Feedback loop: published listing -> human attention -> changed traffic -> new reports -> new listings. Preserve provenance; check representational skew, accessibility and underrepresented resource categories. Metrics should reward successful orientation rather than clicks or message volumes.

## Source refresh
A cached map is a **snapshot**, not a live world. Show dataset version and last-updated date. Weather, closure and hazard information must link to current official sources rather than be presented as contemporaneous offline facts.
