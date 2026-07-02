# WP3 Results: Generic-Feedback Null Models

Grid: `reduced`.

At the highest tested gain, aggregate model behavior was:

- `ar2`: beta change -0.863, burst-rate change -1.000, mean abs SMR collateral 0.002, mean abs high-frequency collateral 0.173.
- `damped_harmonic`: beta change -0.666, burst-rate change -0.945, mean abs SMR collateral 0.007, mean abs high-frequency collateral 0.191.
- `linear_ou`: beta change -0.834, burst-rate change -1.000, mean abs SMR collateral 0.000, mean abs high-frequency collateral 0.003.
- `stuart_landau`: beta change -0.793, burst-rate change -1.000, mean abs SMR collateral 0.000, mean abs high-frequency collateral 0.002.

Interpretation: selective feedback in generic linear oscillators can suppress high-beta power, so stationary suppression alone is not specific. The nonlinear Stuart-Landau model is most informative when evaluated jointly with burst occupancy, saturation, non-target power, and validity-boundary behavior.