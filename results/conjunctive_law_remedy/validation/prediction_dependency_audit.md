# Prediction dependency audit

Every predicted quantity in the composition law is a deterministic function of the
five criterion-level triples (p_j1, p_j2, q_j), each derived from baseline calibration
applied to single-criterion task decisions. The parameter-free prediction J_pred(S) uses
only the marginal products of these single-criterion quantities.

- Blinding test: dropping all observed higher-order columns and reconstructing predictions
  from criterion-level probabilities alone reproduces the stored predictions exactly
  (max abs diff 0.00e+00, n=3534). PASS=True.
- The observed higher-order Jaccard is an OUTCOME compared against the prediction; it never
  enters the prediction.
- Held-out-dataset information and fitted coefficients enter ONLY the optional secondary
  dependence correction, which is fit on development datasets and frozen for the holdout.
  The primary result is the uncorrected theorem prediction.
