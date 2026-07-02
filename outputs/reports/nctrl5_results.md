# NCTRL5 Results: Four-Quadrant Noise-Control Classification

Generated: 2026-07-01T19:05:44.605704+00:00

## Method

Classification based on ses-01 → ses-08 change (rest condition, mean channel):
- SMR improvement: Δ log(SMR SNR) > 0 (primary)
- Noise damping: Δ log(P_HB) < 0 (primary)

Four alternative definitions also tested (see sensitivity table).

## Primary classification (n=5 subjects)

| Quadrant | Label | N |
|---|---|---|
| A_both | SMR SNR + AND noise − | 1 |
| B_acq_only | SMR SNR + only | 1 |
| C_damp_only | Noise − only | 1 |
| D_neither | Neither | 2 |

Mechanistic separability: True (B>0 and C>0)

## Per-subject primary quadrant
subject quadrant_primary  delta_smr_snr_log  delta_hb_power_log
sub-004        D_neither          -0.211473            0.115144
sub-005           A_both           0.009691           -0.044974
sub-012      C_damp_only          -0.012392           -0.286697
sub-013       B_acq_only           0.016934            0.120643
sub-018        D_neither          -0.207671            0.085574

## Sensitivity to metric definition
(See nctrl5_definition_sensitivity.csv for all definitions)

## Interpretation

Quadrants B and C are both populated (separability confirmed): some subjects show SMR SNR improvement without HB reduction (B), and others show HB reduction without SMR SNR improvement (C). This empirically demonstrates that target acquisition and noise damping are separable.

Note: n=5 is very small. These classifications are descriptive only and cannot be
statistically confirmed. Results depend on definition of 'SMR improvement' and
'noise damping' (see sensitivity panel). All definitions should be reported to avoid
cherry-picking.

Generated: 2026-07-01T19:05:44.605704+00:00
