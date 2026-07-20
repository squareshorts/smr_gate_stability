# Quality-only policy definitions

All policies apply to finite, correctly labelled *training* windows only and are applied symmetrically to rest and task. Thresholds are fit from the training session rest baseline using the released p75/p90 policy.

- `ALL`: no quality filter.
- `HB`: high-beta pass only.
- `BBHF`: broadband and high-frequency-reference pass.
- `NFSQI_NO_HB`: broadband, high-frequency-reference, transient, and channel-consistency pass.
- `NFSQI_FULL`: high-beta, broadband, high-frequency-reference, transient, and channel-consistency pass.
- `AMPLITUDE_150`: existing 150 microvolt peak-to-peak baseline.

No policy contains Gate A, an SMR threshold, target positivity, reward candidacy, decoder output, or a task label.
