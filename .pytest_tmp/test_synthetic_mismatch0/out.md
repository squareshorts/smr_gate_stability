# NF-SQI Pseudo-online Reproduction Validation

**Purpose:** Verify that field deployment implementation logic matches manuscript expected counts.

**Validation Type:** feature-level reproduction validation.

## Results

| Dataset | Mode | Status | Task windows | Gate A | Gate B | Gate C | Clean Gate A | Quality flagged | HB blocks | Full blocks | Max absolute delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ds004447 | feature-level | FAIL | 100 | 49 | 40 | 30 | 30 | 19 | 9 | 19 | 1 |

## Consistency Identities

### ds004447
- gate_a_accepted == clean + quality_flagged: PASS
- gate_c_accepted == clean_gate_a: PASS
- full_nfsqi_blocks == gate_a - gate_c: PASS
- high_beta_blocks == gate_a - gate_b: PASS

## Limitations & Command
Command used:
```bash
python validate_nfsqi_pseudo_online_reproduction.py --config C:\work\smr_cn_revision\configs\nfsqi_smr_central.yaml --mode feature-level --datasets ds004447 --out-json C:\work\smr_cn_revision\.pytest_tmp\test_synthetic_mismatch0\out.json --out-md C:\work\smr_cn_revision\.pytest_tmp\test_synthetic_mismatch0\out.md --data-root C:\work\smr_cn_revision\.pytest_tmp\test_synthetic_mismatch0 --batch-results-root C:\work\smr_cn_revision\.pytest_tmp\test_synthetic_mismatch0
```

### Failure in ds004447
Reason: Max delta 1 exceeds tolerance 0 or identity failed
Expected vs Actual:
- task_windows: expected 100, got 100
- gate_a_accepted: expected 50, got 49
- clean_gate_a: expected 30, got 30
- quality_flagged_gate_a: expected 20, got 19
- gate_b_accepted: expected 40, got 40
- gate_c_accepted: expected 30, got 30
- high_beta_blocks: expected 10, got 9
- full_nfsqi_blocks: expected 20, got 19
