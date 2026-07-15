# NF-SQI Field-Deployment Reference Implementation

This repository includes a field-deployment reference implementation for applying NF-SQI reward-window admissibility checks to already acquired or replayed EEG windows.

## Scope

NF-SQI addresses reward-window admissibility: whether a candidate SMR neurofeedback window should be considered acceptable after signal-quality checks. It does not establish neurofeedback efficacy, clinical outcome, individual treatment response, or true hardware streaming validation.

The command-line replay is a pseudo-online replay. It processes previously saved data in online-like windows and is intended to make the implementation inspectable by another lab.

## Calibration Step

Calibration uses a rest baseline with the same channels, sampling rate, units, and preprocessing as the windows that will later be scored. The default configuration uses:

- SMR SNR threshold: 75th percentile of rest.
- High-beta, broadband, noise-floor, and channel-inconsistency thresholds: 75th percentile of rest.
- Transient-amplitude threshold: 90th percentile of rest.

The calibration object records the sampling rate, window and step duration, decision thresholds, and per-channel rest statistics used for channel-inconsistency scoring.

## Window Scoring Step

Each input window should be shaped as channels x samples when calling the Python API. The pseudo-online CLI accepts CSV or NPY data shaped as samples x channels and transposes windows internally.

For each window, the scorer reports:

- `smr_power`
- `smr_snr`
- `high_beta`
- `broadband`
- `noise_floor`
- `transient`
- `channel_inconsistency`
- Gate A/B/C decisions
- Rejection flags and a readable rejection reason

## Gate Logic

Gate A is the SMR-only candidate gate:

```text
accept_gate_a = smr_snr > calibrated SMR-SNR threshold
```

Gate B adds high-beta inhibition:

```text
accept_gate_b = accept_gate_a and high_beta < calibrated high-beta threshold
```

Gate C adds the full NF-SQI quality checks:

```text
accept_gate_c = accept_gate_b
                and broadband < calibrated broadband threshold
                and noise_floor < calibrated noise-floor threshold
                and transient < calibrated transient threshold
                and channel_inconsistency < calibrated channel-inconsistency threshold
```

## Output Fields

The pseudo-online CSV contains one row per scored replay window:

- `timestamp_sec`
- `window_start_sample`
- `window_end_sample`
- `smr_power`
- `smr_snr`
- `high_beta`
- `broadband`
- `noise_floor`
- `transient`
- `channel_inconsistency`
- `accept_gate_a`
- `accept_gate_b`
- `accept_gate_c`
- `rejection_flags`
- `rejection_reason`

`rejection_reason` is `accepted` when no rejection flags are present. Otherwise, it is a semicolon-separated list such as `low_smr_snr`, `high_beta`, `broadband`, `noise_floor`, `transient`, or `channel_inconsistency`.

The JSON sidecar records the config used, calibrated thresholds, window counts, Gate A/B/C accepted counts, rejection counts by flag, input path, sampling rate, and channel list.

## Pseudo-Online Replay Example

```powershell
python scripts\run_nfsqi_pseudo_online.py `
  --input results\final\nfsqi_synthetic_demo_input.csv `
  --config configs\nfsqi_smr_central.yaml `
  --out-csv results\final\nfsqi_pseudo_online_demo.csv `
  --out-json results\final\nfsqi_pseudo_online_demo.json `
  --fs 1000 `
  --channels E36,E104,E128 `
  --rest-start-sample 0 `
  --rest-end-sample 5000
```

## Latency Benchmark Example

```powershell
python scripts\benchmark_nfsqi_latency.py `
  --config configs\nfsqi_smr_central.yaml `
  --n-windows 1000
```

The benchmark is a computational latency benchmark on synthetic EEG-like windows. It is not hardware streaming validation.

## Minimal Online Integration Pseudocode

```python
calibration = calibrate_from_rest(rest_eeg, fs, channels, config)
realtime = NFSQIRealtime.from_calibration(calibration)

for chunk in acquisition_stream:
    decisions = realtime.push(chunk)
    for decision in decisions:
        if decision.admissible:
            deliver_feedback()
        else:
            withhold_feedback()
```

## Reproduction Validation

The repository includes a validation script to test whether the field deployment implementation (`NFSQIRealtime`) logic is coherent and identical to the original analytical pipelines.

Current validation statuses:
- Synthetic pseudo-online demo runs.
- Latency benchmark runs.
- **batch-summary reproduction validation** verifies the final Gate A/B/C counts and identities from the bundled summary CSVs (`results/final`).
- raw-window pseudo-online reproduction was not validated because rest calibration windows were not recovered from task EDFs.
- feature-level validation was not run because window-feature CSVs were not present in the cleaned repo.

To run the batch-summary reproduction validation:

```powershell
python scripts\validate_nfsqi_pseudo_online_reproduction.py `
  --config configs\nfsqi_smr_central.yaml `
  --mode batch-summary `
  --datasets ds004447,ds004444,ds004446 `
  --batch-results-root results\final `
  --out-json results\final\nfsqi_pseudo_online_reproduction_validation.json `
  --out-md results\final\nfsqi_pseudo_online_reproduction_validation.md
```

This script generates a JSON report and a Markdown report (`results/final/nfsqi_pseudo_online_reproduction_validation.md`) comparing expected vs actual counts.
