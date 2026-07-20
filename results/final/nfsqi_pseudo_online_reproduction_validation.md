# NF-SQI Pseudo-online Reproduction Validation

**Purpose:** Verify that field deployment implementation logic matches manuscript expected counts.

**Validation Type:** batch-summary reproduction validation.

## Results

| Dataset | Mode | Status | Task windows | Gate A | Gate B | Gate C | Clean Gate A | Quality flagged | HB blocks | Full blocks | Max absolute delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ds004447 | batch-summary | PASS | 5218 | 905 | 779 | 472 | 472 | 433 | 126 | 433 | 0 |
| ds004444 | batch-summary | PASS | 14400 | 2455 | 1811 | 933 | 933 | 1522 | 644 | 1522 | 0 |
| ds004446 | batch-summary | PASS | 2800 | 451 | 355 | 215 | 215 | 236 | 96 | 236 | 0 |

## Consistency Identities

### ds004447
- gate_a_accepted == clean + quality_flagged: PASS
- gate_c_accepted == clean_gate_a: PASS
- full_nfsqi_blocks == gate_a - gate_c: PASS
- high_beta_blocks == gate_a - gate_b: PASS

### ds004444
- gate_a_accepted == clean + quality_flagged: PASS
- gate_c_accepted == clean_gate_a: PASS
- full_nfsqi_blocks == gate_a - gate_c: PASS
- high_beta_blocks == gate_a - gate_b: PASS

### ds004446
- gate_a_accepted == clean + quality_flagged: PASS
- gate_c_accepted == clean_gate_a: PASS
- full_nfsqi_blocks == gate_a - gate_c: PASS
- high_beta_blocks == gate_a - gate_b: PASS

## Limitations & Command
Command used:
```bash
python scripts\validate_nfsqi_pseudo_online_reproduction.py --config configs\nfsqi_smr_central.yaml --mode batch-summary --datasets ds004447,ds004444,ds004446 --batch-results-root archive\stale_pending_delete\results_submission_readiness --out-json results\final\nfsqi_pseudo_online_reproduction_validation.json --out-md results\final\nfsqi_pseudo_online_reproduction_validation.md
```
