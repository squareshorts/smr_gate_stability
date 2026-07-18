# Result provenance

## Active (canonical) results
| Result | Path | Status |
|---|---|---|
| 31-subset composition law | results/conjunctive_gate_instability/ | verified; Spearman 0.988, MAE 0.013 |
| Theorem + validation | results/conjunctive_law_remedy/theory, /validation | verified symbolically + blinding exact |
| Single-score remedy | results/conjunctive_law_remedy/remedy, /author_package | R1/R2 11/12 criteria |
| Downstream preservation | results/conjunctive_law_remedy/remedy/downstream_*_R.csv | reuses decoder features/folds |
| Controlled degradation | results/conjunctive_gate_final/degradation/ | DEGRADATION-FAIL (documented) |
| Final figures (data + R) | results/conjunctive_gate_final/figure_data, figures; scripts/.../figures_r | render on host |

## Reused verified inputs (not regenerated)
- canonical per-window feature cache; reusable feature cache; decoder features; fold definitions;
  verified M0/M4 downstream results.

## Abandoned / archived narratives (archive/deadends/ or manual_review)
- NF-SQI-as-ready-interlock; general "all baseline gates unstable" negative paper; runtime-interlock;
  scheduler remediation; obsolete external-monitor install attempts; superseded / zero-byte figures.

## Not natural-artifact ground truth
The controlled degradation is engineering measurement-degradation testing, not artifact ground truth,
clinical validation, or neurofeedback-efficacy evidence.
