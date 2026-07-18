# Frozen analysis plan — conjunctive-gate-instability law

Frozen before any results were generated. Do not edit after result generation.

## Objective
Test whether the observed instability of the full five-feature NF-SQI gate follows a
general multiplicative law for conjunctive baseline-calibrated EEG quality criteria.
This is a bounded feasibility test only. It does not attempt to rescue NF-SQI.

## Data
Input is the verified canonical per-window feature cache from the baseline-gate-stability
study (`results/baseline_gate_stability/checkpoints/features/*_canonical.csv.gz`).
No raw EDF, no downloads, no re-run of decoder/runtime/Potato. Same evaluation windows for
every subset (per-session task-window index).

## Frozen criteria (all upper-bound rejections; pass = feature < threshold)
- Q1 high beta — `high_beta_power`, p75
- Q2 broadband / non-target — `broadband_power`, p75
- Q3 35–45 Hz high-frequency reference — `noise_floor_power`, p75
- Q4 transient amplitude — `transient_score`, p90
- Q5 channel inconsistency — `channel_inconsistency`, p75

Excluded by design: Gate A / SMR reward evidence; the fixed 150 µV amplitude gate.
Lattice: all 31 nonempty subsets of {Q1..Q5}. Subsets fixed before results.

## Calibration design (primary)
Two independent baseline (rest) calibration replicates per session:
- Replicate 1 = first 60 s of usable baseline.
- Replicate 2 = final 60 s of usable baseline.
- Nonoverlapping 1 s windows (start times at integer seconds; hop 0.5 s → take every other window).
- If usable baseline < 120 s: two equal-maximum-duration nonoverlapping blocks, ≥30 s each;
  otherwise exclude the session (reported).
Thresholds: canonical empirical quantile (primary). Same quantile estimator for every
criterion and session. Percentile levels are NOT tuned.
Channel inconsistency is baseline-relative: per replicate, the channel baseline (per-band
means/SDs) is fit on that replicate's rest block and applied to the task windows.

## Sensitivity
Harrell–Davis quantile thresholds recomputed as a secondary estimator. Secondary only;
does not replace the primary empirical result.

## Evaluation
Gate decisions evaluated on the session's task windows. For each subset and estimator:
observed accepted-set Jaccard between the two calibration replicates, and the parameter-free
independence-predicted Jaccard (see theoretical_derivation.md). No fitting of the law.

## Dependence
Report pairwise feature and pass-indicator correlations, observed vs independence-predicted
acceptance and joint acceptance, dependence correction ratio, and residual J_obs − J_pred.
Optional correction: a single linear calibration of observed logit-Jaccard on predicted
logit-Jaccard plus a prespecified mean-absolute-pairwise-correlation term, fit only on
development datasets and applied unchanged to the held-out dataset. No other predictors.

## Checkpointing
One session at a time; write `checkpoints/<dataset>_<participant>_<session>.parquet`.
Maintain execution_progress.csv, execution_errors.csv, completed_checkpoint_manifest.csv.
Skip valid checkpoints on restart. Do not hold all session decision matrices in memory.

## Material-change threshold (frozen)
A one-criterion addition is a material change iff |ΔJaccard| ≥ 0.02.
