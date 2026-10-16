/* Fog mode (demo): Crescent City sea fog over the map, cleared place by place by a little explorer.
 *
 * Mathematics (checked in backend/examples/fog_math.py, written up in research/14_fog_mode.md):
 * - Belief a spot is unexplored: u(x) = prod_i (1 - c_i exp(-d_i^2 / 2 r_i^2)), one factor per footprint.
 * - Opacity = fog density x theta / pi, theta = 2 asin(sqrt(u)): the Fisher-Rao angle of Bern(u).
 * - Coherence, C = (1/sigma) int v_FR dt: every clearing moves along the Fisher-Rao geodesic at constant speed,
 *   so fog thins (and rolls back) evenly.
 * - Rupture, a unit event at t_{n+1}: an arrival. Targets change only then, and the explored count rises by one.
 * - Regeneration, m_new = q m + (1 - q) Phi, on the event clock: its fixed point is Phi. With Phi = 1 for every
 *   path and place, explored ground stays clear for good, as in a game: you can always see where you have been.
 * - Each walk is one capsule (a band from where it started to where the explorer is) that grows behind them, so a
 *   long journey costs one shape per walk. Trails are saved on this device with the places visited.
 * - The explorer carries a lantern footprint that moves with every step, so the fog visibly parts around them.
 * - Footprints are flat-topped, exp(-(d^2/r^2)^2 / 2): a clear core and a crisp, wispy edge. The edge is shaded by
 *   the Bernoulli variance u(1 - u), largest where the belief is most uncertain.
 * - Lived surplus, S = C - C* >= 0: distance walked minus the straight line from the start, shown as wandering.
 * - Omega = 1, a normalisation only: noise octave weights sum to one.
 * The look is ordinary graphics: domain-warped noise, light from the west-south-west, a marine layer thick offshore
 * and on the coastal plain, thinner inland, drifting onshore from the north-west. It is drawn by a small shader in
 * ground coordinates (metres), redrawn in the same frame as every map movement, at half resolution.
 * Privacy: no device location is ever read; the explorer goes only where you choose; the trail stays on this device.
 */
