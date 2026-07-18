# Conjunctive law + single-score remedy — final report

**Branch:** analysis/conjunctive-law-and-single-score-remedy
**Decision: LAW-ONLY GO-B. Readiness: 8.0/10.**

## Theorem (Stage 1)
J_old = Q/(P1+P2−Q); J_new = Qc/(P1a+P2b−Qc). Proven (sympy, exact):
**J_new ≤ J_old ⇔ c(P1+P2) ≤ P1a+P2b ⇔ P1(a−c)+P2(b−c) ≥ 0.**
Symmetric a=b=p ⇒ c ≤ p. Since c ≤ min(a,b), independence ⇒ monotonic non-increase.
Equality iff added criterion perfectly reproducible; increase requires dependence.
Numeric: factorized-identity match 1.0; independence non-increase 0.9998; dependence
increase 9693/10000.

## Non-circular validation (Stage 2)
Blinding test: predictions reconstructed from criterion-level probabilities alone reproduce
stored predictions exactly (max|diff| = 0, n=3534). Observed higher-order Jaccard never enters
prediction. Pooled Spearman 0.988, median |err| 0.013; LODO Spearman 0.980–0.991. Framed as a
parameter-free composition prediction — not prospective forecasting, not artifact ground truth.

## Single-score remedy (Stages 3–6)
Split-half accepted-set Jaccard (p75): R0 0.707, R1 0.944, R2 0.945, R3 0.735.
%sessions ≥0.80: R0 22.8, R1 93.9, R2 93.9, R3 28.1.
Transport Jaccard: R0 0.596, R1 0.933, R2 0.932, R3 0.653.
Matched-availability transitions/min: R0 47.5, R1 40.5, R2 41.0, R3 53.7 (R1/R2 ~15% lower).
Downstream natural vs no gate: R1 −0.0011 [−0.0047,+0.0027], R2 −0.0009 [−0.0045,+0.0024],
R3 −0.0072 [−0.0121,−0.0028]. Count-matched vs R0: R1 +0.0042, R2 +0.0054, R3 +0.0030.
p95 latency: all < 5 ms. Fail-closed + deterministic: pass.

## Scorecard
R1 and R2 pass 11/12 frozen criteria, failing only C7 (≥30% transition reduction; achieved ~15%).
R3 passes 4/12. No method passes all 12 ⇒ REMEDY-GO precluded. Stage 7 (degradation) not run
(gated on passing 1–8).

## Conclusion
The composition theorem is proved and non-circularly validated; the single-score remedy fixes
the dominant calibration/transport instability and preserves downstream information, but does not
meet the strict streaming-smoothness bar. Supports a strong methodological paper (LAW-ONLY GO-B).
A corrected single-score gate targeting C7 is a justified next step, not started here.
