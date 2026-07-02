# Task 6: Reliability and Robustness

## Threshold Sensitivity

| Baseline | Threshold_Method | Gate_A_Yield | Gate_B_Yield | Blocked_by_HB_Pct |
|---|---|---|---|---|
| rest | p70 | 0.2127 | 0.1719 | 0.2854 |
| rest | p80 | 0.1296 | 0.1142 | 0.1810 |
| rest | p90 | 0.0519 | 0.0496 | 0.0738 |
| rest | mad | 0.1593 | 0.1382 | 0.2005 |
| task | p70 | 0.3009 | 0.1955 | 0.4082 |
| task | p80 | 0.1997 | 0.1501 | 0.3286 |
| task | p90 | 0.1012 | 0.0868 | 0.2140 |
| task | mad | 0.2286 | 0.1704 | 0.3376 |

## Subject Influence (LOO)

The percentage of false-admissible windows blocked by High Beta inhibition varies from 19.9% to 22.9% across LOO iterations, indicating the effect is not driven by a single subject.
