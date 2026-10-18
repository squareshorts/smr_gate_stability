# Benchmark-session phase geometry: manuscript-ready numerical results

This is a results-only drafting aid. No manuscript file was edited.

## Primary endpoint

The prespecified early-session Gini contrast was large but did not reach significance under exact participant-level randomization inference. Across the first 15 minutes, the mean Gini slope was -4.93259e-05/min in trained participants and 0.00252022/min in controls (trained-minus-control difference -0.00256955/min, 95% participant-bootstrap CI [-0.00690433, 0.0016279], Hedges g=-0.602533, 95% CI [-2.40798, 0.418871]; exact p=0.305051, 495 allocations).

A window-level participant-fixed-effect sensitivity gave a similar group-by-elapsed-time coefficient (-0.00307212/min; exact participant-label permutation p=0.185859, 495 allocations). The participant-slope permutation remained the primary analysis.

## Secondary geometric endpoints

For phase-coherence radius, the trained-minus-control slope difference was 0.00395488/min (95% CI [-0.00191447, 0.0102498], raw exact p=0.307071, Holm p=0.307071). For DMD modal decay per cycle, the difference was -0.00834004/min (95% CI [-0.014011, -0.00289304], raw exact p=0.0161616, Holm p=0.0323232).

## Duration sensitivities

The Gini contrast retained the negative primary direction in all four prespecified duration checks but was attenuated. Differences ranged from -0.00126524 to -0.000615174/min, with raw exact p-values from 0.208333 to 0.329293.

| Duration analysis               |   n trained |   n control |   Gini difference/min |   95% CI low |   95% CI high |   Exact p |
|:--------------------------------|------------:|------------:|----------------------:|-------------:|--------------:|----------:|
| all_available_ge15_min          |           8 |           4 |          -0.000676274 |  -0.00174586 |   0.000209707 |  0.329293 |
| common_first_30_min             |           7 |           4 |          -0.00126524  |  -0.00309617 |   0.000371932 |  0.239394 |
| common_first_45_min             |           7 |           3 |          -0.000968608 |  -0.00256886 |   0.000444156 |  0.208333 |
| common_first_60_min_approx_full |           6 |           3 |          -0.000615174 |  -0.00164884 |   0.000200952 |  0.22619  |

## Manipulation checks

| Measure                                  |   Slope difference/min |   95% CI low |   95% CI high |   Exact p |
|:-----------------------------------------|-----------------------:|-------------:|--------------:|----------:|
| C3 SMR 12-15 Hz log10 power (uV^2)       |            -0.00336989 |  -0.0105073  |    0.00233743 |  0.345455 |
| C3 high-beta 20-30 Hz log10 power (uV^2) |            -0.00328001 |  -0.00969375 |    0.00269358 |  0.490909 |

Neither C3 SMR nor C3 high-beta showed a trained-control slope difference under exact participant-label inference.

## Exploratory transfer

Among the eight trained participants, Gini slope was positively associated with resting C3 SMR change (Spearman rho=-0.52381, raw exact p=0.196627, Holm p=0.393254) and inversely associated with validated PAC change (rho=0, raw exact p=1, Holm p=1). The inverse Gini-PAC association did not survive Holm correction across the two prespecified transfer outcomes.

All eight Gini-PAC leave-one-participant-out estimates remained negative (rho range -0.321429 to 0.214286; raw exact p range 0.497619 to 0.963492), indicating that no single participant was necessary for the negative direction. Gini-SMR leave-one-out estimates ranged from -0.857143 to -0.285714 (raw exact p range 0.0238095 to 0.555952).

### Gini-PAC leave-one-participant-out values

| Participant omitted   |   Spearman rho |   Raw exact p |
|:----------------------|---------------:|--------------:|
| ARN                   |     -0.214286  |      0.661508 |
| EFS                   |     -0.0357143 |      0.963492 |
| FFS                   |      0.214286  |      0.661508 |
| IBJ/IBP               |      0.0714286 |      0.906349 |
| JAM                   |      0.0714286 |      0.906349 |
| JBS                   |      0.178571  |      0.713095 |
| JDS                   |      0.0357143 |      0.963492 |
| RCB                   |     -0.321429  |      0.497619 |

No additional endpoints, bands, descriptors, or time windows were analyzed.
