# Reproducibility commands

All commands run from the repository root with `PYTHONPATH="$PWD:$PWD/src"`.

## Default final check (no heavy rerun)
```
python scripts/conjunctive_gate_stability/run_final_checks.py
```
Validates saved law + remedy + degradation outputs, all figure source data, runs tests, checks
protected paths, and writes the final output manifest. Does NOT reload EDFs, rerun the 31-subset
analysis, rerun all decoder fits, or rerun Riemannian Potato.

## Validate existing results only
```
python scripts/conjunctive_gate_stability/validate_existing_results.py
```

## Re-run controlled degradation (resumable, checkpointed; uses raw EDF)
```
python scripts/conjunctive_gate_stability/run_degradation_verification.py
python scripts/conjunctive_gate_stability/stage5_degradation_aggregate.py
```

## Render figures (host R)
```
cd scripts/conjunctive_gate_stability/figures_r
for f in figure*.R; do Rscript "$f"; done
```

## Build author package
```
python scripts/conjunctive_gate_stability/build_author_package.py
```

## Tests
```
python -m pytest tests/conjunctive_gate_instability tests/conjunctive_law_remedy tests/conjunctive_gate_stability -q
```

## Protected-path check (must be clean, CRLF-insensitive)
```
git diff --ignore-cr-at-eol --exit-code -- manuscript results/final
```
