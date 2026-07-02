# NCTRL2 Results: Noise-Control Metrics in Simulation

Generated: 2026-07-01T19:04:33.491603+00:00

## Metrics computed

For each of 81 parameter-grid simulations:
- hb_variance: variance of eta(t)
- hb_burst_rate: bursts per minute above eta_thr = 1.0
- hb_burst_duration_s: mean burst duration
- hb_burst_occupancy: fraction of time above threshold
- hf_noise_floor: std of eta(t)
- diffusion_x: variance of x increments per unit time
- reward_occupancy: fraction in reward-compatible state
- smr_snr: mean(x)^2 / var(x - mean(x))
- broadband_contam: var(z(t))
- false_reward_risk: fraction of reward states with high z

## Key results

Noise-damped regime (k_damp high, burst_occ < 0.15):
  Median SMR SNR = 5.536
  Median diffusion_x = 0.0027
  Median noise floor = 0.321

Non-damped regime:
  Median SMR SNR = 1.567
  Median diffusion_x = 0.0049
  Median noise floor = 1.121

SNR improvement with damping: 3.970
Diffusion reduction with damping: 0.0022

## Interpretation

Active damping improves SMR SNR and reduces state-space diffusion even in cases where
SMR acquisition does not occur (quadrant C). This demonstrates that noise control has
signal-quality benefits independent of the target learning process.

The false-reward risk is elevated when sigma_z (broadband) is high, regardless of k_damp.
This confirms that broadband contamination is a separate failure mode from HB noise.

Generated: 2026-07-01T19:04:33.491603+00:00
