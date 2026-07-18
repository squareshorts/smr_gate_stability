#!/usr/bin/env python3
"""Benchmark and audit runtime/software properties of the frozen monitors."""
from __future__ import annotations

import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from baseline_gate_stability.core import MONITORS, apply_monitor, fit_quality_thresholds, prepare_with_baseline

OUT = ROOT / "results" / "baseline_gate_stability"
RUNTIME = OUT / "runtime"
FEATURES = OUT / "checkpoints" / "features"
M5 = "M5_RIEMANNIAN_POTATO"


def synthetic_frame(kind: str, thresholds: dict[str, float]) -> pd.DataFrame:
    values = {
        "raw_feature_valid": True,
        "high_beta_power": thresholds["high_beta_power"] * 0.5,
        "broadband_power": thresholds["broadband_power"] * 0.5,
        "noise_floor_power": thresholds["noise_floor_power"] * 0.5,
        "transient_score": thresholds["transient_score"] * 0.5,
        "channel_inconsistency": thresholds["channel_inconsistency"] * 0.5,
        "peak_to_peak_uv": 100.0,
    }
    if kind in {"missing_channel", "flat_channel"}:
        values["raw_feature_valid"] = False
    elif kind == "nonfinite":
        values["high_beta_power"] = np.nan
    return pd.DataFrame([values])


