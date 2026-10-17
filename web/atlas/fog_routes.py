"""Real paths for fog mode: a small walking and road network built from our own OpenStreetMap basemap tiles.

Source: data/tiles/delnorte_basemap.pmtiles (Protomaps OSM build, zoom 14; rights logged as approved with attribution).
The routes are an OSM-derived database: published under ODbL 1.0 with "(c) OpenStreetMap contributors". They are an
illustration for the fog game, never directions: closures, tides and private roads are not known here.

Steps: decode the roads layer -> nodes on the tile grid (exact across tiles) -> heal tile seams and T-junctions by
snapping loose ends onto the nearest segment within a few metres -> snap each place onto the network -> Dijkstra per
place with a walking or a driving cost -> simplify (Douglas-Peucker) -> encode (Google polyline, 1e-5 degrees).
"""
from __future__ import annotations

import gzip
import heapq
import math
from collections import defaultdict

Z, EXTENT = 14, 4096
N = (1 << Z) * EXTENT
LAT0 = 41.75
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110540

# cost per metre; None = not allowed. Walking prefers paths and quiet streets, avoids the trunk roads (US-101, 199)
# and treats logging tracks as a last resort; driving uses roads only.
WALK = {"path": 1.0, "footway": 1.0, "pedestrian": 1.0, "steps": 1.1, "sidewalk": 1.0, "crossing": 1.0, "cycleway": 1.0,
        "pier": 1.0, "residential": 1.0, "living_street": 1.0, "unclassified": 1.15, "service": 1.3, "tertiary": 1.4,
        "tertiary_link": 1.4, "secondary": 1.6, "secondary_link": 1.6, "primary": 2.2, "trunk": 3.5, "trunk_link": 3.5,
        "track": 1.8}
DRIVE = {"motorway": 0.55, "motorway_link": 0.7, "trunk": 0.6, "trunk_link": 0.75, "primary": 0.7, "secondary": 0.8,
         "secondary_link": 0.85, "tertiary": 0.9, "tertiary_link": 0.9, "unclassified": 1.0, "residential": 1.1,
         "living_street": 1.4, "service": 1.5, "track": 3.0}
WALK_MAX_STRAIGHT_M = 2500          # longer hops go by road


def to_lonlat(gx: float, gy: float) -> tuple[float, float]:
    lon = gx / N * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * gy / N))))
    return lon, lat


def to_xy(lon: float, lat: float) -> tuple[float, float]:
    return (lon + 124.2) * KX, (lat - LAT0) * KY


