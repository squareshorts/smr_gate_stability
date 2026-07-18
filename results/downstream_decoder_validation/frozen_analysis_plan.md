# Frozen downstream decoder validation plan

Frozen on 2026-07-15 before substantive modeling. Repository commit at freeze: `2062eb33119f1606098fb8e6bd667399fdcd88f8`.

## Scientific question and endpoint

The primary question is whether training-data filtering with the complete quality-only NF-SQI rule improves held-out-session decoding relative to high-beta-only filtering. The decoder target will be an experimental event label, never an NF-SQI flag. The primary endpoint is participant-aggregated held-out-session balanced accuracy and the primary contrast is `NFSQI_FULL - HB`.

## Immutable scope and isolation

- All new code will be under `scripts/downstream_decoder_validation/` and all new outputs under `results/downstream_decoder_validation/`.
- No manuscript, bibliography, manuscript PDF, cover letter, supplementary manuscript, archived release metadata, release, existing manuscript table/figure/caption, file under `manuscript/`, or existing file under `results/final/` will be modified.
- The existing rule-defined classifier analysis will remain intact.
- Existing released loaders, feature extraction, channel definitions, thresholds, and cached products will be reused wherever possible.

## Mandatory pre-modeling gates

1. Inventory loaders, event parsing, identifiers, caches, replay outputs, quality implementation, montages, and tests.
2. Reproduce the released consistency counts: ds004447 (5218 task windows, 126 high-beta blocks among Gate A candidates, 472 Gate C retained), ds004444 (14400, 644, 933 batch), and ds004446 (2800, 96, 215).
3. If the counts cannot be reproduced using released paths/code, stop modeling and write an explicit blocker report.
4. Audit event semantics and construct `event_label_audit.csv` before decoder fitting.

## Labels and windows

- Prefer rest versus SMR/motor-imagery task when event semantics support it.
- Map only explicit experimental event codes; document dataset-specific mappings.
- Exclude transitions and ambiguous windows.
- Apply one prespecified temporal-overlap rule across datasets wherever semantics permit; the rule will be fixed in the event audit before fitting models.
- Preserve session, trial, and continuous-segment identifiers. No overlapping or adjacent windows from one segment may cross train/test partitions.

## Validation design

- Primary validation: within-participant held-out-session folds, training on one session and testing on the other, reversing directions when valid, then averaging valid directions per participant.
- Secondary validation: chronological earlier-to-later session when ordering is trustworthy.
- The test set within a fold is complete, unfiltered, and byte-for-byte/index-identical for every training policy.
- Participant is the inferential unit; window metrics are descriptive only.

## Threshold calibration and quality policies

Thresholds will be calibrated independently for each training session from that session's rest baseline using the released implementation and fixed policy: p75 HB, p75 BB, p75 HF, p75 CI, and p90 transient amplitude. No held-out-session task value or other held-out value will be used to fit or tune thresholds.

Quality-only policies applied symmetrically to both decoder classes:

- `ALL`: all finite labelled training windows.
- `HB`: `HB_pass`.
- `BBHF`: `BB_pass AND HF_pass`.
- `NFSQI_NO_HB`: `BB_pass AND HF_pass AND TR_pass AND CI_pass`.
- `NFSQI_FULL`: `HB_pass AND BB_pass AND HF_pass AND TR_pass AND CI_pass`.
- `AMPLITUDE_150`: released 150 microvolt peak-to-peak rejection.

Gate A, SMR thresholding, target positivity, reward candidacy, decoder output, and task labels are prohibited from every quality mask. Automated tests will enforce this.

## Decoder specifications

Primary decoder: the canonical three central channels; log band powers for 8-12, 12-15, 15-20, and 20-30 Hz; train-only finite-value handling and standardization; balanced logistic regression with fixed hyperparameters shared by all policies. The 30-45 Hz band will not be used unless the released representation requires it consistently and a pre-fit implementation note documents why.

Sensitivity decoder, after Priority 1: 8-30 Hz covariance features with a faithful tangent-space/MDM implementation if dependencies and epoch access permit, using the standard three-channel montage and then the repository's exact expanded central ROI. All fitting remains training-only.

External baseline, after Priority 1: implement Riemannian Potato/Field only from the original method or a verified package implementation, fit on training data only. If infeasible, document the exact blocker without substituting an approximation.

## Training quantity analyses

- Natural retention: fit each policy with all retained training windows.
- Count matched: within every fold and class, use the `NFSQI_FULL` retained count as the target; group-aware subsample other policies without replacement for at least 100 fixed seeds; never oversample `NFSQI_FULL`; average repeats per fold.
- Use the same class-weighting strategy for every policy.
- Flag folds with inadequate retained samples/classes as nonviable; never replace or omit silently.

## Metrics and inference

Primary metric: balanced accuracy. Secondary metrics: ROC-AUC, accuracy, macro F1, sensitivity, specificity, log loss, Brier score, overall/task/rest retention, valid participants, nonviable folds, between-session variability, and runtime. Aggregate probabilities by real trial/segment identifiers for a secondary segment-level analysis when supported.

For paired participant contrasts, report mean and median differences, a subject-grouped bootstrap 95% confidence interval using 10,000 resamples, and a two-sided paired sign-flip permutation p-value using at least 5,000 draws (exact enumeration when smaller). Fixed seeds will be declared in the manifest. Report each dataset and the pooled participant analysis, plus leave-one-participant-out and leave-one-dataset-out sensitivity.

## Expanded ROI, controls, and optional analyses

- Repeat retention and primary decoding with the exact released expanded central ROI.
- Test no Gate A contamination, identical test indices, training-only thresholds/scalers/transforms, session grouping/no overlap leakage, class-retention imbalance, session feasibility, participant/dataset dominance, and independence from Gate A/SMR-SNR definitions.
- After Priority 1, attempt the covariance decoder, faithful RPF, and synthetic perturbation benchmark in that order as resources permit.
- The synthetic benchmark, if run, will use a fixed balanced subset of initially `NFSQI_FULL`-passing windows, copied in memory; eight prespecified disturbance families; at least four severity levels fixed relative to training-session rest robust scale; and fixed seeds. It will be explicitly labeled fault injection rather than artifact-label validation.

## Reproducibility and deliverables

- One entry point: `python scripts/downstream_decoder_validation/run_all.py`.
- Capture Python/package/OS/CPU versions, commands, seeds, commit, and practical input hashes.
- Add isolated tests for masks, Gate A exclusion, threshold provenance, identical tests, count matching, labels, folds, sampling reproducibility, and result tables. Existing tests will not be changed to force success.
- Generate only new figures under `results/downstream_decoder_validation/figures/`, in vector PDF and 600 dpi PNG, with no titles and participant-grouped intervals.
- Generate every required CSV/Markdown/manifest/audit output; optional outputs will be present only when genuinely completed or will have an explicit feasibility report.

## Stop conditions

Modeling stops if released primary counts diverge, independent labels cannot be constructed, valid session-held-out folds do not exist, or source epochs cannot be connected to released quality features without leakage. In each case, the analysis will report the blocker and evidence rather than fabricate or silently substitute a different design.
