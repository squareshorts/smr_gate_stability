# Canonical project map

## Active source modules
- `src/baseline_gate_stability/core.py` — frozen primitives (agreement, temporal, thresholds).
- `scripts/conjunctive_law_remedy/remedy_methods.py` — R0-R3 methods + percentile transforms.
- `scripts/conjunctive_gate_stability/degradation_common.py` — raw-window loading + faithful feature
  re-extraction (reuses `src/empirical/nf_sqi_t1_features.py`) + frozen D0-D9 transforms.

## Active scripts (scripts/conjunctive_gate_stability/ and scripts/conjunctive_law_remedy/)
- Theorem: `conjunctive_law_remedy/stage1_theorem.py`
- Composition validation: `conjunctive_law_remedy/stage2_validation.py`
- Remedy build/eval: `conjunctive_law_remedy/stage3_6_remedy.py`, `stage3_6_aggregate.py`, `stage6_downstream.py`, `stage8_finalize.py`
- Degradation: `conjunctive_gate_stability/stage2_5_degradation.py`, `stage5_degradation_aggregate.py`
- Figures: `conjunctive_gate_stability/figures_r/*.R`
- Entry points: `conjunctive_gate_stability/{validate_existing_results,run_degradation_verification,build_author_package,run_final_checks}.py`

## Active tests
- `tests/conjunctive_gate_instability/`, `tests/conjunctive_law_remedy/`, `tests/conjunctive_gate_stability/`

## Validated source-result directories (reused, not regenerated)
- `results/conjunctive_gate_instability/` — 31-subset law study + figure data.
- `results/conjunctive_law_remedy/` — theorem, validation, remedy, downstream, author package.
- `results/conjunctive_gate_final/` — degradation, final figures, author package, audit.
- `results/baseline_gate_stability/checkpoints/features/` — canonical per-window cache.
- `results/baseline_gate_stability/checkpoints/downstream_decoder_features/` — decoder features.
- `results/runtime_assurance_remediation/checkpoints/feature_cache/` — reusable feature cache.
- `results/downstream_decoder_validation/fold_definition.csv` — frozen decoder folds.

## Raw data
- `data/raw/openneuro/{ds004447,ds004444,ds004446}` (gitignored; used only for degradation extraction).

## Archived precursors
- `archive/deadends/` (superseded_figures, obsolete_outputs; see archive_index.csv).

## Reproducibility entry point
- `scripts/conjunctive_gate_stability/run_final_checks.py`
