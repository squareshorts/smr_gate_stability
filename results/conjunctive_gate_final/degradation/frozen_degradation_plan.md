# Frozen controlled-degradation plan

Frozen before any degraded signal was created. Do not edit after results.

## Purpose (scope)
Engineering verification of whether the R1 MEAN_PERCENTILE single-score gate gained calibration
stability merely by becoming insensitive to meaningful controlled measurement degradation. This is
controlled measurement-degradation testing and a comparison of gate-response properties. It is NOT
natural-artifact validation, artifact ground truth, clinical validation, proof of neurofeedback
efficacy, or proof of artifact removal.

## Methods
Primary: R0 ORIGINAL_AND vs R1 MEAN_PERCENTILE. Secondary sensitivity only: R2 RMS_PERCENTILE.
R3 excluded from the primary campaign. R1 is not tuned; the final p75 threshold is frozen.

## Source windows (Stage 2)
Real task EEG windows, canonical three-channel montage (E36,E104,E128), 1 s window, 0.5 s hop,
canonical sampling rate. Eligibility: structurally valid, finite, and accepted by BOTH R0 and R1
under the primary p75 calibration before degradation. Up to 10 eligible windows per session,
distributed approximately evenly, avoiding adjacent overlapping windows; all eligible if fewer than
10; sessions with <5 eligible are reported. Deterministic selection (fixed seed 20260717).
Mandatory reproduction: unchanged-window features match canonical within tolerance and R0/R1
decisions reproduce exactly.

## Robust scale
Per channel, robust_sigma = 1.4826 * MAD(channel_signal). Disturbance amplitudes are defined
relative to this robust standard-deviation-equivalent scale.

## Degradation families
D0 unchanged copy; D1 single-channel broadband; D2 common-mode broadband; D3 35–45 Hz narrowband;
D4 20–30 Hz narrowband; D5 transient impulse; D6 clipping/saturation; D7 partial channel freeze
(temporal fraction); D8 full channel variance collapse (top severity = fully frozen); D9 missing
channel / structurally invalid (fail-closed, single structural level, not imputed).
Affected single channel balanced across E36/E104/E128 by window index mod 3 (deterministic).
D1–D8 use four severity levels defined in frozen_degradation_definitions.yaml. Narrowband uses
deterministic phase; impulses use frozen duration/location/sign/amplitude; clipping limits frozen.
Original EDF files are never modified; only degraded copies of extracted windows are created.

## Endpoints & criteria
See frozen_degradation_success_criteria.md and expected_response_matrix.csv. Response = a window
accepted before degradation is withheld after degradation. Primary comparison is requirements-based
response behaviour, not synthetic-label classification AUC.
