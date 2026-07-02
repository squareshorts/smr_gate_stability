# WP2 Analytical Weak-Coupling Validity Statement

Grid: `reduced`.

Finite-difference checks were run on normalized SMR and high-beta powers. The tested qualitative inequalities were:

- `dP_beta/dk < 0`
- `|dP_SMR/dk| <= C epsilon`, with `C=3` and a small numerical tolerance of 0.015.

Coarse-grid outcomes:

- Mean high-beta negative-derivative rate: 1.000.
- Mean SMR coupling-bound hold rate: 1.000.

Working validity statement:

For weak linear, amplitude, or phase coupling, the simulated Stuart-Landau system usually satisfies a monotone high-beta suppression inequality as feedback gain increases. The induced SMR derivative remains bounded by coupling strength in most weak-coupling settings, but the bound fails when coupling terms directly contaminate the slow mode or when numerical finite differences straddle unstable transition regions.

This supports a restricted weak-coupling statement rather than a universal theorem.
