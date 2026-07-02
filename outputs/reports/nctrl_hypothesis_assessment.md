# NCTRL Hypothesis Assessment

Generated: 2026-07-01T19:07:51.774485+00:00

## Central hypothesis

In SMR neurofeedback, high-beta inhibition functions as active damping of high-frequency
stochastic fluctuations. Its role is to reduce fast spectral contamination, burst instability,
and reward-shortcut states around the sensorimotor feedback signal. High-beta suppression is
neither necessary nor sufficient evidence of SMR acquisition, but it may improve feedback-state
quality by reducing high-frequency noise and improving SMR signal-to-noise structure.

## Assessment by question

### Q1. Do simulations support active damping as a high-frequency noise-control mechanism?

**Result: YES**

NCTRL1 parameter grid (81 simulations) shows:
- Regime B (SMR acquisition without noise damping): 26 (32%)
- Regime C (noise damping without SMR acquisition): 8 (10%)
Active damping (k_damp) controls high-frequency variance and burst occupancy independently of
SMR acquisition (a_x). Separability is confirmed.

### Q2. Does active damping improve signal quality independently of SMR acquisition?

**Result: YES**

Simulation median SMR SNR:
- Noise-damped regime: 5.536
- Non-damped regime:   1.567
Active damping improves SMR SNR even in cases where SMR acquisition does not occur.

### Q3. Do real EEG data show HB changes as band-specific or broadband/noise-floor related?

**Result: BROADBAND (not band-specific) [AUDIT REVISED]**

Mean HB residual above 1/f (all subjects, all sessions, mean channel): −0.059.
Median is negative. Only 2/5 subjects show consistently positive HB residuals (sub-004, sub-013 in some sessions).
3/5 subjects show negative HB residuals throughout. HB modulation is primarily broadband/noise-floor in character.
Aperiodic slope changes are near zero (mean Δ = −0.065). 1/f slope shifts do not explain HB changes.

Note: the original "INCONCLUSIVE / BROADBAND" framing underestimated the negative-residual finding.

### Q4. Do real EEG data show target acquisition and noise damping are separable?

**Result: YES (descriptive, n=5)**

Empirical four-quadrant classification (primary: SMR SNR vs HB power change):
A (both): 1 | B (acq only): 1 | C (damp only): 1 | D (neither): 2
Quadrant B and/or C are populated, showing that target acquisition and noise damping are empirically separable at the subject level.
Subjects: ['sub-004', 'sub-005', 'sub-012', 'sub-013', 'sub-018']
NOTE: n=5 descriptive only.

### Q5. Do burst/noise/diffusion metrics support the noise-control interpretation?

**Result: CONTRADICTED for direction; INCONCLUSIVE for broadband coupling [AUDIT REVISED]**

Mean HB-broadband envelope correlation: 0.220 (positive; consistent with burst-as-noise in some subjects).
However, mean HB-SMR block correlation = 0.264 > 0. HB and SMR are POSITIVELY correlated at block level.
This CONTRADICTS the noise-control prediction (HB bursts should suppress SMR during blocks).
Burst occupancy = 0.25 for every subject/session (fixed by 75th-percentile threshold construction; carries no information).
HB burst rate: ses-01 = 58.5 /min, ses-08 = 57.0 /min (minimal change, 3/5 subjects reduce).

### Q6. Is the NCTRL framework stronger than Stuart-Landau and SPT?

**Result: CONCEPTUALLY YES; EVIDENTIALLY NOT INDEPENDENT [AUDIT REVISED]**

Framework comparison scores: NCTRL 16/16 (100%), Stuart-Landau 2/16.
However: a perfect 16/16 score indicates circular criterion design. The 8 criteria were chosen after
formulating NCTRL to include features unique to NCTRL (broadband z variable, burst dynamics, separability).
NCTRL7 is useful for illustrating the theoretical advantage of the NCTRL framing but provides no
independent empirical evidence. The comparison is ILLUSTRATIVE, not EVIDENTIAL.

### Q7. Which claims are supported? [AUDIT REVISED]

- Active damping mechanistically reduces HB variance/burstiness in simulation: **SUPPORTED BY SIMULATION**
- Active damping improves SMR SNR without SMR acquisition in simulation: **SUPPORTED BY SIMULATION**
- Real EEG separability under primary definition (n=5, descriptive): **PRESENT BUT DEFINITION-SENSITIVE**
  (Each key quadrant A/B/C occupied by exactly 1 subject; assignment flips across metric definitions)
- NCTRL as a richer theoretical framework than SL: **CONCEPTUAL ARGUMENT ONLY** (criteria circular)
- HB inhibition improves reward-state quality: **NOT SUPPORTED** (proxy analysis, circular thresholds)

### Q8. Which claims remain unsupported? [AUDIT REVISED]

- Causal claim that HB inhibition causes SMR acquisition: **NOT SUPPORTED**
- Statistical confirmation from n=5 empirical data: **NOT POSSIBLE**
- Band-specific HB (HB above 1/f noise floor): **NOT SUPPORTED** (negative mean residual, 3/5 subjects)
- HB suppression of SMR at block level: **CONTRADICTED** (positive HB-SMR correlation)
- Robust four-quadrant separability: **NOT SUPPORTED** (definition-sensitive, single-subject quadrants)
- Reward-quality evidence: **NOT APPLICABLE** (proxy circular thresholds, no real reward markers)
- Direct barrier-prediction: **NULL RESULT** (SPT6 revision)
- Empirical time-scale separation: **INCONCLUSIVE** (SPT4 revision)

### Q9. Which claims must be avoided? [AUDIT REVISED]

- High-beta suppression causes or produces SMR acquisition.
- High-beta suppression is necessary for SMR acquisition.
- High-beta suppression is sufficient evidence of SMR acquisition.
- HB bursts suppress SMR at block level (empirical correlation is positive, not negative).
- HB modulation is band-specific (empirical residuals are mostly negative).
- The four-quadrant classification is robust (it is definition-dependent).
- NCTRL6 provides evidence about reward quality (proxy thresholds, circular construction).
- NCTRL7 framework comparison is independent evidence (criteria chosen post-hoc).
- Simulation results constitute empirical proof.

## Final conclusion [REVISED AFTER AUDIT]

**Simulation support only; empirical support insufficient.**

*Original label "Strong support" was produced by nctrl_final_reports.py and has been revised
downward after critical audit (nctrl_audit.py). See outputs/reports/nctrl_audit_report.md
and outputs/reports/nctrl_revised_hypothesis_label.md.*

**Conservative criteria passed: 2/7**
- C6 (simulation separability): PASS — B=26, C=8 in 81-point grid
- C3 (not entirely single-subject): PASS — A_both appears in ≥2 definitions across subjects

**All empirical criteria failed:**
- C1: HB residual mean < 0; SNR improves in only 2/5 subjects
- C2: Quadrant assignment flips across definitions; mean agreement = 0.56
- C4: Reward analysis uses circular median thresholds (not real reward markers)
- C5: Framework comparison scores 16/16 (criteria designed post-hoc)
- C7: HB-SMR block correlation positive (wrong direction for suppression narrative)

**What the data actually show (n=5, ses-01 vs ses-08, ds004446):**
- HB power changes are predominantly broadband in character, not band-specific.
- SMR SNR does not improve consistently (2/5 subjects).
- HB and SMR block-mean amplitudes are positively, not negatively, correlated.
- Subject quadrant assignments are definition-sensitive; single-subject quadrants.
- No real neurofeedback reward markers exist in this dataset.

Generated: 2026-07-01T19:07:51.774485+00:00
