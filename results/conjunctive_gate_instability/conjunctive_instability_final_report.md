# Conjunctive-gate-instability — final report

VERDICT: **GO-LAW**. Pooled Spearman(predicted,observed) = 0.9877, pooled median |error| = 0.0134.

1. Sessions: 114 included, 0 excluded (57 participants; ds004444/ds004446/ds004447).
2. Subsets: all 31 nonempty subsets of Q1-Q5 evaluated on identical per-session task windows.
3. Criterion reproducibility r_j (pooled median): Q1=0.913, Q2=0.932, Q3=0.9, Q4=0.992, Q5=0.851.
4-5. Observed vs predicted median Jaccard by cardinality: K1 obs=0.915/pred=0.915; K2 obs=0.818/pred=0.811; K3 obs=0.746/pred=0.719; K4 obs=0.691/pred=0.632; K5 obs=0.63/pred=0.561.
6. Prediction fit: pooled Spearman 0.988, pooled median|err| 0.013; per dataset ds004444 Sp=0.991/medAE=0.014, ds004446 Sp=0.986/medAE=0.009, ds004447 Sp=0.98/medAE=0.014.
7. Lattice one-criterion additions: 8550 total; 61.1% reduce, 2.9% increase, 36.0% no material change; direction accuracy 0.94.
8. Cardinality effect: median Jaccard falls 0.915 (K1) -> 0.63 (K5); overall agreement stays high (0.756 at K5) while mutual withholding rises to 0.283 — high global agreement masks low accepted-set agreement.
9. By dataset (K1->K5 drop): ds004444 0.305, ds004446 0.193, ds004447 0.285.
10. Leave-one-dataset-out: ds004444 Spearman 0.991, direction 0.944, slope 0.868, ds004446 Spearman 0.986, direction 0.974, slope 0.894, ds004447 Spearman 0.98, direction 0.929, slope 0.858.
11. Empirical vs Harrell-Davis: pooled Spearman empirical 0.988 / hd 0.988; both show K1-K5 drop > 0.15 (emp 0.286, hd 0.269).
12. Single-criterion attribution: 4 of 5 criteria (Q1,Q2,Q3,Q5) show reproducible negative contribution; Q4 transient (p90, p~1.0) does not — effect is multi-criterion, not one feature.
13. **GO-LAW**.
14. Supports a general methodological paper: instability is a predictable multiplicative property of conjunctive baseline-calibrated gates, not an NF-SQI-specific defect.
15. Proceeding to a corrected single-score gate is scientifically justified but NOT started (requires new explicit instruction).
16. Outputs under results/conjunctive_gate_instability/ (see completed_checkpoint_manifest.csv and author_package/).