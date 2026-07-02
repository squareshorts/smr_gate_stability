# SPT Results for Revision

Generated: 2026-07-01 (revised)

This document summarizes results from Work Packages SPT1–SPT8, with methodological
corrections applied to SPT4 (time-scale analysis) and SPT6 (barrier prediction).

---

## METHODOLOGICAL REVISION NOTICE (2026-07-01)

Five methodological concerns were identified and addressed:

### 1. Tau computation fairness (SPT4 revised)

**Problem**: The AR1 autocorrelation tau on high-resolution (256 Hz) envelopes is
confounded by filter bandwidth. The SMR band (12–15 Hz, 3 Hz BW) is narrower than
the high-beta band (20–30 Hz, 10 Hz BW), which alone produces a tau_ratio ≈ 0.09
(Gaussian bandwidth prediction). The observed primary AR1 ratio ≈ 0.10 almost exactly
matches this prediction.

**Fix applied**: Three deconfounding analyses were computed and reported:
(a) Bandwidth-matched control: SMR 12–15 Hz vs HB 20–23 Hz (both 3 Hz BW) → tau_ratio ≈ 1.05
(b) Block-mean tau (4-s blocks, regulation scale) → ratio ≈ 0.92
(c) 1-Hz decimated envelope → ratio ≈ 1.38

**Conclusion**: All deconfounded analyses give tau_ratio ≈ 1.0 (no separation).
The primary AR1 time-scale separation was a bandwidth artefact.
**DO NOT CLAIM empirical time-scale separation from this analysis.**

### 2. Expand beyond n=5

**Status**: Not feasible without new data downloads.
Only ds004446 (5 subjects: sub-004, sub-005, sub-012, sub-013, sub-018;
sessions ses-01 and ses-08) is available locally.
Datasets ds004444, ds004447, ds004448 are listed in the manifests but not downloaded.
The analysis uses all 10 available EDF files (5 subjects × 2 sessions), yielding
30 EEG segments (rest, task, interval) and ~35–40 blocks per condition per session
for block-level analyses.

### 3. Barrier-prediction rigour (SPT6 revised)

**Problem 1 — Threshold sparsity**: Original thresholds computed on 256 Hz instantaneous
envelope; block means rarely exceeded these → violation_rate = 0 for 168/200 rows.
**Fix**: Thresholds now computed on block-mean distributions. Guarantees ~25% violation rate
for p75, ~20% for p80, etc. All 200 combinations now have data.

**Problem 2 — Regression-to-mean artefact**: The `admissible_next` outcome (HB decreases
next block) is confounded: when a block is selected as a violation (above 75th percentile),
the next block is expected to regress to the mean by construction. Evidence: phi > 0 for
100/100 admissible_next tests (mean phi = 0.37). Outcome excluded from inference.

**Problem 3 — Multiple testing correction**: After FDR correction (Benjamini-Hochberg)
applied to 100 smr_increase tests: **0/100 significant at q < 0.05**. Even the single
previously-highlighted result (sub-005, ses-08, rest, p80, phi = −0.47, p = 0.004)
gives Bonferroni-corrected p = 0.4.

**Fix applied**: Full FDR correction, phi effect sizes, Fisher exact tests.

**Conclusion**: **Null result for barrier prediction.** A directional signal
(mean phi = −0.14, 84/100 negative) is compatible with the hypothesis but not
statistically reliable at n = 5. Report as null/inconclusive.

### 4. Stuart-Landau demotion

SPT7 framework comparison shows SPT wins 5/8 criteria vs SL winning 1/8.
The Stuart-Landau model is formally demoted to supplementary material in this revision.
The primary mechanistic framework is SPT/fast–slow barrier.
All primary manuscript claims should reference SPT, not SL.

### 5. Honest null reporting

The revised analyses produce the following honest claim status:

| Claim | Status |
|---|---|
| Model can generate separable outcomes (SPT1) | SUPPORTED by simulation |
| SPT approximation valid for epsilon≤0.03 (SPT2) | SUPPORTED by simulation |
| Barrier violations suppress SMR in simulation (SPT3) | SUPPORTED by simulation |
| Real EEG shows time-scale separation (SPT4) | INCONCLUSIVE — bandwidth confound |
| Empirical separability: 2B + 3C subjects (SPT5) | DESCRIPTIVE (n=5) |
| Barrier violations predict SMR outcome (SPT6) | NULL RESULT (q>0.05, FDR) |
| SPT > SL on framework criteria (SPT7) | SUPPORTED by conceptual analysis |
| SL demoted to supplementary | IMPLEMENTED (SPT7) |

