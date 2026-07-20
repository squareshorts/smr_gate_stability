# Controlled-degradation final report

VERDICT: **DEGRADATION-FAIL**

- Source windows: 1140 across 114 sessions; feature reproduction max rel diff 7.4e-13.
- Unchanged control (D0): R1 false-withhold 0.0000, decision reproduction 1.0000.
- Fail-closed (D9 missing/invalid): R0 1.000, R1 1.000.

## Top-severity response (level 4)
- D1_single_channel_broadband: R0 0.80, R1 0.54 (R1-R0 -0.26)
- D2_common_mode_broadband: R0 1.00, R1 0.96 (R1-R0 -0.04)
- D3_narrowband_35_45: R0 1.00, R1 0.96 (R1-R0 -0.04)
- D4_narrowband_20_30: R0 1.00, R1 0.58 (R1-R0 -0.42)
- D5_transient_impulse: R0 0.99, R1 0.89 (R1-R0 -0.10)
- D6_clipping: R0 0.31, R1 0.00 (R1-R0 -0.31)
- D7_partial_channel_freeze: R0 0.34, R1 0.00 (R1-R0 -0.33)
- D8_full_channel_variance_collapse: R0 0.35, R1 0.00 (R1-R0 -0.35)

## What R0 detects but R1 under-detects (R1 >15pp below R0 at top severity):
- D1_single_channel_broadband: R1 26pp below R0
- D4_narrowband_20_30: R1 42pp below R0
- D6_clipping: R1 31pp below R0
- D7_partial_channel_freeze: R1 33pp below R0
- D8_full_channel_variance_collapse: R1 35pp below R0

## Blind spots (R1 top response < 0.60):
- D1_single_channel_broadband: R1 top 0.54
- D4_narrowband_20_30: R1 top 0.58
- D6_clipping: R1 top 0.00
- D7_partial_channel_freeze: R1 top 0.00
- D8_full_channel_variance_collapse: R1 top 0.00

## Did R1 gain stability by becoming generally insensitive? YES — R1 is materially less responsive than R0 across multiple fault families.
## Monotonic (nondecreasing) families: 7/8.
## DEGRADATION result: DEGRADATION-FAIL.