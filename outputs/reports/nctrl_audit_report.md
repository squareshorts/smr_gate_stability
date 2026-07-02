# NCTRL Audit Report

**Purpose**: Critical audit of the "Strong support" hypothesis label. Do not defend the hypothesis; try to falsify or narrow it.

Generated: 2026-07-01T19:48:51.544662+00:00

---

## Summary

**Original label (NCTRL_final_reports.py)**: Strong support for active-damping noise-control hypothesis.

**Revised label (this audit)**: Simulation support only; empirical support insufficient.

**Conservative criteria passed**: 2/7

---

## Issues found (25 total)

- SIM-BUG-1: R1_damp_only has noise_damped=False in summary. Regime labeling is inconsistent with noise_damped flag.
- SIM-BUG-2: R3_both has noise_damped=False in summary. The 'both' regime should have noise_damped=True by definition.
- SIM-BUG-3: broadband_contam=0 for 5/6 regimes. Broadband variable z has negligible effect in most regimes; noise-control claim for broadband contamination is not demonstrated.
- SIM-INFO: Median SMR SNR by k_damp: {0.0: 1.6128323620811973, 2.0: 3.086000923446784, 8.0: 6.79953634864316}
- EMP-HB-1: Mean HB residual above 1/f = -0.0442 < 0. HB power is BELOW the 1/f aperiodic line on average. HB modulation is consistent with broadband/1/f changes, not band-specific. This directly undermines 'band-specific HB' claim.
- EMP-HB-3: Only 30% of observations show positive HB residual. Majority of HB observations are below or at the 1/f noise floor.
- EMP-SNR-1: SMR SNR improves in only 1/5 subjects. No consistent SMR SNR improvement across ses-01 → ses-08.
- EMP-SLOPE-1: Mean 1/f slope change = -0.0650 (near zero). No consistent 1/f steepening across sessions. Aperiodic changes cannot explain HB changes.
- BURST-ARTIFACT-1: hb_burst_occupancy = 0.25 for ALL subjects/sessions/conditions. Burst threshold is the 75th percentile → burst occupancy is 25% by construction. This metric contains NO information about session differences.
- BURST-DIRECTION-1: Mean HB-SMR block correlation = 0.264 > 0. HB and SMR are POSITIVELY correlated at block level. This CONTRADICTS the noise-control hypothesis (HB bursts should suppress SMR). HB and SMR may co-vary due to shared arousal/attention rather than noise suppression.
- BURST-SUBJECTVAR-1: HB-broadband correlation varies strongly across subjects (range 0.10–0.37). Noise-floor interpretation is subject-specific, not general.
- QUAD-ROBUST-1: Subjects occupy on average 2.4 different quadrants across definitions (max=4). Quadrant assignment is highly definition-sensitive. Cannot claim robust separability from this evidence.
- QUAD-ROBUST-2: No subject has the same quadrant across all 4 definitions. Separability result is entirely definition-dependent.
- QUAD-ROBUST-3: No subject has A_both (successful damping+acquisition) as their modal quadrant. At best A_both appears for 1 subject in 1 definition.
- QUAD-INFLUENCE: Quadrant A_both is driven by single subject: sub-005. Loss of one subject would eliminate this quadrant from results.
- QUAD-INFLUENCE: Quadrant B_acq_only is driven by single subject: sub-013. Loss of one subject would eliminate this quadrant from results.
- QUAD-INFLUENCE: Quadrant C_damp_only is driven by single subject: sub-012. Loss of one subject would eliminate this quadrant from results.
- REWARD-PROXY-1: ds004446 event markers (instruction: rest/task/interval) are NOT real-time neurofeedback reward signals. States (clean_target/noisy_target etc.) are defined by session-median thresholds on SMR and HB envelopes. This is a circular proxy: the 'reward' state is defined as being above/below the session median, which is guaranteed to give ~50% total_reward_frac by construction. NCTRL6 results provide NO evidence about actual neurofeedback reward quality.
- REWARD-RISK-1: Mean false_reward_risk = 0.75. Over 60% of 'reward' states are 'noisy_target' (SMR up AND HB up). This is a ceiling effect of the proxy definition, not a real finding. With median thresholds, ~50% of target-state blocks will have elevated HB.
- CIRC-1: NCTRL receives maximum score (16/16) on all 8 criteria. A framework that scores 2/2 on EVERY criterion is almost certainly the result of criteria designed after seeing NCTRL outputs. Perfect scores indicate circular reasoning, not independent validation.
- CIRC-2: NCTRL scores 2/2 on 'Broadband handling'. Empirical evidence for this criterion is weak (negative HB residuals, constant burst occupancy by construction). This score reflects the theoretical framework's claims, not the empirical evidence.
- CIRC-2: NCTRL scores 2/2 on 'Burst handling'. Empirical evidence for this criterion is weak (negative HB residuals, constant burst occupancy by construction). This score reflects the theoretical framework's claims, not the empirical evidence.
- CIRC-2: NCTRL scores 2/2 on 'Empirical fit'. Empirical evidence for this criterion is weak (negative HB residuals, constant burst occupancy by construction). This score reflects the theoretical framework's claims, not the empirical evidence.
- CIRC-3: NCTRL scores 2/2 on 'Empirical fit' despite: (a) HB residuals mostly negative (no band-specific HB), (b) HB-SMR positively correlated (contradicts suppression claim), (c) burst occupancy constant by construction, (d) n=5 descriptive only. Score should be 0–1.
- CIRC-GENERAL: The 8 criteria were explicitly chosen to highlight advantages of the NCTRL framework (broadband modeling, burst dynamics, separability) after NCTRL was formulated. This is criterion-by-design and inflates the NCTRL score. The framework comparison should be treated as illustrative only, not as evidence.

