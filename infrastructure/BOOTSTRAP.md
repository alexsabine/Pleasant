# Claude Code bootstrap path

1. Create organization-controlled GitHub repository; add this kit (not enormous map files) to it.
2. Check `CLAUDE.md`; agree design and current Wagtail/Django/Python compatibility. Pin tested versions and record lockfiles rather than assuming this reference's environment is production-ready.
3. In development with Docker installed, copy `infrastructure/.env.example` -> `infrastructure/.env` and set a strong random local password. Run `cd infrastructure && docker compose --env-file .env up -d`.
4. Claude Code creates Django/Wagtail project scaffold and Django migrations for `resources`, `events`, `review`, `provenance` etc. Do NOT simultaneously run `schema_reference.sql` and then create duplicate models.
5. Build a simple MapLibre client (with npm/vite or Wagtail static bundling) displaying locally served permitted vector/raster tiles and your own published directory GeoJSON.
6. After public-layer licensing approval, stage per-layer ingest with approval receipts. Never use Google/Esri cached tile scraping as a shortcut.
7. First successful demo: 5 **fictional** places, admin UI, submit/review/publish, refresh map, public list alternative, verification metadata.
8. Content team verifies 40 real entries independently. Later add agent under feature flag, request-limited and read-only.

## Security/reliability QA
- Separate staging and production; GitHub Actions tests and basic migrations; approval before production deployment.
- Treat POST/PUT/PATCH/DELETE as authenticated server-side actions, with CSRF protection where applicable and object-level authorization.
- Give app minimum database permissions. Public API never returns private-source fields or precise restricted biological data.
- Input file validation, MIME sniffing, EXIF stripping from public derivatives, virus scanning where appropriate, max upload sizes.
- Restore tested backups; private-key rotation; rate-limits and log retention; admin MFA where possible.
