# Benchmark-session phase geometry: manuscript-ready numerical results

This is a results-only drafting aid. No manuscript file was edited.

## Primary endpoint

The prespecified early-session Gini contrast was large but did not reach significance under exact participant-level randomization inference. Across the first 15 minutes, the mean Gini slope was -0.000120429/min in trained participants and 0.00183848/min in controls (trained-minus-control difference -0.00195891/min, 95% participant-bootstrap CI [-0.00673369, 0.00211388], Hedges g=-0.471244, 95% CI [-1.80902, 0.795113]; exact p=0.420202, 495 allocations).

A window-level participant-fixed-effect sensitivity gave a similar group-by-elapsed-time coefficient (-0.00228952/min; exact participant-label permutation p=0.355556, 495 allocations). The participant-slope permutation remained the primary analysis.

## Secondary geometric endpoints

For phase-coherence radius, the trained-minus-control slope difference was 0.00413519/min (95% CI [-0.00100821, 0.00964635], raw exact p=0.242424, Holm p=0.242424). For DMD modal decay per cycle, the difference was -0.00834004/min (95% CI [-0.014011, -0.00289304], raw exact p=0.0161616, Holm p=0.0323232).

## Duration sensitivities

The Gini contrast retained the negative primary direction in all four prespecified duration checks but was attenuated. Differences ranged from -0.000561839 to -0.000406079/min, with raw exact p-values from 0.167677 to 0.608333.

| Duration analysis               |   n trained |   n control |   Gini difference/min |   95% CI low |   95% CI high |   Exact p |
|:--------------------------------|------------:|------------:|----------------------:|-------------:|--------------:|----------:|
| all_available_ge15_min          |           8 |           4 |          -0.00051049  |  -0.00120611 |   9.51592e-05 |  0.167677 |
| common_first_30_min             |           7 |           4 |          -0.000495836 |  -0.00190437 |   0.000768474 |  0.49697  |
| common_first_45_min             |           7 |           3 |          -0.000406079 |  -0.00169728 |   0.000768942 |  0.608333 |
| common_first_60_min_approx_full |           6 |           3 |          -0.000561839 |  -0.00141919 |   0.000224208 |  0.25     |

## Manipulation checks

| Measure                                  |   Slope difference/min |   95% CI low |   95% CI high |   Exact p |
|:-----------------------------------------|-----------------------:|-------------:|--------------:|----------:|
| C3 SMR 12-15 Hz log10 power (uV^2)       |            -0.00336989 |  -0.0105073  |    0.00233743 |  0.345455 |
| C3 high-beta 20-30 Hz log10 power (uV^2) |            -0.00328001 |  -0.00969375 |    0.00269358 |  0.490909 |

Neither C3 SMR nor C3 high-beta showed a trained-control slope difference under exact participant-label inference.

## Exploratory transfer

Among the eight trained participants, Gini slope was positively associated with resting C3 SMR change (Spearman rho=-0.47619, raw exact p=0.243056, Holm p=0.486111) and inversely associated with validated PAC change (rho=-0.0952381, raw exact p=0.840129, Holm p=0.840129). The inverse Gini-PAC association did not survive Holm correction across the two prespecified transfer outcomes.

All eight Gini-PAC leave-one-participant-out estimates remained negative (rho range -0.357143 to 0.0714286; raw exact p range 0.444444 to 0.963492), indicating that no single participant was necessary for the negative direction. Gini-SMR leave-one-out estimates ranged from -0.678571 to -0.214286 (raw exact p range 0.109524 to 0.661508).

### Gini-PAC leave-one-participant-out values

| Participant omitted   |   Spearman rho |   Raw exact p |
|:----------------------|---------------:|--------------:|
| ARN                   |     -0.321429  |      0.497619 |
| EFS                   |     -0.0357143 |      0.963492 |
| FFS                   |     -0.0714286 |      0.906349 |
| IBJ/IBP               |     -0.142857  |      0.78254  |
| JAM                   |      0.0714286 |      0.906349 |
| JBS                   |      0.0357143 |      0.963492 |
| JDS                   |      0.0714286 |      0.906349 |
| RCB                   |     -0.357143  |      0.444444 |

No additional endpoints, bands, descriptors, or time windows were analyzed.
