# Methods Parameter Report

Generated: 2026-07-03 17:54:18 UTC

## Analysis Inputs

- Workspace: repository root
- Existing primary ds004447 tables: `outputs/tables/nf_sqi_*`
- Existing companion tables: `outputs/replication_tables/ds004444_*` and `outputs/replication_tables/ds004446_*`
- Dataset inventory: `outputs/replication_tables/dataset_inventory.csv` and `outputs/replication_logs/dataset_inventory.md`

## Datasets

- Analyzed: ds004447, ds004444, ds004446
- Skipped: ds004448
- ds004448 skip reason: inventory status `not_suitable_or_metadata_only`; event markers `1`; condition markers `Trial start`. No safe rest/task-compatible path was identified.

## Signal And Gate Parameters

- Sensorimotor channels: E36, E104, E128 when present.
- Candidate window: 1.0 s length with 0.5 s step for companion extraction and primary model comparison.
- SMR band: 12-15 Hz.
- High beta band: 20-30 Hz.
- Noise-floor band: 35-45 Hz.
- Broadband/noise predictors: broadband power and noise-floor power.
- Gate A: SMR above the subject/session rest-baseline 75th percentile.
- Gate B: Gate A plus high beta at or below the subject/session rest-baseline 75th percentile.
- Gate C / full NF-SQI: Gate B plus broadband, noise floor, transient amplitude, and channel inconsistency exclusions.
- Transient threshold: subject/session rest-baseline 90th percentile.
- Channel inconsistency threshold: subject/session rest-baseline 75th percentile.

## Model Parameters

- Classifier: logistic regression.
- Class weighting: balanced.
- Cross-validation: leave-one-subject-out.
- Standardization: `StandardScaler` fit on training subjects only.
- ds004447 full model predictors: broadband power, noise-floor power, high beta power, transient score, channel inconsistency, nonstationarity.
- ds004444/ds004446 full model predictors were reused from the existing companion outputs.

## Bootstrap Parameters

- Bootstrap iterations: 5000.
- Bootstrap grouping: subject-level grouped bootstrap.
- Confidence interval: percentile 95% CI.
- Random seed base: 20260702.

## Exact Command Used

```powershell
python analysis_replication\finish_replication.py > outputs\replication_logs\finish_replication_run.log 2>&1
```
