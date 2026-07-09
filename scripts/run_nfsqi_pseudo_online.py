from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
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


DEFAULT_CONFIG: dict[str, Any] = {
    "window_sec": 1.0,
    "overlap": 0.5,
    "target_metric": "smr_snr",
    "thresholds": {
        "baseline": "rest",
        "smr_percentile": 75,
        "quality_percentile": 75,
        "transient_percentile": 90,
    },
    "outputs": {
        "include_features": True,
        "include_rejection_flags": True,
    },
}


def _coerce_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        return [_coerce_scalar(part) for part in value[1:-1].split(",") if part.strip()]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, data)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, raw_value = line.strip().partition(":")
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if raw_value.strip():
            parent[key] = _coerce_scalar(raw_value)
        else:
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
    return data


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")
    if config_path.suffix.lower() == ".json":
        loaded = json.loads(text)
    else:
        try:
            import yaml  # type: ignore

            loaded = yaml.safe_load(text)
        except ImportError:
            loaded = _minimal_yaml_load(text)
    config = dict(DEFAULT_CONFIG)
    for key, value in (loaded or {}).items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            merged = dict(config[key])
            merged.update(value)
            config[key] = merged
        else:
            config[key] = value
    return config


def threshold_config_from_deployment(config: dict[str, Any]) -> ThresholdConfig:
    thresholds = config.get("thresholds", {})
    quality = float(thresholds.get("quality_percentile", 75))
    return ThresholdConfig(
        smr_snr_percentile=float(thresholds.get("smr_percentile", 75)),
        high_beta_percentile=quality,
        broadband_percentile=quality,
        noise_floor_percentile=quality,
        transient_percentile=float(thresholds.get("transient_percentile", 90)),
        channel_inconsistency_percentile=quality,
        min_valid_windows=3,
    )


def load_eeg(path: str | Path, channels: list[str], delimiter: str) -> tuple[np.ndarray, list[str]]:
    input_path = Path(path)
    if input_path.suffix.lower() == ".npy":
        data = np.load(input_path)
        if data.ndim != 2:
            raise ValueError("NPY input must have shape samples x channels.")
        if data.shape[1] < len(channels):
            raise ValueError("NPY input has fewer columns than requested channels.")
        return np.asarray(data[:, : len(channels)], dtype=float), channels

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        sample = handle.read(4096)
    try:
        sniffed = csv.Sniffer().has_header(sample)
    except csv.Error:
        sniffed = True

    if sniffed:
        array = np.genfromtxt(input_path, delimiter=delimiter, names=True, dtype=float, encoding="utf-8")
        names = list(array.dtype.names or [])
        missing = [channel for channel in channels if channel not in names]
        if names and not missing:
            columns = [np.asarray(array[channel], dtype=float) for channel in channels]
            return np.column_stack(columns), channels
        raw = np.genfromtxt(input_path, delimiter=delimiter, skip_header=1, dtype=float)
    else:
        raw = np.genfromtxt(input_path, delimiter=delimiter, dtype=float)

    if raw.ndim == 1:
        raw = raw.reshape(-1, 1)
    if raw.shape[1] < len(channels):
        raise ValueError("CSV input has fewer columns than requested channels.")
    return np.asarray(raw[:, : len(channels)], dtype=float), channels


def windows_from_samples(samples_by_channels: np.ndarray, fs: float, window_sec: float, step_sec: float) -> list[np.ndarray]:
    window_samples = int(round(window_sec * fs))
    step_samples = int(round(step_sec * fs))
    windows = []
    for start in range(0, samples_by_channels.shape[0] - window_samples + 1, step_samples):
        windows.append(samples_by_channels[start : start + window_samples, :].T)
    return windows


def rejection_reason(flags: tuple[str, ...]) -> str:
    return "accepted" if not flags else ";".join(flags)


