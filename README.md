# Calibration instability in conjunctive EEG quality gates: An exact composition law and external validation

**Authors:** Suzana Cescon de Souza, Antonio Pereira Jr

## Study purpose

Conjunctive (AND-joined) quality gates are widely used to admit or reject EEG windows in signal-quality pipelines (e.g., artifact rejection, neurofeedback readiness gating). This repository contains the reproducible analysis package for a study showing that:

1. the accepted-set behavior of a conjunctive gate can be predicted from its constituent per-criterion gates through a **composition theorem**, validated empirically across internal edges;
2. conjunctive gates are calibration-unstable across sessions/datasets, and this instability is remedied by a **single-score alternative** (percentile-based scoring in place of independent per-criterion AND-thresholding) and structural **hard interlocks**;
3. the remedy (H1) preserves performance, transports across external validation datasets (OpenBMI), and is robust under **controlled measurement degradation**.

## Main repository contents

- `scripts/utilities/` — frozen core primitives, hard interlocks, and empirical feature extraction modules.
- `scripts/internal/` — composition theorem derivation, evaluation on internal datasets, and baseline metrics.
- `scripts/external_validation/` — independent validation of the H1 single-score remedy on the external OpenBMI dataset.
- `scripts/controlled_degradation/` — controlled-degradation campaign (synthetic measurement degradation).
- `scripts/figures/` — final figure rendering and source-data aggregation scripts.
- `results/` — final canonical outputs for the internal, external validation, and controlled degradation analyses.
- `tests/` — scientific unit and regression tests.

## External Validation (OpenBMI)

The single-score remedy and exact composition law are robustly evaluated on the OpenBMI dataset in `scripts/external_validation/`. Canonical outputs, including exact edge decompositions and Pareto stability metrics, are generated here.

## Controlled Degradation

Gate behavior under **synthetic, controlled measurement degradation** (e.g. signal freezing, clipping, variance collapse) is evaluated in `scripts/controlled_degradation/`.

## Public source datasets

This analysis uses publicly available OpenNeuro datasets (e.g., ds004447, ds004444) and the OpenBMI dataset.
**Raw EEG data are NOT redistributed in this repository.** For full reproduction, download the raw data independently.

## Environment setup

Python (cross-platform):

```bash
uv venv .venv
uv pip install -r requirements.txt
```

R (figure rendering):

```bash
Rscript -e 'renv::restore()'
```

## Reproducibility package

The repository contains the final scientific products and data underlying all figures in the manuscript. To regenerate the compact figure source data and render the main text figures:

```bash
# Aggregate raw canonical outputs into compact figure source data
python scripts/figures/build_figure_source_data.py

# Render figures (requires R)
Rscript scripts/figures/plot_main_figures.R
```

## Citation

Please refer to the `CITATION.cff` file in this repository.

## License

This project is licensed under the MIT License — see `LICENSE`.
