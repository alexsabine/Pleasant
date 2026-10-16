/* Fog mode (demo): the map starts under sea fog, and a little explorer clears it place by place.
 *
 * The maths, kept light enough for a phone:
 * - Belief that a spot is still unexplored: p(x) = prod_i (1 - c_i * exp(-d_i^2 / (2 s_i^2))), one factor per
 *   place visited (a Bayesian "visited here" update with a Gaussian footprint).
 * - Opacity follows the Fisher-Rao angle theta = 2 asin(sqrt p), the coordinate the crescent logo uses, so the fog
 *   thins in even steps of belief rather than all at once (phoenix_selected/03_math_selected.md).
 * - Wisps: drifting value noise, weighted by p(1 - p), so edges move most where the belief is least certain.
 * - Each clearing eases in with the past-only average m <- q m + (1 - q) target: derived visual state only.
 * - Drawn on a canvas of about 20,000 pixels, upscaled smoothly; about 24 frames a second, paused when hidden;
 *   still for people who prefer reduced motion.
 * Privacy: no device location is ever read. The explorer only goes where you choose, and the trail stays on this
 * device (localStorage), never sent anywhere. Choices favour kinds of place not yet visited, never popularity.
 */
(function () {
  "use strict";
  const btn = document.querySelector(".fog-toggle");
  if (!btn) return;
  const reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const KEY = "pc_fog_v1", Q = 0.9, FPS = 24, MAX_PIXELS = 20000;
  const VISIT_M = 240, TRAIL_M = 80;    // footprint radius of a visited place and of the trail, in metres

  let map = null, places = [], on = false, canvas = null, ctx = null, img = null, field = null, raf = 0, last = 0, t0 = performance.now();
  let spots = [], visited = [], current = null, explorer = null, card = null, walking = false, anchor = null;

  // --- noise: one tileable fBm texture, computed once ------------------------------------------
  const N = 256, NOISE = new Float32Array(N * N);
  (function buildNoise() {
    const G = 16, grid = new Float32Array(G * G);
    let seed = 20261016;
    const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < grid.length; i++) grid[i] = rnd();
    const sm = t => t * t * (3 - 2 * t);
    const val = (x, y) => {                          // bilinear value noise, wraps every G cells
      const xi = Math.floor(x), yi = Math.floor(y), fx = sm(x - xi), fy = sm(y - yi);
      const a = grid[((yi % G + G) % G) * G + ((xi % G + G) % G)], b = grid[((yi % G + G) % G) * G + (((xi + 1) % G + G) % G)];
      const c = grid[(((yi + 1) % G + G) % G) * G + ((xi % G + G) % G)], d = grid[(((yi + 1) % G + G) % G) * G + (((xi + 1) % G + G) % G)];
      return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
    };
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
      let v = 0, amp = 0.55, f = G / N, norm = 0;
      for (let o = 0; o < 3; o++) { v += amp * val(x * f, y * f); norm += amp; amp *= 0.5; f *= 2; }
      NOISE[y * N + x] = v / norm;
    }
  })();
  const noiseAt = (x, y) => NOISE[((y & 255) << 8) | (x & 255)];

  // --- state on this device only -----------------------------------------------------------------
  function load() {
    try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s && Array.isArray(s.visited)) return s; } catch (e) { /* private mode */ }
    return null;
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify({ visited: visited.map(p => p.id), current: current && current.id })); } catch (e) { /* ignore */ }
  }

  // --- geography helpers ---------------------------------------------------------------------------
  const R = 6371000, rad = d => d * Math.PI / 180;
  function metres(a, b) {
    const dLat = rad(b.lat - a.lat), dLon = rad(b.lon - a.lon);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  function heading(a, b) {
    const y = Math.sin(rad(b.lon - a.lon)) * Math.cos(rad(b.lat));
    const x = Math.cos(rad(a.lat)) * Math.sin(rad(b.lat)) - Math.sin(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.cos(rad(b.lon - a.lon));
    const deg = (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
    return ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"][Math.round(deg / 45) % 8];
  }
  const miles = m => { const mi = m / 1609.344; return mi < 0.2 ? Math.round(m * 3.281 / 10) * 10 + " ft" : (mi < 10 ? mi.toFixed(1) : Math.round(mi)) + " mi"; };
  function metresPerPixel() {
    const lat = map.getCenter().lat;
    return 40075016.686 * Math.cos(rad(lat)) / (512 * Math.pow(2, map.getZoom()));
  }

  // --- choices: nearest unvisited place in up to three different kinds, new kinds first -------------
  function starts() {
    const byCommunity = new Map();
    places.forEach(p => { const k = p.community_label || "Elsewhere"; (byCommunity.get(k) || byCommunity.set(k, []).get(k)).push(p); });
    const picks = [...byCommunity.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 3).map(([, list]) => {
      const c = { lat: list.reduce((t, p) => t + p.lat, 0) / list.length, lon: list.reduce((t, p) => t + p.lon, 0) / list.length };
      return list.slice().sort((a, b) => metres(c, a) - metres(c, b))[0];          // the place nearest the community's centre
    });
    const here = { lat: map.getCenter().lat, lon: map.getCenter().lng };
    picks.forEach(p => { p._d = metres(here, p); });
    return picks;
  }

  function choices(from) {
    if (!from) return starts();
    const seenGroups = new Set(visited.map(p => p.group)), seenIds = new Set(visited.map(p => p.id));
    const pool = places.filter(p => !seenIds.has(p.id) && (!from || p.id !== from.id));
    const origin = from || { lat: map.getCenter().lat, lon: map.getCenter().lng };
    pool.forEach(p => { p._d = metres(origin, p); });
    pool.sort((a, b) => a._d - b._d);
    const byGroup = new Map();
    for (const p of pool) if (!byGroup.has(p.group)) byGroup.set(p.group, p);
    const ranked = [...byGroup.values()].sort((a, b) => (seenGroups.has(a.group) - seenGroups.has(b.group)) || (a._d - b._d));
    return ranked.slice(0, 3);
  }

  // --- the card: a small choose-your-own-adventure ----------------------------------------------------
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const article = w => (/^[aeiou]/i.test(w) ? "an " : "a ") + w.toLowerCase();
  function render() {
    if (!card) return;
    const opts = choices(current);
    let story;
    if (!current) story = `<p class="fog-story">Sea fog has rolled in over Del Norte County. Where would you like to begin?</p>`;
    else {
      const kinds = new Set(visited.map(p => p.group)).size;
      story = `<p class="fog-story">You reach <b>${esc(current.name)}</b>, ${esc(article(current.category_label))}. The fog lifts around you.</p>
        <p class="fog-meta">${visited.length} place${visited.length === 1 ? "" : "s"} explored, ${kinds} kind${kinds === 1 ? "" : "s"} · <a href="${esc(window.PC_ORIGIN || "")}/resource/${esc(current.slug)}/">About this place</a></p>`;
    }
    const list = opts.length ? opts.map((p, i) =>
      `<button type="button" class="fog-choice" data-id="${p.id}"><span class="fog-n">${i + 1}</span><span><b>${esc(p.name)}</b><small>${esc(p.category_label)} · ${current ? esc(heading(current, p)) + ", " + miles(p._d) : "in " + esc(p.community_label || "the county")}</small></span></button>`).join("")
      : `<p class="fog-story">You have explored every place on the map. The fog is gone.</p>`;
    card.innerHTML = `${story}<p class="fog-q">${current ? "Where next?" : "Choose a starting place:"}</p><div class="fog-choices">${list}</div>
      <p class="fog-foot"><button type="button" class="fog-link" data-act="restart">Start again</button> · <button type="button" class="fog-link" data-act="off">Leave fog mode</button><br>
      <small>Demo. Your trail stays on this device, and fog never uses your location.</small></p>`;
  }

  function onCard(e) {
    const b = e.target.closest("button");
    if (!b || walking) return;
    if (b.dataset.act === "off") return toggle(false);
    if (b.dataset.act === "restart") { visited = []; current = null; spots = []; save(); placeExplorer(null); render(); return; }
    const p = places.find(x => String(x.id) === b.dataset.id);
    if (p) go(p);
  }

  // --- the explorer ---------------------------------------------------------------------------------------
  function explorerEl() {
    const el = document.createElement("div");
    el.className = "fog-explorer";
    el.setAttribute("aria-hidden", "true");
    // MapLibre positions the marker with a transform on this element, so all animation lives on the inner .fog-body
    el.innerHTML = `<span class="fog-body"><span class="fog-glow"></span><svg viewBox="0 0 24 32" width="30" height="39">
      <circle cx="12" cy="6" r="3.6" fill="#f3dcc0" stroke="#364868" stroke-width="1.2"/>
      <path d="M8.5 12.5c0-1.6 1.6-2.6 3.5-2.6s3.5 1 3.5 2.6l.6 8.2H7.9z" fill="#00848b" stroke="#364868" stroke-width="1.1"/>
      <path class="leg l" d="M10.2 20.5l-1.2 7.6" stroke="#364868" stroke-width="2" stroke-linecap="round"/>
      <path class="leg r" d="M13.8 20.5l1.2 7.6" stroke="#364868" stroke-width="2" stroke-linecap="round"/>
      <path d="M15.6 13.4l3.4 4.2" stroke="#364868" stroke-width="1.6" stroke-linecap="round"/>
      <circle cx="19.6" cy="19.2" r="2.2" fill="#e4b572" stroke="#a3675b" stroke-width=".9"/></svg></span>`;
    return el;
  }
  function placeExplorer(p) {
    if (!p) { if (explorer) { explorer.remove(); explorer = null; } return; }
    if (!explorer) explorer = new maplibregl.Marker({ element: explorerEl(), anchor: "bottom" }).setLngLat([p.lon, p.lat]).addTo(map);
    else explorer.setLngLat([p.lon, p.lat]);
  }

  function pad() {
    if (!card) return 0;
    const box = map.getContainer().getBoundingClientRect(), c = card.getBoundingClientRect();
    return c.width > box.width * 0.7 ? { top: 20, bottom: Math.min(box.height * 0.6, c.height + 10), left: 0, right: 0 }
                                     : { left: c.width + 20, top: 0, bottom: 0, right: 0 };
  }

  function clearAt(lon, lat, radius, strength) { spots.push({ lon, lat, r: radius, target: strength, c: reduced ? strength : 0 }); }

  function go(p) {
    const from = current;
    const z = Math.max(map.getZoom(), 13.2), padding = pad();
    if (!from || reduced) {
      current = p; visited.push(p); clearAt(p.lon, p.lat, VISIT_M, 1); placeExplorer(p);
      if (reduced) map.jumpTo({ center: [p.lon, p.lat], zoom: z, padding }); else map.flyTo({ center: [p.lon, p.lat], zoom: z, padding, duration: 2200 });
      save(); render(); return;
    }
    walking = true;
    card.classList.add("busy");
    const d = metres(from, p), dur = Math.min(4200, 1400 + d / 6);
    map.easeTo({ center: [p.lon, p.lat], zoom: z, padding, duration: dur });
    const el = explorer.getElement();
    el.classList.add("walking");
    el.classList.toggle("west", p.lon < from.lon);
    const start = performance.now();
    let trail = { lon: from.lon, lat: from.lat };
    (function step(now) {
      const k = Math.min(1, (now - start) / dur), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      const lon = from.lon + (p.lon - from.lon) * e, lat = from.lat + (p.lat - from.lat) * e;
      explorer.setLngLat([lon, lat]);
      if (metres(trail, { lon, lat }) > TRAIL_M * 0.9) { clearAt(lon, lat, TRAIL_M, 0.75); trail = { lon, lat }; }   // a footprint every ~150 m
      if (k < 1) return requestAnimationFrame(step);
      el.classList.remove("walking");
      current = p; visited.push(p); clearAt(p.lon, p.lat, VISIT_M, 1);
      walking = false; card.classList.remove("busy");
      save(); render();
      const first = card.querySelector(".fog-choice"); if (first) first.focus({ preventScroll: true });
    })(start);
  }

  // --- drawing -----------------------------------------------------------------------------------------------
  function size() {
    const box = map.getContainer();
    const w = box.clientWidth, h = box.clientHeight;
    const s = Math.max(3, Math.ceil(Math.sqrt((w * h) / MAX_PIXELS)));
    canvas.width = Math.ceil(w / s); canvas.height = Math.ceil(h / s);
    canvas.dataset.scale = s;
    img = ctx.createImageData(canvas.width, canvas.height);
    field = new Float32Array(canvas.width * canvas.height);
  }
  function fogColour() {
    const dark = window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches && document.documentElement.dataset.theme !== "light";
    return dark ? [[24, 30, 42], [58, 68, 86]] : [[206, 215, 224], [250, 252, 253]];   // trough and crest of the billows
  }
  function draw(now) {
    const W = canvas.width, H = canvas.height, s = +canvas.dataset.scale, data = img.data, [lo, hi] = fogColour();
    const mpp = metresPerPixel() * s;
    // log p(x) = sum_i log(1 - c_i g_i(x)); each clearing only touches pixels within three radii of it
    field.fill(0);
    for (const sp of spots) {
      sp.c = Q * sp.c + (1 - Q) * sp.target;                       // past-only easing of each clearing
      const pt = map.project([sp.lon, sp.lat]), r = sp.r / mpp, cx = pt.x / s, cy = pt.y / s, reach = 3 * r;
      const x0 = Math.max(0, Math.floor(cx - reach)), x1 = Math.min(W - 1, Math.ceil(cx + reach));
      const y0 = Math.max(0, Math.floor(cy - reach)), y1 = Math.min(H - 1, Math.ceil(cy + reach));
      if (x0 > x1 || y0 > y1) continue;
      const inv = 1 / (2 * r * r), c = sp.c * 0.999;
      for (let y = y0; y < y1 + 1; y++) {
        const dy2 = (y - cy) * (y - cy), row = y * W;
        for (let x = x0; x < x1 + 1; x++) {
          const dx = x - cx;
          field[row + x] += Math.log(1 - c * Math.exp(-(dx * dx + dy2) * inv));
        }
      }
    }
    const a = map.project(anchor), t = reduced ? 0 : (now - t0) / 1000;
    const ox1 = Math.round(-a.x / s + t * 2.2), oy1 = Math.round(-a.y / s + t * 0.6);
    const ox2 = Math.round(-a.x / s * 1.7 - t * 1.4), oy2 = Math.round(-a.y / s * 1.7 + t * 1.1);
    for (let y = 0, j = 0, i = 0; y < H; y++) {
      for (let x = 0; x < W; x++, j++, i += 4) {
        let p = Math.exp(field[j]);
        const raw = 0.6 * noiseAt(x + ox1, y + oy1) + 0.4 * noiseAt((x >> 1) + ox2, (y >> 1) + oy2);
        const n = Math.min(1, Math.max(0, (raw - 0.5) * 2.4 + 0.5));            // stretch contrast so billows read
        p = Math.min(1, Math.max(0, p + (n - 0.5) * 1.6 * p * (1 - p)));   // wisps where belief is least certain
        const theta = 2 * Math.asin(Math.sqrt(p));                          // Fisher-Rao coordinate, 0..pi
        const alpha = Math.pow(theta / Math.PI, 0.8) * (0.8 + 0.2 * n) * 0.97;
        data[i] = lo[0] + (hi[0] - lo[0]) * n; data[i + 1] = lo[1] + (hi[1] - lo[1]) * n; data[i + 2] = lo[2] + (hi[2] - lo[2]) * n;
        data[i + 3] = alpha * 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }
  function loop(now) {
    if (!on) return;
    raf = requestAnimationFrame(loop);
    if (document.hidden || now - last < 1000 / FPS) return;
    last = now;
    draw(now);
  }
  const redraw = () => { if (on && reduced) draw(performance.now()); };

  // --- switching on and off ---------------------------------------------------------------------------
  function toggle(want) {
    on = want === undefined ? !on : want;
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    const wrap = map.getContainer().parentElement;
    wrap.classList.toggle("fog-on", on);
    if (on) {
      canvas = document.createElement("canvas");
      canvas.className = "fog-canvas";
      canvas.setAttribute("aria-hidden", "true");
      const host = map.getCanvasContainer();                       // under markers and popups, over the map itself
      host.insertBefore(canvas, map.getCanvas().nextSibling);
      ctx = canvas.getContext("2d");
      anchor = map.getCenter();
      size();
      card = document.createElement("section");
      card.className = "fog-card";
      card.setAttribute("aria-label", "Fog mode");
      card.setAttribute("aria-live", "polite");
      card.addEventListener("click", onCard);
      wrap.appendChild(card);
      const saved = load();
      visited = saved ? saved.visited.map(id => places.find(p => p.id === id)).filter(Boolean) : [];
      current = saved && saved.current ? places.find(p => p.id === saved.current) || null : null;
      spots = [];
      visited.forEach(p => clearAt(p.lon, p.lat, VISIT_M, 1));
      spots.forEach(sp => { sp.c = sp.target; });
      placeExplorer(current);
      render();
      map.on("resize", size);
      map.on("move", redraw);
      if (reduced) draw(performance.now()); else raf = requestAnimationFrame(loop);
    } else {
      cancelAnimationFrame(raf);
      map.off("resize", size); map.off("move", redraw);
      if (canvas) canvas.remove(); if (card) card.remove();
      placeExplorer(null);
      canvas = ctx = card = null;
    }
  }

  window.addEventListener("pc:mapready", e => {
    map = e.detail.map;
    places = (e.detail.pins.features || []).map(f => f.properties).filter(p => p.lon != null && p.lat != null);
    btn.hidden = false;
    btn.addEventListener("click", () => toggle());
  });
})();
