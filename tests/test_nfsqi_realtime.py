from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import numpy as np

from empirical.nf_sqi_realtime import (
    NFSQICalibration,
    NFSQIRealtime,
    ThresholdConfig,
    calibrate_nf_sqi_bundle,
    evaluate_nf_sqi_window,
)

ROOT = Path(__file__).resolve().parents[1]


def _scratch_dir() -> Path:
    path = ROOT / "results" / "test_tmp" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _synthetic_windows(n_windows: int = 12, fs: float = 128.0, channels: int = 3) -> list[np.ndarray]:
    rng = np.random.default_rng(42)
    samples = int(fs)
    times = np.arange(samples) / fs
    windows = []
    for _ in range(n_windows):
        smr = np.sin(2 * np.pi * 13.0 * times + rng.uniform(0, 2 * np.pi))
        beta = 0.2 * np.sin(2 * np.pi * 24.0 * times + rng.uniform(0, 2 * np.pi))
        noise = rng.normal(0, 0.5, size=(channels, samples))
        windows.append(1e-6 * (smr + beta + noise))
    return windows


def _calibration(fs: float = 128.0):
    return calibrate_nf_sqi_bundle(
        _synthetic_windows(fs=fs),
        fs,
        config=ThresholdConfig(min_valid_windows=5),
    )[0]


def test_calibration_returns_expected_threshold_keys() -> None:
    calibration = _calibration()
    thresholds = calibration.limits.to_dict()
    assert {
        "smr_snr_min",
        "high_beta_max",
        "broadband_max",
        "noise_floor_max",
        "transient_max",
        "channel_inconsistency_max",
        "nonstationarity_max",
    } <= set(thresholds)


def test_calibration_serializes_and_deserializes() -> None:
    scratch = _scratch_dir()
    try:
        calibration = _calibration()
        output = scratch / "calibration.json"
        calibration.save_json(output)
        loaded = NFSQICalibration.load_json(output)
        assert loaded.fs == calibration.fs
        assert loaded.limits.to_dict() == calibration.limits.to_dict()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_score_window_returns_expected_feature_fields() -> None:
    calibration = _calibration()
    window = _synthetic_windows(n_windows=1)[0]
    result = evaluate_nf_sqi_window(
        window,
        calibration.fs,
        calibration.limits,
        calibration.channel_baseline,
    )
    features = result.features.to_dict()
    assert {
        "smr_power",
        "smr_snr",
        "high_beta_power",
        "broadband_power",
        "noise_floor_power",
        "transient_score",
        "channel_inconsistency",
    } <= set(features)


def test_gate_window_fields_and_rejection_reason_are_interpretable() -> None:
    calibration = _calibration()
    window = _synthetic_windows(n_windows=1)[0]
    result = evaluate_nf_sqi_window(
        window,
        calibration.fs,
        calibration.limits,
        calibration.channel_baseline,
    )
    row = result.to_dict()
    assert {"gate_A", "gate_B", "gate_C"} <= set(row)
    assert isinstance(row["rejection_flags"], str)
    reason = row["rejection_flags"] or "accepted"
    assert reason == "accepted" or all(part for part in reason.split(";"))


def test_realtime_push_returns_expected_decisions() -> None:
    calibration = _calibration()
    realtime = NFSQIRealtime.from_calibration(calibration)
    chunk = np.concatenate(_synthetic_windows(n_windows=3), axis=1)
    results = realtime.push(chunk)
    assert len(results) >= 3
    assert all(isinstance(result.gate_C, bool) for result in results)


def _write_demo_csv(path: Path, fs: int = 128, channels: tuple[str, ...] = ("E36", "E104", "E128")) -> None:
    rng = np.random.default_rng(123)
    samples = fs * 8
    times = np.arange(samples) / fs
    data = []
    for channel_index in range(len(channels)):
        phase = channel_index * 0.25
        signal = np.sin(2 * np.pi * 13.0 * times + phase)
        signal += 0.25 * np.sin(2 * np.pi * 24.0 * times + phase)
        signal += rng.normal(0, 0.5, size=samples)
        data.append(1e-6 * signal)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(channels)
        writer.writerows(zip(*data))


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return env


def test_pseudo_online_script_writes_csv_and_json() -> None:
    scratch = _scratch_dir()
    try:
        input_csv = scratch / "demo.csv"
        output_csv = scratch / "out.csv"
        output_json = scratch / "out.json"
        _write_demo_csv(input_csv)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_nfsqi_pseudo_online.py"),
                "--input",
                str(input_csv),
                "--config",
                str(ROOT / "configs" / "nfsqi_smr_central.yaml"),
                "--out-csv",
                str(output_csv),
                "--out-json",
                str(output_json),
                "--fs",
                "128",
                "--channels",
                "E36,E104,E128",
                "--rest-start-sample",
                "0",
                "--rest-end-sample",
                "512",
            ],
            check=True,
            cwd=ROOT,
            env=_subprocess_env(),
        )
        assert output_csv.exists()
        assert output_json.exists()
        sidecar = json.loads(output_json.read_text(encoding="utf-8"))
        assert sidecar["number_of_windows"] > 0
        assert "gate_c_accepted_count" in sidecar
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_latency_benchmark_writes_json() -> None:
    scratch = _scratch_dir()
    try:
        output_json = scratch / "latency.json"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "benchmark_nfsqi_latency.py"),
                "--config",
                str(ROOT / "configs" / "nfsqi_smr_central.yaml"),
                "--n-windows",
                "5",
                "--fs",
                "128",
                "--channels",
                "3",
                "--out-json",
                str(output_json),
            ],
            check=True,
            cwd=ROOT,
            env=_subprocess_env(),
        )
        result = json.loads(output_json.read_text(encoding="utf-8"))
        assert result["n_windows"] == 5
        assert result["mean_ms"] >= 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
