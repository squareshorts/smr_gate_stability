# SPT8 Figure Notes

Generated: 2026-07-01T18:12:30.787725+00:00

## Figure 1: Fast-slow model schematic
Source: `spt8_figure_1_fast_slow_model_source.csv`
Shows: Conceptual structure of the fast-slow closed-loop model with slow SMR variable (x),
fast high-beta variable (y), and barrier controller. Illustrative trajectories derived from
model equations, not from real EEG.

## Figure 2: Separability simulation
Source: `spt8_figure_2_separability_simulation_source.csv`
Data origin: `spt1_time_scale_separation_examples_source.csv` (SPT1 simulation)
Shows: Four mechanistic regimes demonstrating that high-beta stabilization and SMR acquisition
are independently producible in the fast-slow model. This is the core separability simulation.

## Figure 3: Timescale separation
Source: `spt8_figure_3_timescale_separation_source.csv`
Data origin: `spt2_timescale_metrics.csv`, `spt2_manifold_error.csv`
Shows: tau_beta / tau_SMR ratio as a function of epsilon, and manifold approximation error.
SPT is valid (ratio < 0.1) for epsilon <= 0.03 in simulations.

## Figure 4: Four-quadrant empirical classification
Source: `spt8_figure_4_four_quadrant_empirical_source.csv`
Data origin: `spt5_four_quadrant_classification.csv`
Shows: Classification of real subjects (ds004446, n=5) into four quadrants.
NOTE: Sample size is very small. Previous WP8 result (0/5 joint-signature subjects)
dominates this plot. Mixed/negative result is shown as-is without selective reporting.

## Figure 5: Barrier prediction
Source: `spt8_figure_5_barrier_prediction_source.csv`
Data origin: `spt3_barrier_metrics.csv`, `spt6_barrier_prediction_models.csv`
Shows: (A-B) Simulation evidence that barrier violations predict reduced SMR improvement.
(C) Empirical prediction analysis from real EEG (SPT6). If empirical data was insufficient,
panel C shows a null result placeholder.

## Figure 6: Framework comparison
Source: `spt8_figure_6_framework_comparison_source.csv`
Data origin: `spt7_framework_comparison.csv`
Shows: Criterion-by-criterion comparison of Stuart-Landau vs SPT frameworks.
Recommendation: demote SL to supplementary material.

## Negative results present

- Figure 4 shows empirical mixed/negative result (most subjects in D: neither quadrant).
- Figure 5 panel C shows insufficient empirical evidence for barrier prediction.
- These are not hidden; they are included as required by repository rules.

Generated: 2026-07-01T18:12:30.787725+00:00
