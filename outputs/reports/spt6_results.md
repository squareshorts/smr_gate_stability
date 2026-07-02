# SPT6 Results: Barrier-Prediction Analysis (Revised)

Generated: 2026-07-01 (revised with block-mean thresholds, regression-to-mean correction, FDR)

## Method (revised)

**Original problem**: Thresholds were computed on the high-resolution (256 Hz) envelope.
Block means (4-second windows) almost never exceeded these instantaneous percentiles --
violation_rate ≈ 0 for 168/200 rows -- making the original analysis uninformative.

**Fix**: Thresholds are now computed on the **distribution of block means** (not the raw
envelope). The p75 block-mean threshold ensures exactly ~25% of blocks are labelled as
violations, giving the analysis power.

**Outcomes tested**:
1. `smr_increase`: SMR block mean in block t+1 > block t. **Theoretically meaningful**.
   Does a high-beta violation impair subsequent SMR acquisition?
2. `admissible_next`: HB block mean in block t+1 < block t. **Confounded by regression
   to the mean** (see below). Excluded from primary inference.

Tests: Fisher exact + permutation test + phi coefficient (effect size).
Multiple testing: Benjamini-Hochberg FDR applied to the 100 smr_increase tests.

## Regression-to-mean confound in admissible_next

When the violation threshold is the 75th percentile of the block-mean distribution,
violation blocks are by construction at or above that percentile. These extreme values
regress toward the mean in the next block, making admissible_next = 1 more likely
regardless of any real barrier dynamics.

Evidence: phi > 0 for 100/100 admissible_next tests (mean phi = 0.37). This uniformly
positive direction is inconsistent with genuine prediction and reflects regression artifact.
All admissible_next results are excluded from primary inference.

## Primary analysis: smr_increase outcome

N tests: 5 subjects x 2 sessions x 2 conditions x 5 thresholds = 100 tests.

| Correction            | N significant  |
|-----------------------|----------------|
| Uncorrected (p<0.05)  | 9 / 100        |
| FDR (q<0.05)          | **0 / 100**    |
| Bonferroni (p<0.0005) | 0 / 100        |

Mean phi (smr_increase, all 100 tests): -0.143
Direction: 84/100 tests have negative phi (violations associated with LESS SMR
increase in the next block), directionally consistent with the barrier hypothesis.
However, effect too small and inconsistent for statistical reliability at n=5.

The previously-reported "significant" result (sub-005, ses-08, rest, p80, phi=-0.47,
Fisher p=0.004) does NOT survive FDR correction (q=0.038 in 100-test family; Bonferroni
corrected p=0.4). This was a single-subject, single-session finding.

## Summary

- All 200 test combinations now have data (block-mean threshold fix resolves sparsity).
- admissible_next outcome excluded (regression-to-mean artefact).
- smr_increase outcome: NULL RESULT after FDR correction (0/100 survive at q<0.05).
- A directional signal exists (84/100 negative phi, mean=-0.14) consistent with
  violations impairing SMR acquisition, but not statistically reliable at n=5.

## Claim status

**Q5 (barrier-prediction): NULL RESULT.**

After fixing the threshold methodology and applying FDR correction, high-beta violations
at time t do NOT reliably predict SMR change at time t+1 in this dataset.

**DO NOT CLAIM**: "High-beta violations predict subsequent SMR changes."

**SHOULD STATE**: "The barrier-prediction test was conducted across 100 block-level
sequential tests (5 subjects, 2 sessions, 2 conditions, 5 thresholds). After FDR
correction, no result survived (q<0.05). A consistent negative direction (violations
associated with less SMR increase; mean phi=-0.14, 84/100 tests) is compatible with
the theoretical claim but does not constitute statistical evidence at n=5."

## Note on null result

The null result does not invalidate the SPT framework. The framework predicts that
violations impair regulation over the learning time scale (sessions, not blocks).
Block-by-block prediction is a stringent test that may require larger n or longer
recordings to detect small effects.

Generated: 2026-07-01 (revised)
