# NF-SQI Field-Deployment Report

## Files Added Or Modified

- Added `src/empirical/nf_sqi_realtime.py`
- Added `configs/nfsqi_smr_central.yaml`
- Added `scripts/run_nfsqi_pseudo_online.py`
- Added `scripts/benchmark_nfsqi_latency.py`
- Added `tests/test_nfsqi_realtime.py`
- Added `docs/nfsqi_deployment.md`
- Added `results/final/nfsqi_synthetic_demo_input.csv`
- Added `results/final/nfsqi_pseudo_online_demo.csv`
- Added `results/final/nfsqi_pseudo_online_demo.json`
- Added `results/final/nfsqi_latency_benchmark.json`
- Updated `README.md`

No LaTeX manuscript, bibliography, abstract, title, paper figure, or paper-text file was edited.

## Public Realtime API

- `ThresholdConfig`
- `NFSQLimits`
- `ChannelBaseline`
- `NFSQICalibration`
- `NFSQIWindowFeatures`
- `NFSQIResult`
- `extract_realtime_features`
- `calibrate_nf_sqi`
- `calibrate_nf_sqi_bundle`
- `evaluate_nf_sqi_window`
- `NFSQIRealtime`

## Commands Tested

Pseudo-online replay:

```powershell
python scripts\run_nfsqi_pseudo_online.py --input results\final\nfsqi_synthetic_demo_input.csv --config configs\nfsqi_smr_central.yaml --out-csv results\final\nfsqi_pseudo_online_demo.csv --out-json results\final\nfsqi_pseudo_online_demo.json --fs 1000 --channels E36,E104,E128 --rest-start-sample 0 --rest-end-sample 5000
```

Latency benchmark:

```powershell
python scripts\benchmark_nfsqi_latency.py --config configs\nfsqi_smr_central.yaml --n-windows 1000
```

Verification:

```powershell
$env:PYTHONPATH="src"
python -m py_compile src\empirical\nf_sqi_realtime.py
python -m pytest
```

## Pytest Result

- `tests/test_nfsqi_realtime.py`: 7 passed.

## Latency Benchmark Numbers

The benchmark is a computational latency benchmark on synthetic EEG-like windows, not hardware streaming validation.

- Mean: 1.286 ms/window
- Median: 1.175 ms/window
- P95: 1.941 ms/window
- Max: 3.316 ms/window
- Windows: 1000
- Sampling rate: 1000 Hz
- Window length: 1.0 s
- Channels: 3
- Platform: Windows-10-10.0.26200-SP0
- Python: 3.10.11

These values are computationally compatible with online use for the configured 0.5 s step on this machine, but they do not constitute real-time hardware validation.

## Demo Output Paths

- Synthetic input: `results/final/nfsqi_synthetic_demo_input.csv`
- Pseudo-online CSV: `results/final/nfsqi_pseudo_online_demo.csv`
- Pseudo-online JSON: `results/final/nfsqi_pseudo_online_demo.json`
- Latency JSON: `results/final/nfsqi_latency_benchmark.json`

Demo pseudo-online counts:

- Number of replay windows: 13
- Gate A accepted: 3
- Gate B accepted: 2
- Gate C accepted: 0
- Rejection counts: `low_smr_snr=10`, `high_beta=5`, `broadband=3`, `noise_floor=4`, `transient=6`, `channel_inconsistency=9`

## Limitations

- The replay script is a pseudo-online replay over stored CSV/NPY data.
- EDF support is not included in the deployment CLI.
- The latency benchmark uses synthetic EEG-like windows.
- The implementation does not validate acquisition hardware, operating-system scheduling, closed-loop feedback timing, clinical efficacy, or neurofeedback outcomes.
- Calibration and scoring must use consistent sampling rate, channel order, units, and preprocessing.

## Manuscript-Relevant Facts To Add Later

Potential sentence for a future manuscript/tooling note:

> A repository-level field-deployment reference implementation was added for NF-SQI pseudo-online replay over CSV/NPY data, including rest-baseline calibration, per-window Gate A/B/C decisions, JSON/CSV outputs, automated tests, and a synthetic 1000-window computational latency benchmark showing mean 1.286 ms, median 1.175 ms, and P95 1.941 ms per 1-s, 3-channel window on the tested Windows/Python 3.10.11 environment.