---

## Detailed findings by domain

### A. Simulation (NCTRL1-2)

1. **Regime-flag inconsistency**: The `noise_damped` column in `nctrl1_simulation_summary.csv` is `False` for
   R1_damp_only and R3_both — the two regimes that are supposed to demonstrate noise damping. Only R5_false_reward
   has `noise_damped=True`. This suggests the boolean criterion for "noise damped" is incorrectly implemented or
   uses a threshold that the damping regime does not meet. The parameter grid separability result (B=26, C=8)
   likely uses a different criterion than the regime summary.

2. **Broadband contamination absent**: `broadband_contam = 0.0` for 5/6 simulation regimes. The model's z variable
   (broadband contamination) contributes no meaningful power in any regime except R5_false_reward. Claims about
   active damping of broadband contamination are NOT demonstrated in the simulation.

3. **Grid separability (B=26, C=8) is real** but C_damp_only represents only 10% of
   the 81-point parameter space. Pure noise-damping without acquisition is a minority outcome. Whether the
   noise_damped flag in the grid is correct requires code inspection.

4. **SNR improvement with k_damp**: The simulation does show improved SMR SNR with higher k_damp. This is the
   strongest simulation result. However, this improvement is by model construction (eta drives x; damping eta
   improves x stability).

**Simulation verdict**: Mechanistic separability exists in the model, but (a) the simulation summary flags are
inconsistent with regime intent, and (b) broadband contamination is not actually modeled. Simulation support is
real but partial.

---

### B. Empirical HB character (NCTRL3)

1. **HB residual above 1/f** (mean channel, all subjects/sessions):
   - Mean = -0.0442
   - Median = -0.0247
   - Positive in 6/20 observations (30%)

   The mean HB residual is NEGATIVE.
   **This means HB power is below the 1/f aperiodic line on average.**
   HB changes in this dataset are primarily broadband/noise-floor in character, not band-specific.

2. **SMR SNR session change**: Improves in 1/5 subjects (ses-01→ses-08).
   Mean Δ log(SNR) = -0.0070. Not consistently positive.

3. **Subject heterogeneity**: sub-004 and sub-013 show positive HB residuals (mild band-specific HB);
   sub-005, sub-012, sub-018 show negative residuals (broadband character). No common pattern.

4. **Aperiodic slope**: Mean change = -0.0650 (near zero). No consistent
   1/f steepening across sessions. HB changes are not explained by systematic 1/f slope shifts.

---

### C. Burst/diffusion (NCTRL4)

1. **Burst occupancy by construction**: `hb_burst_occupancy = 0.25` for every row in the dataset. The 75th-percentile
   threshold guarantees 25% burst occupancy by definition. This metric is mathematically constant and contributes
   zero information about session differences or subject differences.

2. **HB-SMR block correlation direction**: Mean = 0.264.
   **HB and SMR are POSITIVELY correlated** at the block level in most subjects. This contradicts the noise-control
   prediction (HB bursts should suppress SMR during the block). The positive correlation likely reflects shared
   arousal, effort, or overall amplitude covariation.

3. **HB-broadband correlation**: Mean = 0.220, but varies widely across
   subjects (SD = 0.100). sub-005 shows high correlation
   (0.42–0.51), sub-004 shows low correlation (0.05–0.13). This is subject-specific, not a general pattern.

---

### D. Four-quadrant robustness (NCTRL5)

1. **Definition sensitivity** is high. Per subject, the mean number of different quadrant labels across 4 definitions
   is 2.4. Mean agreement = 0.65.

