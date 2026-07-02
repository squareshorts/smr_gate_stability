# Beta Escape: Strengthened Analysis Results

## 1. Incremental Model Comparison
Beta-state persistence metrics (Model C) successfully add explanatory value beyond mean high-beta power (Model A) in predicting SMR acquisition and SNR changes. This supports the claim that mean power is non-diagnostic on its own.

## 2. Amplitude-Occupancy-Persistence Decomposition
Empirically, 'high-beta suppression' in ds004447 primarily reflects reduced beta-state occupancy and shorter dwell times, rather than a uniform reduction in amplitude inside the beta state. The variance in mean power is overwhelmingly driven by persistence and occupancy changes.

## 3. Negative-Control Band Analysis
The persistence and dissociation effects are specific to the high-beta band. Control bands (theta, alpha, high-frequency) do not show the same systematic relationship with SMR acquisition, ruling out a generic broadband or artifact-driven shift.

## 4. Threshold-Free State Validation
A data-driven Gaussian Mixture Model (GMM) applied to spectral envelopes shows strong agreement (high Dice coefficient) with the predeclared threshold-defined S1 state. This validates that the thresholding approach isolates a genuine dynamic state.

## 5. Subject Influence and Robustness
The main conclusions survive leave-one-subject-out (LOO) influence checks, robust regression (Huber), bootstrap resampling, and artifact exclusions. Furthermore, channel sensitivity analysis confirms the effect across the sensorimotor cluster (E36, E104, E128).

