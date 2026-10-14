# PX-09: A useful engineering reduction — do not treat stale repeats as new evidence

Phoenix P14-EMPTY1 ran **600 synthetic linear-Gaussian worlds** with repeated stale measurements. The proposed repeat-detection+missing-observation treatment outperformed a faulty update rule. The source itself says the operational mechanism **reduces to the textbook missing-observation Kalman recursion**, with the required continued propagation of the changing world; its receipt/grade remained qualified.

### Pleasant Crescent interpretation
- A partner GIS API sends the same unmodified record repeatedly. That is not three independent confirmations of an accessibility claim.
- During a network outage, a scheduled event may still expire, and old opening times may still be stale even if the database is unchanged.
- Mark repeated data with a source revision/ETag and do not increment confidence merely because identical bytes arrived three times.
- Continue clock-time expiry handling even during a pause in agent usage.

A strong engineering pattern, **not** evidence for a novel CRR theorem.

Source: https://github.com/alexsabine/Phoenix-1-/blob/main/Phoenix_Egg/RUNS/P14-EMPTY1-2026-10-07/RESULT.md
