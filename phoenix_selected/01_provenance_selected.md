# PX-01: Map ≠ territory; provenance is a first-class type

Selected **short excerpt** from `Phoenix_Egg/AI_SAFETY/PROVENANCE_AND_MAPS.md` (Phoenix):

> OBSERVED != GENERATED != INFERRED != SIMULATED

Further source instruction (paraphrased): attach source, confidence, intervention status, version and known failure modes to explanations.

### Apply to Pleasant Crescent
Every record has an explicit epistemic class: `observed`, `reported`, `inferred`, `generated`, `simulated`. A verifiable fact can be supported by multiple claims; do not promote an AI-generated summary into an observation. Distinguish *source reliability* from a verified event's *currentness*.

- Example: a volunteer submits a photograph of a trail (`reported`); EXIF GPS suggests a coordinate (`inferred` from metadata, not independently checked); the contributor confirms it (`user_confirmed`); an editor verifies the trail record (`verified`). The public summary names its uncertainty and sources.
- Example: an LLM suggests a park that does not exist in the approved records. It remains `generated`, not automatically a listing.
- Example: a map recommendation influences visits. Record its own intervention footprint if feasible, rather than treating subsequent click patterns as unbiased observation.

**Research candidate, not a claim:** explicit provenance may reduce overconfident answers, stale-cache misuse or recursive AI-summary contamination; compare with standard verification+retrieval and confidence-weighted baselines.

Full source: https://github.com/alexsabine/Phoenix-1-/blob/main/Phoenix_Egg/AI_SAFETY/PROVENANCE_AND_MAPS.md
