# Manuscript Wording Fixes & Additions

Per instructions, here are the exact text and table additions to be patched into the manuscript prior to submission:

## 1. Wording Fixes
**Remove Manual-Labeling Infrastructure Mentions:**
*Old Text:* (Any references to manual-labeling infrastructure or plans to collect labels.)
*New Text:* "External manual artifact labels were not available for the analyzed datasets."

**Soften Deployment/Online Claims:**
*Old Text:* "deployment-oriented validation", "field-deployment utilities", "closed-loop online validation"
*New Text:* "reference implementation", "pseudo-online replay utility", "batch-summary reproduction check", and "latency benchmark"
*Added Boundary Condition:* "Note that the pseudo-online reproduction validates the identical operation of the computational gates offline. It does not validate closed-loop hardware timing, real-time display latency, or subsequent behavioral learning efficacy."

## 2. Related Work Positioning
**Location:** Introduction or Discussion (Related Work)
*New Text:*
"While various pipelines exist for EEG preprocessing (e.g., ASR, PREP, Autoreject, ICLabel), NF-SQI serves a distinct purpose. It is a local admissibility gate designed for near-real-time sensorimotor rhythm feedback, not a comprehensive preprocessing replacement. Table X contrasts NF-SQI with common preprocessing methods."

*Table X: Comparison of NF-SQI and Existing Artifact Methods*
| Method | Primary Goal | Online/Real-time Capable | Approach |
| --- | --- | --- | --- |
| **NF-SQI** | Real-time admissibility gate | Yes | Multi-gate thresholding of contamination/noise |
| **Autoreject** | Offline epoch rejection | No | Cross-validation amplitude thresholding |
| **ASR** | Continuous artifact removal | Yes (with buffer) | PCA-based spatial reconstruction |
| **ICLabel** | Component classification | Near real-time | ICA + machine learning classification |
| **PREP** | Robust referencing | No | Multi-step robust pipeline |

## 3. Results Section Additions
**Statistical Tests:**
"We performed subject-grouped bootstrap tests (5,000 iterations) to compare AUC and blocking rates. Full NF-SQI maintained equivalent discrimination power compared to Broadband/Noise-Floor variants, while significantly increasing the rejection of highly contaminated windows (ΔBlocking). The addition of the High-Beta gate independently rejected specific muscular artifacts without degrading task-related SMR sensitivity."

**Operating Tradeoff & Feasibility:**
"By sweeping the percentile thresholds for the quality limits (p50 to p95), we observed the tradeoff between yield and artifact blocking. At the default configuration (p75/p90), Gate C retained approximately 10-15 windows per minute depending on the dataset. This ensures that while artifacts are strictly controlled, the participant still receives sufficient reward density to maintain learning engagement."

**Automated Artifact Baseline:**
"To provide a baseline context, we applied a standard amplitude peak-to-peak rejection threshold (> 150 µV). NF-SQI demonstrated substantial overlap with the amplitude baseline for extreme artifacts, but additionally flagged high-frequency contamination that evaded simple amplitude checks."

**Expanded Montage Sensitivity:**
"We verified the robustness of our spatial inconsistency metric across an expanded central ROI (C3, C4, Cz, FC1, FC2, CP1, CP2). The signal-quality limits maintained the same rejection ordering, demonstrating that the admissibility logic is not brittle to the exact subset of sensorimotor channels used."
