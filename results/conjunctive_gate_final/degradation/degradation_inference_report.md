# Degradation paired-inference report

Participant-grouped (dataset,subject) paired R1-R0 response-rate contrasts; bootstrap 4000 resamples over participants; two-sided bootstrap p; BH across families at top severity.

## Top-severity (level 4) pooled paired contrasts (R1 - R0)
- D4_narrowband_20_30: -0.423 [-0.491, -0.355], boot p 0.0003, BH p 0.0003 (n=57)
- D8_full_channel_variance_collapse: -0.352 [-0.396, -0.310], boot p 0.0003, BH p 0.0003 (n=57)
- D7_partial_channel_freeze: -0.333 [-0.375, -0.292], boot p 0.0003, BH p 0.0003 (n=57)
- D6_clipping: -0.308 [-0.379, -0.242], boot p 0.0003, BH p 0.0003 (n=57)
- D1_single_channel_broadband: -0.262 [-0.314, -0.208], boot p 0.0003, BH p 0.0003 (n=57)
- D5_transient_impulse: -0.097 [-0.132, -0.065], boot p 0.0003, BH p 0.0003 (n=57)
- D3_narrowband_35_45: -0.039 [-0.067, -0.018], boot p 0.0003, BH p 0.0003 (n=57)
- D2_common_mode_broadband: -0.035 [-0.054, -0.018], boot p 0.0003, BH p 0.0003 (n=57)

## Severity-response AUC contrast (R1 - R0, mean over severities 1-4)
- D4_narrowband_20_30: R0 AUC 1.00, R1 AUC 0.47, diff -0.530 [-0.593, -0.467], p 0.0003
- D8_full_channel_variance_collapse: R0 AUC 0.24, R1 AUC 0.00, diff -0.241 [-0.277, -0.209], p 0.0003
- D7_partial_channel_freeze: R0 AUC 0.26, R1 AUC 0.05, diff -0.209 [-0.235, -0.183], p 0.0003
- D1_single_channel_broadband: R0 AUC 0.57, R1 AUC 0.37, diff -0.203 [-0.232, -0.173], p 0.0003
- D3_narrowband_35_45: R0 AUC 1.00, R1 AUC 0.82, diff -0.177 [-0.222, -0.136], p 0.0003
- D2_common_mode_broadband: R0 AUC 0.88, R1 AUC 0.71, diff -0.170 [-0.201, -0.138], p 0.0003
- D5_transient_impulse: R0 AUC 0.65, R1 AUC 0.49, diff -0.166 [-0.185, -0.146], p 0.0003
- D6_clipping: R0 AUC 0.16, R1 AUC 0.00, diff -0.163 [-0.209, -0.120], p 0.0003

## Dataset heterogeneity (top-severity contrast range across datasets)
- D1_single_channel_broadband: range 0.233 (min -0.400, max -0.167)
- D4_narrowband_20_30: range 0.231 (min -0.552, max -0.322)
- D6_clipping: range 0.138 (min -0.365, max -0.227)
- D5_transient_impulse: range 0.135 (min -0.175, max -0.040)
- D8_full_channel_variance_collapse: range 0.095 (min -0.395, max -0.300)
- D7_partial_channel_freeze: range 0.060 (min -0.360, max -0.300)
- D3_narrowband_35_45: range 0.054 (min -0.070, max -0.017)
- D2_common_mode_broadband: range 0.051 (min -0.061, max -0.010)

Interpretation: negative R1-R0 means R1 responds LESS than R0 to that degradation.
R1 is significantly less responsive than R0 for single-channel/localized faults (clipping, channel freeze, single-channel broadband) and comparable for common-mode broadband, 35-45 Hz, and transient.
## Baseline-scale sensitivity (prespecified)
The primary campaign scales disturbances by a robust scale from each task window (preserved). The
prespecified sensitivity re-scales by the robust scale from the session rest baseline, holding
selected windows, transforms, methods, thresholds, and severity ordering fixed
(degradation_scale_sensitivity.csv).

- Persistent R1 top-severity blind spots under BOTH scales: D6 clipping, D7 partial channel freeze,
  D8 full channel freeze. The core qualitative conclusion (R1 is insensitive to localized
  clipping/channel-freeze faults) is UNCHANGED by the scale choice.
- Scale-sensitive families: D1 single-channel broadband and D4 20-30 Hz move above the 0.60
  threshold under baseline scale (no longer "blind"), i.e. the breadth of blind spots is
  scale-dependent but the central finding and the DEGRADATION-FAIL verdict are not.
