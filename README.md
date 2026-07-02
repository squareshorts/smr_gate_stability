# SMR Cognitive Neurodynamics Revision Analyses

This repository supports a manuscript revision framed as a nonlinear neural-dynamics study of sensorimotor neurofeedback.

The central test is whether a coupled two-mode Stuart-Landau system has a validity regime in which selective stabilization of a fast beta mode suppresses high-beta amplitude and beta-burst expression while leaving the slower SMR mode approximately unchanged.

The repository is intentionally evidence-generating only. It does not edit manuscript files, write submission prose, or claim empirical support unless real EEG files are downloaded, inventoried, loaded, and analyzed.

## Quick Start

Create an environment with either `requirements.txt` or `environment.yml`, then run:

```bat
run_all_smoke_tests.bat
run_all_main_analyses.bat
```

The main analysis uses reduced/coarse grids by default. Outputs are written to `outputs/`, and all generated files are listed in `analysis_manifest.csv`.

## Work Packages

- WP1: coupled Stuart-Landau validity simulations.
- WP2: finite-difference weak-coupling derivative and bound checks.
- WP3: generic-feedback null model comparisons.
- WP4: criticality and near-Hopf sensitivity.
- WP5: burst-threshold and surrogate robustness.
- WP6: parameter-regime validity maps.
- WP7: approved dataset acquisition planning and local inventory.
- WP8: empirical analysis only after suitable real EEG files are locally available.
- WP9: Cognitive Neurodynamics figure candidates.

## Interpretation Guardrails

- The model is a validity-domain analysis, not a universal mechanism of SMR neurofeedback.
- Failed, unstable, mixed, or negative results are retained in tables and reports.
- Simulated outputs are never used as placeholders for empirical EEG analyses.
- Empirical claims are withheld unless real EEG files are downloaded, verified, and processed.
