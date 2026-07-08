from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from empirical.nf_sqi_realtime import (  # noqa: E402
    NFSQIRealtime,
    ThresholdConfig,
    calibrate_nf_sqi_bundle,
)

from run_nfsqi_pseudo_online import load_config, threshold_config_from_deployment  # noqa: E402


def synthetic_eeg(n_windows: int, fs: float, channels: int, window_sec: float, rng: np.random.Generator) -> np.ndarray:
    samples = int(round(window_sec * fs))
    times = np.arange(samples, dtype=float) / fs
    data = np.empty((n_windows, channels, samples), dtype=float)
    for index in range(n_windows):
        smr = np.sin(2 * np.pi * 13.0 * times + rng.uniform(0, 2 * np.pi))
        beta = 0.35 * np.sin(2 * np.pi * 24.0 * times + rng.uniform(0, 2 * np.pi))
        noise = rng.normal(0, 0.5, size=(channels, samples))
        scale = 1e-6 * (1.0 + 0.03 * index / max(n_windows, 1))
        data[index] = scale * (smr + beta + noise)
    return data


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an NF-SQI computational latency benchmark.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--n-windows", type=int, default=1000)
    parser.add_argument("--fs", type=float, default=1000)
    parser.add_argument("--channels", type=int, default=3)
    parser.add_argument("--out-json", default="results/final/nfsqi_latency_benchmark.json")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    window_sec = float(config.get("window_sec", 1.0))
    overlap = float(config.get("overlap", 0.5))
    step_sec = window_sec * (1.0 - overlap)
    rng = np.random.default_rng(20260708)

    rest = synthetic_eeg(20, args.fs, args.channels, window_sec, rng)
    calibration, _ = calibrate_nf_sqi_bundle(
        rest,
        args.fs,
        window_s=window_sec,
        step_s=step_sec,
        config=threshold_config_from_deployment(config),
    )
    realtime = NFSQIRealtime.from_calibration(calibration)
    windows = synthetic_eeg(args.n_windows, args.fs, args.channels, window_sec, rng)

    durations_ms: list[float] = []
    accepted = 0
    for window in windows:
        start = time.perf_counter()
        result = realtime.evaluate_window(window)
        durations_ms.append((time.perf_counter() - start) * 1000.0)
        accepted += int(result.gate_C)

    output: dict[str, Any] = {
        "description": "NF-SQI computational latency benchmark.",
        "mean_ms": statistics.fmean(durations_ms),
        "median_ms": statistics.median(durations_ms),
        "p95_ms": percentile(durations_ms, 95),
        "max_ms": max(durations_ms),
        "n_windows": args.n_windows,
        "fs": args.fs,
        "window_sec": window_sec,
        "channels": args.channels,
        "gate_c_accepted_count": accepted,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
    }

    output_path = Path(args.out_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    compatibility = ""
    if output["p95_ms"] < 0.5 * step_sec * 1000.0:
        compatibility = " This is computationally compatible with online use for the configured step."
    print(
        "NF-SQI computational latency benchmark: "
        f"mean={output['mean_ms']:.3f} ms, median={output['median_ms']:.3f} ms, "
        f"p95={output['p95_ms']:.3f} ms, max={output['max_ms']:.3f} ms."
        f"{compatibility}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
