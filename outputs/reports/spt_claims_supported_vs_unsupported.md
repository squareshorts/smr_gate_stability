# SPT Claims: Supported vs Unsupported

Generated: 2026-07-01T18:19:08.192896+00:00

## Claims assessed

### 1. The fast-slow model can generate separable outcomes

**Claim:** The fast-slow closed-loop model can produce high-beta stabilization without
SMR acquisition, SMR acquisition without high-beta stabilization, both, and neither.

**Evidence source:** SPT1 simulation (spt1_simulation_summary.csv)

**Status:** SUPPORTED BY SIMULATION

By design of the fast-slow model, all four regimes are producible by varying alpha_x,
beta_y, K_beta, and epsilon. This is a structural separability property, not a
contingent empirical finding.

---

### 2. The singular perturbation approximation is valid in the SMR-neurofeedback parameter range

**Claim:** For realistic parameters, tau_beta << tau_SMR (time-scale separation holds).

**Evidence source:** SPT2 simulation (spt2_timescale_metrics.csv)

**Status:** SUPPORTED IN SIMULATIONS (epsilon <= 0.03)

Simulation shows that for epsilon <= 0.03 and beta_y >= 1/s, alpha_x ~ 0.05/s,
tau_ratio < 0.1. Whether these conditions apply to real EEG is not proven.

---

### 3. High-beta barrier violations reduce subsequent SMR improvement (simulation)

**Claim:** When the high-beta state violates the admissible region, subsequent
SMR acquisition is suppressed in the simulation.

**Evidence source:** SPT3 simulation (spt3_barrier_metrics.csv)

**Status:** SUPPORTED IN SIMULATIONS

Simulation shows that blocks after admissible-state occupation show greater SMR improvement
than blocks after violation, though the effect size is modest and parameter-dependent.

---

### 4. Real EEG shows empirical time-scale separation (tau_beta < tau_SMR)

**Claim:** In real SMR-BCI EEG data, high-beta envelope time scale is shorter
than SMR learning/regulation time scale.

**Evidence source:** SPT4 revised (spt4_empirical_tau_ratios.csv, spt4_tau_bandwidth_control.csv)

**Status:** INCONCLUSIVE — BANDWIDTH CONFOUND

The primary AR1 tau_ratio ≈ 0.10 matches the Gaussian bandwidth prediction (0.09) for
SMR (3 Hz BW) vs high-beta (10 Hz BW) almost exactly. Bandwidth-matched control
(SMR 12–15 Hz vs HB 20–23 Hz, both 3 Hz BW) gives tau_ratio ≈ 1.05. Block-mean
ratios are ≈ 0.92 and 1-Hz decimated ratios are ≈ 1.38. The observed separation cannot
be distinguished from a filter bandwidth artefact with the current analysis.

**DO NOT CLAIM**: 'Real EEG shows empirical time-scale separation consistent with SPT'
based on the AR1 analysis alone.

---

### 5. Empirical separability of SMR acquisition and high-beta stabilization

**Claim:** In real EEG data, some subjects show SMR acquisition without high-beta
stabilization (B) or high-beta stabilization without SMR acquisition (C).

**Evidence source:** SPT5 classification (spt5_four_quadrant_classification.csv)

**Status:** PRESENT (n_B=2, n_C=3)

Note: Previous WP8 showed 0/5 subjects with full joint signature. With n=5, many
combinations simply cannot be empirically observed. This is a sample-size limitation.

---

### 6. High-beta barrier violations predict next-state instability in real EEG

**Claim:** Barrier violations at time t predict reduced SMR increase at t+1 in real data.

**Evidence source:** SPT6 revised (spt6_barrier_prediction_models.csv, spt6_nonzero_viol_summary.csv)

**Status:** NULL RESULT (after FDR correction)

With block-mean thresholds (fixing the original threshold-on-raw-envelope sparsity),
all 200 combinations have data. The theoretically meaningful outcome (smr_increase)
yields 0/100 tests significant at q < 0.05 after FDR correction. A consistent negative
direction (mean phi = −0.14, 84/100 tests) is compatible with the hypothesis but not
statistically reliable at n = 5.

The `admissible_next` outcome (HB decreases next block) is excluded from inference:
it is confounded by regression to the mean when percentile-based thresholds select
extreme blocks (phi > 0 in 100/100 tests).

**DO NOT CLAIM**: 'High-beta violations predict subsequent SMR changes' (null result).

---

### 7. The SPT framework is scientifically stronger than the Stuart-Landau framing

**Claim:** The singular perturbation / fast-slow barrier framework better explains
empirical results and supports the non-diagnostic interpretation of high-beta suppression.

**Evidence source:** SPT7 (spt7_framework_comparison.csv)

**Status:** SUPPORTED BY CONCEPTUAL ANALYSIS

SPT wins 5 / 8 framework-comparison criteria vs SL winning 1 / 8.
The SPT framework is recommended as the primary framework.

---

## Claims that MUST NOT be made

- That high-beta suppression causes SMR learning (not supported, and not claimed by SPT).
- That high-beta suppression is necessary for SMR learning (explicitly refuted by separability).
- That high-beta suppression is sufficient evidence of SMR acquisition (explicitly refuted).
- That the empirical data prove a physiological mechanism (sample too small, descriptive only).
- That any simulation result constitutes empirical proof.
- That the fast-slow barrier hypothesis is proven; it is supported by simulation and
  is consistent with empirical data (SPT5 quadrants) but NOT confirmed by the tau or
  barrier-prediction tests.
- That real EEG shows time-scale separation (tau_beta << tau_SMR): bandwidth confound.
- That high-beta violations predict subsequent SMR changes: null result after FDR.
- That the Stuart-Landau model is the primary mechanistic framework: it is demoted to
  supplementary material (SPT7 shows SL loses on 5/8 criteria).
- That 'at least one significant barrier prediction result' constitutes support: the
  one previously-significant result (sub-005, ses-08) was a single subject, did not
  survive Bonferroni correction, and used a flawed threshold methodology.

Generated: 2026-07-01 (revised)
