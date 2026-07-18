# Frozen success criteria

A. Calibration stability

Preferred success:

- pooled median accepted-set Jaccard >= 0.85;
- target >= 0.90 if achievable without post hoc tuning;
- at least 80% of sessions with Jaccard >= 0.80;
- pooled median overall decision agreement >= 0.97;
- no dataset with median accepted-set Jaccard < 0.75.

B. Temporal availability

Preferred success:

- pooled median longest feedback-free period <= 20 s;
- fewer than 10% of sessions with a feedback-free period >30 s;
- median accepted feedback availability retains at least 50% of instantaneous Gate C availability;
- no dataset-level availability collapse.

C. Chattering

Preferred success:

- median displayed-feedback transitions <=4/min;
- availability retention >=50%;
- no increase in invalid-input acceptance;
- exact deterministic replay.

D. External baseline

- implement at least one faithful, recognized EEG/BMI signal-quality monitor, or document why Riemannian Potato/RPF is unavailable or technically invalid and use one defensible online-compatible alternative labeled accurately;
- compare under the same data, calibration, and temporal metrics;
- no universal-superiority claim is required.

E. Controlled degradation response

- expected gate component responds to the specified degradation;
- unrelated components do not dominate unexpectedly;
- false withholding on unchanged control copies is quantified;
- limitations and blind spots are explicitly reported.

F. Reproducibility

- exact batch-streaming identity preserved;
- all tests pass;
- canonical configuration is machine readable;
- manuscript and protected final outputs remain untouched.
