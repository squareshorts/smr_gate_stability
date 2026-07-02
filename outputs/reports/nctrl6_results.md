# NCTRL6 Results: Closed-Loop Reward-Quality Analysis

Generated: 2026-07-01T19:06:51.643707+00:00

## Method

Proxy reward states (no direct feedback markers in ds004446):
- Clean target: SMR > session-median AND HB < session-median AND broad < broad-median
- Noisy target: SMR > session-median AND (HB or broad above median)
- Clean non-target: SMR ≤ median AND HB < median
- Noisy non-target: SMR ≤ median AND HB or broad above median

Block size: 4.0 s. State transitions computed as empirical probabilities.

## Key results

### Mean state occupancies (rest condition)
ses-01: clean_target=0.128, noisy_target=0.365
ses-08: clean_target=0.117, noisy_target=0.375

### Reward-state quality
False-reward risk: ses-01 = 0.741 | ses-08 = 0.761
Change: +0.020 (risk increased or unchanged)

Reward purity: ses-01 = 0.259 | ses-08 = 0.239
Change: -0.020 (purity decreased or unchanged)

## Interpretation

The false-reward risk did not consistently decrease from ses-01 to ses-08. Reward-state quality was not reliably improved by the training session.

Note: These classifications use proxy criteria (median-based thresholds). Without direct
reward/inhibit timing markers from the neurofeedback software, true reward-state analysis
cannot be performed. Results should be interpreted as proxy estimates only.

Generated: 2026-07-01T19:06:51.648332+00:00
