# Canonical pipeline map

The count-reproduction gate used the released implementation, with only a thin isolated wrapper to prevent writes outside this analysis directory.

| Purpose | Canonical entry point | Inputs | Output / rule |
|---|---|---|---|
| Dataset paths and event sidecar resolution | `src/empirical/nf_sqi_common.py:read_events_for_edf` | EDF path, raw duration | Reads `*_task-smrbmi_events.tsv`; converts millisecond onsets when necessary. |
| Channel definition | `src/empirical/nf_sqi_common.py:SENSORIMOTOR_CHANNELS` | EDF channel names | `E36`, `E104`, `E128`. |
| Window features | `src/empirical/nf_sqi_t1_features.py:extract_window_features` | Three-channel 1 s raw window, sampling rate | Welch band powers, transient amplitude, and per-channel band powers. |
| Batch channel inconsistency | `src/empirical/nf_sqi_t1_features.py:main` and `src/analysis_replication/step3_apply_companion_datasets.py:extract_dataset_features` | Session rows, rest rows | Rest-standardized across-channel SD averaged over SMR, beta, broadband, and noise bands. |
| Batch thresholds and gates | `src/empirical/nf_sqi_t2_t3_gates_and_admissibility.py` | Rest feature distribution | p75 for SMR-SNR, high beta, broadband, noise floor, channel inconsistency; p90 transient. Batch pass convention is inclusive at a threshold (`not >` contamination), explaining the ds004444 tie. |
| Streaming thresholds and decision | `src/empirical/nf_sqi_realtime.py:calibrate_nf_sqi_bundle`, `evaluate_nf_sqi_window` | Training/session rest windows then raw scored windows | Same bands and p75/p90 policy; streaming quality checks use strict `<` comparisons. |
| Released replay entry point | `scripts/run_nfsqi_pseudo_online_real_edf.py` | `data/raw/openneuro/<dataset>` first/last session trees | Task windows use `mean(task samples) > 0.5`, 1 s windows and 0.5 s hop. |

The fixed input snapshot is OpenNeuro `1.0.1` for all datasets. ds004447 uses all 22 participants' first/last sessions (44 EDFs); ds004444 uses all 30 participants' first/last sessions (60 EDFs); ds004446 uses the release-defined `sub-004`, `sub-005`, `sub-012`, `sub-013`, and `sub-018` first/last (`ses-01`, `ses-08`) sessions (10 EDFs). This selection is identified by the released replay session tables and reproduced exactly above.

The wrapper `scripts/downstream_decoder_validation/reproduce_batch_counts.py` imports the canonical `extract_window_features` function; it changes only destination isolation, not windowing, features, thresholds, montage, event parsing, or gate arithmetic.
