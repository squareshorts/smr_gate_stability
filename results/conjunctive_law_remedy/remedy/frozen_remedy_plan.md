# Frozen remedy plan — single-score alternative

Frozen before any remedy outcome was inspected. Do not modify after results.

## Features (fixed, all five, no subset search)
Q1 high beta (`high_beta_power`), Q2 broadband/non-target (`broadband_power`),
Q3 35–45 Hz reference (`noise_floor_power`), Q4 transient amplitude (`transient_score`),
Q5 channel inconsistency (`channel_inconsistency`, baseline-relative).
No Gate A, no SMR target evidence.

## Percentile-score transform
For each feature j and calibration rest block, u_j(x) = empirical CDF of the feature
relative to the calibration rest block = mean(rest_j <= x). Higher u_j = more extreme
vs baseline. Q5 uses channel inconsistency computed with the block's channel baseline.
Nonfinite feature or invalid window → fail closed (rejected). Ties: <= convention (CDF).

## Methods compared (prespecified, no additions)
- R0 ORIGINAL_AND: original per-criterion thresholds (Q1,Q2,Q3,Q5 at p75; Q4 at p90)
  joined by logical AND (identical to the canonical full NF-SQI gate).
- R1 MEAN_PERCENTILE: score = mean(u_1..u_5); one upper threshold.
- R2 RMS_PERCENTILE: score = sqrt(mean(u_j^2)); one upper threshold.
- R3 ROBUST_MAHALANOBIS_PERCENTILE: robust center (per-dim median) and regularized
  covariance (shrinkage alpha=0.10 toward scaled identity, frozen constant) of the rest
  u-vectors; score = Mahalanobis distance; one upper threshold.

## Threshold policy
R1–R3 use exactly one threshold, taken as a percentile of the calibration rest score
distribution. Primary p75; sensitivity p80. No broad grid; no per-dataset percentile.
Matched-availability (secondary): a single threshold chosen on development datasets to
match the median R0 acceptance proportion, frozen, applied unchanged to the holdout.

## Calibration stability design
Two independent rest splits: first-half/second-half and odd/even nonoverlapping.
Each method calibrated independently on each split half, applied to task windows,
accepted sets compared (accepted-set Jaccard and agreement).

## Holdout
Three leave-one-dataset-out rotations. R1,R2 need no fitted weights. R3 regularization
constant and numerical choices are frozen before holdout application.

## Checkpointing
One session at a time; parquet checkpoint per session; skip valid checkpoints on restart.
