# Survival And Hazard Analysis

Created: 2026-07-02T12:39:03.675238+00:00

Primary hypothesis tested:

Successful high-beta inhibition should reduce the survival tail of S1 beta episodes and increase escape hazard more clearly than it reduces mean high-beta power.

Model status:

- Cox/PH episode-level summary: hazard ratio late vs early = 1.0087993518908065; status = fit_success.
- Subject-level paired and permutation tests are in `beta_escape_survival_models.csv`.
- Escape-rate model rows are in `beta_escape_hazard_models.csv`.

Observed primary mean changes:

- Mean high-beta power: -0.104226.
- Mean S1 dwell time: -0.00147972.
- Mean long-burst fraction: -0.0129162.
- Mean escape rate: 0.103291.

No result is hidden if null or directionally mixed; see the model tables for exact p-values and effect directions.
