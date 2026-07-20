# Frozen success and failure criteria

- Stable calibration: participant-grouped median accepted-set Jaccard >=0.80 and >=80% of sessions at Jaccard >=0.80.
- Stable transport: participant-grouped median accepted-set Jaccard >=0.75.
- Operationally usable: median longest feedback-free interval <=20 s and <10% of sessions with any gap >30 s.
- High global agreement conceals poor accepted-set stability when overall agreement >=0.95 while accepted-set Jaccard or positive agreement <0.80.
- General instability is supported when at least three calibrated monitor families have median independent-split Jaccard <0.80 in at least two datasets. M0 and fixed M3 are controls, not calibrated families.
- Complexity is associated with improved stability only if the more complex monitor has a higher participant median Jaccard with a grouped 95% interval excluding zero for the paired difference.
- Downstream null results are not equivalence; all confidence intervals and nonviable folds are retained.
- M5 is a faithful established monitor only after environment, API, covariance, metric, threshold, and online-use checks pass. Otherwise it is labeled ROBUST_COV_DISTANCE.
