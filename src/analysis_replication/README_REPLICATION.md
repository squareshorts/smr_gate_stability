# NF-SQI Replication Pipeline

This directory contains the scripts used to reproduce the primary ds004447 NF-SQI outputs and apply the same reviewer-audit workflow to companion OpenNeuro datasets.

Run from the repository root:

```bash
python analysis_replication/run_full_replication.py
python analysis_replication/finish_replication.py
```

Pipeline steps:

- `step1_dataset_inventory.py`: scans local data and downloads missing first/last-session OpenNeuro subsets when manifests are available.
- `step2_reproduce_ds004447.py`: reruns the primary ds004447 NF-SQI scripts and checks key summary values.
- `step3_apply_companion_datasets.py`: extracts companion features and applies Gate A/B/C logic to ds004444 and ds004446.
- `step4_5_bootstrap_and_added_value.py`: bootstraps subject-grouped CIs and added-value comparisons.
- `step6_cross_dataset_summary.py`: writes the cross-dataset summary table.
- `step7_integrated_figures.py`: writes compact replication figures.
- `step8_sensitivity_checks.py`: evaluates p70, p75, p80, p90, and MAD threshold sensitivity.
- `step9_10_11_reports.py`: writes compact leakage/methods/final reports.
- `finish_replication.py`: validates required outputs and writes the final reviewer-facing summary artifacts.
