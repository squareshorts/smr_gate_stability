# NF-SQI Pseudo-online Reproduction Validation

**Purpose:** Verify that pseudo-online replay reproduces manuscript gate counts using identical windows, channels, and thresholds.

**Data Sources:** Raw OpenNeuro datasets in `archive/stale_pending_delete/data/data/raw/openneuro` and batch outputs in `archive/stale_pending_delete/results_submission_readiness`.

**Validation Type:** Raw-window replay. Using `raw-window replay`.

## Results

| Dataset | Mode | Status | Task windows | Gate A | Gate B | Gate C | Clean Gate A | Quality flagged | HB blocks | Full blocks | Max absolute delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ds004446 | raw-window replay | FAIL | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2800 |

## Limitations & Command
Validation requires OpenNeuro raw data availability, and simulates field deployment using equivalent parameters. Latency benchmarks and online adaptation require real hardware in-the-loop.

Command used:
```bash
python scripts\validate_nfsqi_pseudo_online_reproduction.py --config configs\nfsqi_smr_central.yaml --datasets ds004446 --out-json results\final\nfsqi_pseudo_online_reproduction_validation_ds004446.json --out-md results\final\nfsqi_pseudo_online_reproduction_validation_ds004446.md
```

### Failure in ds004446
Reason: Max delta 2800 exceeds tolerance 0
Expected vs Actual:
- task_windows: expected 2800, got 0
- gate_a_accepted: expected 451, got 0
- clean_gate_a: expected 215, got 0
- quality_flagged_gate_a: expected 236, got 0
- gate_b_accepted: expected 355, got 0
- gate_c_accepted: expected 215, got 0
- high_beta_blocks: expected 96, got 0
- full_nfsqi_blocks: expected 236, got 0
