/* Pleasant Crescent map: MapLibre + PMTiles from our own origin only.
   Layers: self-hosted OSM basemap, 3DEP hillshade, Census boundaries,
   exact H3 venue cells (res 8-12) with a one-step halo, directory labels,
   and the coarse k-anonymous H3 aggregate for debugging. */
(function () {
  const el = document.getElementById("map");
  if (!el || !window.maplibregl || !window.pmtiles) return;
  const cfg = JSON.parse(el.dataset.config);
  const protocol = new pmtiles.Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  fetch(cfg.styleUrl).then(r => r.json()).then(style => {
    for (const [k, s] of Object.entries(style.sources)) {
      if ((s.url && !s.url.startsWith("pmtiles:///")) || s.tiles) throw new Error("off-origin source " + k);
      if (s.url) s.url = "pmtiles://" + location.origin + s.url.slice("pmtiles://".length);
    }
    style.glyphs = location.origin + style.glyphs;
    style.sprite = location.origin + style.sprite;
    init(style);
  }).catch(err => { el.innerHTML = '<p class="empty">Map unavailable: ' + err.message + '. The list view has everything.</p>'; });

  function venueUrl(res) { return cfg.api.venues + (cfg.api.venues.includes("?") ? "&" : "?") + "res=" + res; }

  function init(style) {
    const map = new maplibregl.Map({ container: "map", style, center: cfg.center, zoom: cfg.zoom, minZoom: 7, maxZoom: 17.5, attributionControl: false });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-left");
    let currentRes = cfg.venueRes || 11;

    map.on("load", () => {
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

      // Exact venue cells: halo (one grid step) under the venue cell
      map.addSource("venues", { type: "geojson", data: venueUrl(currentRes) });
      map.addLayer({ id: "pc_venue_halo", type: "fill", source: "venues", filter: ["==", ["get", "role"], "halo"],
        paint: { "fill-color": cfg.colors.hexFill, "fill-opacity": 0.14 } });
      map.addLayer({ id: "pc_venue_halo_line", type: "line", source: "venues", filter: ["==", ["get", "role"], "halo"],
        paint: { "line-color": cfg.colors.hex, "line-opacity": 0.25, "line-width": 0.6 } });
      map.addLayer({ id: "pc_venue_cell", type: "fill", source: "venues", filter: ["==", ["get", "role"], "venue"],
        paint: { "fill-color": cfg.colors.hexFill, "fill-opacity": ["interpolate", ["linear"], ["zoom"], 10, 0.55, 15, 0.42] } });
      map.addLayer({ id: "pc_venue_cell_line", type: "line", source: "venues", filter: ["==", ["get", "role"], "venue"],
        paint: { "line-color": cfg.colors.hex, "line-width": ["interpolate", ["linear"], ["zoom"], 10, 1.2, 15, 2.2] } });

      // Directory points: a small centre dot plus label, over the cells
      map.addSource("pins", { type: "geojson", data: cfg.api.pins });
      map.addLayer({ id: "pc_pins", type: "circle", source: "pins", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 4, 15, 7], "circle-color": cfg.colors.hex, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
      map.addLayer({ id: "pc_pins_label", type: "symbol", source: "pins", layout: {
        "text-field": ["get", "name"], "text-size": ["interpolate", ["linear"], ["zoom"], 10, 11, 15, 13], "text-offset": [0, 1.1], "text-anchor": "top",
        "text-font": ["Noto Sans Medium"], "text-max-width": 9, "text-optional": true },
        paint: { "text-color": cfg.colors.ink, "text-halo-color": "#ffffff", "text-halo-width": 1.6 } });

      const popup = (e, p) => {
        const vl = p.verification_label || "";
        const html = `<b>${esc(p.name)}</b><br>${esc(p.category_label)} · ages ${p.min_age} to ${p.max_age} · ${esc(p.cost_status)} · access: ${esc(String(p.accessibility_status).replace("_", " "))}<br>` +
          `<small>${freshness(p)}${vl ? " · " + esc(vl) : ""}</small><br><small>H3 ${esc(p.h3_res_11 || "")}</small><br><a href="/resource/${esc(p.slug)}/">Details and sources</a>`;
        new maplibregl.Popup({ offset: 12 }).setLngLat(e.lngLat).setHTML(html).addTo(map);
      };
      map.on("click", "pc_pins", e => popup(e, e.features[0].properties));
      map.on("click", "pc_venue_cell", e => {
        const f = e.features[0].properties;
        const pin = map.querySourceFeatures("pins").find(x => x.properties.id == f.id);
        if (pin) popup(e, pin.properties);
      });
      ["pc_pins", "pc_venue_cell"].forEach(id => { map.on("mouseenter", id, () => map.getCanvas().style.cursor = "pointer"); map.on("mouseleave", id, () => map.getCanvas().style.cursor = ""); });

      // Layer switcher and H3 resolution control
      const switches = { terrain: ["pc_hillshade"], boundaries: ["pc_county", "pc_places"], tribal: ["pc_aiannh", "pc_aiannh_line"],
        h3: ["pc_h3", "pc_h3_line"], venues: ["pc_venue_halo", "pc_venue_halo_line", "pc_venue_cell", "pc_venue_cell_line"], pins: ["pc_pins", "pc_pins_label"] };
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
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function freshness(p) {
    const band = { recently_verified: "Recently checked", verified_this_season: "Checked this season", needs_recheck: "Needs re-check", unverified: "Not yet verified" }[p.freshness_band] || "";
    return band + (p.age_days != null ? ` · ${Math.round(p.age_days)} days since check` : "");
  }
})();
