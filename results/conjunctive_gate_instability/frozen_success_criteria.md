# Frozen GO / NO-GO criteria — conjunctive-instability law

Frozen before results. Do not change after seeing results.

GO-LAW is assigned only if ALL of the following hold:

1. Pooled Spearman correlation between predicted and observed subset Jaccard ≥ 0.80.
2. Spearman correlation ≥ 0.70 in each of the three datasets.
3. Pooled median absolute prediction error ≤ 0.05.
4. Dataset-specific median absolute prediction error ≤ 0.08.
5. ≥ 80% of one-criterion additions with a theoretically predicted decrease show an observed
   decrease in Jaccard.
6. Median five-criterion Jaccard is ≥ 0.15 lower than median one-criterion Jaccard in each dataset.
7. The five-criterion instability is not attributable to only one criterion: at least three of
   the five criteria show a reproducible negative contribution when added to at least one
   lower-order subset.
8. Leave-one-dataset-out direction accuracy ≥ 75% in each dataset.
9. Empirical and Harrell–Davis sensitivity analyses support the same qualitative conclusion.

NO-GO-LAW if ANY of conditions 1–6 fails.
Conditions 7–9 may be classified as PARTIAL only if conditions 1–6 all pass.

Prediction error = |J_observed − J_predicted| at the subset level (empirical primary estimator).
Direction accuracy = fraction of one-criterion additions whose observed ΔJaccard sign matches
the predicted ΔJaccard sign (material additions, |ΔJ_pred| ≥ 0.02 or |ΔJ_obs| ≥ 0.02).
