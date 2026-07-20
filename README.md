# Calibration stability in conjunctive EEG quality gates: A composition law and a single-score remedy

**Authors:** Suzana Cescon de Souza, Antonio Pereira Jr

## Study purpose

Conjunctive (AND-joined) quality gates are widely used to admit or reject EEG windows in
signal-quality pipelines (e.g., artifact rejection, neurofeedback readiness gating). This
repository contains the reproducible analysis package for a study showing that:

1. the accepted-set behavior of a conjunctive gate can be predicted from its constituent
   per-criterion gates through a **composition theorem**, validated empirically across the
   **complete 31-subset lattice** of a 5-criterion gate (2^5 − 1 non-empty subsets);
2. conjunctive gates are calibration-unstable across sessions/datasets, and this instability
   is remedied by a **single-score alternative** (percentile-based scoring in place of
   independent per-criterion AND-thresholding);
3. the remedy preserves **downstream decoder performance**, transports across sessions, and is
   evaluated under **controlled, synthetic measurement degradation**, with **computational
   latency** verified to be compatible with real-time / neurofeedback use.

## Main repository contents

- `src/` — frozen core primitives (agreement, temporal, threshold logic) and empirical feature
  extraction modules reused across analyses.
- `scripts/conjunctive_law_remedy/` — composition theorem derivation and symbolic/empirical
  validation, R0-R3 single-score remedy construction and evaluation, downstream-decoder reuse,
  and final scorecard assembly.
- `scripts/conjunctive_gate_stability/` — controlled-degradation campaign, figure rendering,
  reproducibility entry points (`run_final_checks.py`, `validate_existing_results.py`,
  `build_author_package.py`).
- `scripts/baseline_gate_stability/` — canonical per-window feature cache construction.
- `results/` — frozen output directories for the composition law, remedy, downstream, and
  degradation analyses (see `docs/conjunctive_gate_stability/result_provenance.md`).
- `configs/` — configuration files for the analyses and tests.
- `docs/` — reproducibility guides, canonical project map, analysis dependency graph, and result
  provenance.
- `environments/` — Python and R environment/reproducibility manifests.
- `tests/` — scientific unit and regression tests.

## Composition theorem and the 31-subset lattice

The composition theorem gives the accepted-set behavior of a conjunctive gate built from any
subset of per-criterion gates. It is derived and validated in
`scripts/conjunctive_law_remedy/stage1_theorem.py` (theorem) and `stage2_validation.py`
(empirical/blinding validation), against the **complete lattice of all 31 non-empty subsets**
of a 5-criterion gate (`results/conjunctive_gate_instability/`, Spearman correlation 0.988,
MAE 0.013 between predicted and observed accepted-set agreement). Figure source data and
rendering: `results/conjunctive_gate_final/figure_data/`,
`scripts/conjunctive_gate_stability/figures_r/figure1_composition_theorem.R` and
`figure3_cardinality_lattice.R`.

## R0-R3 remedy comparison

Four scoring methods are compared (`scripts/conjunctive_law_remedy/remedy_methods.py`):

- **R0 (original AND):** the baseline conjunctive gate — independent per-criterion percentile
  thresholds joined by logical AND. This is the calibration-unstable method being remedied.
- **R1 (mean percentile):** the proposed single-score remedy — a single percentile score
  computed as the mean of per-criterion percentiles, thresholded once.
- **R2 (RMS percentile):** a sensitivity variant using the root-mean-square of per-criterion
  percentiles.
- **R3 (robust Mahalanobis percentile):** a robust multivariate alternative; evaluated as a
  **negative result** — it underperforms R1/R2 and is retained in the package for completeness
  and transparency, not as a recommended method.

R1 and R2 satisfy 11/12 and 12/12 stability/operational criteria respectively in the final
scorecard (`scripts/conjunctive_law_remedy/stage8_finalize.py`,
`results/conjunctive_law_remedy/remedy/`, `results/conjunctive_law_remedy/author_package/`).

## Cross-session transport

