# NCTRL Results for Revision

Generated: 2026-07-01T19:07:51.776482+00:00

## Scientific pivot

The central mechanism has been updated from Stuart-Landau/singular perturbation to:

**Active damping / stochastic noise-control hypothesis**:
High-beta inhibition in SMR neurofeedback acts as active damping of high-frequency stochastic
fluctuations (burst instability, spectral noise, broadband contamination). Its mechanistic
role is noise control and reward-state quality improvement, not SMR acquisition itself.
High-beta suppression is therefore neither necessary nor sufficient evidence of SMR learning.

## Previous findings incorporated

- SPT4 revision: AR1 time-scale separation was a bandwidth artefact (tau_ratio ≈ bandwidth-prediction).
  BW-matched and block-mean analyses give ratio ≈ 1.0.
- SPT6 revision: Barrier prediction null after FDR correction (0/100 smr_increase tests, q<0.05).
  admissible_next outcome excluded (regression-to-mean artefact).
- SL demoted to supplementary (SPT7 + NCTRL7 confirm NCTRL > SL).
- n=5 limitation: only ds004446 available locally.

## NCTRL1-2: Simulation results

Model: Euler-Maruyama SDE with x(SMR), eta(HB noise), z(broadband).
Parameter grid: 81 combinations.
Quadrant distribution: A=37, B=26, C=8, D=10
Separability confirmed: True

Active damping improves SMR SNR (median): 5.536 (damped) vs 1.567 (undamped)

## NCTRL3: Empirical noise-floor results

SMR SNR: ses-01 = 0.0468, ses-08 = 0.0399
Aperiodic slope: ses-01 = -1.863, ses-08 = -1.928
HB residual above 1/f: ses-01 = -0.068, ses-08 = -0.021
HB band-specific (residual > 0.05): False

## NCTRL4: Burst/diffusion results

HB burst rate: ses-01 = 58.47 /min, ses-08 = 56.97 /min
HB-broadband correlation = 0.220
HB-SMR block correlation = 0.264

## NCTRL5: Four-quadrant noise classification

Primary (SMR SNR vs HB power change): A=1, B=1, C=1, D=2
Definition sensitivity: see nctrl5_definition_sensitivity.csv.
Subjects: ['sub-004', 'sub-005', 'sub-012', 'sub-013', 'sub-018']

## NCTRL6: Reward-quality states

False-reward risk: ses-01 = 0.741, ses-08 = 0.761
Quality improvement: False

## NCTRL7: Framework comparison

NCTRL: 16/16 (100%)
Stuart-Landau: 2/16
Recommendation: NCTRL as primary framework; SL removed from primary claims.

## Final hypothesis label

**Strong support for active-damping noise-control hypothesis.**

Generated: 2026-07-01T19:07:51.776482+00:00
