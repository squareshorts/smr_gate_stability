# Frozen comparative analysis plan

Frozen before comparative monitor outcomes were computed on this branch.

Operational unit: dataset-participant-session. Inferential unit: dataset-participant. Task windows are evaluated identically across calibration variants. All calibration uses rest windows only. No task label, decoder outcome, or held-out session enters threshold fitting.

Monitors: M0 no quality gate; M1 high beta; M2 broadband/high-frequency; M3 fixed 150 microvolt peak-to-peak screen; M4 full NF-SQI quality criteria without the independent Gate-A reward-request criterion; M5 faithful Riemannian Potato if verified, otherwise the frozen ROBUST_COV_DISTANCE fallback.

Primary analysis: accepted-set Jaccard across first/second rest halves, odd/even nonoverlapping rest blocks, paired independent temporal block-bootstrap draws, and available duration versus full rest. Secondary analyses: cross-session transport, inherent operational availability, downstream decoder information cost, latency, fail-closed behavior, and reason-code transparency.

Negative, null, and mixed findings are retained. No monitor is treated as an artifact detector without independent ground truth.
