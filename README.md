# Signal-Quality Admissibility for Sensorimotor Rhythm Neurofeedback: Beyond High-Beta Inhibition

This repository contains the reproducible analysis code, derived final outputs, and figures for the manuscript **"Signal-Quality Admissibility for Sensorimotor Rhythm Neurofeedback: Beyond High-Beta Inhibition"**.

## Study Purpose
This study evaluates the admissibility of Sensorimotor Rhythm (SMR) neurofeedback using a comprehensive rule set (NF-SQI) rather than the traditional high-beta inhibition alone. The code here generates the virtual gate analyses, cross-dataset blocking comparisons, threshold sensitivities, and leave-one-subject-out (LOSO) predictive models.

## Raw Data Sources
This analysis was performed on publicly available OpenNeuro datasets:
- `ds004447` (Primary dataset)
- `ds004444` (Companion replication dataset)
- `ds004446` (Companion replication dataset)

**Raw EEG data are NOT redistributed in this repository.** For full reproduction, the raw EDFs must be downloaded independently. See `docs/data_availability.md` for DOIs and links.

## Repository Structure
- `scripts/`: Final top-level scripts used to generate the manuscript metrics.
- `src/`: Core Python modules for empirical processing, data loading, and replication logic.
- `results/final/`: The exact derived CSVs and tables reported in the final manuscript.
- `manuscript/figures/`: High-resolution figures generated for the manuscript.
- `docs/`: Guides for reproducing the analyses and acquiring the data.

## Reproducibility
For exact commands to regenerate window-level features, virtual gate outputs, denominator accounting, and final figures, see `docs/reproducibility.md`.

## Field-deployment reference implementation
The repository also includes a pseudo-online NF-SQI reference path for other labs to inspect and test: `src/empirical/nf_sqi_realtime.py`, `configs/nfsqi_smr_central.yaml`, `scripts/run_nfsqi_pseudo_online.py`, `scripts/benchmark_nfsqi_latency.py`, and `docs/nfsqi_deployment.md`.

The raw-window streaming path has been validated directly on the source recordings. `scripts/run_nfsqi_pseudo_online_real_edf.py` calibrates on each session's rest windows and streams its task windows through the deployment evaluation function straight from the OpenNeuro EDF files. Run over all sessions of ds004447, ds004444, and ds004446, it reproduces the offline Gate A and Gate B counts exactly and the Gate C counts either exactly (ds004447, ds004446) or to within a single window (ds004444: 932 vs 933), at a mean compute latency near 1 ms per 1-s window. See `results/final/nfsqi_pseudo_online_real_validation.md`.

## Expected Final Outputs
Running the harmonization scripts generates cross-dataset tables showing that high-beta inhibition alone covers only a partial, largely overlapping subset of rule-defined quality-flagged candidates (29-42%), whereas broadband/noise-floor criteria cover more (63-66%) and outperform high beta in leave-one-subject-out (LOSO) AUC across all analyzed datasets, with no added value from high beta on top of broadband/noise-floor. The full NF-SQI rule removes 100% of the rule-defined quality-flagged set **by construction** (the gate enforces exactly the constraints that define a flag), so this value is reported as a definitional identity rather than as measured performance; the substantive evidence is the component-wise coverage and the LOSO comparison. A raw-window pseudo-online replay reproduces these gate counts on the real recordings through the streaming code path (see above).
