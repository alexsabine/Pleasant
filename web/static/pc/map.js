/* Pleasant Crescent map: MapLibre + PMTiles from our own origin only.
   Layers: self-hosted OSM basemap, 3DEP hillshade, Census boundaries, directory pins, H3 aggregate. */
(function () {
  const el = document.getElementById("map");
  if (!el || !window.maplibregl || !window.pmtiles) return;
  const cfg = JSON.parse(el.dataset.config);
  const protocol = new pmtiles.Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);

  // Guard: refuse any style source that is not on our origin.
  fetch(cfg.styleUrl).then(r => r.json()).then(style => {
    for (const [k, s] of Object.entries(style.sources)) {
      if ((s.url && !s.url.startsWith("pmtiles:///")) || s.tiles) throw new Error("off-origin source " + k);
    }
    for (const [k, s] of Object.entries(style.sources)) {
      if (s.url) s.url = "pmtiles://" + location.origin + s.url.slice("pmtiles://".length);
    }
    style.glyphs = location.origin + style.glyphs;
    style.sprite = location.origin + style.sprite;
    init(style);
  }).catch(err => { el.innerHTML = '<p class="empty">Map unavailable: ' + err.message + '. The list view has everything.</p>'; });

  function init(style) {
    const map = new maplibregl.Map({ container: "map", style, center: cfg.center, zoom: cfg.zoom, minZoom: 7, maxZoom: 16.5,
      attributionControl: false, hash: false });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-left");
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    map.on("load", () => {
      // Boundaries (public domain, Census TIGER)
      map.addSource("county", { type: "geojson", data: cfg.api.county });
      map.addLayer({ id: "pc_county", type: "line", source: "county", paint: { "line-color": cfg.colors.boundary, "line-width": 2, "line-dasharray": [3, 2] } });
      map.addSource("places", { type: "geojson", data: cfg.api.places });
      map.addLayer({ id: "pc_places", type: "line", source: "places", paint: { "line-color": cfg.colors.boundary, "line-width": 1, "line-opacity": .7 } });
      map.addSource("aiannh", { type: "geojson", data: cfg.api.aiannh });
      map.addLayer({ id: "pc_aiannh", type: "fill", source: "aiannh", layout: { visibility: "none" }, paint: { "fill-color": cfg.colors.sensitive, "fill-opacity": .08 } });
      map.addLayer({ id: "pc_aiannh_line", type: "line", source: "aiannh", layout: { visibility: "none" }, paint: { "line-color": cfg.colors.sensitive, "line-width": 1.2, "line-dasharray": [2, 2] } });

      // H3 aggregate (derived index; k-anonymous counts)
      map.addSource("h3", { type: "geojson", data: cfg.api.h3 });
      map.addLayer({ id: "pc_h3", type: "fill", source: "h3", layout: { visibility: "none" }, paint: {
        "fill-color": cfg.colors.accent, "fill-opacity": ["case", ["get", "suppressed"], 0.05, ["min", 0.55, ["+", 0.12, ["*", 0.08, ["get", "count"]]]]] } });
      map.addLayer({ id: "pc_h3_line", type: "line", source: "h3", layout: { visibility: "none" }, paint: { "line-color": cfg.colors.ink2, "line-opacity": .5, "line-width": .8 } });
      map.addLayer({ id: "pc_h3_label", type: "symbol", source: "h3", layout: { visibility: "none", "text-field": ["case", ["get", "suppressed"], "<k", ["to-string", ["get", "count"]]], "text-size": 11, "text-font": ["Noto Sans Medium"] }, paint: { "text-color": cfg.colors.ink } });

      // Directory pins (published projection only)
      map.addSource("pins", { type: "geojson", data: cfg.api.pins });
      map.addLayer({ id: "pc_pins_halo", type: "circle", source: "pins", paint: { "circle-radius": 13, "circle-color": "#ffffff", "circle-opacity": .9 } });
      map.addLayer({ id: "pc_pins", type: "circle", source: "pins", paint: { "circle-radius": 10, "circle-color": cfg.colors.accent, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
      map.addLayer({ id: "pc_pins_label", type: "symbol", source: "pins", layout: { "text-field": ["get", "name"], "text-size": 12, "text-offset": [0, 1.4], "text-anchor": "top", "text-font": ["Noto Sans Medium"], "text-max-width": 10 },
        paint: { "text-color": cfg.colors.ink, "text-halo-color": "#ffffff", "text-halo-width": 1.6 } });

      map.on("click", "pc_pins", e => {
        const p = e.features[0].properties;
        const html = `<b>${esc(p.name)}</b>${p.is_fictional === "true" || p.is_fictional === true ? ' <span class="tag fiction">fictional demo</span>' : ""}<br>` +
          `${esc(p.category_label)} · ages ${p.min_age} to ${p.max_age} · ${esc(p.cost_status)} · access: ${esc(String(p.accessibility_status).replace("_", " "))}<br>` +
          `<small>${freshness(p)}</small><br><a href="/resource/${esc(p.slug)}/">Details and sources</a>`;
        new maplibregl.Popup({ offset: 14 }).setLngLat(e.lngLat).setHTML(html).addTo(map);
      });
      map.on("mouseenter", "pc_pins", () => map.getCanvas().style.cursor = "pointer");
      map.on("mouseleave", "pc_pins", () => map.getCanvas().style.cursor = "");

      // Layer switcher
      const switches = { terrain: ["pc_hillshade"], boundaries: ["pc_county", "pc_places"], tribal: ["pc_aiannh", "pc_aiannh_line"], h3: ["pc_h3", "pc_h3_line", "pc_h3_label"], pins: ["pc_pins_halo", "pc_pins", "pc_pins_label"] };
      document.querySelectorAll(".layer-switch input[data-layer]").forEach(cb => {
        cb.addEventListener("change", () => {
          (switches[cb.dataset.layer] || []).forEach(id => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", cb.checked ? "visible" : "none"); });
        });
      });
      // Pin list: keyboard-reachable equivalent of clicking a pin
      document.querySelectorAll("[data-fly]").forEach(btn => btn.addEventListener("click", () => {
        const [lon, lat] = btn.dataset.fly.split(",").map(Number);
        if (prefersReduced) map.jumpTo({ center: [lon, lat], zoom: 14.5 }); else map.flyTo({ center: [lon, lat], zoom: 14.5, speed: 0.9 });
      }));
    });
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function freshness(p) {
    const band = { recently_verified: "Recently verified", verified_this_season: "Verified this season", needs_recheck: "Needs re-check", unverified: "Not yet verified" }[p.freshness_band] || "";
    return band + (p.age_days != null ? ` · ${Math.round(p.age_days)} days since verification` : "");
  }
})();
