# NF-SQI Pseudo-online Reproduction Validation

**Purpose:** Verify that field deployment implementation logic matches manuscript expected counts.

**Validation Type:** feature-level reproduction validation.

## Results

| Dataset | Mode | Status | Task windows | Gate A | Gate B | Gate C | Clean Gate A | Quality flagged | HB blocks | Full blocks | Max absolute delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ds004447 | feature-level | SKIPPED | - | - | - | - | - | - | - | - | - |

## Consistency Identities

## Limitations & Command
Command used:
```bash
python C:\work\smr_cn_revision\scripts\validate_nfsqi_pseudo_online_reproduction.py --config C:\work\smr_cn_revision\configs\nfsqi_smr_central.yaml --mode feature-level --datasets ds004447 --out-json C:\work\smr_cn_revision\.pytest_tmp\test_missing_data_skipped0\out.json --out-md C:\work\smr_cn_revision\.pytest_tmp\test_missing_data_skipped0\out.md --data-root C:\work\smr_cn_revision\.pytest_tmp\test_missing_data_skipped0 --batch-results-root C:\work\smr_cn_revision\.pytest_tmp\test_missing_data_skipped0 --allow-missing-data
```

### Skipped ds004447
Reason: Expected batch targets missing for ds004447
