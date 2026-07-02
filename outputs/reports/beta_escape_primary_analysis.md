# Primary Beta-State Persistence Analysis

Created: 2026-07-02T12:39:03.673226+00:00

Dataset analyzed: `ds004447` (larger empirical dataset).

Predeclared definitions:

- SMR band: 12-15 Hz.
- High-beta band: 20-30 Hz.
- Broadband control: 4-45 Hz excluding SMR and high-beta for power metrics.
- Sensorimotor channels: E36, E104, E128, following the family helper-code C3/C4/Cz equivalents.
- Primary high-beta episode threshold: subject/session rest-baseline 75th percentile high-beta envelope.
- Sensitivity thresholds computed: 80th percentile, 90th percentile, z-score, MAD.
- S1 high-beta state excludes bins classified as S2 broadband/artifact state.

Primary task-condition sample:

- Subjects with early/late task contrasts: 22.
- Mean high-beta power change: -0.104226.
- Mean S1 dwell-time change: -0.00147972 s.
- Mean long-burst fraction change: -0.0129162.
- Mean escape-rate change: 0.103291 per s.
- Mean S1 re-entry probability change: -0.00945437.

Interpretation boundary:

These are real-EEG early/late contrasts. They do not establish causality and they do not treat event-derived states as reward states because no true reward/feedback markers were detected.
