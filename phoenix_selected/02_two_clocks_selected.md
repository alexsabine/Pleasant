# PX-02: Two clocks and historical event counting

Selected core definitions from `Phoenix_Egg/FOUNDATIONS/TWO_CLOCKS.md`:

> Accumulated C, signed s and count N are different: backtracking increases C but may delay N. None specifies ds/dt.

> Changing actual drive, friction or forcing can change the history and is a physical intervention, not merely a relabelling.

### Apply to civic records
Use *several typed timestamps*, not a metaphysical universal clock:
- source's `observed_at` and `valid_from`;
- our `submitted_at`, `approved_at`, `last_verified_at`;
- `last_material_change_at` (hours, cost, accessibility, route restrictions);
- `last_shown_to_user_at` only if consented and really necessary;
- `event_count` for completed approved revisions.

Directory example: three successive reviews confirm the same opening hours. Verification time updates; material-change count stays fixed. A year passes with no feedback: age rises and uncertainty may grow even though observed event count is zero. No new verification was observed.

**No mapping-specific first-passage event is determined by CRR**. Define operational triggers such as `new verified cost`, `closed`, `date changed` and `source mismatch` directly, then independently study Fisher-distance triggers where defensible.

Full source: https://github.com/alexsabine/Phoenix-1-/blob/main/Phoenix_Egg/FOUNDATIONS/TWO_CLOCKS.md
