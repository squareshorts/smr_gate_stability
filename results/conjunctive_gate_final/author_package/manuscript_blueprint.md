# Manuscript blueprint (structured only — not prose)

Format per section: heading | scientific purpose | result artifacts | tables/figures | claim boundaries | limitations to mention.

A. Composition theorem
- purpose: state and prove the accepted-set stability condition for conjunctive gates.
- artifacts: theory/formal_theorem.md, theorem_evidence_table.csv, algebra_verification.txt.
- figures/tables: Figure 1; theorem_statement.md.
- boundaries: probabilistic composition identity under independence; not a universal law.
- limitations: dependence approximation.

B. Validation across all 31 criterion combinations
- purpose: show the parameter-free prediction tracks observed subset Jaccard.
- artifacts: composition_validation_table.csv; validation/higher_order_outcome_blinding_test.txt.
- figures/tables: Figure 2.
- boundaries: composition prediction, not prospective forecast; non-circular (blinding exact).
- limitations: three datasets.

C. Replication across three datasets
- purpose: leave-one-dataset-out generalisation.
- artifacts: composition_validation_table.csv.
- figures/tables: Figure 6.
- boundaries: 0.980-0.991 Spearman on held-out datasets.

D. Global vs accepted-set agreement
- purpose: show high global agreement conceals low accepted-set agreement.
- artifacts: cardinality_results_table.csv.
- figures/tables: Figure 3.
- boundaries: accepted-set metric distinct from overall agreement.

E. R1 single-score remedy
- purpose: single averaged percentile score with one threshold improves stability.
- artifacts: remedy_primary_results_table.csv, calibration_stability_table.csv.
- figures/tables: Figure 5.
- boundaries: retrospective; R2 sensitivity; R3 negative.
- limitations: does not meet 30% transition target.

F. Cross-session transport
- artifacts: transport_results_table.csv. figures: Figure 6/7.
- boundaries: 3-dataset scope.

G. Downstream information preservation
- artifacts: downstream_results_table.csv. figures: Figure 8.
- boundaries: reused decoder/folds; not efficacy.

H. Controlled degradation response
- purpose: verify R1 is not merely insensitive; report blind spots.
- artifacts: degradation_results_table.csv, degradation/degradation_final_report.md.
- figures/tables: Figure 9.
- boundaries: engineering test; DEGRADATION-FAIL; blind to clipping/channel-freeze.
- limitations: not natural-artifact validation.

I. Remaining temporal-transition limitation
- artifacts: operational_results_table.csv. figures: Figure 7.
- boundaries: ~15% transition reduction; open problem.
