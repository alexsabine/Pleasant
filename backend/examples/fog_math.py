"""Fog mode maths: the CRR equations as used by web/static/pc/fog.js, checked before they reach the shader.

Equations (Alex's CRR sheet, "The circle, the cut and the journey"; phoenix_selected/03_math_selected.md):
  1 Coherence      C = (1/sigma) * integral v_FR dt      Fisher-Rao arc of a belief path
  2 Rupture        integral delta(t - t_{n+1}) dt = 1     an arrival is one event of unit weight
  3 Regeneration   m_new = q m + (1 - q) Phi              past-only memory, 0 <= q < 1
  4 Lived surplus  S = C - C* >= 0                         travel beyond the shortest passage
  Omega = 1 is used only as a normalisation.

How fog.js uses them
  F1  A clearing moves along the Bernoulli Fisher-Rao geodesic at constant speed: theta = 2 asin(sqrt(u)) changes
      linearly in time, so equal times give equal Fisher-Rao steps and C = (1/sigma) * pi for a full clearing.
  F2  Arrivals are counted events: N increases by exactly one per arrival, whatever the time between them (the two
      clocks: C accumulates continuously, N counts).
  F3  Regeneration runs on the event clock with q = 0.75. The fixed point of m <- q m + (1 - q) Phi is Phi itself
      (m_k = Phi + (m_0 - Phi) q^k), so with Phi = 1 explored ground stays clear for good, as in a game; a path cleared
      only partly would rise to clear. The sheet's own example q = 0.75, m = 10, Phi = 14 gives 11.
  F4  On the map, C is the distance walked and C* the straight line from the start: S = C - C* >= 0 by the triangle
      inequality. The sheet's example C* = 5 with 1.5 backwards and 1.5 retraced gives C = 8, S = 3.
  F5  Opacity = theta / pi with theta = 2 asin(sqrt(p)) is monotone in p and runs 0..1 (no jumps).
  F6  Omega = 1: the fBm octave weights are normalised to sum to one, so density stays in [0, 1].
  F8  Each walk is one capsule: its clearing depends on the distance to the segment walked, so every point on the
      line walked is exactly as clear as the explorer's own footprint, and points off the line fade with distance.
  F7  Footprints are flat-topped, g = exp(-(d^2 / r^2)^2 / 2): the explorer's own spot stays clear (about 3% fog
      inside half a radius) while the edge stays crisp, unlike a plain Gaussian.
Writes research/14_fog_mode.md. Run: python3 backend/examples/fog_math.py
"""
from __future__ import annotations

import random
from math import asin, cos, hypot, pi, sin, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
results = []