(function () {
  "use strict";
  const btn = document.querySelector(".fog-toggle");
  if (!btn) return;
  const reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const KEY = "pc_fog_v2", SCALE = 0.5, FPS = 30;
  const VISIT_M = 340, TRAIL_M = 160, LANTERN_M = 230, Q = 0.75, PHI = 1;   // radii (m); regeneration, fixed point
  const V_FR = Math.PI / 1.6;                              // Fisher-Rao speed: a full clearing takes 1.6 s
  const LON0 = -124.20, LAT0 = 41.755, KX = 111320 * Math.cos(LAT0 * Math.PI / 180), KY = 110540;
  const toXY = (lon, lat) => [(lon - LON0) * KX, (lat - LAT0) * KY];
  // Del Norte coastline, north to south (approximate), for a marine layer that thins inland
  const COAST = [[42.00, -124.21], [41.85, -124.22], [41.78, -124.25], [41.745, -124.19], [41.70, -124.14], [41.55, -124.08], [41.40, -124.06]]
    .map(([lat, lon]) => toXY(lon, lat));
  const WIND = [0.78, -0.62];                              // onshore, from the north-west

  let map = null, places = [], on = false, canvas = null, gl = null, prog = null, buf = null, loc = {}, NS = 32;
  let spots = [], lantern = null, visited = [], current = null, walked = 0, arrivals = 0, explorer = null, card = null, walking = false;
  let raf = 0, lastT = 0, lastDraw = 0, windOff = [0, 0], tEvo = 0;

  // --- state on this device only ---------------------------------------------------------------------------
  function load() {
    try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s && Array.isArray(s.visited)) return s; } catch (e) { /* private mode */ }
    return null;
  }
  function save() {
    const trails = spots.filter(s => s.kind === "trail").map(s => [s.a[0], s.a[1], s.b[0], s.b[1]].map(v => +v.toFixed(5)));
    try { localStorage.setItem(KEY, JSON.stringify({ visited: visited.map(p => p.id), current: current && current.id, walked, trails })); } catch (e) { /* ignore */ }
  }

  // --- geography ---------------------------------------------------------------------------------------------
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
  const mpp = () => 40075016.686 * Math.cos(rad(map.getCenter().lat)) / (512 * Math.pow(2, map.getZoom()));

  // --- choices: starts in three communities; then the nearest unvisited place in up to three kinds, new kinds first
  function starts() {
    const byCommunity = new Map();
    places.forEach(p => { const k = p.community_label || "Elsewhere"; (byCommunity.get(k) || byCommunity.set(k, []).get(k)).push(p); });
    return [...byCommunity.entries()].sort((a, b) => b[1].length - a[1].length).slice(0, 3).map(([, list]) => {
      const c = { lat: list.reduce((t, p) => t + p.lat, 0) / list.length, lon: list.reduce((t, p) => t + p.lon, 0) / list.length };
      return list.slice().sort((a, b) => metres(c, a) - metres(c, b))[0];
    });
  }
  function choices(from) {
    if (!from) return starts();
    const seenGroups = new Set(visited.map(p => p.group)), seenIds = new Set(visited.map(p => p.id));
    const pool = places.filter(p => !seenIds.has(p.id) && p.id !== from.id);
    pool.forEach(p => { p._d = metres(from, p); });
    pool.sort((a, b) => a._d - b._d);
    const byGroup = new Map();
    for (const p of pool) if (!byGroup.has(p.group)) byGroup.set(p.group, p);
    return [...byGroup.values()].sort((a, b) => (seenGroups.has(a.group) - seenGroups.has(b.group)) || (a._d - b._d)).slice(0, 3);
  }

  // --- the card -------------------------------------------------------------------------------------------------
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const article = w => (/^[aeiou]/i.test(w) ? "an " : "a ") + w.toLowerCase();
  function render() {
    if (!card) return;
    const opts = choices(current);
    let story;
    if (!current) story = `<p class="fog-story">Sea fog has rolled in over Del Norte County. Where would you like to begin?</p>`;
    else {
      const kinds = new Set(visited.map(p => p.group)).size;
      const straight = visited.length ? metres(visited[0], current) : 0, wander = Math.max(0, walked - straight);   // S = C - C*
      story = `<p class="fog-story">You reach <b>${esc(current.name)}</b>, ${esc(article(current.category_label))}. The fog lifts around you.</p>
        <p class="fog-meta">${visited.length} place${visited.length === 1 ? "" : "s"} explored, ${kinds} kind${kinds === 1 ? "" : "s"}${walked > 0 ? ` · walked ${miles(walked)}, ${miles(wander)} of it wandering` : ""} · <a href="${esc(window.PC_ORIGIN || "")}/resource/${esc(current.slug)}/">About this place</a></p>`;
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
    if (b.dataset.act === "restart") { visited = []; current = null; spots = []; walked = 0; arrivals = 0; save(); placeExplorer(null); render(); kick(); return; }
    const p = places.find(x => String(x.id) === b.dataset.id);
    if (p) go(p);
  }

  // --- the explorer -----------------------------------------------------------------------------------------------
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
    if (!p) { if (explorer) { explorer.remove(); explorer = null; } lantern = null; return; }
    if (!explorer) explorer = new maplibregl.Marker({ element: explorerEl(), anchor: "bottom" }).setLngLat([p.lon, p.lat]).addTo(map);
    else explorer.setLngLat([p.lon, p.lat]);
    moveLantern(p.lon, p.lat);
  }
  function moveLantern(lon, lat) {                         // the clearing the explorer carries with them
    if (!lantern) lantern = capsule([lon, lat], [lon, lat], LANTERN_M, "lantern", !reduced);
    else { lantern.a = lantern.b = [lon, lat]; lantern.ax = lantern.bx = toXY(lon, lat)[0]; lantern.ay = lantern.by = toXY(lon, lat)[1]; }
  }

  // --- footprints: Fisher-Rao clearing, regeneration on arrivals -------------------------------------------------
  const thetaOf = c => 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, 1 - c))));   // theta of u = 1 - c
  // every footprint is a capsule from a to b ([lon, lat]); a place is a capsule of zero length
  function capsule(a, b, r, kind, animate) {
    const [ax, ay] = toXY(a[0], a[1]), [bx, by] = toXY(b[0], b[1]);
    return { a, b, ax, ay, bx, by, r, kind, walk: arrivals, target: 1, th: animate ? Math.PI : 0, c: animate ? 0 : 1 };
  }
  function footprint(lon, lat, r, kind) { const s = capsule([lon, lat], [lon, lat], r, kind, !reduced); spots.push(s); return s; }
  function stretch(s, lon, lat) { s.b = [lon, lat]; [s.bx, s.by] = toXY(lon, lat); }
  function arrive(p) {                                     // a rupture: one event of unit weight
    arrivals += 1;
    // regeneration: m <- q m + (1 - q) Phi has fixed point Phi; with Phi = 1, explored ground stays clear
    for (const s of spots) if (s.kind === "trail") s.target = Q * s.target + (1 - Q) * PHI;
    current = p; visited.push(p); footprint(p.lon, p.lat, VISIT_M, "visit");
    if (reduced) for (const s of spots) { s.th = thetaOf(s.target); s.c = s.target; }
  }
  function step(dt) {                                      // coherence: constant Fisher-Rao speed toward each target
    let moving = false;
    for (const s of lantern ? spots.concat([lantern]) : spots) {
      const goal = thetaOf(s.target), d = goal - s.th;
      if (Math.abs(d) > 1e-4) { s.th += Math.sign(d) * Math.min(Math.abs(d), V_FR * dt); moving = true; }
      s.c = 1 - Math.sin(s.th / 2) ** 2;
    }
    return moving;
  }

  function pad() {
    if (!card) return 0;
    const box = map.getContainer().getBoundingClientRect(), c = card.getBoundingClientRect();
    return c.width > box.width * 0.7 ? { top: 20, bottom: Math.min(box.height * 0.6, c.height + 10), left: 0, right: 0 }
                                     : { left: c.width + 20, top: 0, bottom: 0, right: 0 };
  }
  function go(p) {
    const from = current, z = Math.max(map.getZoom(), 13.2), padding = pad();
    if (!from || reduced) {
      if (from) walked += metres(from, p);
      arrive(p); placeExplorer(p);
      if (reduced) map.jumpTo({ center: [p.lon, p.lat], zoom: z, padding }); else map.flyTo({ center: [p.lon, p.lat], zoom: z, padding, duration: 2200 });
      save(); render(); kick(); return;
    }
    walking = true;
    card.classList.add("busy");
    const d = metres(from, p), dur = Math.min(4200, 1400 + d / 6);
    map.easeTo({ center: [p.lon, p.lat], zoom: z, padding, duration: dur });
    const el = explorer.getElement();
    el.classList.add("walking");
    el.classList.toggle("west", p.lon < from.lon);
    const start = performance.now();
    const trail = capsule([from.lon, from.lat], [from.lon, from.lat], TRAIL_M, "trail", false);   // grows behind the explorer
    spots.push(trail);
    (function walk(now) {
      const k = Math.min(1, (now - start) / dur), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      const lon = from.lon + (p.lon - from.lon) * e, lat = from.lat + (p.lat - from.lat) * e;
      explorer.setLngLat([lon, lat]); moveLantern(lon, lat);
      stretch(trail, lon, lat);
      if (k < 1) return requestAnimationFrame(walk);
      el.classList.remove("walking");
      walked += d;
      arrive(p);
      walking = false; card.classList.remove("busy");
      save(); render();
      const first = card.querySelector(".fog-choice"); if (first) first.focus({ preventScroll: true });
    })(start);
  }

  // --- the shader --------------------------------------------------------------------------------------------------
  const VERT = `attribute vec2 aPos; attribute vec2 aWorld; varying vec2 vW;
    void main(){ vW = aWorld; gl_Position = vec4(aPos, 0.0, 1.0); }`;
  const FRAG = (precision, ns) => `precision ${precision} float;
    #define NS ${ns}
    varying vec2 vW;
    uniform vec2 uWind; uniform float uT; uniform vec4 uSeg[NS]; uniform vec4 uRC[NS / 2]; uniform int uCount;
    uniform vec2 uCoast[7]; uniform vec3 uLo; uniform vec3 uHi; uniform float uMax; uniform float uMpp;
    uniform vec4 uLamp; uniform vec3 uWarm;
    float hash(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
    float noise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);   // quintic: no grid creases
      return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y); }
    // Omega = 1: octave weights are renormalised to sum to one. Octaves finer than about three pixels fade out
    // (level of detail), so nothing shimmers or streaks when zoomed out. wl = wavelength of the first octave, metres.
    float lod(float wl){ return clamp((wl / uMpp - 3.0) / 3.0, 0.0, 1.0); }
    float fbm(vec2 p, float wl){
      float v = 0.0, a = 0.5, n = 0.0; mat2 r = mat2(0.8, -0.6, 0.6, 0.8);
      for (int o = 0; o < 5; o++){ float k = o == 0 ? 1.0 : lod(wl); v += a * k * noise(p); n += a * k;
        p = r * p * 2.02 + vec2(17.1, 9.2); a *= 0.48; wl /= 2.02; }
      return v / n; }
    float fbm3(vec2 p, float wl){            // a cheaper three-octave version for the slow warp fields
      float v = 0.0, a = 0.5, n = 0.0; mat2 r = mat2(0.8, -0.6, 0.6, 0.8);
      for (int o = 0; o < 3; o++){ float k = o == 0 ? 1.0 : lod(wl); v += a * k * noise(p); n += a * k;
        p = r * p * 2.02 + vec2(17.1, 9.2); a *= 0.5; wl /= 2.02; }
      return v / n; }
    float coastX(float y){
      float x = uCoast[0].x;
      for (int i = 0; i < 6; i++){ vec2 a = uCoast[i], b = uCoast[i + 1];
        if (y <= a.y && y >= b.y) x = mix(a.x, b.x, (a.y - y) / (a.y - b.y)); }
      if (y < uCoast[6].y) x = uCoast[6].x;
      return x; }
    void main(){
      vec2 km = (vW - uWind) / 1000.0;                      // the air moves; the ground stays put
      vec2 p = km / 6.0;                                    // banks several kilometres across
      vec2 q = vec2(fbm3(p + vec2(0.0, 0.010 * uT), 6000.0), fbm3(p + vec2(5.2, 1.3) - vec2(0.008 * uT, 0.0), 6000.0));
      vec2 r = vec2(fbm3(p + 1.4 * q + vec2(1.7, 9.2), 6000.0), fbm3(p + 1.4 * q + vec2(8.3, 2.8), 6000.0));
      vec2 w = p + 0.8 * r;                                 // gentle domain warp: rolling, not marbled
      float d = fbm(w, 6000.0);
      float dBig = fbm3(w, 6000.0);                         // the broad billows only, for light and shade
      float dSun = fbm3(w + vec2(-0.11, -0.045), 6000.0);   // one step toward the sun, low in the west-south-west
      float lit = clamp(0.64 + (dBig - dSun) * 2.6 + (d - dBig) * 0.6, 0.0, 1.0);
      float inland = (vW.x - coastX(vW.y)) / 1000.0;        // km east of the coast
      float coast = 1.0 - 0.12 * smoothstep(2.0, 24.0, inland);          // thick everywhere, a touch thinner inland
      float cover = coast * (0.93 + 0.07 * smoothstep(0.30, 0.64, d));
      float wob = fbm3(km * 1.3 + vec2(3.1, 7.7) + 0.02 * uT, 770.0) - 0.5;   // ragged, breathing edges to each clearing
      float logu = 0.0;
      for (int i = 0; i < NS; i++){ if (i >= uCount) break;
        vec4 sg = uSeg[i]; vec4 rc4 = uRC[i / 2]; vec2 rc = (i - 2 * (i / 2)) == 0 ? rc4.xy : rc4.zw;
        vec2 pa = vW - sg.xy, ba = sg.zw - sg.xy;           // distance to the capsule from a to b
        vec2 dv = pa - ba * clamp(dot(pa, ba) / max(dot(ba, ba), 1e-3), 0.0, 1.0);
        float e = dot(dv, dv) / (rc.x * rc.x) * (1.0 + 0.9 * wob);
        logu += log(max(1e-4, 1.0 - rc.y * exp(-0.5 * e * e))); }      // flat-topped: clear core, crisp edge
      float u = clamp(exp(logu), 0.0, 1.0);                 // belief the spot is unexplored
      float a = uMax * cover * (2.0 / 3.14159265) * asin(sqrt(u));   // density x theta / pi, the Fisher-Rao angle
      vec3 col = mix(uLo, uHi, lit) * mix(0.93, 1.0, lit);
      col *= 1.0 - 0.16 * 4.0 * u * (1.0 - u);              // edge shade where belief is least certain, u(1 - u)
      vec2 dl = vW - uLamp.xy;                              // lantern light scattering in the nearby fog
      col = mix(col, uWarm, 0.38 * uLamp.w * exp(-dot(dl, dl) / (2.0 * 3.2 * uLamp.z * uLamp.z)));
      gl_FragColor = vec4(col * a, a);                      // premultiplied
    }`;

  function compile(type, src) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  function setupGL() {
    gl = canvas.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: false, depth: false, stencil: false });
    if (!gl) return false;
    const hp = gl.getShaderPrecisionFormat(gl.FRAGMENT_SHADER, gl.HIGH_FLOAT);
    NS = 2 * Math.floor(Math.max(8, Math.min(120, (gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS) - 24) / 1.5)) / 2);   // 1.5 vectors each
    prog = gl.createProgram();
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG(hp && hp.precision > 0 ? "highp" : "mediump", NS)));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
    gl.useProgram(prog);
    ["uWind", "uT", "uSeg", "uRC", "uCount", "uCoast", "uLo", "uHi", "uMax", "uMpp", "uLamp", "uWarm"].forEach(n => { loc[n] = gl.getUniformLocation(prog, n); });
    loc.aPos = gl.getAttribLocation(prog, "aPos"); loc.aWorld = gl.getAttribLocation(prog, "aWorld");
    buf = gl.createBuffer();
    gl.uniform2fv(loc.uCoast, new Float32Array(COAST.flat()));
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    return true;
  }
  function colours() {
    const dark = window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches && document.documentElement.dataset.theme !== "light";
    return dark ? { lo: [0.07, 0.09, 0.13], hi: [0.40, 0.44, 0.52], warm: [0.85, 0.62, 0.32], max: 0.96 }
                : { lo: [0.62, 0.67, 0.74], hi: [0.975, 0.97, 0.955], warm: [1.0, 0.86, 0.6], max: 0.975 };
  }

  function draw(now) {
    if (!on || !gl) return;
    const dt = Math.min(0.1, Math.max(0, (now - (lastT || now)) / 1000));
    lastT = now; lastDraw = now;
    if (!reduced) {
      const v = 7 * mpp();                                 // about 7 screen pixels a second, at any zoom
      windOff[0] += WIND[0] * v * dt; windOff[1] += WIND[1] * v * dt;
      tEvo += dt;
    }
    const animating = step(reduced ? 1e9 : dt);
    const box = map.getContainer(), w = Math.max(1, Math.round(box.clientWidth * SCALE)), h = Math.max(1, Math.round(box.clientHeight * SCALE));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    const cw = box.clientWidth, ch = box.clientHeight;
    const corner = (x, y) => { const ll = map.unproject([x, y]); return toXY(ll.lng, ll.lat); };
    const bl = corner(0, ch), br = corner(cw, ch), tl = corner(0, 0), tr = corner(cw, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, ...bl, 1, -1, ...br, -1, 1, ...tl, 1, 1, ...tr]), gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(loc.aPos); gl.vertexAttribPointer(loc.aPos, 2, gl.FLOAT, false, 16, 0);
    gl.enableVertexAttribArray(loc.aWorld); gl.vertexAttribPointer(loc.aWorld, 2, gl.FLOAT, false, 16, 8);
    // footprints near the view, most recent first, up to the GPU's budget
    const xs = [bl[0], br[0], tl[0], tr[0]], ys = [bl[1], br[1], tl[1], tr[1]];
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const live = lantern && lantern.c > 0.004 ? [lantern] : [];
    for (let i = spots.length - 1; i >= 0 && live.length < NS; i--) {
      const s = spots[i], m = 3 * s.r;
      if (s.c > 0.004 && Math.max(s.ax, s.bx) > minX - m && Math.min(s.ax, s.bx) < maxX + m && Math.max(s.ay, s.by) > minY - m && Math.min(s.ay, s.by) < maxY + m) live.push(s);
    }
    const seg = new Float32Array(NS * 4), rc = new Float32Array(NS * 2);
    // a visit blooms out from lantern size to full size as it clears (the rupture made visible)
    live.forEach((s, i) => {
      seg.set([s.ax, s.ay, s.bx, s.by], i * 4);
      rc.set([s.kind === "visit" ? s.r * (0.6 + 0.4 * s.c) : s.r, s.c], i * 2);
    });
    const col = colours();
    gl.uniform4fv(loc.uSeg, seg); gl.uniform4fv(loc.uRC, rc); gl.uniform1i(loc.uCount, live.length);
    gl.uniform2f(loc.uWind, windOff[0], windOff[1]); gl.uniform1f(loc.uT, tEvo);
    gl.uniform3fv(loc.uLo, col.lo); gl.uniform3fv(loc.uHi, col.hi); gl.uniform1f(loc.uMax, col.max);
    gl.uniform1f(loc.uMpp, mpp() / SCALE);                 // metres per fog pixel, for level of detail
    gl.uniform4f(loc.uLamp, lantern ? lantern.ax : 0, lantern ? lantern.ay : 0, LANTERN_M, lantern ? lantern.c : 0);
    gl.uniform3fv(loc.uWarm, col.warm);
    gl.viewport(0, 0, w, h);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    if (reduced && animating) kick();
  }
  function loop(now) {
    if (!on) return;
    raf = requestAnimationFrame(loop);
    if (document.hidden || now - lastDraw < 1000 / FPS - 2) return;
    draw(now);
  }
  function kick() { if (on) requestAnimationFrame(t => draw(t)); }
  const onRender = () => { if (on) draw(performance.now()); };   // same frame as the map: no lag, no jitter

  // --- switching on and off ------------------------------------------------------------------------------------------
  function toggle(want) {
    const next = want === undefined ? !on : want;
    const wrap = map.getContainer().parentElement;
    if (next) {
      canvas = document.createElement("canvas");
      canvas.className = "fog-canvas";
      canvas.setAttribute("aria-hidden", "true");
      const host = map.getCanvasContainer();               // under markers and popups, over the map itself
      host.insertBefore(canvas, map.getCanvas().nextSibling);
      try { if (!setupGL()) throw new Error("no WebGL"); } catch (err) { canvas.remove(); canvas = null; gl = null; console.warn("Fog mode unavailable:", err); return; }
      on = true;
      btn.setAttribute("aria-pressed", "true");
      wrap.classList.add("fog-on");
      card = document.createElement("section");
      card.className = "fog-card";
      card.setAttribute("aria-label", "Fog mode");
      card.setAttribute("aria-live", "polite");
      card.addEventListener("click", onCard);
      wrap.appendChild(card);
      const saved = load();
      visited = saved ? saved.visited.map(id => places.find(p => p.id === id)).filter(Boolean) : [];
      current = saved && saved.current ? places.find(p => p.id === saved.current) || null : null;
      walked = saved && saved.walked || 0; arrivals = visited.length;
      spots = [];
      visited.forEach(p => footprint(p.lon, p.lat, VISIT_M, "visit"));
      (saved && Array.isArray(saved.trails) ? saved.trails : []).forEach(t => spots.push(capsule([t[0], t[1]], [t[2], t[3]], TRAIL_M, "trail", false)));
      spots.forEach(s => { s.th = 0; s.c = 1; });
      placeExplorer(current);
      render();
      if (current) {                                       // resume where the explorer left off
        const view = { center: [current.lon, current.lat], zoom: Math.max(map.getZoom(), 12.5), padding: pad() };
        if (reduced) map.jumpTo(view); else map.flyTo({ ...view, duration: 1600 });
      }
      lastT = 0;
      map.on("render", onRender);
      if (reduced) kick(); else raf = requestAnimationFrame(loop);
    } else {
      on = false;
      btn.setAttribute("aria-pressed", "false");
      wrap.classList.remove("fog-on");
      cancelAnimationFrame(raf);
      map.off("render", onRender);
      if (gl) { const ext = gl.getExtension("WEBGL_lose_context"); if (ext) ext.loseContext(); }
      if (canvas) canvas.remove(); if (card) card.remove();
      placeExplorer(null);
      canvas = gl = card = null;
    }
  }

  window.addEventListener("pc:mapready", e => {
    map = e.detail.map;
    places = (e.detail.pins.features || []).map(f => f.properties).filter(p => p.lon != null && p.lat != null);
    btn.hidden = false;
    btn.addEventListener("click", () => toggle());
  });
})();
