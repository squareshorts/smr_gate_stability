# Comparative results report

1. Most stable accepted set: M0, M3, and M5 tied at split-half Jaccard 1.000; M1 was the most stable active percentile gate (0.925).
2. Least stable accepted set: M4 (split-half Jaccard 0.687).
3. Complexity did not improve stability: the five-feature conjunction was worse, while Potato accepted all windows.
4. High global agreement did not broadly conceal poor positive agreement; the prespecified pattern was rare.
5. M4 caused the most starvation, but its median longest gap was only 3.0 s and no session exceeded 30 s.
6. M4 caused the most state switching (42.1 transitions/min).
7. M4 had the largest downstream information cost versus no gate (natural balanced accuracy -0.0164).
8. Instability was NF-SQI-specific in this comparison, not general across baseline-calibrated gates.
9. Potato materially weakens the general thesis because it reproduced the no-gate decision set at z=3.
10. Minimum reporting: accepted-set Jaccard, positive/negative agreement, independent calibration splits, duration sensitivity, cross-session transport, temporal gaps/transitions, downstream retention/cost, latency, fail-closed behavior, and reason codes.

Decision: NO-GO for a paper claiming general baseline-gate instability. Readiness: 7.5/10 for a transparent comparative engineering report.
