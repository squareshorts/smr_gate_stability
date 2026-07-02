# NCTRL4 Results: Empirical Burst/Noise-Instability Analysis

Generated: 2026-07-01T19:05:35.705326+00:00

## Method
Dataset: ds004446, 5 subjects, ses-01 + ses-08
Conditions: ['rest', 'task']
Burst threshold: 75th percentile of HB envelope
Block duration for diffusion: 4.0 s

## Key results

### HB burst characteristics (mean across subjects)
ses-01 burst rate: 58.47 /min | ses-08: 56.97 /min
ses-01 burst occ.: 0.250 | ses-08: 0.250
ses-01 burst dur.: 0.153 s | ses-08: 0.158 s

### HB-broadband correlation (stochastic noise interpretation)
Mean HB-broadband envelope correlation = 0.220
Positive (HB bursts co-occur with broadband fluctuations): consistent with HB as noise event.

### HB-SMR block correlation (suppression interpretation)
Mean HB-SMR block correlation = 0.264
Near zero or positive: HB bursts do not reliably suppress SMR at the block level.

### SMR state-space diffusion
ses-01: 0.0000 | ses-08: 0.0000
SMR diffusion did not decrease from ses-01 to ses-08.

## Interpretation

HB burst metrics are positively correlated with broadband envelope fluctuations (mean r=0.22), suggesting that HB bursts in this dataset co-occur with broadband noise events rather than purely band-specific activity. This is consistent with the active-damping/noise-control hypothesis: HB inhibition may reduce a broader class of high-frequency instability events.

The HB-SMR block correlation = 0.26 does not show reliable suppression of SMR by HB bursts at the block level.

Generated: 2026-07-01T19:05:35.705326+00:00
