# External monitor method audit

Implementation decision: faithful pyRiemann `Potato`, version 0.10; fallback not used.

- Class: `pyriemann.clustering.Potato(metric="riemann", threshold=3, n_iter_max=100)`.
- Input: one 3 x 3 sample covariance matrix per 1 s canonical window. Three channels and 1,000 samples per window make full-rank SCM covariance technically applicable; every matrix is explicitly checked for finite values and strictly positive eigenvalues.
- Covariance regularization: none for the faithful Potato analysis. Singular/nonfinite matrices fail closed and are listed as nonviable. The frozen regularized log-Euclidean method remains only the unused fallback.
- Calibration: rest matrices only; at least 20 valid rest matrices required. Task outcomes, decoder labels, the other session, and held-out participants never enter fitting.
- Distance: affine-invariant Riemannian distance as implemented by pyRiemann.
- Threshold: z-score threshold 3.0, the documented default. Prediction accepts only standardized log-distance `z < 3`; equality is withheld.
- Runtime use: the fitted Potato is fixed and predicts one covariance at a time. `partial_fit` is not used, so online adaptation cannot leak task outcomes.
- Three-channel scope: technically valid but narrower than typical high-density demonstrations; results are an engineering comparison, not artifact ground truth.

Verified sources:

- pyRiemann 0.10 Potato API: https://pyriemann.readthedocs.io/en/v0.10/generated/pyriemann.clustering.Potato.html
- Original Riemannian Potato record: https://hal.science/hal-00781701
- Riemannian Potato Field paper record: https://pubmed.ncbi.nlm.nih.gov/30668501/