2. **Per-subject consistency**:
   - sub-004: primary=D_neither, burst=C_damp_only, resid=D_neither, diff=D_neither (3 of 4 = D)
   - sub-005: primary=A_both, burst=C_damp_only, resid=B_acq_only, diff=B_acq_only (all different)
   - sub-012: primary=C_damp_only, burst=C_damp_only, resid=D_neither, diff=C_damp_only (3 of 4 = C)
   - sub-013: primary=B_acq_only, burst=A_both, resid=B_acq_only, diff=B_acq_only (3 of 4 = B)
   - sub-018: primary=D_neither, burst=B_acq_only, resid=C_damp_only, diff=D_neither (2 of 4 = D)

3. **No subject is consistently in A_both** (the "success" quadrant). sub-005 is A_both only under the primary
   (SNR/HB power) definition. sub-012 is most robustly C_damp_only (3/4 defs).

4. **Single-subject quadrants**: Each of A, B, C in the primary classification is occupied by exactly 1 subject.
   The quadrant result is entirely driven by individual variation.

5. **D_neither majority**: 2/5 subjects (sub-004, sub-018) are D_neither in the primary classification. A third
   of the sample shows neither noise damping nor SMR acquisition between ses-01 and ses-08.

---

### E. Reward quality (NCTRL6)

1. **No real reward markers**: ds004446 provides only instruction labels (rest/task/interval). There are no
   real-time neurofeedback reward signals in the available data. All NCTRL6 results are based on proxy criteria.

2. **Median threshold circularity**: States are defined by session medians → total_reward_frac ≈ 0.50 by arithmetic.
   This is not a finding; it is a construction artifact. **All NCTRL6 "results" are products of the thresholding
   method, not empirical evidence.**

3. **False-reward risk** (mean = 0.75) is high, but this is also
   an artifact: with median thresholds, ~50% of "reward" blocks will have above-median HB, making them "noisy target"
   by definition. The "60–85% false-reward risk" is the expected outcome of the method, not a pathological finding.

4. **NCTRL6 cannot be cited as evidence for or against the hypothesis**. It must be removed from evidence assessment.

---

### F. Framework comparison (NCTRL7)

1. **Perfect score = circular**: NCTRL receives 16/16 (100%) across all 8 criteria. In any objective multi-framework
   comparison, a single framework scoring perfectly on all criteria almost always means the criteria were designed to
   match that framework's features. This is evidenced by criteria such as "Handles broadband contamination" and
   "Handles burst instability" — these are structural features of the NCTRL model, not empirically validated claims.

2. **Criteria chosen post-hoc**: The 8 criteria explicitly include features that are unique to NCTRL (broadband z
   variable, stochastic burst dynamics) and that SL/SPT were never designed to provide. This stacks the comparison.

3. **"Matches empirical data" = 2/2 for NCTRL despite**:
   - HB-SMR correlation being positive (contradicts model);
   - HB residuals mostly negative (contradicts band-specific claim);
   - n=5 descriptive only.
   This score is based on theoretical alignment, not empirical fit.

4. **Correct treatment**: NCTRL7 can be used to argue NCTRL is a more complete theoretical framework for generating
   hypotheses. It cannot be used as evidence that the hypothesis is supported by data. The framework comparison is
   ILLUSTRATIVE, not EVIDENTIAL.

---

## Conservative criteria assessment

- **C1_empirical_noise_metric_support**: FAIL
- **C2_quadrant_robust**: FAIL
- **C3_not_single_subject**: PASS
- **C4_reward_not_proxy**: FAIL
- **C5_framework_not_circular**: FAIL
- **C6_simulation_support**: PASS
- **C7_hb_smr_direction**: FAIL

**Criteria passed: 2/7**

---

## Revised hypothesis label

**Simulation support only; empirical support insufficient.**

### Justification

**Why not "Strong support":**
- HB residuals mostly negative → HB changes are broadband, not band-specific (fails C1)
- Four-quadrant classification is definition-sensitive, single-subject quadrants (fails C2)
- Reward analysis is proxy-only and arithmetically circular (fails C4)
- Framework comparison gives circular perfect score (fails C5)
- HB-SMR positive correlation contradicts suppression narrative (fails C7)

**Why not "Hypothesis not supported":**
- Simulation mechanistically demonstrates separability of noise damping and SMR acquisition (C6 passes)
- Some subjects show patterns consistent with noise-control (sub-012: C_damp_only in 3/4 defs)
- HB-broadband correlation positive in most subjects (weak support for burst-as-noise interpretation)

**Why "Simulation support only; empirical support insufficient":**
- All affirmative empirical criteria fail the conservative test
- The "Partial support" threshold requires both simulation AND some empirical separability;
  empirical separability is highly definition-sensitive and driven by single subjects

Generated: 2026-07-01T19:48:51.544662+00:00
