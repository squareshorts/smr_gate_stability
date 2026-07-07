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

## Expected Final Outputs
Running the harmonization scripts generates cross-dataset tables demonstrating that the full NF-SQI rule strictly blocks 100.0% of rule-defined contaminated candidates, outperforming standard high-beta inhibition in LOSO AUC metrics across all analyzed datasets.
