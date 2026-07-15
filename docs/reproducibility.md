# Reproducibility Guide

## Prerequisites
Ensure `uv` is installed, as it provides the most reproducible execution environment for this repository.
If you wish to regenerate the manuscript figures, you must also have `R` installed with the `ggplot2`, `dplyr`, and `tidyr` packages.

## 1. Quick Reproduction for Reviewers (Figures & Tables)
The repository contains the final derived data required to regenerate manuscript figures without downloading the raw terabyte-scale EDF files. The intermediate statistics and regression results are bundled in `results/final/`.

To regenerate the publication-quality manuscript figures (PDF, PNG, TIFF):
```bash
Rscript scripts/make_submission_figures_r.R
```

To run the lightweight synthetic computational latency benchmark:
```bash
python scripts/benchmark_nfsqi_latency.py --config configs/nfsqi_smr_central.yaml --n-windows 1000
```

## 2. Full Reproduction from Raw EDFs
If you intend to reproduce the full window-level feature extraction or the real-time EDF streaming benchmark, you must first download the raw EEG datasets from OpenNeuro (`ds004447`, `ds004444`, `ds004446`) into the `data/raw/openneuro/` directory.

See `docs/data_availability.md` for DOIs and dataset access instructions.

Once the raw data is present at `data/raw/openneuro/<dataset_id>`, you can re-run the pseudo-online raw EDF deployment path:
```bash
python scripts/run_nfsqi_pseudo_online_real_edf.py
```
*(This extracts features window-by-window directly from the source EDF files.)*

## Reviewing the Output
The `results/final/` folder contains all pre-computed outputs used in the manuscript, including:
- `bootstrap_ci_all_variants.csv`
- `loso_model_comparison_all_variants.csv`
- `table6A_gate_blocking.csv`
- `table6B_auc_comparison.csv`

The `manuscript/figures/` folder contains the compiled figures:
- `fig_gate_blocking_clean.*`
- `fig_model_comparison_clean.*`
- `fig6_cross_dataset_clean.*`