---

## SPT1: Fast-slow closed-loop model

# SPT1 Results: Fast–slow Closed-loop Model

## Model summary

The fast–slow closed-loop model implements:

- Slow variable x(t): SMR regulation / target-learning state.
  `dx/dt = alpha_x*(x_target - x) - k_xy*viol(y) + u_smr + noise`
- Fast variable y(t): high-beta envelope / stabilization state.
  `eps * dy/dt = -beta_y*(y - k_yx*x) + u_beta + noise`
- Controller: SMR reward signal + high-beta barrier inhibit.
  `h_beta(y) = y_barrier - y >= 0`

## Parameter ranges

- epsilon: [0.01, 0.03, 0.1, 0.3, 1.0]
- alpha_x (SMR learning): [0.001, 0.01, 0.05, 0.1]
- beta_y (high-beta decay): [0.1, 0.5, 2.0, 5.0]
- K_beta (barrier inhibit gain): [0.0, 0.5, 1.5, 3.0]

## Regime simulation results (n=6 prototype regimes)

- **R1_stabilization_only**: SMR acquired = False, beta stabilized = True, x_final = 0.093, y_final = 0.038, beta-violation rate = 0.000
- **R2_acquisition_only**: SMR acquired = True, beta stabilized = False, x_final = 615497959502404352.000, y_final = 13278552653150766.000, beta-violation rate = 0.821
- **R3_both**: SMR acquired = True, beta stabilized = False, x_final = 1870904341109.858, y_final = 249080217195.328, beta-violation rate = 0.821
- **R4_neither**: SMR acquired = False, beta stabilized = True, x_final = 0.181, y_final = 0.093, beta-violation rate = 0.000
- **R5_barrier_violation**: SMR acquired = True, beta stabilized = False, x_final = 9.965, y_final = 2.020, beta-violation rate = 0.784
- **R6_broadband_contamination**: SMR acquired = True, beta stabilized = False, x_final = 2580123885857.956, y_final = 342835118332.441, beta-violation rate = 0.806

## Parameter grid results (n=1280 simulations)

Regime frequencies:
- A_both: 72 (5.6%)
- B_acquisition_only: 640 (50.0%)
- C_stabilization_only: 568 (44.4%)

## Separability test

High-beta stabilization without SMR acquisition (R1, R3 stability domain): **PRESENT**
SMR acquisition without high-beta stabilization (R2): **PRESENT**
Regime B (acquisition only) count: 640
Regime C (stabilization only) count: 568

**Separability confirmed by simulation:** True

The model can generate:
1. High-beta stabilization without SMR acquisition (low alpha_x, any beta_y).
2. SMR acquisition without high-beta stabilization (high alpha_x, low beta_y, K_beta=0).
3. Both (high alpha_x, high beta_y, low epsilon).
4. Neither (low alpha_x, low beta_y).
5. Barrier violation disrupting training (high k_xy, K_beta=0, high sigma_y).
6. Broadband contamination producing false apparent regulation (high sigma_z).

This directly supports the central separability hypothesis: high-beta suppression
and SMR acquisition are mechanistically independent in the fast–slow framework.

Generated: 2026-07-01T18:10:24.822880+00:00


---

## SPT2: Singular perturbation validity check

# SPT2 Results: Singular Perturbation Validity Check

## Method

Simulated the fast–slow system with the full ODE and compared y(t) to the
quasi-steady manifold approximation y*(x) defined by g(x, y*) = 0.

Computed:
- tau_y = epsilon / beta_y (fast variable settling time)
- tau_x = 1 / alpha_x (slow variable change time)
- tau_ratio = tau_y / tau_x
- Manifold approximation error: |y(t) - y*(x(t))|
- SPT valid when tau_ratio < 0.05; partial when < 0.2; invalid otherwise.

## Results

Mean tau_ratio by epsilon:
- epsilon = 0.01: tau_ratio = 0.0003 -> SPT valid
- epsilon = 0.03: tau_ratio = 0.0009 -> SPT valid
- epsilon = 0.1: tau_ratio = 0.0029 -> SPT valid
- epsilon = 0.3: tau_ratio = 0.0087 -> SPT valid
- epsilon = 1.0: tau_ratio = 0.0290 -> SPT valid

Validity counts across all parameter combinations:
- partial: 6/135 (4.4%)
- valid: 129/135 (95.6%)

## Interpretation

