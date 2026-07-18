# Conjunctive-gate stability — active project

The active scientific project is: **conjunctive instability in baseline-calibrated EEG quality
gates, its mathematical composition theorem, and a single-score remedy.** The original
NF-SQI-as-ready-interlock / general-baseline-gate-instability / runtime-interlock / scheduler
narratives are abandoned (see `archive/deadends/` and result_provenance.md).

## Scope of the active project
- The composition theorem (accepted-set stability of conjunctive gates).
- The 31-subset empirical composition validation (parameter-free).
- The R1 single-score remedy (mean-percentile); R2 (RMS) sensitivity; R3 (Mahalanobis) negative.
- Downstream information preservation.
- Controlled measurement-degradation verification.
- No claim of natural-artifact ground truth, clinical validation, or neurofeedback efficacy.

## Entry points (scripts/conjunctive_gate_stability/)
- `validate_existing_results.py` — validate saved law + remedy + degradation outputs (no heavy rerun).
- `run_degradation_verification.py` — resumable controlled-degradation campaign (checkpointed).
- `render_all_figures.R` — render the 10 final figures from frozen source data (host R).
- `build_author_package.py` — assemble the author package artifacts.
- `run_final_checks.py` — default final check (validation + tests + protected paths + manifest).

See canonical_project_map.md, analysis_dependency_graph.md, reproducibility_commands.md,
result_provenance.md. Config: `configs/conjunctive_gate_stability/final_project.yaml`.
