# NCTRL Claims: Supported vs Unsupported [REVISED AFTER AUDIT]

Original generated: 2026-07-01T19:07:51.776482+00:00
Audit revision applied: see nctrl_audit_report.md

---

## NCTRL1: Active damping separates noise control from SMR acquisition (simulation)

**Status: SUPPORTED BY SIMULATION** *(unchanged)*

Parameter grid (81 combinations) produces all 4 quadrants.
B (acq without damp): 26 | C (damp without acq): 8 | Separability: True

CAVEAT: noise_damped flag in simulation summary (nctrl1_simulation_summary.csv) is incorrectly False
for R1_damp_only and R3_both regimes. Broadband contamination variable (z) contributes zero power
in 5/6 regimes. The broadband noise-control claim is not demonstrated in the simulation output.

---

## NCTRL2: Active damping improves SMR SNR independently (simulation)

**Status: SUPPORTED BY SIMULATION** *(unchanged)*

Damped SNR: 5.536 | Undamped: 1.567
This result holds within the model by construction (eta drives x; damping eta stabilises x).

---

## NCTRL3: Real EEG shows informative noise-floor/SNR structure

**Status: PARTIAL/NEGATIVE [REVISED]**

SMR SNR change (ses-01→ses-08): improves in 2/5 subjects only.
HB residual above 1/f (mean over all subjects/sessions): NEGATIVE (−0.059).
HB modulation is broadband in character in 3/5 subjects; weakly band-specific in sub-004 and sub-013.
Band-specific HB (mean > 0): False for the dataset as a whole.

---

## NCTRL4: HB bursts track broadband noise (noise-control interpretation)

**Status: CONTRADICTED for direction; INCONCLUSIVE for broadband [REVISED]**

HB-broadband corr = 0.220 (positive; consistent with burst-as-noise interpretation in some subjects).
HB-SMR block corr = +0.264 (POSITIVE). This CONTRADICTS the noise-control prediction that HB bursts
suppress SMR. Positive correlation is more consistent with shared arousal/amplitude covariation.
Burst occupancy = 0.25 for ALL rows (fixed by 75th-percentile threshold; carries zero information).

---

## NCTRL5: Empirical separability of SMR acquisition and noise damping

**Status: DEFINITION-SENSITIVE; SINGLE-SUBJECT QUADRANTS [REVISED]**

Primary: A=1, B=1, C=1, D=2 (each non-D quadrant driven by exactly 1 subject).
Agreement across 4 metric definitions: mean 0.56 (range 0.25–1.00 per subject).
No subject is consistently classified as A_both across all definitions.
sub-012 is most robustly C_damp_only (3/4 definitions). sub-013 is most robustly B_acq_only (3/4 def).
Empirically suggestive of separability but not robust.

---

## NCTRL6: HB inhibition improves reward-state quality

**Status: NOT APPLICABLE — PROXY ANALYSIS IS CIRCULAR [REVISED]**

ds004446 contains NO real-time neurofeedback reward markers. States are defined by session-median
thresholds on SMR and HB envelopes → total_reward_frac ≈ 0.50 by arithmetic construction.
False-reward risk (mean 0.74) is a ceiling artifact of the thresholding method, not a real finding.
NCTRL6 results CANNOT be cited as evidence for or against the hypothesis.

---

## NCTRL7: NCTRL framework stronger than SL and SPT

**Status: ILLUSTRATIVE ONLY; NOT INDEPENDENT EVIDENCE [REVISED]**

NCTRL: 16/16 | SL: 2/16
A perfect 16/16 score indicates criteria were designed to match NCTRL features.
"Handles broadband contamination" (scored 2/2) is based on model structure, not empirical validation.
"Empirical fit" (scored 2/2) is inconsistent with negative HB residuals and positive HB-SMR correlation.
Use NCTRL7 as a conceptual/theoretical argument only.

---

## Claims that MUST NOT be made [EXTENDED BY AUDIT]

- High-beta suppression causes SMR acquisition.
- High-beta suppression is necessary for SMR acquisition.
- High-beta suppression is sufficient evidence of SMR acquisition.
- HB bursts suppress SMR at block level (empirical correlation is POSITIVE, not negative).
- HB modulation is band-specific (empirical HB residuals are mostly negative).
- Simulation results constitute empirical proof.
- The n=5 descriptive results are statistically confirmed.
- NCTRL6 provides evidence about reward quality (proxy, circular thresholds).
- NCTRL7 is an independent validation of the framework (criteria circular).
- The four-quadrant classification is robust (it is highly definition-sensitive).
- Stuart-Landau is the primary mechanism.
- Empirical time-scale separation holds (bandwidth confound: SPT4 revision).
- Barrier violations predict SMR outcomes (null result: SPT6 revision).

---

## Approved claims

- The active-damping SDE model demonstrates mechanistic separability of HB noise reduction and
  SMR acquisition within the simulation (B=26, C=8 in 81-point parameter grid).
- Within the simulation, higher damping gain (k_damp) improves SMR SNR independently of SMR drive (a_x).
- In ds004446 (n=5), HB power changes are predominantly broadband in character (HB residual above 1/f
  is negative for most subjects and sessions).
- Subject-level quadrant classification (ses-01 vs ses-08) suggests heterogeneous outcomes: some subjects
  show HB reduction without SMR SNR improvement (C_damp_only), others the reverse (B_acq_only).
  This pattern is suggestive of separability but depends on the metric used.
- The NCTRL theoretical framework provides a more complete set of empirically testable predictions
  than Stuart-Landau or singular perturbation theory (conceptual argument).

Revision generated: see nctrl_audit_report.md
