# Final package report (submission closure)

**Repository:** C:\work\smr_cn_revision  **Branch:** analysis/conjunctive-gate-final-package  **Base commit:** 2062eb3
**Decision: PACKAGE-GO-B. Readiness: 8.0/10.**

## 1. Paired R1 - R0 degradation contrasts (participant-grouped, top severity; bootstrap 4000; BH-adjusted)
All eight continuous families are significantly negative (R1 responds LESS than R0), BH p = 0.00025 each:
- D1 single-channel broadband: -0.262 [-0.314, -0.208]
- D2 common-mode broadband: -0.035 [-0.054, -0.018]
- D3 35-45 Hz: -0.039 [-0.067, -0.018]
- D4 20-30 Hz: -0.423 [-0.491, -0.355]
- D5 transient impulse: -0.097 [-0.132, -0.065]
- D6 clipping: -0.308 [-0.379, -0.242]
- D7 partial channel freeze: -0.333 [-0.375, -0.292]
- D8 full channel freeze: -0.352 [-0.396, -0.310]
Severity-response AUC contrasts (R1-R0) are negative for all families (degradation_auc_contrasts.csv).

## 2. Dataset heterogeneity (top-severity R1-R0 by dataset)
Direction is consistent across all three datasets for every family (no sign flips). Magnitude varies:
- D6 clipping: ds004447 -0.227 / ds004444 -0.365 / ds004446 -0.320
- D8 full freeze: -0.305 / -0.395 / -0.300
- D4 20-30 Hz: -0.552 / -0.322 / -0.460
- D1 single-ch broadband: -0.361 / -0.167 / -0.400
No dataset shows a response collapse for a degradation detected in the others.

## 3. Baseline-scale sensitivity (prespecified)
Re-scaling disturbances by the session rest-baseline robust scale (windows/transforms/methods/
thresholds/severity unchanged): the core R1 blind spots — D6 clipping, D7 partial freeze, D8 full
freeze (all top-severity R1 response ~0.00) — PERSIST under both scales. D1 and D4 move just above the
0.60 threshold under baseline scale. Qualitative conclusion and DEGRADATION-FAIL verdict are unchanged;
only the breadth of marginal blind spots is scale-dependent (degradation_scale_sensitivity.csv).

## 4. Figures (revised; rendered on host)
10 title-free R sources (Windows/Linux-safe via commandArgs(--file=)) + frozen source data +
value-validation. Figure 1 (J_old/J_new/condition), 5 (session-level by dataset + 0.80 line + proportions),
6 (separate composition vs transport panels), 7 (transitions/min, accepted/min, duty cycle, longest gap;
matched-availability flagged), 9 (R0/R1 curves + paired top-severity CI + separated D0/D9 controls),
10 (categorical evidence matrix). Not rendered in sandbox (host R unreachable); render via
scripts/conjunctive_gate_stability/render_figures_windows.ps1. Paths in figure_source_map.csv;
0 zero-byte figures (none rendered yet; QC pending host render).

## 5. Tests
32 passed, 0 failed (final_test_results.txt).

## 6. Protected-path status
raw exit 1 (pre-existing CRLF only); CRLF-insensitive exit 0; manuscript-only exit 0. Manuscript untouched.

## 7. Repository changes
44 tracked-modified files (pre-existing CRLF workstream) + one intended source fix
(src/empirical/nf_sqi_t1_features.py deprecated standalone main; extract_window_features preserved) +
.gitignore. All new analysis code/outputs untracked. scripts/__init__.py restored. Old
conjunctive_law_remedy author package marked PRECURSOR; conjunctive_gate_final/author_package is active.
No canonical script imports an archived dead-end. Raw data and local envs untracked. Deletion not
possible on this mount (rm denied); disposable caches gitignored.

## 8. Remaining limitations
- DEGRADATION-FAIL: R1 is significantly less responsive than R0 to localized single-channel faults
  (clipping, channel freeze) and single-channel broadband; its stability is partly insensitivity.
- R1 does not meet the 30% transition-reduction target (~15%).
- Figures authored but not rendered in sandbox (host render + visual QC pending).
- Composition prediction exact only under independence; no natural-artifact ground truth; retrospective.

## 9. Final readiness
PACKAGE-GO-B, 8.0/10. Theorem + composition validation + R1 remedy are strong and reproducible; the
honest degradation limitation and pending host figure render preclude GO-A.
