"""Steward trust checks: is the steward model consistent with the Bayes-optimal map decisions?

Checks
  S1  a new steward starts at the group's record (pooled prior), so their first entry can be shown at once
  S2  the decision is still the same Bayes act: show iff r * S(t) > 0.75 under utilities +1 / -3 / 0
  S3  trust changes how long a listing is recommended before re-check, never whether someone may contribute
  S4  fair blame: the share counted against the steward falls steadily with the listing's age, above half when
      fresh and below half when old;
      dated evidence of a later change carries no blame at all
  S5  rule 10 baseline: per-steward trust (pooled prior) is compared with the native baseline, everyone equal,
      on held-out re-check outcomes; Brier score is the metric. Pure per-steward counts (flat prior) are shown too
  S6  recency: an outcome's weight halves every 12 months
  S7  the cautious lower bound used for invitations still matches research/11 (20/0 -> 0.87, 20/2 -> 0.75)
Writes research/13_steward_trust.md.
Run: python3 backend/examples/steward_trust.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from pc_core.bayes import choose_binary_action  # noqa: E402
from pc_core.freshness import GammaRate  # noqa: E402
from pc_core.steward import (PooledPrior, Record, beta_lower, blame_share, prob_current, record_outcome,  # noqa: E402
                             recency_weight, reliability, shelf_life)

PLACES, PROGRAMMES = GammaRate(2, 1080), GammaRate(2, 360)  # the priors in tune_compass
results: list[tuple[str, bool, str]] = []


def record(key, ok, detail):
    results.append((key, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} {key}: {detail}")


# S1 ------------------------------------------------------------------------------------------
founders = [Record(18, 1), Record(25, 0), Record(12, 1), Record(30, 2)]
prior = PooledPrior.from_records(founders)
r_new = reliability(Record(), prior)
r_flat = (1 + 0) / (1 + 1)  # Beta(1, 1): a coin flip
record("S1", abs(r_new - prior.p) < 1e-12 and r_new > 0.75 and r_flat <= 0.75,
       f"pooled group reliability {prior.p:.3f}; a new steward starts there ({r_new:.3f}), so a first entry shows at once. "
       f"A flat prior would start at {r_flat:.2f} and block it")

# S2 ------------------------------------------------------------------------------------------
agree = 0
grid = [(r / 100, t) for r in range(50, 100) for t in range(0, 1500, 25)]
for r, t in grid:
    p = prob_current(r, PROGRAMMES, t)
    agree += (choose_binary_action(p)[0] == "show") == (p > 0.75)
record("S2", agree == len(grid), f"{agree}/{len(grid)} grid points: show iff r * S(t) > 0.75 is exactly the Bayes act")

# S3 ------------------------------------------------------------------------------------------
rows, mono = [], True
prev = -1.0
for r in (0.80, 0.90, 0.95, 0.99, 1.00):
    sp, sl = shelf_life(r, PROGRAMMES), shelf_life(r, PLACES)
    mono &= sp > prev
    prev = sp
    rows.append((r, sp, sl))
record("S3", mono and shelf_life(0.75, PROGRAMMES) == 0.0,
       "shelf life grows with reliability: " + ", ".join(f"r={r:.2f}: programmes {sp:.0f} d, places {sl:.0f} d" for r, sp, sl in rows))

# S4 ------------------------------------------------------------------------------------------
r = 0.9
fresh, old = blame_share(r, PROGRAMMES, 7), blame_share(r, PROGRAMMES, 400)
rec_dated, change_dated = record_outcome(Record(), "changed_since", r, PROGRAMMES, 400, evidence_dated=True)
shares = [blame_share(r, PROGRAMMES, t) for t in range(0, 801, 7)]
falling = all(a > b for a, b in zip(shares, shares[1:]))
record("S4", falling and fresh > 0.5 > old and rec_dated.wrong == 0 and change_dated == 1.0,
       f"found different after 7 days: {fresh:.0%} counted as an entry error; after 400 days: {old:.0%}. "
       "With dated evidence of a later change: no blame")

# S5 ------------------------------------------------------------------------------------------
TRUE = [0.97, 0.95, 0.93, 0.90, 0.88, 0.85, 0.80, 0.70]


def brier(ps, ys):
    return sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ys)


def trial(n, rng):
    train = {i: [int(rng.random() < q) for _ in range(n)] for i, q in enumerate(TRUE)}
    test = {i: [int(rng.random() < q) for _ in range(40)] for i, q in enumerate(TRUE)}
    recs = {i: Record(sum(v), len(v) - sum(v)) for i, v in train.items()}
    pooled = PooledPrior.from_records(list(recs.values()))
    ys, base, hier, flat = [], [], [], []
    for i, outs in test.items():
        for y in outs:
            ys.append(y)
            base.append(pooled.p)
            hier.append(reliability(recs[i], pooled))
            flat.append((1 + recs[i].right) / (2 + recs[i].right + recs[i].wrong))
    return brier(base, ys), brier(hier, ys), brier(flat, ys)


rng = random.Random(20261016)
s5rows, s5ok = [], True
for n in (5, 20, 60):
    sums = [0.0, 0.0, 0.0]
    for _ in range(300):
        for k, v in enumerate(trial(n, rng)):
            sums[k] += v / 300
    b, h, f = sums
    s5rows.append((n, b, h, f))
    s5ok &= h <= b + 0.002 and h <= f + 1e-9
s5ok &= s5rows[-1][2] < s5rows[-1][1] - 0.002
record("S5", s5ok, "mean Brier on held-out outcomes (lower is better): " +
       "; ".join(f"{n} entries each: everyone equal {b:.4f}, per-steward pooled {h:.4f}, per-steward flat {f:.4f}" for n, b, h, f in s5rows))

# S6 ------------------------------------------------------------------------------------------
w = [recency_weight(d) for d in (0, 365, 730)]
record("S6", abs(w[1] - 0.5) < 1e-12 and abs(w[2] - 0.25) < 1e-12, "weights now, 1 year, 2 years: " + ", ".join(f"{x:.2f}" for x in w))

# S7 ------------------------------------------------------------------------------------------
l20, l22 = beta_lower(21, 1), beta_lower(21, 3)
record("S7", round(l20, 2) == 0.87 and round(l22, 2) == 0.75, f"lower 5% bound: 20 right / 0 wrong {l20:.3f}; 20 / 2 {l22:.3f}")

passed = sum(ok for _, ok, _ in results)
print(f"{passed}/{len(results)} checks passed")

out = ROOT / "research" / "13_steward_trust.md"
lines = ["# Steward trust: consistent with the Bayes-optimal map", "",
         "Generated by `backend/examples/steward_trust.py`. Module: `backend/pc_core/steward.py`.", "",
         "## The model in one paragraph", "",
         "Each steward has a reliability r: the probability that an entry is right *when it is made*. It is a Beta "
         "posterior over their checked entries, weighted so an outcome counts half after a year, with a pooled prior "
         "(the group's own record, worth 10 entries), so a new steward starts at the group's level. The map's existing "
         "freshness model gives S(t), the chance a correct entry is still current after t days. A listing is "
         "recommended while r x S(t) > 0.75, the same Bayes act as before under utilities +1 / -3 / 0. Trust therefore "
         "changes how soon a listing is re-checked, never who may contribute. When a re-check finds a listing different, "
         "only the share explained by \"wrong when entered\" counts against the steward; the rest updates the "
         "category's change rate.", "",
         "## Two uses, two numbers, on purpose", "",
         "- Map decisions use the posterior **mean**, because with linear utilities the Bayes act depends only on "
         "the expected probability.",
         "- Invitations to a new role use the cautious **lower 5% bound**. That is a governance choice, and it never acts "
         "on its own: stewards invite, the member accepts.", "",
         "## Checks", "", "| Check | Result | Detail |", "|---|---|---|"]
lines += [f"| {k} | {'PASS' if ok else 'FAIL'} | {d} |" for k, ok, d in results]
lines += ["", f"{passed}/{len(results)} passed.", "",
          "## Shelf life before a re-check is due", "", "| Reliability r | Programmes (days) | Places (days) |", "|---|---|---|"]
lines += [f"| {r:.2f} | {sp:.0f} | {sl:.0f} |" for r, sp, sl in rows]
lines += ["", "## Baseline and metric (rule 10)", "",
          "Native baseline: every steward treated equally, at the group's pooled rate. Metric: Brier score of the "
          "predicted chance an entry is right, against later re-check outcomes. Per-steward trust is switched on only "
          "if it beats the baseline on real held-out months. In simulation it matches the baseline when records are "
          "short and beats it as they grow; a flat prior without pooling is worse when records are short.", "",
          "| Entries per steward | Everyone equal | Per-steward, pooled prior | Per-steward, flat prior |", "|---|---|---|---|"]
lines += [f"| {n} | {b:.4f} | {h:.4f} | {f:.4f} |" for n, b, h, f in s5rows]
lines += ["", "## What must be recorded for this to work", "",
          "For each steward entry: the steward, what they told Lumen, Lumen's draft, what they confirmed, the source "
          "and whether they saw it themselves (observed) or were told (reported), and the time. For each later "
          "re-check: who checked, the outcome (still right, changed since, wrong when entered, can't tell) and any "
          "dated evidence. Comparing what the steward said with Lumen's draft also measures Lumen's own accuracy, "
          "separately, so a steward is never blamed for Lumen's misreading.", "",
          "Synthetic simulation only; no real stewards or listings are scored here."]
out.write_text("\n".join(lines) + "\n")
print(f"wrote {out.relative_to(ROOT)}")
sys.exit(0 if passed == len(results) else 1)
