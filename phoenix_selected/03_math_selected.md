# PX-03/04: What the mathematical core safely licenses

Source: `Phoenix_Egg/CORE/MATHEMATICS.md` and `FOUNDATIONS/MATHEMATICAL_OBJECT.md`.

## Supported conditional constructs

**Fisher–Rao length.** On an independently specified distribution family `p(z|theta)`, with Fisher metric `g(theta)`, accumulated path length in fixed units:

`C = (1/sigma) * integral sqrt(theta_dot^T g(theta) theta_dot) dt`.

**Bernoulli** example `p in (0,1)`: metric `g(p)=1/[p(1-p)]`, and endpoint distance on the 1D Bernoulli family:

`d_FR(p,q) = 2*abs(asin(sqrt(p))-asin(sqrt(q)))`.

**Path surplus** `S = path_length - intrinsic_geodesic_distance >= 0` for suitable rectifiable paths; on a specified circle with a completed oriented intrinsic half-turn, the source derives `S=2B/sigma`. That is standard geometry, not proof of a novel cognitive or social mechanism. No circular carrier is justified merely because a listing undergoes updates.

**Past-only memory**, one chosen flat-coordinate model:

`m_{n+1}=q*m_n+(1-q)*phi_n`, `0 <= q < 1`.

This is an exponential moving average. It is not uniquely forced by CRR and is **lossy**, so use only for an optional derived working state, never as a replacement for original evidence or consent history. There is no universal optimal `q` or notion of "balanced" equal precision established by the geometry.

## Clean integration point
Use normal PostGIS records as source of truth. Construct a **declared** probability model of, e.g., whether a directory listing remains current; apply Bayesian updates. Optionally measure changes in this *belief distribution* with Fisher–Rao distance, with a threshold selected on training/validation data independently of evaluation. Compare against age-based verification schedules, JS divergence and ordinary confidence thresholds.

**Not licensed by Phoenix:** that Fisher distance alone decides optimal output length; that the system knows a universal social saturation point; a special natural circular half-turn in every dataset; that surplus provides information if path length and geodesic distance are already available; that an arithmetic mean is a lossless history map; that Bayesian optimality follows from CRR alone.

Sources:
- https://github.com/alexsabine/Phoenix-1-/blob/main/Phoenix_Egg/CORE/MATHEMATICS.md
- https://github.com/alexsabine/Phoenix-1-/blob/main/Phoenix_Egg/FOUNDATIONS/MATHEMATICAL_OBJECT.md
