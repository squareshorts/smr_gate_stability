# NCTRL Submission Readiness Assessment [REVISED AFTER AUDIT]

Original generated: 2026-07-01T19:07:51.777481+00:00
Audit revision applied: see nctrl_audit_report.md

## Hypothesis label [REVISED]

**Simulation support only; empirical support insufficient.**

*Original label "Strong support" has been revised downward by critical audit (code/nctrl_audit.py).*
*Conservative criteria passed: 2/7.*

## Scripts

| Script | Purpose |
|---|---|
| simulations/nctrl1_active_damping_model.py | NCTRL1+2 simulation |
| empirical/nctrl3_noise_floor_analysis.py | NCTRL3 PSD + noise floor |
| empirical/nctrl4_burst_instability.py | NCTRL4 bursts + diffusion |
| empirical/nctrl5_four_quadrant_noise.py | NCTRL5 classification |
| empirical/nctrl6_reward_quality.py | NCTRL6 reward states |
| code/nctrl7_framework_comparison.py | NCTRL7 framework comparison |
| code/nctrl8_figures.py | NCTRL8 figure assembly |
| code/nctrl_final_reports.py | Final reports + manifest |

## Checklist: Tables

- [x] nctrl1_parameter_grid.csv
- [x] nctrl1_simulation_summary.csv
- [x] nctrl2_noise_control_metrics.csv
- [x] nctrl3_empirical_noise_features.csv
- [x] nctrl3_spectral_slope_features.csv
- [x] nctrl4_burst_instability_features.csv
- [x] nctrl4_diffusion_features.csv
- [x] nctrl5_four_quadrant_noise_classification.csv
- [x] nctrl5_definition_sensitivity.csv
- [x] nctrl6_reward_quality_states.csv
- [x] nctrl6_state_transition_probabilities.csv
- [x] nctrl7_framework_comparison.csv

## Checklist: Figures

- [x] nctrl1_active_damping_model_schematic.*
- [x] nctrl1_noise_damping_examples.*
- [x] nctrl1_four_regime_map.*
- [x] nctrl2_damping_vs_noise_floor.*
- [x] nctrl2_damping_vs_diffusion.*
- [x] nctrl2_smr_snr_vs_damping.*
- [x] nctrl3_psd_noise_floor_panel.*
- [x] nctrl3_smr_snr_panel.*
- [x] nctrl4_burst_noise_relationship.*
- [x] nctrl4_state_diffusion_panel.*
- [x] nctrl5_four_quadrant_noise_panel.*
- [x] nctrl5_definition_sensitivity_panel.*
- [x] nctrl6_reward_quality_state_space.*
- [x] nctrl6_state_transition_panel.*
- [x] nctrl7_framework_comparison.*
- [x] nctrl8_figure_1_active_damping_model.*
- [x] nctrl8_figure_2_separability_simulation.*
- [x] nctrl8_figure_3_noise_control_metrics.*
- [x] nctrl8_figure_4_empirical_noise_floor.*
- [x] nctrl8_figure_5_burst_diffusion.*
- [x] nctrl8_figure_6_four_quadrant_noise.*
- [x] nctrl8_figure_7_framework_comparison.*

## Checklist: Reports

- [x] nctrl1_results.md
- [x] nctrl2_results.md
- [x] nctrl3_results.md
- [x] nctrl4_results.md
- [x] nctrl5_results.md
- [x] nctrl6_results.md
- [x] nctrl7_framework_decision.md
- [x] nctrl8_figure_notes.md
- [x] nctrl_results_for_revision.md
- [x] nctrl_claims_supported_vs_unsupported.md
- [x] nctrl_hypothesis_assessment.md
- [x] nctrl_submission_readiness.md

## Critical weaknesses identified in audit

1. **n=5** subjects; all empirical results are descriptive and statistically underpowered.
2. **No real reward markers**: ds004446 has no neurofeedback reward signals; NCTRL6 uses circular proxy thresholds and must be excluded from evidence.
3. **HB is broadband, not band-specific**: Mean HB residual above 1/f is negative across the dataset. "Band-specific HB" claim is not supported.
4. **HB-SMR block correlation is positive** (+0.264 mean): contradicts the noise-suppression narrative; may reflect shared arousal.
5. **Burst occupancy is constant** (0.25) by construction of the 75th-percentile threshold: this metric carries zero session-level information.
6. **Four-quadrant result is definition-sensitive**: No subject is consistently A_both across definitions; each key quadrant is driven by exactly 1 subject.
7. **Framework comparison (NCTRL7) is circular**: NCTRL scores 16/16 on criteria designed post-hoc to match NCTRL's features. Evidential weight: illustrative only.
8. **Simulation flag inconsistency**: noise_damped=False for R1_damp_only and R3_both in nctrl1_simulation_summary.csv. Broadband z variable contributes zero contamination in 5/6 regimes.
9. **SPT null results**: tau analysis bandwidth-confounded (SPT4); barrier prediction null after FDR (SPT6).

## Recommended manuscript framing [REVISED]

- **Primary theoretical contribution**: NCTRL1-2 simulation demonstrating mechanistic separability of noise damping and SMR acquisition. Explicitly acknowledge this is model evidence, not empirical proof.
- **Primary empirical contribution**: NCTRL3-5 descriptive results (n=5, ds004446) showing heterogeneous subject outcomes and predominantly broadband HB character. Frame as hypothesis-generating, not hypothesis-confirming.
- **NCTRL6**: Exclude from evidence section. Mention in limitations only: no real reward markers available.
- **NCTRL7**: Use in Discussion as conceptual/theoretical motivation, clearly labelled as illustrative.
- **Central claim**: High-beta inhibition in SMR neurofeedback may serve a noise-control function (broadband amplitude reduction rather than band-specific suppression). This is supported by simulation and is consistent with (but not proven by) descriptive EEG findings in n=5.
- **Do not claim**: empirical confirmation, robust separability, or reward-quality improvement.
3. HB band-specificity vs broadband: mixed evidence (residual-above-1/f analysis inconclusive).
4. SPT4 and SPT6 were null/inconclusive after methodological correction.
5. NCTRL framework superiority is from conceptual scoring, not from direct empirical tests.

## Recommended manuscript framing

- Primary theoretical contribution: NCTRL1-2 (simulation, separability, SNR improvement).
- Primary empirical result: NCTRL5 (four-quadrant classification, n=5 descriptive).
- Supporting empirical: NCTRL3-4 (noise floor, burst metrics, broadband correlation).
- Reward-state analysis (NCTRL6): proxy only; report honestly.
- Framework comparison (NCTRL7): use to motivate NCTRL over SL and SPT.
- Stuart-Landau: remove from primary claims.
- Singular perturbation: retain as mechanistic motivation only; not empirically supported.
- Central claim: high-beta inhibition as noise control may improve SMR feedback state quality
  without directly producing SMR acquisition.

Generated: 2026-07-01T19:07:51.777481+00:00
