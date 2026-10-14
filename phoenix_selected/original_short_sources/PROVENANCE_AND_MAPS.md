# Provenance, maps and territories

Candidate design principle:

```text
OBSERVED != GENERATED != INFERRED != SIMULATED
```

A system may use all four, but should retain their provenance when safety depends on what actually happened.

Phoenix question:
> Does explicit provenance reduce recursive self-training drift, reward hacking, overconfidence, unsafe memory contamination or evaluator gaming beyond confidence-weighted and standard data-curation baselines?

This is a testable engineering hypothesis, not proof that "only the past is real."

An Empty-Centre implementation should also mark every explanation as a map with:
- source;
- confidence;
- causal intervention status;
- version;
- known failure modes.