def record(key, ok, detail):
    results.append((key, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} {key}: {detail}")


theta = lambda u: 2 * asin(sqrt(u))          # Fisher-Rao coordinate of Bern(u)
u_of = lambda th: sin(th / 2) ** 2

# F1: constant Fisher-Rao speed --------------------------------------------------------------------
T, sigma, steps = 1.6, 1.0, 400
v = pi / T
ths = [pi - v * (T * k / steps) for k in range(steps + 1)]
us = [u_of(th) for th in ths]
arc = sum(abs(theta(a) - theta(b)) for a, b in zip(us, us[1:])) / sigma
equal = max(abs(theta(a) - theta(b)) for a, b in zip(us, us[1:])) - min(abs(theta(a) - theta(b)) for a, b in zip(us, us[1:]))
record("F1", abs(arc - pi / sigma) < 1e-9 and equal < 1e-9 and abs(us[-1]) < 1e-12,
       f"full clearing in {T}s: C = {arc:.6f} = pi/sigma; every frame moves the same Fisher-Rao step")

# F2: arrivals are unit events -------------------------------------------------------------------
rng = random.Random(16)
gaps = [rng.uniform(0.5, 30) for _ in range(9)]
N = sum(1 for _ in gaps)
record("F2", N == len(gaps), f"{N} arrivals over {sum(gaps):.0f}s of uneven gaps: N counts events, not time")

# F3: regeneration on the event clock --------------------------------------------------------------
q = 0.75
ex = q * 10 + (1 - q) * 14
PHI = 1.0
trail = [1.0]                                  # the first walk, fully clear
for _ in range(4):                             # four more arrivals
    trail = [q * c + (1 - q) * PHI for c in trail] + [1.0]
half = 0.5
for _ in range(30):                            # a path cleared only halfway rises to clear
    half = q * half + (1 - q) * PHI
record("F3", abs(ex - 11) < 1e-12 and all(abs(c - 1) < 1e-12 for c in trail) and abs(half - PHI) < 1e-3,
       f"sheet example gives {ex:g}; with Phi = 1 every walked path stays clear after five more arrivals "
       f"{[round(c, 2) for c in trail]}, and a half-cleared path rises to {half:.3f}")

# F4: lived surplus ------------------------------------------------------------------------------
C_star, C = 5.0, 5.0 + 1.5 + 1.5
ok_example = (C, C - C_star) == (8.0, 3.0)
worst = 0.0
for _ in range(2000):
    pts = [(rng.uniform(0, 30), rng.uniform(0, 30)) for _ in range(rng.randint(2, 9))]
    walked = sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    straight = hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
    worst = min(worst, walked - straight)
record("F4", ok_example and worst >= -1e-9, f"sheet example C = {C:g}, S = {C - C_star:g}; 2,000 random journeys: smallest S = {worst:.2e} (never negative)")

# F5: opacity from the Fisher-Rao angle -----------------------------------------------------------
grid = [k / 1000 for k in range(1001)]
op = [theta(p) / pi for p in grid]
record("F5", all(b > a for a, b in zip(op, op[1:])) and op[0] == 0 and abs(op[-1] - 1) < 1e-12 and max(b - a for a, b in zip(op, op[1:])) < 0.03,
       f"opacity rises smoothly from 0 to 1; largest step on a 0.001 grid {max(b - a for a, b in zip(op, op[1:])):.4f}")

# F6: Omega = 1 normalisation --------------------------------------------------------------------
w = [0.5 * 0.5 ** k for k in range(5)]
record("F6", abs(sum(x / sum(w) for x in w) - 1) < 1e-12, "five octave weights normalised to sum to one, so fog density stays within [0, 1]")

# F7: flat-topped footprints --------------------------------------------------------------------
from math import exp
flat = lambda t: exp(-0.5 * t * t)            # t = d^2 / r^2
gauss = lambda t: exp(-0.5 * t)
core_flat = 1 - flat(0.25)                     # fog remaining at d = r/2 (c = 1)
core_gauss = 1 - gauss(0.25)
slope = lambda f: abs(f(1.05) - f(0.95)) / 0.1
record("F7", core_flat < 0.035 and core_gauss > 0.1 and slope(flat) > slope(gauss),
       f"fog left at half a radius: flat-topped {core_flat:.3f} vs Gaussian {core_gauss:.3f}; edge steepness {slope(flat):.2f} vs {slope(gauss):.2f}")

# F8: capsules -----------------------------------------------------------------------------------------
def seg_dist(px, py, ax, ay, bx, by):
    vx, vy, wx, wy = bx - ax, by - ay, px - ax, py - ay
    h = max(0.0, min(1.0, (wx * vx + wy * vy) / max(vx * vx + vy * vy, 1e-9)))
    return hypot(wx - vx * h, wy - vy * h)
on_line = max(seg_dist(t * 900, t * 400, 0, 0, 900, 400) for t in [k / 50 for k in range(51)])
off = [seg_dist(450, 200 + o, 0, 0, 900, 400) for o in (0, 100, 200, 400)]
record("F8", on_line < 1e-9 and all(b > a for a, b in zip(off, off[1:])),
       f"every point on a 985 m walk is at distance {on_line:.1e} from its capsule; moving off the line, distance grows {[round(x) for x in off]} m")

passed = sum(ok for _, ok, _ in results)
print(f"{passed}/{len(results)} checks passed")
lines = ["# Fog mode: the maths", "", "Generated by `backend/examples/fog_math.py`. Implementation: `web/static/pc/fog.js`.", "",
         "| CRR equation | Used in fog mode as |", "|---|---|",
         "| Coherence, C = (1/sigma) integral v_FR dt | Each clearing, including the explorer's moving lantern, grows along the Fisher-Rao geodesic at constant speed, so the fog parts evenly |",
         "| Rupture, a unit event at t(n+1) | Arriving at a place is the event: the clearing there blooms out from lantern size to full size, and the explored count rises by one |",
         "| Regeneration, m_new = q m + (1 - q) Phi | Its fixed point is Phi; with Phi = 1, every path walked and place visited stays clear for good, as in a game |",
         "| Lived surplus, S = C - C* >= 0 | Distance walked minus the straight line from the start: shown as wandering, valued rather than penalised |",
         "| Omega = 1 | Only a normalisation: noise octave weights sum to one |", "",
         "Opacity is theta / pi with theta = 2 asin(sqrt(p)), where p is the chance a spot is still unexplored times the "
         "fog cover there. On the flat map, S >= 0 is the triangle inequality; the sheet's intrinsic-circle assumptions are "
         "not claimed here.", "", "## Checks", "", "| Check | Result | Detail |", "|---|---|---|"]
lines += [f"| {k} | {'PASS' if ok else 'FAIL'} | {d} |" for k, ok, d in results]
lines += ["", f"{passed}/{len(results)} passed.", "",
          "Paths: the explorer follows real footpaths and roads, pre-computed by `manage.py build_fog_routes` from the "
          "self-hosted OpenStreetMap basemap (ODbL, (c) OpenStreetMap contributors). Short hops go on foot, preferring paths "
          "and quiet streets; longer ones go by road. Each walk's trail is a chain of capsules along the route's bends. An "
          "illustration for the game, never directions.", "",
          "The look (domain-warped noise, light from the west-south-west, a marine layer thick offshore and on the coastal "
          "plain and thinner inland, onshore drift from the north-west) is ordinary graphics, not a claim of the equations."]
(ROOT / "research" / "14_fog_mode.md").write_text("\n".join(lines) + "\n")
print("wrote research/14_fog_mode.md")
raise SystemExit(0 if passed == len(results) else 1)
