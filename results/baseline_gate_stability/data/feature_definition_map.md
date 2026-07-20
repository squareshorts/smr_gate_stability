# Feature definition map

Canonical NF-SQI scalar and per-channel bandpower features are reused unchanged from the verified runtime-assurance cache. Window start, condition/segment, maximum three-channel peak-to-peak amplitude, and six unique covariance entries are appended from a single session-level EDF read using the identical 1 s window and 0.5 s hop. M4 is the quality-only full monitor and deliberately excludes Gate A; `reference_gate_c` retains Gate A for exact conformance reproduction.
