# Input cache audit

- Cache directory: `results/baseline_gate_stability/checkpoints/features`
- Sessions found: 114 (expected 114) -> PASS
- Unique participants: 57 (expected 57) -> PASS
- Datasets present: ['ds004444', 'ds004446', 'ds004447'] -> PASS
- Config hashes (must be single): ['73958aa880e6eb76e9e47325054c0a7a2b231467a05a5f4915c8c3a6157f5a4d'] -> PASS
- Required features present in every session -> PASS

## Canonical decision reproduction (recomputed vs cached)
- M0_NO_GATE: 0 differing windows
- M1_HIGH_BETA: 0 differing windows
- M2_BROADBAND_HIGH_FREQUENCY: 0 differing windows
- M3_AMPLITUDE_150: 0 differing windows
- M4_NFSQI_FULL_QUALITY: 0 differing windows

## Pooled count reproduction
- ds004444: compared=14400, decision_differences=0
- ds004446: compared=2800, decision_differences=0
- ds004447: compared=5218, decision_differences=0
- pooled: compared=22418, decision_differences=0

## VERDICT: CACHE VALID — proceed

Same evaluation windows are guaranteed for every gate subset because all subsets
are evaluated on the identical per-session task-window index from this single cache.