def result_row(result: Any, start_sample: int, end_sample: int) -> dict[str, Any]:
    features = result.features
    return {
        "timestamp_sec": result.timestamp_s,
        "window_start_sample": start_sample,
        "window_end_sample": end_sample,
        "smr_power": features.smr_power,
        "smr_snr": features.smr_snr,
        "high_beta": features.high_beta_power,
        "broadband": features.broadband_power,
        "noise_floor": features.noise_floor_power,
        "transient": features.transient_score,
        "channel_inconsistency": features.channel_inconsistency,
        "accept_gate_a": result.gate_A,
        "accept_gate_b": result.gate_B,
        "accept_gate_c": result.gate_C,
        "rejection_flags": ";".join(result.rejection_flags),
        "rejection_reason": rejection_reason(result.rejection_flags),
    }


def write_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp_sec",
        "window_start_sample",
        "window_end_sample",
        "smr_power",
        "smr_snr",
        "high_beta",
        "broadband",
        "noise_floor",
        "transient",
        "channel_inconsistency",
        "accept_gate_a",
        "accept_gate_b",
        "accept_gate_c",
        "rejection_flags",
        "rejection_reason",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run NF-SQI pseudo-online replay as a field-deployment reference implementation."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--fs", required=True, type=float)
    parser.add_argument("--channels", required=True, help="Comma-separated channel names.")
    parser.add_argument("--rest-input")
    parser.add_argument("--rest-start-sample", type=int)
    parser.add_argument("--rest-end-sample", type=int)
    parser.add_argument("--delimiter", default=",")
    args = parser.parse_args(argv)

    channels = [channel.strip() for channel in args.channels.split(",") if channel.strip()]
    config = load_config(args.config)
    window_sec = float(config.get("window_sec", 1.0))
    overlap = float(config.get("overlap", 0.5))
    step_sec = window_sec * (1.0 - overlap)
    if not 0 <= overlap < 1:
        raise ValueError("overlap must be >= 0 and < 1.")

    eeg, channel_list = load_eeg(args.input, channels, args.delimiter)
    if args.rest_input:
        rest_eeg, _ = load_eeg(args.rest_input, channels, args.delimiter)
        task_start_sample = 0
        task_eeg = eeg
    else:
        if args.rest_start_sample is None or args.rest_end_sample is None:
            raise ValueError("Provide --rest-input or both --rest-start-sample and --rest-end-sample.")
        rest_eeg = eeg[args.rest_start_sample : args.rest_end_sample, :]
        task_start_sample = args.rest_end_sample
        task_eeg = eeg[task_start_sample:, :]

    rest_windows = windows_from_samples(rest_eeg, args.fs, window_sec, step_sec)
    calibration, _ = calibrate_nf_sqi_bundle(
        rest_windows,
        args.fs,
        window_s=window_sec,
        step_s=step_sec,
        config=threshold_config_from_deployment(config),
    )

    realtime = NFSQIRealtime.from_calibration(calibration)
    results = realtime.push(task_eeg.T)
    window_samples = int(round(window_sec * args.fs))
    step_samples = int(round(step_sec * args.fs))
    rows = []
    for index, result in enumerate(results):
        start_sample = task_start_sample + index * step_samples
        rows.append(result_row(result, start_sample, start_sample + window_samples))

    write_csv(args.out_csv, rows)

    rejection_counts = Counter()
    for result in results:
        for flag in result.rejection_flags:
            rejection_counts[flag] += 1
    sidecar = {
        "description": "NF-SQI pseudo-online replay field-deployment reference implementation.",
        "config_used": config,
        "thresholds": calibration.limits.to_dict(),
        "number_of_windows": len(results),
        "gate_a_accepted_count": sum(result.gate_A for result in results),
        "gate_b_accepted_count": sum(result.gate_B for result in results),
        "gate_c_accepted_count": sum(result.gate_C for result in results),
        "rejection_counts_by_flag": dict(sorted(rejection_counts.items())),
        "input_file_path": str(Path(args.input)),
        "sampling_rate": args.fs,
        "channel_list": channel_list,
        "window_sec": window_sec,
        "step_sec": step_sec,
        "task_start_sample": task_start_sample,
    }
    output_json = Path(args.out_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    print(
        "NF-SQI pseudo-online replay complete: "
        f"{len(results)} windows, Gate C accepted {sidecar['gate_c_accepted_count']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
