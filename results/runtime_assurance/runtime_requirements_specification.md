# Runtime-assurance requirements specification

Frozen before execution on 2026-07-15. This specification concerns deterministic measurement-admissibility and reward withholding only; it does not validate physiological artifacts, clinical safety, decoder training, or neurofeedback efficacy.

| ID | Requirement and rationale | Component / test method | Pass criterion / artifact | Status |
|---|---|---|---|---|
| R1 | Target evidence must be separate from quality admissibility. | `reference_interlock.evaluate`; independence unit test. | Gate A uses only SMR-SNR; quality changes cannot change Gate A. | pending |
| R2 | Gate C must use quality limits only after a Gate-A request. | Reference evaluator truth-table test. | Gate C is Gate B plus upper-quality checks. | pending |
| R3 | Equal inputs must yield equal decisions. | Repeated deterministic evaluation. | Identical result object and reasons. | pending |
| R4 | Batch and streaming must agree. | Per-window replay under one strict specification. | Zero decision and reason differences. | pending |
| R5 | Boundary behavior must be explicit. | Below/equal/above tests. | Upper-limit equality withholds; target equality does not request. | pending |
| R6 | Withholding must be traceable. | Reason-code replay audit. | Every withhold has >=1 reason. | pending |
| R7 | Processing must precede the 0.5-s hop. | Full feature-plus-decision latency timing. | Maximum observed latency <250 ms (engineering headroom). | pending |
| R8 | Candidate stream must remain nonzero. | Per-session availability. | Gate C accepts >=1 task window per analyzable session. | pending |
| R9 | Availability must not be burst-only. | Gap/run metrics. | Characterize; no universal clinical threshold imposed. | pending |
| R10 | Chattering must be quantified. | Transition/run metrics and variants. | Metrics generated for each session/policy. | pending |
| R11 | Calibration must stabilize with baseline. | Cumulative-rest calibration. | Median relative limit deviation <10% and agreement >95% where evaluable. | pending |
| R12 | Threshold uncertainty must be bounded. | Nonoverlapping-block bootstrap. | Report unstable decisions; no universal pass threshold. | pending |
| R13 | Session transport must be characterized. | First-to-last and reverse replay. | Agreement/shift/availability recorded. | pending |
| R14 | Same policy must operate across datasets. | Shared evaluator for all three snapshots. | All datasets processed without redefinition. | pending |
| R15 | Invalid inputs must fail closed. | Controlled faults. | No acceptance; explicit reason; no top-level exception. | pending |
| R16 | Channel failures must be deterministic. | Missing/flat/nonfinite controlled faults. | Fail closed with reason. | pending |
| R17 | Criterion-level decisions must be interpretable. | Reason-code conformance. | Stable, explicit code per failed criterion. | pending |
| R18 | Configuration must be machine-readable/versioned. | YAML and hash manifest. | Complete runtime specification and hash. | pending |
