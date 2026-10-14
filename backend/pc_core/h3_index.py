"""Guarded H3 helpers: a DERIVED index, never a source of geography.

H3 (Uber, Apache-2.0; https://h3geo.org/docs) is a hierarchical hexagonal grid.
We use it only for (a) coarse aggregate grouping, (b) cache keys for map
projections, (c) k-anonymous counts. PostGIS geometry stays authoritative.

Guards enforced here:
- public aggregates are suppressed below a k-anonymity threshold;
- no function returns a travel time or a road distance;
- sensitive records are only ever aggregated at or above a coarsening
  resolution, never placed in a fine cell.

The `h3` package is optional; import errors surface as H3Unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass

try:  # optional dependency
    import h3 as _h3
except ImportError:  # pragma: no cover
    _h3 = None


class H3Unavailable(RuntimeError):
    pass


def _require():
    if _h3 is None:
        raise H3Unavailable("python -m pip install h3  (pin the version in requirements)")
    return _h3


# Resolutions we allow for public aggregates. 7 (~5 km2 cells) and 8 (~0.7 km2)
# suit a county; 9+ can single out a house and is NOT used for people.
PUBLIC_MIN_RES, PUBLIC_MAX_RES = 5, 8
SENSITIVE_MAX_RES = 6  # coarse cells only for sensitive categories


@dataclass(frozen=True)
class CellCount:
    cell: str
    count: int
    suppressed: bool


def cell_for(lat: float, lon: float, res: int) -> str:
    h3 = _require()
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("lat/lon out of range")
    if not 0 <= res <= 15:
        raise ValueError("H3 resolution must be 0..15")
    return h3.latlng_to_cell(lat, lon, res)


def public_aggregate(points: list[tuple[float, float, bool]], res: int, k: int = 5) -> list[CellCount]:
    """Count points per cell; suppress counts < k; sensitive points are coarsened.

    points: (lat, lon, is_sensitive). Sensitive points are counted at
    min(res, SENSITIVE_MAX_RES) and then reported under the coarse cell id, so a
    reader cannot localise them finer than the policy allows.
    """
    h3 = _require()
    if not PUBLIC_MIN_RES <= res <= PUBLIC_MAX_RES:
        raise ValueError(f"public aggregates only at resolutions {PUBLIC_MIN_RES}..{PUBLIC_MAX_RES}")
    if k < 2:
        raise ValueError("k-anonymity threshold must be at least 2")
    counts: dict[str, int] = {}
    for lat, lon, sensitive in points:
        r = min(res, SENSITIVE_MAX_RES) if sensitive else res
        c = h3.latlng_to_cell(lat, lon, r)
        counts[c] = counts.get(c, 0) + 1
    return [CellCount(c, n if n >= k else 0, n < k) for c, n in sorted(counts.items())]


def grid_distance(a: str, b: str) -> int:
    """Hex-grid steps between cells. This is NOT a road distance or a travel time."""
    return _require().grid_distance(a, b)


def cell_area_km2(cell: str) -> float:
    return _require().cell_area(cell, unit="km^2")


def cells_covering(polygon_latlon: list[tuple[float, float]], res: int) -> set[str]:
    """Cells whose centre falls inside the polygon (h3 'polygon_to_cells')."""
    h3 = _require()
    return set(h3.polygon_to_cells(h3.LatLngPoly(polygon_latlon), res))


def parent(cell: str, res: int) -> str:
    return _require().cell_to_parent(cell, res)