Calibration and remedy stability are evaluated across sessions and datasets (transport
analysis) in `scripts/conjunctive_law_remedy/stage3_6_remedy.py` /
`stage3_6_aggregate.py`, with results in `results/conjunctive_law_remedy/`. Figure source
data and rendering: `figures_r/figure4_stability_transport.R`.

## Downstream decoder

The single-score remedy is verified to preserve downstream decoding performance by reusing
verified canonical decoder features and fold definitions (not regenerated) —
`results/downstream_decoder_validation/fold_definition.csv`,
`results/baseline_gate_stability/checkpoints/downstream_decoder_features/`. Evaluation code:
`scripts/conjunctive_law_remedy/stage6_downstream.py`; results:
`results/conjunctive_law_remedy/remedy/downstream_*_R.csv`. Figure:
`figures_r/figure6_downstream_information.R`.

## Controlled degradation

Gate behavior under **synthetic, controlled measurement degradation** (transforms D0-D9 applied
to re-extracted raw windows) is evaluated in
`scripts/conjunctive_gate_stability/stage2_5_degradation.py` and
`stage5_degradation_aggregate.py`, with outputs in `results/conjunctive_gate_final/degradation/`.
This is engineering measurement-degradation testing — **not** a claim of natural-artifact ground
truth, clinical validation, or neurofeedback efficacy (see
`docs/conjunctive_gate_stability/result_provenance.md`). Figure:
`figures_r/figure7_controlled_degradation.R`.

## Latency tests

A lightweight computational latency benchmark verifies the single-score remedy is compatible
with real-time / neurofeedback deployment budgets:

```bash
python scripts/benchmark_nfsqi_latency.py --config configs/nfsqi_smr_central.yaml --n-windows 1000
```

Results: `results/final/nfsqi_latency_benchmark.json`.

## Public source datasets

This analysis uses publicly available OpenNeuro datasets:

- `ds004447` — DOI: [10.18112/openneuro.ds004447.v1.0.1](https://doi.org/10.18112/openneuro.ds004447.v1.0.1)
- `ds004444` — DOI: [10.18112/openneuro.ds004444.v1.0.1](https://doi.org/10.18112/openneuro.ds004444.v1.0.1)
- `ds004446` — DOI: [10.18112/openneuro.ds004446.v1.0.1](https://doi.org/10.18112/openneuro.ds004446.v1.0.1)

**Raw EEG data are NOT redistributed in this repository.** For full reproduction, download the
raw EDFs from OpenNeuro independently into `data/raw/openneuro/<dataset_id>/`. See
`docs/data_availability.md`.

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

The recommended entry point validates all frozen results, figure source data, and tests without
any heavy rerun (no EDF reload, no 31-subset re-analysis, no decoder refit):

```bash
python scripts/conjunctive_gate_stability/run_final_checks.py
```

Individual steps:

```bash
# Validate existing results only
python scripts/conjunctive_gate_stability/validate_existing_results.py

# Render figures from frozen source data (host R)
cd scripts/conjunctive_gate_stability/figures_r
for f in figure*.R; do Rscript "$f"; done

# Assemble the author package
python scripts/conjunctive_gate_stability/build_author_package.py
```

Re-running the controlled-degradation campaign from raw EDFs (resumable, checkpointed) is
optional and requires the raw OpenNeuro data described above:

```bash
python scripts/conjunctive_gate_stability/run_degradation_verification.py
python scripts/conjunctive_gate_stability/stage5_degradation_aggregate.py
```

See `docs/conjunctive_gate_stability/reproducibility_commands.md`,
`docs/conjunctive_gate_stability/canonical_project_map.md`, and
`docs/conjunctive_gate_stability/analysis_dependency_graph.md` for the full command reference
and analysis dependency graph.

## Test commands

```bash
export PYTHONPATH="$PWD:$PWD/src:$PWD/scripts"
python -m pytest tests -q
```

## Citation

Please refer to the `CITATION.cff` file in this repository.

## License

This project is licensed under the MIT License — see `LICENSE`.

## Version

v1.0.0
