# NCTRL3 Results: Empirical High-Frequency Noise-Floor Analysis

Generated: 2026-07-01T19:04:46.183629+00:00

## Dataset
ds004446, 5 subjects, ses-01 + ses-08, conditions: ['rest', 'task']
Channels: ['E36', 'E104', 'E128'] (computed per-channel and as mean)

## Key results

### Band power (mean ± across subjects, mean channel, rest condition)
SMR (12-15 Hz): ses-01 = 0.0000, ses-08 = 0.0000
HB (20-30 Hz): ses-01 = 0.0000, ses-08 = 0.0000

### Aperiodic 1/f slope
ses-01 mean slope: -1.863 (log-log)
ses-08 mean slope: -1.928
Note: A more negative slope = steeper 1/f falloff.
Slope became more negative from ses-01 to ses-08: HF power relatively decreased.

### HB residual above 1/f background
ses-01 mean HB residual: -0.0679 (positive = HB above 1/f background)
ses-08 mean HB residual: -0.0205
HB activity does not clearly exceed the 1/f background; changes may reflect broadband rather than band-specific modulation.

### SMR SNR (P_SMR / (P_HB + P_nontarget))
ses-01: 0.0468
ses-08: 0.0399
Change: -0.0070

### Relative HB power
ses-01: 0.0231
ses-08: 0.0273

## Interpretation

The HB residual above the 1/f aperiodic background is near zero or slightly negative, suggesting that HB changes may partly reflect broadband noise-floor modulation rather than band-specific HB regulation.

The SMR SNR changes (ses-01→ses-08) vary across subjects and are mixed in direction.
This is consistent with the noise-control hypothesis: subjects differ in whether HB reduction
improves SMR SNR (noise damping improves signal quality) or not.

Generated: 2026-07-01T19:04:46.185638+00:00