class Network:
    def __init__(self):
        self.key = {}            # tile-grid key -> node id
        self.ll = []             # node id -> (lon, lat)
        self.xy = []             # node id -> local metres
        self.adj = defaultdict(dict)   # node -> {node: (metres, kind)}

    def node(self, key, lonlat=None):
        if key in self.key:
            return self.key[key]
        i = len(self.ll)
        self.key[key] = i
        lon, lat = lonlat or to_lonlat(*key)
        self.ll.append((lon, lat)); self.xy.append(to_xy(lon, lat))
        return i

    def link(self, a, b, kind):
        if a == b:
            return
        (ax, ay), (bx, by) = self.xy[a], self.xy[b]
        d = math.hypot(bx - ax, by - ay)
        if b not in self.adj[a] or self.adj[a][b][0] > d:
            self.adj[a][b] = (d, kind); self.adj[b][a] = (d, kind)

    def unlink(self, a, b):
        self.adj[a].pop(b, None); self.adj[b].pop(a, None)

    # -- building from tiles -----------------------------------------------------------------------------------
    def add_tile(self, z, x, y, data):
        import mapbox_vector_tile
        t = mapbox_vector_tile.decode(gzip.decompress(data))
        layer = t.get("roads")
        if not layer:
            return
        ext = layer.get("extent", EXTENT)
        for f in layer["features"]:
            kind = f["properties"].get("kind_detail") or f["properties"].get("kind")
            if kind not in WALK and kind not in DRIVE:
                continue
            g = f["geometry"]
            lines = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"] if g["type"] == "MultiLineString" else []
            for line in lines:
                prev = None
                for px, py in line:            # decoder gives y up; the tile grid counts y down
                    k = (x * EXTENT + round(px * EXTENT / ext), y * EXTENT + round((ext - py) * EXTENT / ext))
                    cur = self.node(k)
                    if prev is not None:
                        self.link(prev, cur, kind)
                    prev = cur

    # -- healing seams and T-junctions ------------------------------------------------------------------------
    def _grid(self, cell):
        g = defaultdict(list)
        for a, nb in self.adj.items():
            for b in nb:
                if a < b:
                    (ax, ay), (bx, by) = self.xy[a], self.xy[b]
                    for gx in range(int(min(ax, bx) // cell), int(max(ax, bx) // cell) + 1):
                        for gy in range(int(min(ay, by) // cell), int(max(ay, by) // cell) + 1):
                            g[(gx, gy)].append((a, b))
        return g

    def nearest_segment(self, x, y, grid, cell, radius, skip=None, ok=None, kinds=None):
        best = None
        for gx in range(int((x - radius) // cell), int((x + radius) // cell) + 1):
            for gy in range(int((y - radius) // cell), int((y + radius) // cell) + 1):
                for a, b in grid.get((gx, gy), ()):
                    if b not in self.adj[a] or (skip is not None and (a == skip or b == skip)) or (ok and not ok(a)):
                        continue
                    if kinds is not None and self.adj[a][b][1] not in kinds:
                        continue
                    (ax, ay), (bx, by) = self.xy[a], self.xy[b]
                    vx, vy = bx - ax, by - ay
                    h = max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / max(vx * vx + vy * vy, 1e-9)))
                    d = math.hypot(x - ax - vx * h, y - ay - vy * h)
                    if d <= radius and (best is None or d < best[0]):
                        best = (d, a, b, h)
        return best

    def split(self, a, b, h):
        """Insert a node at fraction h along a-b (or reuse an end within 1.5 m) and return it."""
        (ax, ay), (bx, by) = self.xy[a], self.xy[b]
        seg = math.hypot(bx - ax, by - ay)
        if h * seg < 1.5:
            return a
        if (1 - h) * seg < 1.5:
            return b
        kind = self.adj[a][b][1]
        (alon, alat), (blon, blat) = self.ll[a], self.ll[b]
        m = self.node(("split", a, b, round(h, 6)), (alon + (blon - alon) * h, alat + (blat - alat) * h))
        self.unlink(a, b); self.link(a, m, kind); self.link(m, b, kind)
        return m

    def index(self, grid, cell, a, b):
        (sx, sy), (tx, ty) = self.xy[a], self.xy[b]
        for gx in range(int(min(sx, tx) // cell), int(max(sx, tx) // cell) + 1):
            for gy in range(int(min(sy, ty) // cell), int(max(sy, ty) // cell) + 1):
                grid[(gx, gy)].append((a, b))

    def split_indexed(self, a, b, h, grid, cell):
        m = self.split(a, b, h)
        if m not in (a, b):
            self.index(grid, cell, a, m); self.index(grid, cell, m, b)
        return m

    def heal(self, radius=10.0):
        cell = 40.0
        grid = self._grid(cell)
        healed = 0
        for n in [i for i in list(self.adj) if len(self.adj[i]) == 1]:
            if len(self.adj[n]) != 1:
                continue
            (only,) = self.adj[n]
            x, y = self.xy[n]
            hit = self.nearest_segment(x, y, grid, cell, radius, skip=n, ok=lambda a: True)
            if hit and only not in (hit[1], hit[2]):
                d, a, b, h = hit
                m = self.split_indexed(a, b, h, grid, cell)
                if m != n:
                    self.link(n, m, self.adj[n][only][1])
                    self.index(grid, cell, n, m)
                    healed += 1
        return healed

    def components(self, kinds=None):
        """Connected pieces of the network, optionally using only links of the given kinds (one mode's network)."""
        comp, size = {}, defaultdict(int)
        for s in self.adj:
            if s in comp:
                continue
            stack, comp[s] = [s], s
            while stack:
                u = stack.pop(); size[s] += 1
                for v, (_, k) in self.adj[u].items():
                    if v not in comp and (kinds is None or k in kinds):
                        comp[v] = s; stack.append(v)
        return comp, size

    # -- routing ------------------------------------------------------------------------------------------------
    def dijkstra(self, src, costs, targets, limit=None):
        dist, prev, left = {src: 0.0}, {}, set(targets)
        pq = [(0.0, src)]
        while pq and left:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, math.inf):
                continue
            left.discard(u)
            if limit and d > limit:
                break
            for v, (m, kind) in self.adj[u].items():
                w = costs.get(kind)
                if w is None:
                    continue
                nd = d + m * w
                if nd < dist.get(v, math.inf):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        return dist, prev

    def path(self, prev, src, dst):
        if dst != src and dst not in prev:
            return None
        out = [dst]
        while out[-1] != src:
            out.append(prev[out[-1]])
        return out[::-1]


def length_m(coords):
    xy = [to_xy(*c) for c in coords]
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(xy, xy[1:]))


def simplify(coords, tol_m):
    """Douglas-Peucker in local metres."""
    if len(coords) < 3:
        return list(coords)
    xy = [to_xy(*c) for c in coords]
    keep = [False] * len(coords); keep[0] = keep[-1] = True
    stack = [(0, len(coords) - 1)]
    while stack:
        i, j = stack.pop()
        (ax, ay), (bx, by) = xy[i], xy[j]
        vx, vy = bx - ax, by - ay
        L = max(math.hypot(vx, vy), 1e-9)
        best, at = 0.0, None
        for k in range(i + 1, j):
            d = abs((xy[k][0] - ax) * vy - (xy[k][1] - ay) * vx) / L
            if d > best:
                best, at = d, k
        if at is not None and best > tol_m:
            keep[at] = True; stack += [(i, at), (at, j)]
    return [c for c, k in zip(coords, keep) if k]


def encode(coords):
    """Google encoded polyline, precision 1e-5 (lat, lon order)."""
    out, plat, plon = [], 0, 0
    for lon, lat in coords:
        ilat, ilon = round(lat * 1e5), round(lon * 1e5)
        for v in (ilat - plat, ilon - plon):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        plat, plon = ilat, ilon
    return "".join(out)


def decode(s):
    coords, i, lat, lon = [], 0, 0, 0
    while i < len(s):
        vals = []
        for _ in range(2):
            shift = res = 0
            while True:
                b = ord(s[i]) - 63; i += 1
                res |= (b & 0x1f) << shift; shift += 5
                if b < 0x20:
                    break
            vals.append(~(res >> 1) if res & 1 else res >> 1)
        lat += vals[0]; lon += vals[1]
        coords.append((lon / 1e5, lat / 1e5))
    return coords
