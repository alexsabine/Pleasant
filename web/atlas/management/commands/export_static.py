"""Export the public site as static files for GitHub Pages (link-only review with Kim).

Renders every public page through the real views, rewrites absolute links to the Pages base
path, freezes the JSON/GeoJSON API, copies static assets and our own map tiles (basemap, and
terrain cut to z<=12 so the file stays small), and writes `.nojekyll`.
What a static host cannot do (accounts, suggestions, audit records) is replaced by notes in
`static/pc/static.js`; Compass runs the same deterministic policy in the browser.

    python manage.py export_static --out ../site --base /Pleasant/
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test import Client

from atlas.models import GROUPS, Resource
from compass import policy, tools

PREFIXES = ("static", "api", "tiles", "logo.svg", "explore", "resource", "about", "this-week", "local-help", "contribute", "review", "accounts", "compass")
URL_RE = re.compile(r'"(/(?:' + "|".join(re.escape(p) for p in PREFIXES) + r')(?:[/?.][^"]*)?)"')
REL_QS_RE = re.compile(r'href="\?([^"]*)"')
CSS_URL_RE = re.compile(r"url\((['\"]?)/static/")


def static_path(url: str) -> str:
    """Map a dynamic URL (with query string) to the file the export writes for it."""
    path, _, qs = url.partition("?")
    params = {k: v[0] for k, v in parse_qs(qs.replace("&amp;", "&")).items()}
    if path == "/explore/":
        if params.get("view") == "map":
            return "/explore/map/"
        return f"/explore/group/{params['group']}/" if params.get("group") else "/explore/"
    if path == "/api/h3_venues.geojson":
        return "/api/h3_venues.geojson"           # map.js swaps in _res{N}.geojson
    return path                                   # every other query string is dropped


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--out", default=str(Path(settings.REPO_ROOT) / "site"))
        parser.add_argument("--base", default=settings.PC_STATIC_BASE, help="URL path prefix on the host, e.g. /Pleasant/")

    def handle(self, *args, **opts):
        out = Path(opts["out"]).resolve()
        base = "/" + opts["base"].strip("/") + "/" if opts["base"].strip("/") else "/"
        prefix = base.rstrip("/")
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        settings.ALLOWED_HOSTS.append("testserver")
        settings.PC_STATIC_BASE = base
        c = Client(HTTP_X_PC_STATIC="1")

        def rewrite(html: str) -> str:
            html = REL_QS_RE.sub(lambda m: f'href="{prefix}{static_path("/explore/?" + m.group(1))}"', html)
            html = URL_RE.sub(lambda m: f'"{prefix}{static_path(m.group(1))}"', html)
            return html

        def put(url: str, target: str, content_type_hint: str = ""):
            r = c.get(url)
            if r.status_code != 200:
                raise SystemExit(f"{url} -> {r.status_code}")
            body = b"".join(r.streaming_content) if r.streaming else r.content
            dest = out / target.lstrip("/")
            if target.endswith("/"):
                dest = dest / "index.html"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.suffix == ".html":
                dest.write_text(rewrite(body.decode("utf8")), encoding="utf8")
            else:
                dest.write_bytes(body)
            return dest

        pages = ["/", "/explore/", "/explore/?view=map", "/this-week/", "/local-help/", "/about/", "/review/", "/contribute/", "/accounts/join/", "/accounts/sign-in/"]
        pages += [f"/explore/?group={k}" for k, _ in GROUPS]
        slugs = list(Resource.objects.filter(live=True, visibility="public", is_sensitive=False).values_list("slug", flat=True))
        pages += [f"/resource/{s}/" for s in slugs]
        for p in pages:
            put(p, static_path(p))
        # frozen API
        put("/api/resources.json", "/api/resources.json")
        put("/api/resources.geojson", "/api/resources.geojson")
        put("/api/events.json", "/api/events.json")
        put("/api/manifest.json", "/api/manifest.json")
        put("/api/h3.geojson?res=7&k=2", "/api/h3.geojson")
        for res in (9, 10, 11, 12):
            put(f"/api/h3_venues.geojson?res={res}", f"/api/h3_venues_res{res}.geojson")
        for name in ("county", "places", "aiannh"):
            put(f"/api/boundaries/{name}.geojson", f"/api/boundaries/{name}.geojson")
        put("/logo.svg?size=64&static=1", "/logo.svg")
        (out / "api" / "compass_rules.json").write_text(json.dumps({
            "keywords": tools.KEYWORDS, "stopwords": sorted(tools.STOPWORDS), "event_words": sorted(policy.EVENT_WORDS),
            "word_ages": policy.WORD_AGES, "utilities": settings.COMPASS_UTILITIES,
            "communities": [["smith_river", "smith river"], ["gasquet", "gasquet"], ["klamath", "klamath"], ["fort_dick", "fort dick"], ["hiouchi", "hiouchi"], ["crescent_city", "crescent city"]],
        }, indent=1))

        # static assets (CSS url(/static/...) rewritten to the base)
        src = Path(settings.BASE_DIR) / "static"
        shutil.copytree(src, out / "static", ignore=shutil.ignore_patterns("__pycache__", "*.py"))
        for css in (out / "static").rglob("*.css"):
            css.write_text(CSS_URL_RE.sub(lambda m: f"url({m.group(1)}{prefix}/static/", css.read_text(encoding="utf8")), encoding="utf8")

        # our own tiles: basemap as is, terrain cut to z<=12 (keeps the file ~17 MB, under GitHub's limits)
        tiles = Path(settings.TILES_DIR)
        (out / "tiles").mkdir()
        shutil.copy(tiles / "delnorte_basemap.pmtiles", out / "tiles" / "delnorte_basemap.pmtiles")
        self.subset_terrain(tiles / "delnorte_terrain.pmtiles", out / "tiles" / "delnorte_terrain.pmtiles", max_zoom=12)

        (out / ".nojekyll").write_text("")
        (out / "404.html").write_text(f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title>Not found · Pleasant Crescent</title>'
                                      f'<p style="font-family:system-ui;padding:2rem">That page is not part of the static preview. <a href="{base}">Back to the atlas</a>.</p>')
        n = sum(1 for _ in out.rglob("*") if _.is_file())
        size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) / 1e6
        self.stdout.write(f"exported {len(pages)} pages, {n} files, {size:.1f} MB to {out} (base {base})")

    @staticmethod
    def subset_terrain(src: Path, dst: Path, max_zoom: int):
        from pmtiles.reader import MmapSource, Reader, all_tiles
        from pmtiles.tile import zxy_to_tileid
        from pmtiles.writer import write
        with open(src, "rb") as fh:
            source = MmapSource(fh)
            reader = Reader(source)
            header, metadata = dict(reader.header()), reader.metadata()
            entries = sorted(((zxy_to_tileid(z, x, y), data) for (z, x, y), data in all_tiles(source) if z <= max_zoom), key=lambda t: t[0])
            header["max_zoom"] = max_zoom
            with write(str(dst)) as w:
                for tid, data in entries:
                    w.write_tile(tid, data)
                w.finalize(header, metadata)
