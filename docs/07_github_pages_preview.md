# Sharing the draft with Kim as a GitHub Pages link

GitHub Pages serves static files only, so the Django/Wagtail site cannot run there. Instead the
repository carries a **static export** of the public site in `site/`, and a workflow publishes it.
The link is public but not indexed (every page carries `noindex`), so it works as a link-only preview.

## One-time setup (repository owner, about two minutes)

1. Open https://github.com/alexsabine/Pleasant/settings/pages.
2. Under **Build and deployment → Source**, choose **GitHub Actions** (not "Deploy from a branch").
3. Open https://github.com/alexsabine/Pleasant/actions, pick **Static preview on GitHub Pages**, and press
   **Run workflow** on the branch that holds the export (`claude/tender-dijkstra-a7w57t`, or `main` once merged).
   The workflow also runs on its own whenever `site/` changes on either branch.
4. When the run is green, the site is at **https://alexsabine.github.io/Pleasant/**.
   Send Kim that link, or the review page directly: https://alexsabine.github.io/Pleasant/review/

If the first run fails at "configure-pages" with a permissions error, step 2 was skipped: set the source to GitHub Actions and run it again.

## What works on the static preview

- Home, the nine groups, Explore (list and map), every listing page, This week, Local help, About, Suggest, the review page.
- The map, from our own tiles in `site/tiles/` (OpenStreetMap via Protomaps, ODbL, and USGS 3DEP terrain cut to zoom 12). GitHub Pages supports the byte-range requests PMTiles needs; nothing is fetched from a third party.
- Filters on Explore run in the browser over the rendered cards. Unknown access is still never shown as accessible.
- Crescent Compass runs the same deterministic policy in the browser over the frozen `api/resources.json` (hard constraints as filters, recommend only when P(current) > 0.75, nothing invented). It says on every answer that no audit record is written in the preview.

## What does not work there, and says so

- Joining, signing in, saving places, the suggestion form and Compass's "correct: …" drafts. Each shows a note instead of pretending.
- The review form cannot store replies: it compiles them into text to copy or email (set `PC_REVIEW_EMAIL` before exporting to add an "Open in email" button).
- The audit log, admin and freshness updates. Listings age in place until the export is regenerated.

## Updating the preview

```bash
cd web
python manage.py export_static --out ../site --base /Pleasant/
git add site && git commit -m "Refresh static preview" && git push
```

The workflow redeploys within a minute or two. If the repository is renamed, pass the new name as `--base /NewName/` (the path prefix is baked into the export).

## Why the tiles are committed

`site/tiles/*.pmtiles` is an exception to the `*.pmtiles` ignore rule so the preview needs no build step in CI. Both files are our own extracts of public-domain and ODbL data, attributed on every map and on the About page, and total about 23 MB.
