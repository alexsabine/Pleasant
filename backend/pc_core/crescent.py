"""The living crescent: a logo whose phase is the Fisher–Rao coordinate of the
directory's freshness belief.

Mathematics (all public; see research/04_mathematics_register.md F11–F15):
- On the Bernoulli family, the Fisher–Rao geodesic coordinate of a probability
  p is theta = 2·asin(sqrt(p)), theta in [0, pi]. Distances along the family
  are differences of theta. This is exactly the angle CRR/Phoenix integrates.
- A moon's illuminated fraction is (1 - cos(phase)) / 2 with phase in [0, pi].
  Setting phase = theta makes the illuminated fraction equal to p: the
  crescent is a faithful picture of the belief, and the arc the terminator
  sweeps between two states is the Fisher–Rao distance between them.
- "Two clocks": the logo carries three numbers from the system, never a
  metaphysical one: the current belief p (mean P(current) over published
  listings), the path length C the belief travelled over the last window
  (sum of |delta theta| across daily snapshots), and the count N of material
  changes (publications/corrections) in that window. p sets the phase, C the
  gentle breathing amplitude, N the number of small marks on the ring.
- Nothing here claims a cognitive or social law; it is an honest gauge.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, pi, sin, sqrt


def fr_theta(p: float) -> float:
    """Fisher–Rao geodesic coordinate of Bernoulli(p); theta in [0, pi]."""
    if not 0 <= p <= 1:
        raise ValueError("p must lie in [0,1]")
    return 2 * asin(sqrt(p))


def illuminated_fraction(theta: float) -> float:
    return (1 - cos(theta)) / 2


def path_length(ps: list[float]) -> float:
    """Fisher–Rao arc length of a sequence of beliefs (radians)."""
    return sum(abs(fr_theta(b) - fr_theta(a)) for a, b in zip(ps, ps[1:]))


@dataclass(frozen=True)
class CrescentState:
    p: float                  # mean P(current) across published listings
    path_c: float             # FR path length over the window (radians)
    changes_n: int            # material changes in the window
    n_listings: int = 0

    @property
    def theta(self) -> float:
        return fr_theta(self.p)


def terminator_path(theta: float, r: float = 44.0, cx: float = 50.0, cy: float = 50.0, steps: int = 48) -> str:
    """SVG path for the lit part of a moon of radius r at phase theta (0 = new, pi = full).

    The lit region is bounded by the right limb (semicircle) and the
    terminator, a half-ellipse whose horizontal semi-axis is r·cos(theta).
    Light comes from the right; theta in [0, pi] sweeps new -> full.
    """
    k = cos(theta)  # +1 new (terminator on the right limb), -1 full (on the left limb)
    pts = []
    for i in range(steps + 1):
        a = -pi / 2 + pi * i / steps          # right limb from top to bottom
        pts.append((cx + r * cos(a), cy + r * sin(a)))
    for i in range(steps + 1):
        a = pi / 2 - pi * i / steps           # terminator from bottom back to top
        pts.append((cx + r * k * cos(a), cy + r * sin(a)))
    d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
    return d


def crescent_svg(state: CrescentState, colours: dict, size: int = 36, animate: bool = True, title: str | None = None) -> str:
    """Inline SVG. `colours` keys: disc (lit), shadow (dark side), ring, glow."""
    theta = state.theta
    amp = min(0.35, state.path_c)       # breathing amplitude in radians, bounded
    lit = terminator_path(theta)
    lit_lo = terminator_path(max(0.0, theta - amp))
    lit_hi = terminator_path(min(pi, theta + amp))
    marks = ""
    n = min(state.changes_n, 24)
    for i in range(n):
        a = -pi / 2 + 2 * pi * i / max(n, 1)
        x1, y1 = 50 + 47 * cos(a), 50 + 47 * sin(a)
        x2, y2 = 50 + 49.5 * cos(a), 50 + 49.5 * sin(a)
        marks += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{colours["ring"]}" stroke-width="1.2" stroke-linecap="round"/>'
    anim = ""
    if animate and amp > 0.005:
        anim = (f'<animate attributeName="d" dur="14s" repeatCount="indefinite" calcMode="spline" '
                f'keyTimes="0;0.5;1" keySplines="0.45 0 0.55 1;0.45 0 0.55 1" values="{lit_lo};{lit_hi};{lit_lo}"/>')
    ttl = title or (f"Pleasant Crescent. Freshness gauge: mean P(current) {state.p:.2f} over {state.n_listings} listings; "
                    f"belief moved {state.path_c:.2f} rad this window; {state.changes_n} changes")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="{size}" height="{size}" role="img" aria-label="{ttl}">'
            f'<title>{ttl}</title>'
            f'<circle cx="50" cy="50" r="46" fill="{colours["glow"]}" opacity="0.35"/>'
            f'<circle cx="50" cy="50" r="44" fill="{colours["shadow"]}"/>'
            f'<path d="{lit}" fill="{colours["disc"]}">{anim}</path>'
            f'<defs><radialGradient id="pc_limb" cx="0.42" cy="0.40" r="0.62"><stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.22"/></radialGradient></defs>'
            f'<circle cx="50" cy="50" r="44" fill="url(#pc_limb)"/>'
            f'<circle cx="50" cy="50" r="46" fill="none" stroke="{colours["ring"]}" stroke-width="1.5" opacity="0.8"/>'
            f'{marks}</svg>')