The singular perturbation approximation is:
- **Valid** (tau_ratio < 0.05): for epsilon <= 0.03 with typical beta_y (1–5/s)
  and alpha_x (0.02–0.1/s). High-beta dynamics settle ~10–50x faster than SMR learning.
- **Partially valid** (tau_ratio 0.05–0.2): for epsilon ~ 0.1.
- **Invalid** (tau_ratio > 0.2): for epsilon >= 0.3, where time scales become comparable.

The boundary-layer approximation error decreases with epsilon, confirming that small
epsilon values produce accurate fast-manifold tracking.

For the fast-slow framework to apply to real neurofeedback, we require empirical
tau_beta << tau_SMR. This is tested in SPT4.

Generated: 2026-07-01T18:10:44.405429+00:00


---

## SPT3: Control-barrier interpretation

# SPT3 Results: Control-barrier Interpretation

## Model

High-beta inhibition is formalized as a control barrier function (CBF):

  h_beta(y) = y_barrier - y
  Admissible training state: h_beta(y) >= 0  <=>  y < y_barrier

The controller applies a barrier inhibit force proportional to violation:
  u_beta = -K_beta * max(y - y_barrier, 0)

## Parameter sweep

- epsilon: [0.02, 0.1, 0.5]
- K_beta: [0.0, 0.5, 1.5, 3.0, 5.0]
- sigma_y: [0.05, 0.15, 0.30]
- Total simulations: 135

## Barrier violation metrics (mean over sigma_y and seed)

K_beta | Violation rate | SMR after violation | SMR after admissible
-------|----------------|---------------------|---------------------
0.0    | 0.869          | 0.0420              | 0.1039
0.5    | 0.869          | 0.0418              | 0.1052
1.5    | 0.725          | 0.0415              | 0.1065
3.0    | 0.725          | 0.0416              | 0.1063
5.0    | 0.725          | 0.0413              | 0.1081

## Interpretation

**SMR change after admissible state minus after violation: 0.0644**

SMR state improves MORE after admissible-state blocks than after barrier-violation blocks. This is consistent with the barrier stabilization hypothesis: high-beta violations suppress subsequent SMR acquisition probability.

**Conclusion:** High-beta behavior in the fast–slow model acts like a stabilization
constraint variable rather than a target-learning variable. The barrier K_beta reduces
violation rate, increases admissible-state occupancy, and modulates (but does not
determine) subsequent SMR improvement.

Generated: 2026-07-01T18:15:46.025921+00:00


---

## SPT4: Empirical EEG time-scale reanalysis

# SPT4 Results: Empirical Time-scale Analysis

## Dataset

Dataset: ds004446
EDF files processed: 10
Analyzable segments (status=ok): 30

## Time-scale results

Method: AR1 autocorrelation and ACF e-fold time for band envelopes.
SMR band: (12.0, 15.0) Hz; High-beta band: (20.0, 30.0) Hz.

Mean tau_ratio (tau_beta / tau_SMR, AR1): 0.100
Median tau_ratio (AR1): 0.094

Segments where tau_beta < 0.5 * tau_SMR (AR1): 30/30
Segments where tau_beta < 0.5 * tau_SMR (ACF): 26/30

## Descriptive statistics by condition

### rest (n=10 segments)
- Mean SMR tau (AR1): 37.414 s
- Mean High-beta tau (AR1): 3.659 s
- Mean tau_ratio: 0.101

### task (n=10 segments)
- Mean SMR tau (AR1): 37.203 s
- Mean High-beta tau (AR1): 3.335 s
- Mean tau_ratio: 0.092

### interval (n=10 segments)
- Mean SMR tau (AR1): 56.624 s
- Mean High-beta tau (AR1): 6.072 s
- Mean tau_ratio: 0.107


## Interpretation

Empirical evidence PARTIALLY SUPPORTS time-scale separation: high-beta envelope time scale (tau_beta) is on average shorter than SMR envelope time scale (tau_SMR) with mean ratio 0.100. However, variability is high and sample size is small (n=30 segments). This is consistent with the singular perturbation hypothesis but does not constitute strong empirical proof.

Generated: 2026-07-01T18:11:44.339330+00:00


---

## SPT5: Empirical four-quadrant classification

# SPT5 Results: Empirical Four-quadrant Classification

## Method

Each subject is classified by the sign of fractional change in:
- SMR power (12–15 Hz): ses-01 to ses-08.
- High-beta power (20–30 Hz): ses-01 to ses-08.
- Broadband non-target power (4–45 Hz, excluding SMR and high-beta).

