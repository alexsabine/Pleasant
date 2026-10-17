"""Build web/static/data/fog_routes.json: the real path between every pair of published places, for fog mode.

Run after the basemap or the listings change (monthly, with the other checks):
    python3 manage.py build_fog_routes
"""
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from atlas import fog_routes as fr
from atlas.models import Resource

TILES = "delnorte_basemap.pmtiles"


class Command(BaseCommand):
    help = "Build real walking and road routes between published places for fog mode (OSM-derived, ODbL)."

    def handle(self, *args, **opts):
        from pmtiles.reader import MmapSource, Reader, all_tiles
        src = Path(settings.TILES_DIR) / TILES
        net = fr.Network()
        with open(src, "rb") as fh:
            reader = Reader(MmapSource(fh))
            for (z, x, y), data in all_tiles(reader.get_bytes):
                if z == fr.Z:
                    net.add_tile(z, x, y, data)
        healed = net.heal()
        comp, size = net.components()
        # each mode snaps onto its own main connected network, so a car park reached only by steps is not a dead end
        mode_comp = {}
        for mode, kinds in (("walk", fr.WALK), ("drive", fr.DRIVE)):
            c, sz = net.components(kinds)
            mode_comp[mode] = (c, max(sz, key=sz.get))
        self.stdout.write(f"network: {len(net.ll)} nodes, {sum(len(v) for v in net.adj.values()) // 2} links, healed {healed} seams, "
                          f"main network {max(size.values())} nodes")

        places = [r for r in Resource.objects.filter(live=True, visibility="public", is_sensitive=False) if r.location is not None]
        cell = 40.0
        grid = net._grid(cell)
        # snap each place twice: onto the nearest walkable segment and onto the nearest drivable road
        snap = {"walk": {}, "drive": {}}
        for r in places:
            x, y = fr.to_xy(r.location.x, r.location.y)
            for mode, kinds in (("walk", fr.WALK), ("drive", fr.DRIVE)):
                hit = None
                for radius in (60, 250, 1500):
                    c, main = mode_comp[mode]
                    hit = net.nearest_segment(x, y, grid, cell, radius, ok=lambda a, c=c, main=main: c.get(a) == main, kinds=kinds)
                    if hit:
                        break
                if hit:
                    m = net.split_indexed(hit[1], hit[2], hit[3], grid, cell)
                    for c, _ in mode_comp.values():
                        c.setdefault(m, c.get(hit[1]))
                    snap[mode][r.pk] = m
                else:
                    snap[mode][r.pk] = None
        routes, stats = {}, {"on_network": 0, "straight": 0, "walk": 0, "drive": 0, "ratio": []}
        trees = {"walk": {}, "drive": {}}
        for mode, costs, limit in (("walk", fr.WALK, 12000), ("drive", fr.DRIVE, None)):
            targets = [n for n in snap[mode].values() if n is not None]
            for r in places:
                if snap[mode][r.pk] is not None:
                    trees[mode][r.pk] = net.dijkstra(snap[mode][r.pk], costs, targets, limit=limit)
        for i, a in enumerate(places):
            for b in places[i + 1:]:
                lo, hi = (a, b) if a.pk < b.pk else (b, a)
                A, B = (lo.location.x, lo.location.y), (hi.location.x, hi.location.y)
                straight = fr.length_m([A, B])
                coords, mode = None, "walk" if straight <= fr.WALK_MAX_STRAIGHT_M else "drive"
                for m in ([mode, "drive"] if mode == "walk" else ["drive", "walk"]):
                    if snap[m][lo.pk] is not None and snap[m][hi.pk] is not None:
                        dist, prev = trees[m][lo.pk]
                        nodes = net.path(prev, snap[m][lo.pk], snap[m][hi.pk])
                        if nodes:
                            cand = [A] + [net.ll[n] for n in nodes] + [B]
                            if m == "walk" and fr.length_m(cand) > 3 * max(straight, 300) and mode == "walk":
                                continue                     # no sensible footpath: go by road instead
                            coords, mode = cand, m
                            break
                if coords is None:
                    coords, mode = [A, B], "straight"
                    stats["straight"] += 1
                else:
                    stats["on_network"] += 1; stats[mode] += 1
                    stats["ratio"].append(fr.length_m(coords) / max(straight, 1))
                coords = fr.simplify(coords, 6 if mode == "walk" else 20)
                routes[f"{lo.pk}-{hi.pk}"] = [mode[0], round(fr.length_m(coords)), fr.encode(coords)]

        out = Path(settings.BASE_DIR) / "static" / "data" / "fog_routes.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        meta = {"what": "Real walking and road paths between published places, for the fog mode illustration. Not directions.",
                "source": f"OpenStreetMap via the Protomaps basemap build (data/tiles/{TILES}, zoom {fr.Z})",
                "licence": "ODbL 1.0", "attribution": "© OpenStreetMap contributors", "crs": "EPSG:4326",
                "built_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "modes": {"w": "on foot", "d": "by road", "s": "no mapped path: straight line"},
                "places": len(places), "routes": len(routes)}
        out.write_text(json.dumps({"meta": meta, "routes": routes}, separators=(",", ":")))
        raw = out.read_bytes()

        log_path = Path(settings.INGEST_LOG)
        log = json.loads(log_path.read_text()) if log_path.exists() else []
        log = [e for e in log if e.get("id") != "FOG_ROUTES_OSM"]
        log.append({"fetched_at": meta["built_at"], "id": "FOG_ROUTES_OSM", "source_url": "https://docs.protomaps.com/basemaps/downloads",
                    "product": "Fog mode paths derived from the self-hosted OSM basemap (roads layer, zoom 14)",
                    "licence": "ODbL 1.0 (derived database)", "attribution": meta["attribution"],
                    "bbox": {"min_lon": -124.45, "min_lat": 41.35, "max_lon": -123.45, "max_lat": 42.05}, "zoom": [fr.Z, fr.Z],
                    "tiles": None, "output": "web/static/data/fog_routes.json", "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(), "decision": "approved_with_attribution"})
        log_path.write_text(json.dumps(log, indent=2) + "\n")
        r = sorted(stats["ratio"])
        med = r[len(r) // 2] if r else 0
        self.stdout.write(f"{len(routes)} routes for {len(places)} places: {stats['walk']} on foot, {stats['drive']} by road, "
                          f"{stats['straight']} straight lines; median path / crow-flies {med:.2f}; {len(raw) / 1024:.0f} KB -> {out}")
