# SPT Submission Readiness Assessment

Generated: 2026-07-01T18:19:08.198227+00:00

## Hypothesis label

**Partial support for fast–slow barrier hypothesis.**

## Checklist: Figures

- [x] `outputs/figures/spt1_fast_slow_model_schematic.pdf/svg/png`
- [x] `outputs/figures/spt1_time_scale_separation_examples.pdf/svg/png`
- [x] `outputs/figures/spt1_four_regime_simulation_map.pdf/svg/png`
- [x] `outputs/figures/spt2_tau_ratio_vs_epsilon.pdf/svg/png`
- [x] `outputs/figures/spt2_boundary_layer_error.pdf/svg/png`
- [x] `outputs/figures/spt3_barrier_state_space.pdf/svg/png`
- [x] `outputs/figures/spt3_transition_probability_panel.pdf/svg/png`
- [x] `outputs/figures/spt4_empirical_timescale_panel.pdf/svg/png`
- [x] `outputs/figures/spt4_tau_beta_vs_tau_smr.pdf/svg/png`
- [x] `outputs/figures/spt5_four_quadrant_panel.pdf/svg/png`
- [x] `outputs/figures/spt5_artifact_aware_panel.pdf/svg/png`
- [x] `outputs/figures/spt6_prediction_effects.pdf/svg/png`
- [x] `outputs/figures/spt6_threshold_sensitivity.pdf/svg/png`
- [x] `outputs/figures/spt8_figure_1_fast_slow_model.pdf/svg/png`
- [x] `outputs/figures/spt8_figure_2_separability_simulation.pdf/svg/png`
- [x] `outputs/figures/spt8_figure_3_timescale_separation.pdf/svg/png`
- [x] `outputs/figures/spt8_figure_4_four_quadrant_empirical.pdf/svg/png`
- [x] `outputs/figures/spt8_figure_5_barrier_prediction.pdf/svg/png`
- [x] `outputs/figures/spt8_figure_6_framework_comparison.pdf/svg/png`

## Checklist: Tables

- [x] `outputs/tables/spt1_parameter_grid.csv`
- [x] `outputs/tables/spt1_simulation_summary.csv`
- [x] `outputs/tables/spt2_timescale_metrics.csv`
- [x] `outputs/tables/spt2_manifold_error.csv`
- [x] `outputs/tables/spt3_barrier_metrics.csv`
- [x] `outputs/tables/spt3_transition_probabilities.csv`
- [x] `outputs/tables/spt4_empirical_timescale_features.csv`
- [x] `outputs/tables/spt4_empirical_tau_ratios.csv`
- [x] `outputs/tables/spt5_four_quadrant_classification.csv`
- [x] `outputs/tables/spt5_artifact_aware_classification.csv`
- [x] `outputs/tables/spt6_barrier_prediction_models.csv`
- [x] `outputs/tables/spt6_threshold_sensitivity.csv`
- [x] `outputs/tables/spt7_framework_comparison.csv`

## Checklist: Reports

- [x] `outputs/reports/spt1_results.md`
- [x] `outputs/reports/spt2_results.md`
- [x] `outputs/reports/spt3_results.md`
- [x] `outputs/reports/spt4_results.md`
- [x] `outputs/reports/spt5_results.md`
- [x] `outputs/reports/spt6_results.md`
- [x] `outputs/reports/spt7_framework_decision.md`
- [x] `outputs/reports/spt8_figure_notes.md`
- [x] `outputs/reports/spt_results_for_revision.md`
- [x] `outputs/reports/spt_claims_supported_vs_unsupported.md`
- [x] `outputs/reports/spt_hypothesis_assessment.md`

## Readiness summary (REVISED 2026-07-01)

### Methodological revisions applied

1. **SPT4 (tau analysis)**: Bandwidth confound identified and quantified.
   Primary AR1 tau_ratio (0.10) matches bandwidth-predicted ratio (0.09) exactly.
   BW-matched and block-mean controls give ratio ≈ 1.0. Empirical time-scale separation
   claim retracted; result is inconclusive.

2. **SPT6 (barrier prediction)**: Two flaws fixed — block-mean thresholds replace
   raw-envelope thresholds; admissible_next excluded (regression artefact).
   After FDR correction: 0/100 smr_increase tests significant. Honest null result stated.

3. **SL demotion**: Stuart-Landau model formally demoted to supplementary (SPT7).

4. **n=5 limitation**: No additional datasets available locally. Cannot expand.
   All analyses use 5 subjects (ds004446), ses-01 and ses-08 only.

5. **New outputs added**: spt4_tau_bandwidth_control.csv, spt4_bandwidth_control figures,
   spt4_empirical_timescale_panel (revised), spt6_nonzero_viol_summary.csv,
   spt6_effect_size_forest figures, spt6_barrier_prediction_panel (revised).

### Honest hypothesis label (revised)

**Simulation-supported, empirically inconclusive fast–slow barrier hypothesis.**

### Strengths

1. Fast-slow model fully implemented; four separable regimes confirmed (SPT1).
2. SPT validity analytically characterised (SPT2).
3. Barrier constraint simulation complete and numerically stable (SPT3).
4. Framework comparison with SL: SPT wins 5/8 criteria; clear recommendation (SPT7).
5. Figure set covers all six required manuscript candidates (SPT8).
6. **Null results are reported honestly** — the bandwidth confound and FDR-null barrier
   prediction are explicitly stated and not concealed.
7. Four-quadrant separability (SPT5) provides the strongest empirical finding (2B, 3C).

### Weaknesses that must be acknowledged in manuscript

1. n = 5 subjects; all empirical results are descriptive and underpowered.
2. Empirical time-scale separation is confounded by bandwidth (NOT a confirmed finding).
3. Barrier prediction is null after FDR correction (NOT a confirmed finding).
4. Only 2 sessions per subject (ses-01 and ses-08); within-session learning dynamics
   cannot be characterised.

### Recommended manuscript framing

The paper should present:
- The SPT/fast–slow model as the theoretical contribution (SPT1–SPT3).
- The four-quadrant dissociation (SPT5) as the primary empirical result.
- The tau and barrier analyses as negative/inconclusive results, clearly flagged.
- SL as a supplementary comparison only.
- The non-diagnostic framing of high-beta suppression as the clinical contribution.

Generated: 2026-07-01 (revised)

### Limitations

1. Empirical data sample (n=5) is too small for definitive tests (SPT4-SPT6).
2. Barrier violation prediction in real EEG is likely underpowered.
3. Empirical time-scale separation is not confirmed (only consistent with).
4. No new data downloaded; analysis relies on existing ds004446 subset.

### Recommended actions before submission

1. State clearly in manuscript that empirical tests in SPT4-SPT6 are exploratory,
   not confirmatory, given n=5.
2. Use simulation results (SPT1-SPT3) as primary support for the framework.
3. Present empirical results as "consistent with but not confirming" the framework.
4. Do not overstate empirical support for the barrier prediction (SPT6).
5. Retain Stuart-Landau only in supplementary material (SPT7 recommendation).

Generated: 2026-07-01T18:19:08.198227+00:00
