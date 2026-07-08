# NF-SQI Pseudo-online Reproduction Validation

**Purpose:** Verify that field deployment implementation logic matches manuscript expected counts.

**Validation Type:** feature-level reproduction validation.

## Results

| Dataset | Mode | Status | Task windows | Gate A | Gate B | Gate C | Clean Gate A | Quality flagged | HB blocks | Full blocks | Max absolute delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ds004447 | feature-level | PASS | 100 | 50 | 40 | 30 | 30 | 20 | 10 | 20 | 0 |

## Consistency Identities

### ds004447
- gate_a_accepted == clean + quality_flagged: PASS
- gate_c_accepted == clean_gate_a: PASS
- full_nfsqi_blocks == gate_a - gate_c: PASS
- high_beta_blocks == gate_a - gate_b: PASS

## Limitations & Command
Command used:
```bash
python validate_nfsqi_pseudo_online_reproduction.py --config C:\work\smr_cn_revision\configs\nfsqi_smr_central.yaml --mode feature-level --datasets ds004447 --out-json C:\work\smr_cn_revision\.pytest_tmp\test_synthetic_exact_match0\out.json --out-md C:\work\smr_cn_revision\.pytest_tmp\test_synthetic_exact_match0\out.md --data-root C:\work\smr_cn_revision\.pytest_tmp\test_synthetic_exact_match0 --batch-results-root C:\work\smr_cn_revision\.pytest_tmp\test_synthetic_exact_match0
```