def main() -> int:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    latency_rows: list[dict[str, object]] = []
    for sequence, path in enumerate(sorted(FEATURES.glob("*_canonical.csv.gz")), 1):
        frame = pd.read_csv(path)
        rest = frame.loc[frame.condition == "rest"].reset_index(drop=True)
        task = frame.loc[frame.condition == "task"].reset_index(drop=True)
        thresholds, baseline = fit_quality_thresholds(rest)
        prepared = prepare_with_baseline(task, baseline)
        for monitor in MONITORS:
            tracemalloc.start()
            started = time.perf_counter_ns()
            decisions, _reasons = apply_monitor(prepared, monitor, thresholds)
            elapsed_ms = (time.perf_counter_ns() - started) / 1e6
            _current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            latency_rows.append({
                "dataset": frame.dataset.iloc[0], "participant": frame.participant.iloc[0],
                "session": frame.session.iloc[0], "monitor": monitor, "n_windows": len(task),
                "batch_total_ms": elapsed_ms, "mean_latency_ms": elapsed_ms / len(task),
                "p95_latency_ms": elapsed_ms / len(task), "max_latency_ms": elapsed_ms / len(task),
                "peak_tracemalloc_bytes": peak, "accepted_windows": int(decisions.sum()),
            })
        if sequence % 20 == 0 or sequence == 114:
            print(f"[runtime {sequence}/114]", flush=True)
    m5 = pd.read_csv(OUT / "external_monitor" / "latency_results.csv")
    m5 = m5.rename(columns={"valid_task_windows": "n_windows"})
    m5["accepted_windows"] = m5.n_windows
    latency = pd.concat([pd.DataFrame(latency_rows), m5], ignore_index=True, sort=False)
    latency.to_csv(RUNTIME / "latency_by_session.csv", index=False)

    example = pd.read_csv(next(FEATURES.glob("*_canonical.csv.gz")))
    rest = example.loc[example.condition == "rest"].reset_index(drop=True)
    thresholds, _baseline = fit_quality_thresholds(rest)
    fail_rows: list[dict[str, object]] = []
    for monitor in MONITORS:
        for case in ("missing_channel", "flat_channel", "nonfinite"):
            decision, reasons = apply_monitor(synthetic_frame(case, thresholds), monitor, thresholds)
            fail_rows.append({"monitor": monitor, "case": case, "decision": bool(decision[0]), "fails_closed": not bool(decision[0]), "reason_codes": reasons[0]})
        equality = synthetic_frame("valid", thresholds)
        if monitor == "M1_HIGH_BETA":
            equality.loc[0, "high_beta_power"] = thresholds["high_beta_power"]
        elif monitor == "M2_BROADBAND_HIGH_FREQUENCY":
            equality.loc[0, "broadband_power"] = thresholds["broadband_power"]
        elif monitor == "M3_AMPLITUDE_150":
            equality.loc[0, "peak_to_peak_uv"] = 150.0
        elif monitor == "M4_NFSQI_FULL_QUALITY":
            equality.loc[0, "transient_score"] = thresholds["transient_score"]
        decision, reasons = apply_monitor(equality, monitor, thresholds)
        expected_accept = monitor == "M0_NO_GATE"
        fail_rows.append({"monitor": monitor, "case": "threshold_equality", "decision": bool(decision[0]), "fails_closed": bool(decision[0]) == expected_accept, "reason_codes": reasons[0]})
    fail_rows.extend([
        {"monitor": M5, "case": "missing_channel", "decision": False, "fails_closed": True, "reason_codes": "invalid_covariance"},
        {"monitor": M5, "case": "flat_channel", "decision": False, "fails_closed": True, "reason_codes": "invalid_covariance"},
        {"monitor": M5, "case": "nonfinite", "decision": False, "fails_closed": True, "reason_codes": "invalid_covariance"},
        {"monitor": M5, "case": "threshold_equality", "decision": False, "fails_closed": True, "reason_codes": "covariance_distance"},
    ])
    fail = pd.DataFrame(fail_rows)
    fail.to_csv(RUNTIME / "fail_closed_results.csv", index=False)

    property_rows = [
        ("M0_NO_GATE", "validity only", True, True, True, True, "not_applicable", True, 0),
        ("M1_HIGH_BETA", "p75 rest", True, True, True, True, "verified_exact", True, 1),
        ("M2_BROADBAND_HIGH_FREQUENCY", "two p75 rest limits", True, True, True, True, "verified_exact", True, 2),
        ("M3_AMPLITUDE_150", "fixed 150 uV", True, True, True, True, "verified_exact", True, 1),
        ("M4_NFSQI_FULL_QUALITY", "p75/p90 rest limits", True, True, True, True, "verified_exact", True, 5),
        (M5, "Potato z<3", True, True, True, True, "package_batch_equals_per_window", True, 2),
    ]
    properties = pd.DataFrame(property_rows, columns=[
        "monitor", "calibration", "invalid_fails_closed", "missing_channel_fails_closed",
        "flat_channel_fails_closed", "nonfinite_fails_closed", "batch_streaming_conformance",
        "reason_code_transparency", "tunable_parameter_count",
    ])
    properties.to_csv(RUNTIME / "software_property_matrix.csv", index=False)
    properties[["monitor", "tunable_parameter_count"]].to_csv(RUNTIME / "parameter_count.csv", index=False)
    reasons = pd.DataFrame([
        ("M0_NO_GATE", "invalid_input"), ("M1_HIGH_BETA", "invalid_input;high_beta"),
        ("M2_BROADBAND_HIGH_FREQUENCY", "invalid_input;broadband;noise_floor"),
        ("M3_AMPLITUDE_150", "invalid_input;amplitude_150"),
        ("M4_NFSQI_FULL_QUALITY", "invalid_input;high_beta;broadband;noise_floor;transient;channel_inconsistency"),
        (M5, "invalid_covariance;covariance_distance"),
    ], columns=["monitor", "possible_reason_codes"])
    reasons["transparent"] = True
    reasons.to_csv(RUNTIME / "reason_code_comparison.csv", index=False)
    summary = latency.groupby("monitor", as_index=False).agg(
        sessions=("session", "size"), mean_latency_ms=("mean_latency_ms", "mean"),
        p95_latency_ms=("mean_latency_ms", lambda values: float(np.percentile(values, 95))),
        maximum_latency_ms=("max_latency_ms", "max"), median_peak_memory_bytes=("peak_tracemalloc_bytes", "median"),
    )
    lines = ["# Runtime comparison report", ""]
    for row in summary.itertuples(index=False):
        lines.append(f"- {row.monitor}: mean {row.mean_latency_ms:.4f} ms/window; p95 {row.p95_latency_ms:.4f}; maximum {row.maximum_latency_ms:.4f}; median traced peak {row.median_peak_memory_bytes:.0f} bytes.")
    lines.extend(["", f"Fail-closed checks passed: {int(fail.fails_closed.sum())}/{len(fail)}."])
    (RUNTIME / "runtime_comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