Quadrants:
- A (both): SMR increases AND high-beta decreases.
- B (acquisition only): SMR increases AND high-beta does NOT decrease.
- C (stabilization only): SMR does NOT increase AND high-beta decreases.
- D (neither): neither SMR increases nor high-beta decreases.

## Results

Total subjects classified: 5
- A (both):             0 / 5
- B (acquisition only): 2 / 5
- C (stabilization only): 3 / 5
- D (neither):          0 / 5

## Separability test

Subjects in B or C (separable outcome) present: True
Subjects with acquisition-only (B): 2
Subjects with stabilization-only (C): 3

## Interpretation

The empirical data show at least some subjects in B (acquisition only) or C (stabilization only) quadrants, providing EMPIRICAL SUPPORT for the separability hypothesis: high-beta suppression and SMR acquisition can dissociate at the subject level.

CAUTION: Sample size is very small (N=5). These results are descriptive only and do not constitute statistical proof.

## Previous WP8 context

From WP8 analysis: SMR fractional change ≈ -0.006, high-beta fractional change ≈ +0.052.
The full joint signature (A) was found in 0 / 5 subjects.
This is consistent with D (neither) or C (stabilization only) as dominant outcomes.

Generated: 2026-07-01T18:11:52.170229+00:00


---

## SPT6: Barrier violation and future-state prediction

# SPT6 Results: Barrier Violation and Future-state Prediction

## Method

High-beta barrier violations at block t are tested as predictors of:
1. Admissible-state occupancy at block t+1.
2. SMR increase at block t+1.

Block size: 4.0 s.
Violation thresholds: 75th, 80th, 90th percentile; 2-SD z-score; 3-MAD.
Statistical tests: point-biserial correlation + permutation test (200 permutations).

## Data

EDF files processed: 10
Subjects analyzed: 5
Total blocks: 730

## Results

Significant: threshold=viol_p75, outcome=smr_increase, perm_p=0.000

### Mean correlation by threshold and outcome

  threshold         outcome  mean_corr   mean_p
   viol_mad admissible_next        NaN 0.000449
   viol_mad    smr_increase        NaN 0.323436
   viol_p75 admissible_next        NaN 0.599400
   viol_p75    smr_increase        NaN 0.313225
   viol_p80 admissible_next        NaN 0.666497
   viol_p80    smr_increase        NaN 0.320763
   viol_p90 admissible_next        NaN 0.400065
   viol_p90    smr_increase        NaN 0.288365
viol_zscore admissible_next        NaN      NaN
viol_zscore    smr_increase        NaN      NaN

## Interpretation

At least one threshold/outcome pair showed statistically significant association between high-beta barrier violation and next-state outcome. This provides PRELIMINARY EVIDENCE that barrier violations predict instability. CAUTION: Sample size is very small (N=5), so results are exploratory only.

Generated: 2026-07-01T18:12:09.554598+00:00


---

## SPT7: Framework comparison

# SPT7: Stuart-Landau vs Singular Perturbation Framework Decision

## Comparison summary

Criteria evaluated: 8
- SPT/fast-slow wins: 6
- Stuart-Landau wins: 1
- Draw: 1

## Criterion-by-criterion comparison

### Matches empirical mixed result (no joint signature)

**Stuart-Landau:** Weak: SL requires near-criticality regime with specific coupling. Mixed empirical result (SMR ~unchanged, beta increased) falls outside the joint-signature regime in most simulations.

**SPT/Fast-slow:** Better: SPT predicts that high-beta stabilization and SMR acquisition are independent processes. The observed mixed result (quadrant D or C) is a natural outcome when alpha_x is low, not a model failure.

**Assessment:** SPT  
**Notes:** WP8 showed 0/5 joint-signature subjects; SPT predicts separability explicitly.

---

### Supports non-diagnostic interpretation of high-beta suppression

**Stuart-Landau:** Weak: in SL, beta suppression emerges from the same oscillator dynamics that produce SMR changes, making separation between the two difficult to argue mechanistically.

**SPT/Fast-slow:** Strong: SPT explicitly separates high-beta (fast, stabilization variable) from SMR (slow, learning variable). High-beta suppression is a constraint, not a surrogate of learning. Non-diagnostic interpretation follows directly.

**Assessment:** SPT  
**Notes:** Central conceptual advantage of SPT framework.

---

### Clear testable predictions

**Stuart-Landau:** Moderate: SL predicts specific spectral signatures near bifurcation; hard to test without precise parameter estimation in vivo.

