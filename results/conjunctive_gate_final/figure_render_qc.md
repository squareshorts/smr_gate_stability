# Figure render-QC (revised 7+1 set)

## Figure set
Seven main figures + one supplementary, consolidated from the earlier provisional set:
- figure1_composition_theorem — 3 panels (A gate G under G1/G2 with P1,P2,Q,J_old; B added criterion a,b,c; C J_new + exact monotonicity condition + symmetric corollary).
- figure2_composition_validation — A pooled observed vs predicted (31 subsets, colour/shape by K, identity line, Spearman 0.988 / MAE 0.013 annotated); B by dataset.
- figure3_cardinality_lattice — A Jaccard vs K (observed + predicted + overall agreement, grey = participant-grouped 95% CI); B per-criterion contribution (Q1-Q5, points + participant-grouped intervals, zero line, ordered by median).
- figure4_stability_transport — A session-level split-half Jaccard by method x dataset (boxplot + 0.80 line + % sessions >=0.80); B transport Jaccard points + participant-grouped 95% point-range by method x dataset.
- figure5_operational_behavior — A acceptance proportion, B accepted windows/min, C longest no-acceptance interval, D transitions/min; R0/R1/R2; local_p75 vs matched_availability; separate y-scales.
- figure6_downstream_information — A natural-retention vs no gate (R1/R2/R3, 95% CI, zero line); B count-matched vs R0 (95% CI, zero line).
- figure7_controlled_degradation — A D1-D8 severity curves (R0/R1 primary, R2 secondary line); B top-severity paired R1-R0 with 95% CI; C unchanged-copy reproduction + missing-channel fail-closed (labelled software/structural controls).
- figureS1_evidence_scorecard — supplementary study-defined verification scorecard (verified/strong/pass/limited/fail), frozen-criteria source in caption.

Method abbreviations R0/R1/R2/R3; dataset order ds004447/ds004444/ds004446. Multi-panel figures use
patchwork if available, else panels are saved separately. Colorblind palette (Okabe-Ito), shapes +
linetypes for grayscale, base font 10 pt, panel labels A/B/C, no titles, no in-figure conclusions.

## Sandbox-side validation (completed)
- Source-data values assembled ONLY from frozen result tables / checkpoints (no recompute).
- figure_value_validation.csv: all figures ok, max abs discrepancy < 1e-3 (only a 1.5e-5 rounding gap
  vs a 4-dp published stability table).
- Forbidden-token scan over all R scripts: CLEAN (no ggtitle, labs(title=, plot_annotation(title, main=).
- Dataset order and method labels enforced in source data (factor levels).

## Host-side validation (REQUIRED, pending)
R is not reachable from the analysis sandbox, so PDFs/PNGs are NOT rendered here and visual QC is NOT
marked passed. Render on the host:
  powershell -File scripts\conjunctive_gate_stability\render_figures_windows.ps1
The PowerShell entry point fails on any missing/zero-byte PDF or PNG and writes R_sessionInfo.txt +
render_log.txt. Then open each PDF and verify: nonzero size, >=8 pt fonts, no clipped strip labels,
no overlap, visible CIs, identity/zero/0.80 reference lines present, grayscale readable, values equal
the figure_data CSVs. Only then move the superseded provisional figures (old figureN_*.R stubs and any
old rendered outputs) to archive/deadends/superseded_figures/.

## Current QC status: PENDING HOST RENDER (source-data + no-title validation PASSED in sandbox).

## S1 root-cause fix (pipeline-level)
figureS1 previously failed with "cannot open file 'common.R'" when a figure script was executed
directly with Rscript (working directory = repo root, so the bare relative `source("common.R")` could
not be found). Fixed at the shared pipeline level:
- The sole supported entry point is `render_all_figures.R`, which resolves `project_root` and
  `figure_script_dir` and injects them via `options(CGS_PROJECT_ROOT=, CGS_FIGURE_SCRIPT_DIR=)`.
- It renders exactly the figures listed in `configs/conjunctive_gate_stability/final_figures.csv`
  (S1 included) — not a filename regex — sourcing each with `source(path, chdir=TRUE, local=new.env(parent=globalenv()))`.
- Every final figure script now loads common.R via `file.path(getOption("CGS_FIGURE_SCRIPT_DIR"),"common.R")`
  with a guard that errors if run outside the entry point; no bare `source("common.R")` remains.
- The PowerShell wrapper calls ONLY `render_all_figures.R` and verifies outputs against the manifest.
Public command: `powershell -ExecutionPolicy Bypass -File scripts\conjunctive_gate_stability\render_figures_windows.ps1`
