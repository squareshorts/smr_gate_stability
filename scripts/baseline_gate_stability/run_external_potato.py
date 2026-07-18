#!/usr/bin/env python3
"""Run the faithful pyRiemann Potato in the isolated external environment."""
from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
import time
import traceback
import tracemalloc
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyriemann
from pyriemann.clustering import Potato
from pyriemann.utils.distance import distance_riemann


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from scripts.baseline_gate_stability.analyze_stability_transport_availability import (
    grouped_bootstrap_summary,
    segmented_temporal_metrics,
    split_samples,
)
from baseline_gate_stability.core import agreement_metrics


OUT = ROOT / "results" / "baseline_gate_stability"
EXT = OUT / "external_monitor"
CKPT = OUT / "checkpoints" / "external_monitor"
FEATURE_CKPT = OUT / "checkpoints" / "features"
LOG_DIR = OUT / "checkpoints" / "logs"
ENV_DIR = ROOT / "environments" / "external_monitor"
MONITOR = "M5_RIEMANNIAN_POTATO"
HOP = 0.5
DURATIONS = (15, 30, 60, 90, 120)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(message: str) -> None:
    with (LOG_DIR / "external_potato.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{now()} {message}\n")
    print(message, flush=True)


def atomic_csv(frame: pd.DataFrame, path: Path, compression: str | None = None) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False, compression=compression)
    tmp.replace(path)


def covariances(frame: pd.DataFrame) -> np.ndarray:
    values = frame[["cov_00", "cov_01", "cov_02", "cov_11", "cov_12", "cov_22"]].to_numpy(float)
    matrices = np.empty((len(frame), 3, 3), dtype=float)
    matrices[:, 0, 0] = values[:, 0]
    matrices[:, 0, 1] = matrices[:, 1, 0] = values[:, 1]
    matrices[:, 0, 2] = matrices[:, 2, 0] = values[:, 2]
    matrices[:, 1, 1] = values[:, 3]
    matrices[:, 1, 2] = matrices[:, 2, 1] = values[:, 4]
    matrices[:, 2, 2] = values[:, 5]
    return matrices


def valid_spd(matrices: np.ndarray) -> np.ndarray:
    finite = np.isfinite(matrices).all(axis=(1, 2))
    result = np.zeros(len(matrices), dtype=bool)
    if finite.any():
        result[finite] = np.linalg.eigvalsh(matrices[finite]).min(axis=1) > 0
    return result


def fit_potato(calibration: pd.DataFrame) -> Potato:
    matrices = covariances(calibration)
    valid = valid_spd(matrices)
    if valid.sum() < 20:
        raise ValueError(f"Insufficient valid rest covariance matrices: {valid.sum()}")
    return Potato(metric="riemann", threshold=3.0, n_iter_max=100).fit(matrices[valid])


