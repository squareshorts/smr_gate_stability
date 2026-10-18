# Benchmark-session phase geometry: manuscript-ready numerical results

This is a results-only drafting aid. No manuscript file was edited.

## Primary endpoint

The prespecified early-session Gini contrast was large but did not reach significance under exact participant-level randomization inference. Across the first 15 minutes, the mean Gini slope was -0.00107305/min in trained participants and 0.00155248/min in controls (trained-minus-control difference -0.00262553/min, 95% participant-bootstrap CI [-0.00487054, -0.000397308], Hedges g=-1.16757, 95% CI [-3.00569, -0.241963]; exact p=0.0707071, 495 allocations).

A window-level participant-fixed-effect sensitivity gave a similar group-by-elapsed-time coefficient (-0.0026456/min; exact participant-label permutation p=0.0828283, 495 allocations). The participant-slope permutation remained the primary analysis.

## Secondary geometric endpoints

For phase-coherence radius, the trained-minus-control slope difference was 0.00331467/min (95% CI [-0.00177231, 0.00868239], raw exact p=0.337374, Holm p=0.337374). For DMD modal decay per cycle, the difference was -0.00834004/min (95% CI [-0.014011, -0.00289304], raw exact p=0.0161616, Holm p=0.0323232).

## Duration sensitivities

The Gini contrast retained the negative primary direction in all four prespecified duration checks but was attenuated. Differences ranged from -0.00104991 to -0.000104347/min, with raw exact p-values from 0.166667 to 0.684848.

| Duration analysis               |   n trained |   n control |   Gini difference/min |   95% CI low |   95% CI high |   Exact p |
|:--------------------------------|------------:|------------:|----------------------:|-------------:|--------------:|----------:|
| all_available_ge15_min          |           8 |           4 |          -0.000104347 | -0.000573722 |   0.000303484 |  0.684848 |
| common_first_30_min             |           7 |           4 |          -0.00104991  | -0.00246732  |   0.000450503 |  0.30303  |
| common_first_45_min             |           7 |           3 |          -0.000702812 | -0.00144482  |  -6.07602e-05 |  0.166667 |
| common_first_60_min_approx_full |           6 |           3 |          -0.000197049 | -0.000738783 |   0.0002719   |  0.52381  |

## Manipulation checks

| Measure                                  |   Slope difference/min |   95% CI low |   95% CI high |   Exact p |
|:-----------------------------------------|-----------------------:|-------------:|--------------:|----------:|
| C3 SMR 12-15 Hz log10 power (uV^2)       |            -0.00336989 |  -0.0105073  |    0.00233743 |  0.345455 |
| C3 high-beta 20-30 Hz log10 power (uV^2) |            -0.00328001 |  -0.00969375 |    0.00269358 |  0.490909 |

Neither C3 SMR nor C3 high-beta showed a trained-control slope difference under exact participant-label inference.

## Exploratory transfer

Among the eight trained participants, Gini slope was positively associated with resting C3 SMR change (Spearman rho=0.5, raw exact p=0.216171, Holm p=0.216171) and inversely associated with validated PAC change (rho=-0.761905, raw exact p=0.036756, Holm p=0.0735119). The inverse Gini-PAC association did not survive Holm correction across the two prespecified transfer outcomes.

All eight Gini-PAC leave-one-participant-out estimates remained negative (rho range -0.928571 to -0.642857; raw exact p range 0.00674603 to 0.138889), indicating that no single participant was necessary for the negative direction. Gini-SMR leave-one-out estimates ranged from 0.25 to 0.678571 (raw exact p range 0.109524 to 0.594841).

### Gini-PAC leave-one-participant-out values

| Participant omitted   |   Spearman rho |   Raw exact p |
|:----------------------|---------------:|--------------:|
| ARN                   |      -0.714286 |    0.0880952  |
| EFS                   |      -0.928571 |    0.00674603 |
| FFS                   |      -0.642857 |    0.138889   |
| IBJ/IBP               |      -0.821429 |    0.034127   |
| JAM                   |      -0.821429 |    0.034127   |
| JBS                   |      -0.714286 |    0.0880952  |
| JDS                   |      -0.75     |    0.0662698  |
| RCB                   |      -0.642857 |    0.138889   |

No additional endpoints, bands, descriptors, or time windows were analyzed.
