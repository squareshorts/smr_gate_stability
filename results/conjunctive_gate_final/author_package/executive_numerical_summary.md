# Executive numerical summary (final package)

- 114 sessions, 57 participants, 3 datasets (ds004447, ds004444, ds004446); 22,418 task windows.
- Composition theorem: J_new <= J_old iff c(P1+P2) <= P1a+P2b (symbolically exact; independence => non-increasing).
- Parameter-free composition validation: pooled Spearman 0.988, pooled median |error| 0.013; LODO Spearman 0.980-0.991; blinding test exact (0 dependence on higher-order outcomes).
- Cardinality: median accepted-set Jaccard 0.915 (K1) -> 0.630 (K5); overall agreement stays ~0.76 at K5 while accepted-set Jaccard falls (global agreement conceals accepted-set instability).
- Remedy calibration stability (split-half accepted-set Jaccard): R0 0.707, R1 0.944, R2 0.945, R3 0.735; sessions >=0.80: R0 22.8%, R1 93.9%.
- Transport Jaccard: R0 0.596, R1 0.933, R2 0.932, R3 0.653.
- Downstream natural vs no-gate: R1 -0.0011 [-0.0047,+0.0027], R2 -0.0009 [-0.0045,+0.0024]; count-matched vs R0 slightly positive.
- Operational (matched availability): transitions/min R0 47.5, R1 40.5 (~15% reduction; below the 30% target).
- Runtime p95 latency < 5 ms all methods; fail-closed + deterministic.
- Controlled degradation (real windows; feature reproduction max rel diff ~1e-16):
  - Unchanged control D0: R1 false-withhold 0.000; decision reproduction 1.000.
  - Fail-closed D9 (missing/invalid): R1 1.000.
  - Top-severity R1 response: common-mode broadband 0.96, 35-45 Hz 0.96, transient 0.89, single-ch broadband 0.54, 20-30 Hz 0.58, partial freeze 0.00, full freeze 0.00, clipping 0.00.
  - Verdict: DEGRADATION-FAIL (R1 blind to clipping and channel-freeze; under-responds to single-channel broadband and beta-band). R1's stability is partly achieved by insensitivity to localized single-channel faults.
- Package decision: PACKAGE-GO-B; readiness 8.0/10.
