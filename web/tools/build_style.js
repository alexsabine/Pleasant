// Generate the MapLibre style for the self-hosted basemap from design tokens.
// Usage: node web/tools/build_style.js  (writes web/static/style/basemap.json)
// Data: Protomaps schema v4 tiles (OSM, ODbL) served from our own origin.
// Style code: @protomaps/basemaps (BSD-3-Clause); design tokens are ours.
const fs = require("fs");
const path = require("path");
const bm = require(process.env.PROTOMAPS_BASEMAPS || "@protomaps/basemaps");

const tokens = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "static", "style", "tokens.json"), "utf8"));
const t = tokens.map;

// Start from the Protomaps "light" flavor and override with the family palette.
const flavor = Object.assign({}, bm.namedFlavor("light"), {
  background: t.land, earth: t.land,
  park_a: t.park_light, park_b: t.park, wood_a: t.wood_light, wood_b: t.wood,
  scrub_a: t.park_light, scrub_b: t.park, sand: t.sand, beach: t.sand, glacier: "#ffffff",
  hospital: t.civic, school: t.civic, industrial: t.industrial, pedestrian: t.pedestrian, zoo: t.park_light,
  water: t.water, buildings: t.buildings, boundaries: t.boundary, railway: t.railway, pier: t.road_casing,
  minor_casing: t.road_casing, minor_service_casing: t.road_casing, link_casing: t.road_casing,
  major_casing_early: t.road_casing, major_casing_late: t.road_casing,
  highway_casing_early: t.road_casing, highway_casing_late: t.road_casing,
  other: t.road_minor, minor_service: t.road_minor, minor_a: t.road_minor, minor_b: t.road, link: t.road,
  major: t.road, highway: t.road_major,
  bridges_minor: t.road, bridges_link: t.road, bridges_major: t.road, bridges_highway: t.road_major, bridges_other: t.road_minor,
  bridges_minor_casing: t.road_casing, bridges_link_casing: t.road_casing, bridges_major_casing: t.road_casing,
  bridges_highway_casing: t.road_casing, bridges_other_casing: t.road_casing,
  roads_label_minor: t.label_muted, roads_label_major: t.label, roads_label_minor_halo: t.land, roads_label_major_halo: t.land,
  ocean_label: t.water_label, city_label: t.label, city_label_halo: t.land, subplace_label: t.label_muted,
  subplace_label_halo: t.land, state_label: t.label_muted, state_label_halo: t.land, country_label: t.label_muted,
  address_label: t.label_muted, address_label_halo: t.land,
  pois: Object.assign({}, bm.namedFlavor("light").pois, t.pois || {}),
  landcover: {
    grassland: t.park_light, barren: t.sand, urban_area: t.urban, farmland: t.farmland,
    glacier: "#ffffff", scrub: t.park_light, forest: t.wood_light,
  },
});

const layers = bm.layers("protomaps", flavor, { lang: "en" });

const style = {
  version: 8,
  name: "Pleasant Crescent basemap (self-hosted)",
  metadata: {
    "pc:generated_by": "web/tools/build_style.js",
    "pc:attribution": "© OpenStreetMap contributors (ODbL) via Protomaps build; terrain USGS 3DEP via Terrain Tiles; style tokens © Pleasant Crescent; style code @protomaps/basemaps BSD-3",
  },
  glyphs: "/static/fonts/{fontstack}/{range}.pbf",
  sprite: tokens.sprite_url || "/static/sprites/light",
  sources: {
    protomaps: {
      type: "vector",
      url: "pmtiles:///tiles/delnorte_basemap.pmtiles",
      attribution: '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> · Protomaps',
    },
    terrain: {
      type: "raster-dem",
      url: "pmtiles:///tiles/delnorte_terrain.pmtiles",
      encoding: "terrarium",
      tileSize: 256,
      attribution: "Terrain: USGS 3DEP via Terrain Tiles (Mapzen/Tilezen)",
    },
  },
  layers: layers,
};

// Insert hillshade just above the earth/landcover fills, below roads.
const idx = style.layers.findIndex((l) => l.id && /water/.test(l.id) && l.type === "fill");
style.layers.splice(idx < 0 ? 1 : idx, 0, {
  id: "pc_hillshade",
  type: "hillshade",
  source: "terrain",
  layout: { visibility: "visible" },
  paint: {
    "hillshade-exaggeration": 0.35,
    "hillshade-shadow-color": t.hill_shadow,
    "hillshade-highlight-color": t.hill_light,
    "hillshade-accent-color": t.hill_shadow,
  },
});

// Every tile/glyph/sprite URL must be on our own origin.
const offending = [];
for (const [k, s] of Object.entries(style.sources)) {
  if (s.url && !s.url.startsWith("pmtiles:///")) offending.push(k);
  if (s.tiles) offending.push(k);
}
if (!style.glyphs.startsWith("/static/")) offending.push("glyphs");
if (!style.sprite.startsWith("/static/")) offending.push("sprite");
if (offending.length) throw new Error("off-origin references: " + offending.join(", "));

const out = path.join(__dirname, "..", "static", "style", "basemap.json");
fs.writeFileSync(out, JSON.stringify(style, null, 1));
console.log(`wrote ${out}: ${style.layers.length} layers, sources ${Object.keys(style.sources).join(", ")}`);