def safe_predict(model: Potato, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    matrices = covariances(frame)
    valid = valid_spd(matrices)
    decisions = np.zeros(len(frame), dtype=bool)
    z_scores = np.full(len(frame), np.nan)
    if valid.any():
        decisions[valid] = model.predict(matrices[valid]).astype(int) == 1
        z_scores[valid] = model.transform(matrices[valid])
    reasons = ["" if decisions[index] else ("covariance_distance" if valid[index] else "invalid_covariance") for index in range(len(frame))]
    return decisions, z_scores, reasons


def model_rows(dataset: str, participant: str, session: str, split_type: str, side: str, model: Potato, rest_windows: int) -> list[dict[str, object]]:
    rows = []
    for i in range(3):
        for j in range(i, 3):
            rows.append(
                {
                    "dataset": dataset, "participant": participant, "session": session, "monitor": MONITOR,
                    "split_type": split_type, "side": side, "rest_windows": rest_windows,
                    "threshold_z": 3.0, "distance_log_mean": float(model._mean), "distance_log_std": float(model._std),
                    "covmean_element": f"{i}{j}", "covmean_value": float(model.covmean_[i, j]),
                }
            )
    return rows


def enrich(left: np.ndarray, right: np.ndarray) -> dict[str, float | int]:
    result = agreement_metrics(left, right)
    result["accepted_windows_per_min_difference"] = float(result["acceptance_rate_difference"]) * 60.0 / HOP
    result["mutual_withholding_fraction"] = float(np.mean(~left & ~right)) if len(left) else np.nan
    return result


def analyze_session(path: Path) -> dict[str, pd.DataFrame]:
    frame = pd.read_csv(path)
    dataset, participant, session = str(frame.dataset.iloc[0]), str(frame.participant.iloc[0]), str(frame.session.iloc[0])
    key = f"{dataset}_{participant}_{session}"
    rest = frame[frame.condition == "rest"].sort_values("window_start_s").reset_index(drop=True)
    task = frame[frame.condition == "task"].sort_values("window_start_s").reset_index(drop=True)
    stability_rows, calibration_rows, decision_rows, duration_rows, nonviable_rows = [], [], [], [], []
    for split_name, (left_rest, right_rest) in split_samples(rest, key).items():
        try:
            left_model, right_model = fit_potato(left_rest), fit_potato(right_rest)
            left, left_z, left_reasons = safe_predict(left_model, task)
            right, right_z, right_reasons = safe_predict(right_model, task)
            row = {"dataset": dataset, "participant": participant, "session": session, "monitor": MONITOR, "split_type": split_name, "left_rest_windows": len(left_rest), "right_rest_windows": len(right_rest)}
            row.update(enrich(left, right))
            stability_rows.append(row)
            calibration_rows.extend(model_rows(dataset, participant, session, split_name, "left", left_model, len(left_rest)))
            calibration_rows.extend(model_rows(dataset, participant, session, split_name, "right", right_model, len(right_rest)))
            for index, window_id in enumerate(task.window_id):
                decision_rows.append({"dataset": dataset, "participant": participant, "session": session, "monitor": MONITOR, "split_type": split_name, "task_window_index": index, "window_id": window_id, "left_decision": bool(left[index]), "right_decision": bool(right[index]), "left_z": left_z[index], "right_z": right_z[index], "left_reason_codes": left_reasons[index], "right_reason_codes": right_reasons[index]})
        except Exception as exc:
            nonviable_rows.append({"dataset": dataset, "participant": participant, "session": session, "analysis": split_name, "reason": repr(exc)})
    full_model = fit_potato(rest)
    full_decisions, full_z, full_reasons = safe_predict(full_model, task)
    all_windows = frame.sort_values(["condition", "window_start_s"]).reset_index(drop=True)
    all_decisions, all_z, all_reasons = safe_predict(full_model, all_windows)
    calibration_rows.extend(model_rows(dataset, participant, session, "full", "full", full_model, len(rest)))
    for duration in DURATIONS:
        n = int(duration / HOP)
        if n > len(rest):
            continue
        try:
            model = fit_potato(rest.iloc[:n].reset_index(drop=True))
            partial, _z, _reasons = safe_predict(model, task)
            row = {"dataset": dataset, "participant": participant, "session": session, "monitor": MONITOR, "duration_s": duration, "rest_windows": n, "full_rest_windows": len(rest)}
            row.update(enrich(partial, full_decisions))
            duration_rows.append(row)
            calibration_rows.extend(model_rows(dataset, participant, session, f"duration_{duration}s", "partial", model, n))
        except Exception as exc:
            nonviable_rows.append({"dataset": dataset, "participant": participant, "session": session, "analysis": f"duration_{duration}s", "reason": repr(exc)})
    availability, runs = segmented_temporal_metrics(task, full_decisions)
    availability_row = {"dataset": dataset, "participant": participant, "session": session, "monitor": MONITOR, **availability}
    run_rows = [{"dataset": dataset, "participant": participant, "session": session, "monitor": MONITOR, **run} for run in runs]
    matrices = covariances(task)
    valid = valid_spd(matrices)
    timings = []
    for matrix in matrices[valid]:
        start = time.perf_counter_ns()
        model_prediction = full_model.predict(matrix[None, :, :])
        timings.append((time.perf_counter_ns() - start) / 1e6)
        if int(model_prediction[0]) not in (0, 1):
            raise RuntimeError("Unexpected Potato prediction label")
    tracemalloc.start()
    start = time.perf_counter_ns()
    safe_predict(full_model, task)
    batch_ms = (time.perf_counter_ns() - start) / 1e6
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    latency_row = {
        "dataset": dataset, "participant": participant, "session": session, "monitor": MONITOR,
        "valid_task_windows": int(valid.sum()), "mean_latency_ms": float(np.mean(timings)),
        "p95_latency_ms": float(np.percentile(timings, 95)), "max_latency_ms": float(np.max(timings)),
        "batch_total_ms": batch_ms, "batch_per_window_ms": batch_ms / len(task), "peak_tracemalloc_bytes": peak,
    }
    full_decision_rows = pd.DataFrame({
        "dataset": dataset,
        "participant": participant,
        "session": session,
        "condition": all_windows.condition,
        "window_index": all_windows.groupby("condition").cumcount(),
        "window_id": all_windows.window_id,
        "monitor": MONITOR,
        "decision": all_decisions,
        "z_score": all_z,
        "reason_codes": all_reasons,
    })
    return {
        "stability": pd.DataFrame(stability_rows),
        "calibration": pd.DataFrame(calibration_rows),
        "decisions": pd.DataFrame(decision_rows),
        "duration": pd.DataFrame(duration_rows),
        "availability": pd.DataFrame([availability_row]),
        "runs": pd.DataFrame(run_rows),
        "latency": pd.DataFrame([latency_row]),
        "full_decisions": full_decision_rows,
        "nonviable": pd.DataFrame(nonviable_rows, columns=["dataset", "participant", "session", "analysis", "reason"]),
    }


def analyze_transport(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in paths]
    frames.sort(key=lambda frame: str(frame.session.iloc[0]))
    rows = []
    for source, target, direction in ((frames[0], frames[-1], "first_to_final"), (frames[-1], frames[0], "final_to_first")):
        dataset, participant = str(source.dataset.iloc[0]), str(source.participant.iloc[0])
        source_rest = source[source.condition == "rest"].reset_index(drop=True)
        target_rest = target[target.condition == "rest"].reset_index(drop=True)
        task = target[target.condition == "task"].sort_values("window_start_s").reset_index(drop=True)
        source_model, local_model = fit_potato(source_rest), fit_potato(target_rest)
        transported, _z1, _r1 = safe_predict(source_model, task)
        local, _z2, _r2 = safe_predict(local_model, task)
        temporal, _runs = segmented_temporal_metrics(task, transported)
        row = {"dataset": dataset, "participant": participant, "source_session": str(source.session.iloc[0]), "target_session": str(target.session.iloc[0]), "direction": direction, "monitor": MONITOR}
        row.update(enrich(transported, local))
        row.update({"transported_accepted_windows_per_min": temporal["accepted_windows_per_min"], "transported_longest_feedback_free_s": temporal["longest_feedback_free_s"], "transported_transitions_per_min": temporal["state_transitions_per_min"], "centroid_riemann_distance": float(distance_riemann(source_model.covmean_, local_model.covmean_))})
        rows.append(row)
    return pd.DataFrame(rows)


def write_environment_and_tests() -> None:
    python = Path(sys.executable)
    freeze = subprocess.run([str(python), "-m", "pip", "freeze"], check=True, capture_output=True, text=True).stdout
    payload = f"Python: {platform.python_version()}\nExecutable: isolated .venv/Scripts/python.exe\nInstall command: python -m pip install -r requirements_external_monitor.txt\npyRiemann: {pyriemann.__version__}\n\n{freeze}"
    digest = hashlib.sha256(payload.encode()).hexdigest()
    (EXT / "environment_manifest.txt").write_text(payload + f"\nEnvironment manifest SHA256: {digest}\n", encoding="utf-8")
    clean = np.stack([np.eye(3) * (1 + index / 100) for index in range(30)])
    model = Potato(metric="riemann", threshold=3).fit(clean)
    finite_prediction = int(model.predict(np.eye(3)[None, :, :])[0])
    equality_accepts = bool(3.0 < model.threshold)
    invalid_frame = pd.DataFrame([{name: np.nan for name in ("cov_00", "cov_01", "cov_02", "cov_11", "cov_12", "cov_22")}])
    invalid_decision = bool(safe_predict(model, invalid_frame)[0][0])
    singular_frame = pd.DataFrame([{"cov_00": 1, "cov_01": 0, "cov_02": 0, "cov_11": 0, "cov_12": 0, "cov_22": 0}])
    singular_decision = bool(safe_predict(model, singular_frame)[0][0])
    (EXT / "implementation_tests.txt").write_text(
        f"three_channel_fit=pass\nfinite_identity_prediction={finite_prediction}\nnonfinite_fails_closed={not invalid_decision}\nsingular_fails_closed={not singular_decision}\nthreshold_equality_accepts={equality_accepts}\nmetric=riemann\nthreshold=3.0\n",
        encoding="utf-8",
    )


def main() -> int:
    for path in (EXT, CKPT, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
    write_environment_and_tests()
    feature_paths = sorted(FEATURE_CKPT.glob("*_canonical.csv.gz"))
    collected = {name: [] for name in ("stability", "calibration", "decisions", "duration", "availability", "runs", "latency", "full_decisions", "nonviable")}
    errors = []
    progress_path = OUT / "execution_progress.csv"
    progress = pd.read_csv(progress_path) if progress_path.exists() else pd.DataFrame()
    for sequence, path in enumerate(feature_paths, 1):
        key = path.name.removesuffix("_canonical.csv.gz")
        paths = {name: CKPT / f"{key}_{name}.csv.gz" for name in collected}
        try:
            if all(value.exists() and value.stat().st_size > 20 for value in paths.values()):
                result = {name: pd.read_csv(value) for name, value in paths.items()}
                status = "reused"
            else:
                result = analyze_session(path)
                for name, frame in result.items():
                    if frame.empty:
                        frame = pd.DataFrame(columns=frame.columns if len(frame.columns) else ["empty"])
                    atomic_csv(frame, paths[name], "gzip")
                status = "created"
            for name, frame in result.items():
                if not frame.empty and list(frame.columns) != ["empty"]:
                    collected[name].append(frame)
            progress = pd.concat([progress, pd.DataFrame([{
                "timestamp": now(), "stage": "external_potato", "sequence": sequence,
                "total": len(feature_paths), "dataset": key.split("_")[0],
                "participant": key.split("_")[1], "session": "_".join(key.split("_")[2:]),
                "status": status,
            }])], ignore_index=True)
            atomic_csv(progress, progress_path)
            log(f"[session {sequence}/114] {key} {status}")
        except Exception as exc:
            parts = key.split("_")
            errors.append({"timestamp": now(), "stage": "external_potato", "dataset": parts[0], "participant": parts[1], "session": "_".join(parts[2:]), "error": repr(exc)})
            (LOG_DIR / f"{key}_external_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            log(f"[error {sequence}/114] {key}: {exc!r}")
    if errors:
        error_path = OUT / "execution_errors.csv"
        pd.DataFrame(errors).to_csv(error_path, mode="a", header=not error_path.exists(), index=False)
        raise RuntimeError(f"External monitor session errors: {len(errors)}")
    stability = pd.concat(collected["stability"], ignore_index=True)
    calibration = pd.concat(collected["calibration"], ignore_index=True)
    decisions = pd.concat(collected["full_decisions"], ignore_index=True)
    duration = pd.concat(collected["duration"], ignore_index=True)
    availability = pd.concat(collected["availability"], ignore_index=True)
    latency = pd.concat(collected["latency"], ignore_index=True)
    nonviable = pd.concat(collected["nonviable"], ignore_index=True) if collected["nonviable"] else pd.DataFrame(columns=["dataset", "participant", "session", "analysis", "reason"])
    calibration.to_csv(EXT / "calibration_outputs.csv", index=False)
    decisions.to_csv(EXT / "decisions_by_window.csv", index=False)
    stability.to_csv(EXT / "stability_results_by_session.csv", index=False)
    subject_stability = stability.groupby(["dataset", "participant", "monitor", "split_type"], as_index=False).median(numeric_only=True)
    stability_summary = grouped_bootstrap_summary(subject_stability, ["monitor", "split_type"], ["accepted_set_jaccard", "overall_agreement", "positive_agreement", "negative_agreement", "mutual_withholding_fraction"])
    rates = stability.groupby(["monitor", "split_type"], as_index=False).agg(sessions=("session", "size"), percent_sessions_jaccard_ge_0_80=("accepted_set_jaccard", lambda values: 100 * float(np.mean(values >= 0.80))))
    stability_summary.merge(rates, on=["monitor", "split_type"]).to_csv(EXT / "stability_results.csv", index=False)
    duration.to_csv(EXT / "duration_results.csv", index=False)
    grouped: dict[tuple[str, str], list[Path]] = {}
    for path in feature_paths:
        one = pd.read_csv(path, usecols=["dataset", "participant"], nrows=1)
        grouped.setdefault((str(one.dataset.iloc[0]), str(one.participant.iloc[0])), []).append(path)
    transport_frames = []
    for sequence, ((dataset, participant), paths) in enumerate(sorted(grouped.items()), 1):
        checkpoint = CKPT / f"transport_{dataset}_{participant}.csv.gz"
        if checkpoint.exists() and checkpoint.stat().st_size > 100:
            result = pd.read_csv(checkpoint)
        else:
            result = analyze_transport(paths)
            atomic_csv(result, checkpoint, "gzip")
        transport_frames.append(result)
        log(f"[transport {sequence}/57] {dataset}_{participant}")
    transport = pd.concat(transport_frames, ignore_index=True)
    transport.to_csv(EXT / "transport_results_by_pair.csv", index=False)
    transport_subject = transport.groupby(["dataset", "participant", "monitor", "direction"], as_index=False).median(numeric_only=True)
    grouped_bootstrap_summary(transport_subject, ["monitor", "direction"], ["accepted_set_jaccard", "overall_agreement", "transported_longest_feedback_free_s", "transported_transitions_per_min"]).to_csv(EXT / "transport_results.csv", index=False)
    availability.to_csv(EXT / "availability_results_by_session.csv", index=False)
    availability_subject = availability.groupby(["dataset", "participant", "monitor"], as_index=False).median(numeric_only=True)
    availability_summary = grouped_bootstrap_summary(availability_subject, ["monitor"], ["accepted_windows_per_min", "longest_feedback_free_s", "state_transitions_per_min"])
    gap_rates = availability.groupby("monitor", as_index=False).agg(percent_sessions_gap_gt_30s=("any_gap_gt_30s", lambda values: 100 * float(np.mean(values))))
    availability_summary.merge(gap_rates, on="monitor").to_csv(EXT / "availability_results.csv", index=False)
    latency.to_csv(EXT / "latency_results.csv", index=False)
    nonviable.to_csv(EXT / "nonviable_sessions.csv", index=False)
    stable = pd.read_csv(EXT / "stability_results.csv")
    trans = pd.read_csv(EXT / "transport_results.csv")
    avail = pd.read_csv(EXT / "availability_results.csv")
    lines = ["# External monitor comparison report", ""]
    for row in stable.itertuples():
        lines.append(f"- {row.split_type}: median accepted-set Jaccard {row.median_accepted_set_jaccard:.3f}; median overall agreement {row.median_overall_agreement:.3f}; sessions >=0.80 {row.percent_sessions_jaccard_ge_0_80:.1f}%.")
    first = trans[trans.direction == "first_to_final"].iloc[0]
    operational = avail.iloc[0]
    lines.append(f"- First-to-final transport Jaccard: {first.median_accepted_set_jaccard:.3f}.")
    lines.append(f"- Accepted windows/min: {operational.median_accepted_windows_per_min:.1f}; longest feedback-free interval: {operational.median_longest_feedback_free_s:.1f} s; transitions/min: {operational.median_state_transitions_per_min:.1f}.")
    lines.append("- Comparator label is faithful Riemannian Potato; no artifact-ground-truth claim is made.")
    (EXT / "comparison_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("[done] faithful Riemannian Potato")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
