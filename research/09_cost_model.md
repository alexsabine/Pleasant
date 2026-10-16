# One-year running cost (generated)

`backend/examples/cost_model.py`, 2026-10-16. 100 onboarded members, Claude Opus 5.5 at $4.0/$20.0 per million tokens (batch jobs at 50%). Ceiling $1500/year. Estimates from stated assumptions.

## Fixed costs per year

| Item | US$ |
|---|---|
| Server for the website, database and Compass (4 GB virtual server, $24/month) | 288 |
| Off-site backups and photo storage (object storage, about $6/month) | 72 |
| Domain name, e.g. crescentcompass.ca | 20 |
| Email for sign-up and password resets (pay-per-use service) | 5 |
| GitHub Pro for the code owner: private code, public preview site ($4/month) | 48 |
| Anthropic API account: pay as you go, no subscription | 0 |
| Security certificate (Let's Encrypt), uptime and error alerts (free tiers) | 0 |
| Map: our own tiles from public data, no map subscription | 0 |
| Trust system: runs as code on our server, no AI tokens | 0 |
| **Total** | **433** |

## Totals

| Use | Questions/member/week | AI as built | AI optimised | Total optimised | Daily cap on worded answers |
|---|---|---|---|---|---|
| Light | 3 | $546 | $226 | $659 | 233 |
| Typical | 8 | $1,415 | $574 | $1,007 | 225 |
| Heavy | 20 | $3,508 | $1,422 | $1,855 | 204 |

## Typical use, optimised, by job

| Job | Count/year | US$ each | US$/year |
|---|---|---|---|
| Compass answers for members | 41,600 questions | 0.0121 | 503.78 |
| Corrections and suggestions drafted | 1,200 drafts | 0.0160 | 19.20 |
| Photo checks before a steward sees them | 2,400 photos | 0.0068 | 16.32 |
| Monthly check of official web pages | 630 changed pages | 0.0140 | 8.82 |
| Steward digest: one line per item | 4,230 items | 0.0049 | 20.73 |
| Steward asks: what needs approving? | 12 months | 0.0700 | 0.84 |
| Steward follow-up questions | 120 questions | 0.0280 | 3.36 |
| Quadruplicate events sorted | 12 months | 0.0330 | 0.40 |
| Monthly trust and audit summary | 12 months | 0.0500 | 0.60 |

## Suggested hybrid hosting

Public pages on GitHub Pages (covered by GitHub Pro), members' features on a 2 GB server: fixed $289/year.

| Use | Total optimised, hybrid |
|---|---|
| Light | $515 |
| Typical | $863 |
| Heavy | $1,711 |
