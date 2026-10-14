/**
 * MapLibre adapter sketch to be adapted by Claude Code; requires locally
 * generated, licensed map files at your own domain. NOT drop-in final UI.
 * Do not feed Google, restricted ecology or unlicensed county tiles into it.
 * Product credits must be shown in the rendered map.
 */
export const localLayerDefinitions = [
  {id:'streets', label:'Streets & paths', source:'osm_roads', type:'line', visible:true,
    attribution:'© OpenStreetMap contributors (ODbL)'},
  {id:'aerial', label:'Aerial imagery', source:'naip_aerial', type:'raster', visible:false,
    attribution:'USGS / USDA NAIP (acquisition year displayed with layer)'},
  {id:'hillshade', label:'Terrain relief', source:'usgs_hillshade', type:'raster', visible:false,
    attribution:'USGS 3DEP'},
  {id:'parks', label:'Parks & public access', source:'cpad_parks', type:'fill', visible:true,
    attribution:'CPAD / GreenInfo Network, CC BY'},
  {id:'family', label:'Family resources', source:'pc_directory', type:'circle', visible:true,
    attribution:'Pleasant Crescent curated directory'},
  {id:'biodiversity', label:'Reviewed biodiversity', source:'approved_ecology', type:'circle', visible:false,
    attribution:'Data owners per layer; sensitive locations suppressed'},
  {id:'hazards', label:'Tsunami planning map (static)', source:'cgs_tsunami', type:'fill', visible:false,
    attribution:'CGS; static hazard data; check official live alerts'}
];

// Replace urls only with YOUR licensed tile endpoints produced by ingestion.
export const localSourceCatalog = {
  osm_roads:{type:'vector',url:'/maps/osm-roads/tiles.json'},
  naip_aerial:{type:'raster',tiles:['/maps/naip/{z}/{x}/{y}.webp'],tileSize:256},
  usgs_hillshade:{type:'raster',tiles:['/maps/hillshade/{z}/{x}/{y}.png'],tileSize:256},
  cpad_parks:{type:'geojson',data:'/api/layers/cpad.geojson'},
  pc_directory:{type:'geojson',data:'/api/resources/published.geojson'},
  approved_ecology:{type:'geojson',data:'/api/biodiversity/public.geojson'},
  cgs_tsunami:{type:'geojson',data:'/api/layers/tsunami-static.geojson'}
};

export const visitorExperience = {
  defaultTab:'list', // accessible list with map as an option
  maxVisibleSuggestions:3,
  anonymousBrowsing:true,
  userLocation:'off',
  publicSourcesOnly:true,
  consentedProfile:'optional',
  hideSensitiveEcology:true
};
