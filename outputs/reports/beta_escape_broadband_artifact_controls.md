# Broadband And Artifact Controls

Created: 2026-07-02T12:39:03.677353+00:00

Controls computed:

- Broadband non-target power.
- Spectral slope over 4-45 Hz excluding SMR and high-beta.
- High-beta residual after log-log aperiodic fit.
- 35-45 Hz noise-floor power.
- High-amplitude influence via 95th-percentile trimming.
- S2 broadband/artifact occupancy.

Complete subject-level controls are in `beta_escape_broadband_controls.csv`; regression/correlation controls are in `beta_escape_spectral_slope_controls.csv`.

Interpretation:

Persistence effects should not be treated as clean beta-state evidence unless they remain directionally interpretable after these broadband/noise checks.
