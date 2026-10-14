# Pleasant Crescent web platform (first iteration, private preview)

Django 6 + Wagtail 8 + GeoDjango, MapLibre GL + PMTiles served from this origin only, and the Crescent Compass agent (read-only, allow-listed tools, Claude phrasing behind a feature flag).

## Run locally

```bash
# system libraries for GeoDjago on SQLite (Debian/Ubuntu): gdal-bin libgdal-dev libsqlite3-mod-spatialite libgeos-dev libproj-dev
pip install -r web/requirements.txt
cd web
python manage.py migrate
python manage.py load_demo            # demo users, workflow, home page (and five FICTIONAL listings for tests)
python manage.py load_verified --replace-fictional   # 58 real listings from data/verified/*.json, placed from authoritative sources
python manage.py runserver
```

Then open http://localhost:8000/ (public site) and http://localhost:8000/admin/ (Wagtail; users `demo_admin` / `demo_editor`, password from `DEMO_PASSWORD`, default `change-me-locally-123`).

Map tiles are not in Git. Build them once (authorised downloads of public-domain and ODbL data, logged in `data/ingest_log.json`):

```bash
python backend/ingest/extract_protomaps.py --build 20261013 --maxzoom 14   # OSM basemap bbox extract, ~6 MB
python backend/ingest/fetch_terrain.py --minzoom 7 --maxzoom 13           # 3DEP terrain tiles, ~68 MB
python backend/ingest/fetch_tiger.py                                       # Census boundaries (committed, small)
python backend/ingest/geocode_local.py                                     # name index from our own tiles (offline geocoder)
python web/tools/palette.py                                                # solve the palette for contrast -> tokens.json
node web/tools/build_style.js                                              # regenerate the style from tokens.json
```

## Accounts and onboarding

`/accounts/join/` (adult confirmation, no child fields) → `/accounts/welcome/1..3/` (every step skippable) → `/accounts/my-atlas/`. Saved places, preferences (age bands, budget, step-free, community, dosage, consent for Compass, notifications off by default), contributor-rights request as a moderated submission. Public suggestions at `/contribute/`.

## Tests and checks

```bash
cd web && python manage.py test accounts compass atlas  # 19 end-to-end tests: onboarding, honesty, closure
PYTHONPATH=backend python -m unittest discover -s backend/tests
PYTHONPATH=backend python backend/examples/math_checks.py --report research/05_math_check_report.md   # 30 checks
```

## Settings that matter

| Env var | Default | Meaning |
|---|---|---|
| `PC_PRIVATE_MODE` | `1` | Shows the private-preview banner |
| `COMPASS_LLM_ENABLED` | `0` | Enables Claude phrasing and intent extraction (model `COMPASS_MODEL`, default `claude-opus-5-5`); needs `ANTHROPIC_API_KEY` |
| `COMPASS_DAILY_REQUEST_BUDGET` | `200` | Hard cap on Compass answers per day |
| `POSTGRES_HOST` etc. | unset | Switches from SpatiaLite to PostGIS |
| `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS` | dev values | Set in production |

Compass utilities (show-if-true +1, show-if-false −3, abstain 0, so recommend iff P(current) > 0.75) and per-category hazards are editable in the admin under Atlas → Category hazards; see `research/04_mathematics_register.md`.

## What is deliberately not here yet

A map point picker on our own tiles (admin uses WKT text for now), photo upload with EXIF handling, the public correction form (the model exists; the form is next), PostGIS in CI, and the 40 real listings.
