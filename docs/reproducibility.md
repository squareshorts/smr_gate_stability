# Reproducibility Guide

## Prerequisites
Ensure `uv` is installed, as it provides the most reproducible execution environment for this repository. 

## 1. Window-Level NF-SQI Features
To extract the window-level EEG features from raw OpenNeuro EDF files for the primary and companion datasets (requires OpenNeuro data in `data/raw/openneuro/`):

```bash
uv run python src/analysis_replication/run_full_replication.py
```
*(This generates the large intermediate feature CSVs which are not tracked by Git.)*

## 2. Virtual Gate Outputs, LOSO AUC Tables, and Cross-Dataset Blocking
To synthesize the extracted window features into the cross-dataset harmonization tables, virtual gate outputs, and the logistic regression leave-one-subject-out (LOSO) predictive models:

```bash
uv run python scripts/run_snr_harmonization.py
```
*(This populates `results/submission_readiness/` with the final model comparison tables and summary stats).*

## 3. Denominator Accounting
To recompute the exact conservative denominator counts for manuscript tables (matching the count-weighted yields):

```bash
uv run python scripts/recompute_counts.py
```

## 4. Final Figures
To regenerate the publication-quality manuscript figures (PDF, PNG, TIFF) using R's ggplot2:

```bash
Rscript scripts/make_submission_figures_r.R
```

## Reviewing the Output
After running the scripts above, the `results/final/` folder will be populated with:
- `snr_primary_replication_table.csv`
- `loso_model_comparison_all_variants.csv`
- `table6A_gate_blocking.csv`
- `table6B_auc_comparison.csv`

The `manuscript/figures/` folder will contain:
- `fig_gate_blocking_clean.*`
- `fig_model_comparison_clean.*`
- `fig6_cross_dataset_clean.*`
