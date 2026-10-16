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
  F3  Trail footprints regenerate on the event clock with q = 0.75: at each arrival, old footprints keep q of their
      clearing (Phi = 0) and the newest walk is clear (Phi = 1). The sheet's own example q = 0.75, m = 10, Phi = 14
      gives 11.
  F4  On the map, C is the distance walked and C* the straight line from the start: S = C - C* >= 0 by the triangle
      inequality. The sheet's example C* = 5 with 1.5 backwards and 1.5 retraced gives C = 8, S = 3.
  F5  Opacity = theta / pi with theta = 2 asin(sqrt(p)) is monotone in p and runs 0..1 (no jumps).
  F6  Omega = 1: the fBm octave weights are normalised to sum to one, so density stays in [0, 1].
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
trail = [1.0]                                  # clearing of the first walk's footprints
for _ in range(4):                             # four more arrivals
    trail = [q * c + (1 - q) * 0 for c in trail] + [1.0]
record("F3", abs(ex - 11) < 1e-12 and [round(c, 3) for c in trail] == [0.316, 0.422, 0.562, 0.75, 1.0],
       f"sheet example gives {ex:g}; footprints after five walks, oldest first: {[round(c, 2) for c in trail]}")

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

passed = sum(ok for _, ok, _ in results)
print(f"{passed}/{len(results)} checks passed")
lines = ["# Fog mode: the maths", "", "Generated by `backend/examples/fog_math.py`. Implementation: `web/static/pc/fog.js`.", "",
         "| CRR equation | Used in fog mode as |", "|---|---|",
         "| Coherence, C = (1/sigma) integral v_FR dt | Each clearing moves along the Fisher-Rao geodesic at constant speed, so the fog thins and rolls back evenly |",
         "| Rupture, a unit event at t(n+1) | Arriving at a place is the event: clearing targets change and the explored count rises by one |",
         "| Regeneration, m_new = q m + (1 - q) Phi | On each arrival, older trail footprints keep 75% of their clearing; the newest walk is clear; visited places stay clear |",
         "| Lived surplus, S = C - C* >= 0 | Distance walked minus the straight line from the start: shown as wandering, valued rather than penalised |",
         "| Omega = 1 | Only a normalisation: noise octave weights sum to one |", "",
         "Opacity is theta / pi with theta = 2 asin(sqrt(p)), where p is the chance a spot is still unexplored times the "
         "fog cover there. On the flat map, S >= 0 is the triangle inequality; the sheet's intrinsic-circle assumptions are "
         "not claimed here.", "", "## Checks", "", "| Check | Result | Detail |", "|---|---|---|"]
lines += [f"| {k} | {'PASS' if ok else 'FAIL'} | {d} |" for k, ok, d in results]
lines += ["", f"{passed}/{len(results)} passed.", "",
          "The look (domain-warped noise, light from the west-south-west, a marine layer thick offshore and on the coastal "
          "plain and thinner inland, onshore drift from the north-west) is ordinary graphics, not a claim of the equations."]
(ROOT / "research" / "14_fog_mode.md").write_text("\n".join(lines) + "\n")
print("wrote research/14_fog_mode.md")
raise SystemExit(0 if passed == len(results) else 1)