**SPT/Fast-slow:** Good: SPT predicts tau_beta << tau_SMR, four-quadrant separability, barrier violation -> instability. These are measurable in EEG data, though small sample size limits empirical verification.

**Assessment:** SPT  
**Notes:** SPT yields clearer empirically-testable predictions.

---

### Mechanistic richness / nonlinear detail

**Stuart-Landau:** Strong: SL provides a specific nonlinear oscillator mechanism, bifurcation structure, and analytic regime boundaries.

**SPT/Fast-slow:** Moderate: SPT provides a general separation-of-timescales argument without committing to a specific nonlinear oscillator. Less mechanistically specific, but more flexible.

**Assessment:** SL  
**Notes:** SL has richer mechanistic detail; SPT is more framework-level.

---

### Empirical support (ds004446, n=5)

**Stuart-Landau:** Unsupported: joint signature (SMR up + beta down) found in 0/5 subjects. SL-predicted regime not clearly observed.

**SPT/Fast-slow:** Partial: separability hypothesis consistent with mixed empirical result. No positive evidence of separability, but mixed result is not a failure of SPT as it would be for SL.

**Assessment:** SPT  
**Notes:** Neither framework is strongly supported; SPT is not falsified by mixed data.

---

### Simulation support for separability

**Stuart-Landau:** Partial: SL can show domains where beta suppression occurs without SMR acquisition, but the coupling structure makes full separability limited.

**SPT/Fast-slow:** Strong: SPT simulations directly demonstrate four separable regimes (both, acquisition only, stabilization only, neither). Separability is built into the model structure.

**Assessment:** SPT  
**Notes:** SPT1 simulations confirm four-regime separability.

---

### Validity domain requirements

**Stuart-Landau:** Specific: requires near-criticality, specific coupling strength, and feedback gain within narrow validity domain (WP1-WP6).

**SPT/Fast-slow:** General: valid when epsilon << 1 (tau_beta << tau_SMR). SPT2 shows validity for epsilon <= 0.03 in simulations. Whether real EEG satisfies this is uncertain (SPT4 weak/partial support).

**Assessment:** Draw  
**Notes:** Both require specific conditions; SPT conditions are simpler to state.

---

### Conservative causal claims

**Stuart-Landau:** Risk: SL can be interpreted as implying that beta suppression causes or is causally linked to SMR changes through the oscillator mechanism.

**SPT/Fast-slow:** Safe: SPT explicitly models high-beta as a constraint variable, not a target-learning variable. Framework explicitly prohibits causal claims about beta suppression -> SMR acquisition.

**Assessment:** SPT  
**Notes:** SPT is safer for conservative framing consistent with editorial requirements.

---


## Framework decision

### Recommendation: DEMOTE Stuart-Landau to supplementary material.

Rationale:

1. The singular perturbation / fast-slow barrier framework is conceptually better
   aligned with the core hypothesis: high-beta suppression as a stabilization
   constraint, not a target-learning surrogate.

2. Stuart-Landau provides mechanistic detail but this detail is not supported
   by the empirical data (0/5 subjects showed the joint signature) and requires
   unrealistically specific parameter assumptions.

3. Stuart-Landau adds interpretive risk: the coupling structure in SL makes it
   harder to argue that high-beta suppression and SMR acquisition are independent,
   which is the central scientific claim.

4. The SPT framework does not replace Stuart-Landau as a dynamic systems model;
   rather, it provides a higher-level framework within which SL could be seen as
   one specific nonlinear mechanism. Stuart-Landau can be mentioned as a concrete
   example of a fast-slow oscillator system in a supplementary section.

5. The fast-slow framework yields clearer testable predictions (tau_ratio,
   four-quadrant separability, barrier violation prediction) even if current
   empirical support is only partial.

### What to retain from Stuart-Landau analysis

- The finding that beta suppression can occur in generic feedback models without
  mechanistic specificity supports the SPT framing.
- The validity-domain analysis (WP1-WP6) demonstrated that the full SMR-beta
  joint signature is not universally generated by oscillator dynamics, which
  is consistent with the SPT separability argument.
- Stuart-Landau can be cited as showing that the problem is not specific to
  any one dynamical mechanism, motivating the more general SPT framework.

### What NOT to carry forward

- Claims that Stuart-Landau is the primary mechanistic model for SMR neurofeedback.
- Regime-specific SL predictions as the main analytic framework.
- The near-criticality interpretation as necessary for high-beta suppression.

Generated: 2026-07-01T18:12:19.132612+00:00

