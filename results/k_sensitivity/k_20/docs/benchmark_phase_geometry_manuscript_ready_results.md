# Benchmark-session phase geometry: manuscript-ready numerical results

This is a results-only drafting aid. No manuscript file was edited.

## Primary endpoint

The prespecified early-session Gini contrast was large but did not reach significance under exact participant-level randomization inference. Across the first 15 minutes, the mean Gini slope was -0.00115387/min in trained participants and -6.52191e-05/min in controls (trained-minus-control difference -0.00108865/min, 95% participant-bootstrap CI [-0.00419382, 0.00163725], Hedges g=-0.345191, 95% CI [-1.52381, 1.23849]; exact p=0.60404, 495 allocations).

A window-level participant-fixed-effect sensitivity gave a similar group-by-elapsed-time coefficient (-0.00118168/min; exact participant-label permutation p=0.585859, 495 allocations). The participant-slope permutation remained the primary analysis.

## Secondary geometric endpoints

For phase-coherence radius, the trained-minus-control slope difference was 0.0029596/min (95% CI [-0.0021754, 0.00814785], raw exact p=0.40404, Holm p=0.40404). For DMD modal decay per cycle, the difference was -0.00834004/min (95% CI [-0.014011, -0.00289304], raw exact p=0.0161616, Holm p=0.0323232).

## Duration sensitivities

The Gini contrast retained the negative primary direction in all four prespecified duration checks but was attenuated. Differences ranged from -0.00107628 to 3.53167e-05/min, with raw exact p-values from 0.116667 to 0.820202.

| Duration analysis               |   n trained |   n control |   Gini difference/min |   95% CI low |   95% CI high |   Exact p |
|:--------------------------------|------------:|------------:|----------------------:|-------------:|--------------:|----------:|
| all_available_ge15_min          |           8 |           4 |           3.53167e-05 | -0.000291778 |   0.000315329 |  0.820202 |
| common_first_30_min             |           7 |           4 |          -0.00107628  | -0.00225798  |   3.9227e-05  |  0.218182 |
| common_first_45_min             |           7 |           3 |          -0.00070575  | -0.00132945  |  -0.000147829 |  0.116667 |
| common_first_60_min_approx_full |           6 |           3 |          -7.09668e-05 | -0.000424128 |   0.000234728 |  0.690476 |

## Manipulation checks

| Measure                                  |   Slope difference/min |   95% CI low |   95% CI high |   Exact p |
|:-----------------------------------------|-----------------------:|-------------:|--------------:|----------:|
| C3 SMR 12-15 Hz log10 power (uV^2)       |            -0.00336989 |  -0.0105073  |    0.00233743 |  0.345455 |
| C3 high-beta 20-30 Hz log10 power (uV^2) |            -0.00328001 |  -0.00969375 |    0.00269358 |  0.490909 |

Neither C3 SMR nor C3 high-beta showed a trained-control slope difference under exact participant-label inference.

## Exploratory transfer

Among the eight trained participants, Gini slope was positively associated with resting C3 SMR change (Spearman rho=0.238095, raw exact p=0.582143, Holm p=0.582143) and inversely associated with validated PAC change (rho=-0.571429, raw exact p=0.151141, Holm p=0.302282). The inverse Gini-PAC association did not survive Holm correction across the two prespecified transfer outcomes.

All eight Gini-PAC leave-one-participant-out estimates remained negative (rho range -0.714286 to -0.357143; raw exact p range 0.0880952 to 0.444444), indicating that no single participant was necessary for the negative direction. Gini-SMR leave-one-out estimates ranged from -0.142857 to 0.5 (raw exact p range 0.266667 to 0.839683).

### Gini-PAC leave-one-participant-out values

| Participant omitted   |   Spearman rho |   Raw exact p |
|:----------------------|---------------:|--------------:|
| ARN                   |      -0.428571 |     0.353571  |
| EFS                   |      -0.714286 |     0.0880952 |
| FFS                   |      -0.357143 |     0.444444  |
| IBJ/IBP               |      -0.678571 |     0.109524  |
| JAM                   |      -0.535714 |     0.235714  |
| JBS                   |      -0.535714 |     0.235714  |
| JDS                   |      -0.607143 |     0.166667  |
| RCB                   |      -0.642857 |     0.138889  |

No additional endpoints, bands, descriptors, or time windows were analyzed.
