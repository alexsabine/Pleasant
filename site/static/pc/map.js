/* Pleasant Crescent map: MapLibre + PMTiles from our own origin only.
   Family groups (Kim's launch categories) drive colour and the main toggles.
   Points cluster when they overlap; co-located listings open one combined popup.
   Technical layers (H3 cells, terrain, boundaries, aggregate) live under "Map details". */
(function () {
  const el = document.getElementById("map");
  if (!el || !window.maplibregl || !window.pmtiles) return;
  const cfg = JSON.parse(el.dataset.config);
  const layersBtn = document.querySelector(".layers-toggle"), layersPanel = document.getElementById("layer-switch");
  if (layersBtn && layersPanel) layersBtn.addEventListener("click", () => {   // phones: the layer panel is collapsed by default
    const open = !layersPanel.classList.contains("open");
    layersPanel.classList.toggle("open", open); layersBtn.setAttribute("aria-expanded", String(open));
  });
  const ORIGIN = location.origin + ((window.PC_STATIC && window.PC_STATIC.base) || "/").replace(/\/$/, "");
  window.PC_ORIGIN = ORIGIN;
  const protocol = new pmtiles.Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const GROUPS = Object.keys(cfg.groups || {});
  const groupColor = ["match", ["get", "group"]].concat(GROUPS.flatMap(g => [g, cfg.groups[g].color])).concat([cfg.colors.accent]);
  const groupFill = ["match", ["get", "group"]].concat(GROUPS.flatMap(g => [g, cfg.groups[g].fill])).concat([cfg.colors.hexFill]);
  let activeGroups = new Set(GROUPS);

  fetch(cfg.styleUrl).then(r => r.json()).then(style => {
    for (const [k, s] of Object.entries(style.sources)) {
      if ((s.url && !s.url.startsWith("pmtiles:///")) || s.tiles) throw new Error("off-origin source " + k);
      if (s.url) s.url = "pmtiles://" + ORIGIN + s.url.slice("pmtiles://".length);
    }
    style.glyphs = ORIGIN + style.glyphs;
    style.sprite = ORIGIN + style.sprite;
    init(style);
  }).catch(err => { el.innerHTML = '<p class="empty">Map unavailable: ' + err.message + '. The list view has everything.</p>'; });

  function venueUrl(res) {
    if (window.PC_STATIC) return cfg.api.venues.replace(/\.geojson.*$/, "_res" + res + ".geojson");   // static export: one file per resolution
    return cfg.api.venues + (cfg.api.venues.includes("?") ? "&" : "?") + "res=" + res;
  }
  function groupFilter(extra) {
    const f = ["in", ["get", "group"], ["literal", Array.from(activeGroups)]];
    return extra ? ["all", extra, f] : f;
  }

  function init(style) {
    const map = new maplibregl.Map({ container: "map", style, center: cfg.center, zoom: cfg.zoom, minZoom: 7, maxZoom: 17.5, attributionControl: false });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-left");
    let currentRes = cfg.venueRes || 11;
    let pinsData = null;

    if (window.ResizeObserver) new ResizeObserver(() => map.resize()).observe(el);   // phones: address bar and layout changes
    map.on("load", async () => {
      map.resize();
      // Boundaries (public domain, Census TIGER)
      map.addSource("county", { type: "geojson", data: cfg.api.county });
      map.addLayer({ id: "pc_county", type: "line", source: "county", paint: { "line-color": cfg.colors.boundary, "line-width": 2, "line-dasharray": [3, 2] } });
      map.addSource("places", { type: "geojson", data: cfg.api.places });
      map.addLayer({ id: "pc_places", type: "line", source: "places", paint: { "line-color": cfg.colors.boundary, "line-width": 1, "line-opacity": .7 } });
      map.addSource("aiannh", { type: "geojson", data: cfg.api.aiannh });
      map.addLayer({ id: "pc_aiannh", type: "fill", source: "aiannh", layout: { visibility: "none" }, paint: { "fill-color": cfg.colors.sensitive, "fill-opacity": .08 } });
      map.addLayer({ id: "pc_aiannh_line", type: "line", source: "aiannh", layout: { visibility: "none" }, paint: { "line-color": cfg.colors.sensitive, "line-width": 1.2, "line-dasharray": [2, 2] } });

      // Coarse k-anonymous aggregate (debug)
      map.addSource("h3", { type: "geojson", data: cfg.api.h3 });
      map.addLayer({ id: "pc_h3", type: "fill", source: "h3", layout: { visibility: "none" }, paint: { "fill-color": cfg.colors.accent, "fill-opacity": ["case", ["get", "suppressed"], 0.05, ["min", 0.5, ["+", 0.1, ["*", 0.08, ["get", "count"]]]]] } });
      map.addLayer({ id: "pc_h3_line", type: "line", source: "h3", layout: { visibility: "none" }, paint: { "line-color": cfg.colors.ink2, "line-opacity": .5, "line-width": .8 } });

      // Exact venue cells coloured by group (shown from zoom 13 so they do not clutter the county view)
      map.addSource("venues", { type: "geojson", data: venueUrl(currentRes) });
      map.addLayer({ id: "pc_venue_halo", type: "fill", source: "venues", minzoom: 13, filter: groupFilter(["==", ["get", "role"], "halo"]), paint: { "fill-color": groupFill, "fill-opacity": 0.16 } });
      map.addLayer({ id: "pc_venue_cell", type: "fill", source: "venues", minzoom: 13, filter: groupFilter(["==", ["get", "role"], "venue"]), paint: { "fill-color": groupFill, "fill-opacity": 0.5 } });
      map.addLayer({ id: "pc_venue_cell_line", type: "line", source: "venues", minzoom: 13, filter: groupFilter(["==", ["get", "role"], "venue"]), paint: { "line-color": groupColor, "line-width": ["interpolate", ["linear"], ["zoom"], 13, 1.2, 16, 2.2 ] } });

      // Directory points: clustered. Clusters carry the count; a cluster of co-located points stays a cluster until clicked.
      pinsData = await fetch(cfg.api.pins).then(r => r.json());
      window.dispatchEvent(new CustomEvent("pc:mapready", { detail: { map, pins: pinsData, colors: cfg.colors } }));   // fog mode and other add-ons
      map.addSource("pins", { type: "geojson", data: filteredPins(), cluster: true, clusterRadius: 34, clusterMaxZoom: 15,
        clusterProperties: { grp: ["coalesce", ["get", "group"], "attractions"] } });
      map.addLayer({ id: "pc_cluster", type: "circle", source: "pins", filter: ["has", "point_count"], paint: {
        "circle-radius": ["step", ["get", "point_count"], 14, 5, 18, 12, 22], "circle-color": cfg.colors.accent, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2.5, "circle-opacity": 0.92 } });
      map.addLayer({ id: "pc_cluster_count", type: "symbol", source: "pins", filter: ["has", "point_count"], layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12, "text-font": ["Noto Sans Medium"] }, paint: { "text-color": "#ffffff" } });
      map.addLayer({ id: "pc_pins", type: "circle", source: "pins", filter: ["!", ["has", "point_count"]], paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 5, 15, 8], "circle-color": groupColor, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
      map.addLayer({ id: "pc_pins_label", type: "symbol", source: "pins", filter: ["!", ["has", "point_count"]], minzoom: 12, layout: {
        "text-field": ["get", "name"], "text-size": ["interpolate", ["linear"], ["zoom"], 12, 11, 15, 13], "text-offset": [0, 1.1], "text-anchor": "top",
        "text-font": ["Noto Sans Medium"], "text-max-width": 9, "text-optional": true },
        paint: { "text-color": cfg.colors.ink, "text-halo-color": "#ffffff", "text-halo-width": 1.6 } });

      // Clicking a cluster: zoom in, or if its members share one point, open a combined popup.
      map.on("click", "pc_cluster", async e => {
        const f = e.features[0];
        const src = map.getSource("pins");
        const leaves = await src.getClusterLeaves(f.properties.cluster_id, 50, 0);
        const samePoint = leaves.every(l => Math.abs(l.geometry.coordinates[0] - leaves[0].geometry.coordinates[0]) < 1e-5 && Math.abs(l.geometry.coordinates[1] - leaves[0].geometry.coordinates[1]) < 1e-5);
        if (samePoint || map.getZoom() >= 15.5) { listPopup(e.lngLat, leaves.map(l => l.properties)); return; }
        const z = await src.getClusterExpansionZoom(f.properties.cluster_id);
        if (prefersReduced) map.jumpTo({ center: f.geometry.coordinates, zoom: z + 0.3 }); else map.easeTo({ center: f.geometry.coordinates, zoom: z + 0.3 });
      });
      map.on("click", "pc_pins", e => {
        // several features under the cursor at the same spot -> combined popup
        const here = map.queryRenderedFeatures(e.point, { layers: ["pc_pins"] }).map(x => x.properties);
        if (here.length > 1) listPopup(e.lngLat, here); else popup(e.lngLat, here[0]);
      });
      map.on("click", "pc_venue_cell", e => {
        const f = e.features[0].properties;
        const pin = (pinsData.features || []).find(x => x.properties.id == f.id);
        if (pin) popup(e.lngLat, pin.properties);
      });
      ["pc_pins", "pc_cluster", "pc_venue_cell"].forEach(id => { map.on("mouseenter", id, () => map.getCanvas().style.cursor = "pointer"); map.on("mouseleave", id, () => map.getCanvas().style.cursor = ""); });

      // Group toggles
      document.querySelectorAll(".layer-switch input[data-group]").forEach(cb => cb.addEventListener("change", () => {
        if (cb.checked) activeGroups.add(cb.dataset.group); else activeGroups.delete(cb.dataset.group);
        map.getSource("pins").setData(filteredPins());
        ["pc_venue_halo", "pc_venue_cell", "pc_venue_cell_line"].forEach(id => {
          const role = id === "pc_venue_halo" ? "halo" : "venue";
          map.setFilter(id, groupFilter(["==", ["get", "role"], role]));
        });
      }));
      // Technical layer switches
      const switches = { terrain: ["pc_hillshade"], boundaries: ["pc_county", "pc_places"], tribal: ["pc_aiannh", "pc_aiannh_line"],
        h3: ["pc_h3", "pc_h3_line"], venues: ["pc_venue_halo", "pc_venue_cell", "pc_venue_cell_line"], pins: ["pc_pins_label"] };
      document.querySelectorAll(".layer-switch input[data-layer]").forEach(cb => cb.addEventListener("change", () => {
        (switches[cb.dataset.layer] || []).forEach(id => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", cb.checked ? "visible" : "none"); });
      }));
      const resSel = document.querySelector(".layer-switch select[data-res]");
      if (resSel) resSel.addEventListener("change", () => { currentRes = Number(resSel.value); map.getSource("venues").setData(venueUrl(currentRes)); });
      document.querySelectorAll("[data-fly]").forEach(btn => btn.addEventListener("click", () => {
        const [lon, lat] = btn.dataset.fly.split(",").map(Number);
        if (prefersReduced) map.jumpTo({ center: [lon, lat], zoom: 15.5 }); else map.flyTo({ center: [lon, lat], zoom: 15.5, speed: 0.9 });
      }));
    });

    function filteredPins() {
      return { type: "FeatureCollection", features: (pinsData.features || []).filter(f => activeGroups.has(f.properties.group)) };
    }
    function popup(lngLat, p) {
      const html = `<b>${esc(p.name)}</b><br><span class="tag" style="border-color:${esc(colorOf(p.group))};color:${esc(colorOf(p.group))}">${esc(p.group_label)}</span> · ${esc(p.category_label)}<br>` +
        `ages ${p.min_age} to ${p.max_age} · ${esc(p.cost_status)} · access: ${esc(String(p.accessibility_status).replace("_", " "))}<br>` +
        `<small>${freshness(p)}${p.verification_label ? " · " + esc(p.verification_label) : ""}</small><br><a href="${ORIGIN}/resource/${esc(p.slug)}/">Details and sources</a>`;
      new maplibregl.Popup({ offset: 12, maxWidth: "280px" }).setLngLat(lngLat).setHTML(html).addTo(map);
    }
    function listPopup(lngLat, items) {
      const html = `<b>${items.length} listings here</b><ul>` + items.map(p => `<li><span class="sw" style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${esc(colorOf(p.group))};margin-right:5px"></span><a href="${ORIGIN}/resource/${esc(p.slug)}/">${esc(p.name)}</a> <small>· ${esc(p.category_label)}</small></li>`).join("") + "</ul>";
      new maplibregl.Popup({ offset: 12, maxWidth: "300px" }).setLngLat(lngLat).setHTML(html).addTo(map);
    }
  }
  function colorOf(g) { return (cfg.groups[g] || {}).color || cfg.colors.accent; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function freshness(p) {
    const band = { recently_verified: "Recently checked", verified_this_season: "Checked this season", needs_recheck: "Needs re-check", unverified: "Not yet verified" }[p.freshness_band] || "";
    return band + (p.age_days != null ? ` · ${Math.round(p.age_days)} days since check` : "");
  }
})();
