# Downstream information-cost report

M0-M4 reuse the verified event labels, session-held-out folds, decoder features, models, and seeds. M5 is added as a completed training-only quality mask; every test session remains unfiltered.

Count matching uses the frozen M4 class-specific retained counts, matching the verified comparator analysis.

- M1_HIGH_BETA minus M0_NO_GATE: -0.0016 balanced accuracy (95% bootstrap CI -0.0056 to +0.0025; p=0.4283; n=57).
- M2_BROADBAND_HIGH_FREQUENCY minus M0_NO_GATE: -0.0116 balanced accuracy (95% bootstrap CI -0.0196 to -0.0036; p=0.0070; n=57).
- M3_AMPLITUDE_150 minus M0_NO_GATE: -0.0010 balanced accuracy (95% bootstrap CI -0.0032 to +0.0012; p=0.3911; n=54).
- M4_NFSQI_FULL_QUALITY minus M0_NO_GATE: -0.0164 balanced accuracy (95% bootstrap CI -0.0265 to -0.0068; p=0.0010; n=57).
- M5_RIEMANNIAN_POTATO minus M0_NO_GATE: -0.0006 balanced accuracy (95% bootstrap CI -0.0013 to -0.0000; p=0.0486; n=57).

Nonviable fold-monitor-analysis records: 9.
