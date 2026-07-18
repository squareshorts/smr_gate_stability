#!/usr/bin/env python3
"""Checkpointed M0-M4 stability, transport, and availability analyses."""
from __future__ import annotations

import hashlib
import sys
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from baseline_gate_stability.core import MONITORS, agreement_metrics, apply_monitor, fit_quality_thresholds, prepare_with_baseline, temporal_metrics


OUT = ROOT / "results" / "baseline_gate_stability"
CKPT = OUT / "checkpoints"
FEATURE_CKPT = CKPT / "features"
CAL_CKPT = CKPT / "calibration"
TEMP_CKPT = CKPT / "temporal_metrics"
LOG_DIR = CKPT / "logs"
CAL_OUT = OUT / "calibration"
TRANSPORT_OUT = OUT / "transport"
AVAIL_OUT = OUT / "availability"
HOP = 0.5
DURATIONS = (15, 30, 60, 90, 120)
SPLITS = ("first_half_second_half", "odd_even_nonoverlap", "temporal_block_bootstrap_pair")
CALIBRATED = {"M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M4_NFSQI_FULL_QUALITY"}
THRESHOLD_FEATURES = {
    "M1_HIGH_BETA": ("high_beta_power",),
    "M2_BROADBAND_HIGH_FREQUENCY": ("broadband_power", "noise_floor_power"),
    "M4_NFSQI_FULL_QUALITY": ("high_beta_power", "broadband_power", "noise_floor_power", "transient_score", "channel_inconsistency"),
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(message: str) -> None:
    with (LOG_DIR / "comparative_analysis.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{now()} {message}\n")
    print(message, flush=True)


def atomic_csv(frame: pd.DataFrame, path: Path, compression: str | None = None) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False, compression=compression)
    tmp.replace(path)


def key_from_path(path: Path) -> str:
    return path.name.removesuffix("_canonical.csv.gz")


def identity(frame: pd.DataFrame) -> tuple[str, str, str]:
    return str(frame.dataset.iloc[0]), str(frame.participant.iloc[0]), str(frame.session.iloc[0])


def temporal_block_draw(rest: pd.DataFrame, rng: np.random.Generator, block_rows: int = 20) -> pd.DataFrame:
    blocks = [rest.iloc[start : start + block_rows] for start in range(0, len(rest), block_rows)]
    selected = []
    count = 0
    while count < len(rest):
        block = blocks[int(rng.integers(0, len(blocks)))]
        selected.append(block)
        count += len(block)
    return pd.concat(selected, ignore_index=True).iloc[: len(rest)].reset_index(drop=True)


def split_samples(rest: pd.DataFrame, key: str) -> dict[str, tuple[pd.DataFrame, pd.DataFrame]]:
    rest = rest.sort_values("window_start_s").reset_index(drop=True)
    half = len(rest) // 2
    nonoverlap = rest.iloc[::2].reset_index(drop=True)
    seed = int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)
    rng = np.random.default_rng(seed)
    return {
        "first_half_second_half": (rest.iloc[:half].reset_index(drop=True), rest.iloc[half:].reset_index(drop=True)),
        "odd_even_nonoverlap": (nonoverlap.iloc[::2].reset_index(drop=True), nonoverlap.iloc[1::2].reset_index(drop=True)),
        "temporal_block_bootstrap_pair": (temporal_block_draw(rest, rng), temporal_block_draw(rest, rng)),
    }


def monitor_fit_and_apply(task: pd.DataFrame, calibration: pd.DataFrame, monitor: str) -> tuple[np.ndarray, list[str], dict[str, float]]:
    if monitor not in CALIBRATED:
        decisions, reasons = apply_monitor(task.reset_index(drop=True), monitor, None)
        return decisions, reasons, {}
    thresholds, baseline = fit_quality_thresholds(calibration)
    prepared = prepare_with_baseline(task.reset_index(drop=True), baseline)
    decisions, reasons = apply_monitor(prepared, monitor, thresholds)
    return decisions, reasons, {name: thresholds[name] for name in THRESHOLD_FEATURES[monitor]}


def enrich_agreement(left: np.ndarray, right: np.ndarray) -> dict[str, float | int]:
    result = agreement_metrics(left, right)
    result["accepted_windows_per_min_difference"] = float(result["acceptance_rate_difference"]) * 60.0 / HOP
    result["mutual_withholding_fraction"] = float(np.mean(~left & ~right)) if len(left) else np.nan
    result["mutual_acceptance_fraction"] = float(np.mean(left & right)) if len(left) else np.nan
    return result


def segmented_temporal_metrics(task: pd.DataFrame, decisions: np.ndarray) -> tuple[dict[str, float | int | bool], list[dict[str, object]]]:
    decisions = np.asarray(decisions, dtype=bool)
    if len(task) != len(decisions):
        raise ValueError("Task rows and decisions must match")
    run_rows: list[dict[str, object]] = []
    intervals: list[float] = []
    withhold_durations: list[float] = []
    accept_durations: list[float] = []
    transitions = 0
    active_offset = 0.0
    first_accepted = np.nan
    for segment_id, positions in task.groupby("segment_id", sort=False).indices.items():
        positions = np.asarray(positions, dtype=int)
        segment = decisions[positions]
        segment_metrics, segment_runs = temporal_metrics(segment, HOP)
        accepted = np.flatnonzero(segment)
        if len(accepted) > 1:
            intervals.extend((np.diff(accepted) * HOP).tolist())
        if np.isnan(first_accepted) and len(accepted):
            first_accepted = active_offset + float(accepted[0] * HOP)
        transitions += int(round(float(segment_metrics["state_transitions_per_min"]) * (len(segment) * HOP) / 60.0))
        for run in segment_runs:
            tagged = {"segment_id": segment_id, **run}
            run_rows.append(tagged)
            if run["state"] == "withhold":
                withhold_durations.append(float(run["duration_s"]))
            else:
                accept_durations.append(float(run["duration_s"]))
        active_offset += len(segment) * HOP
    n = len(decisions)
    duration_s = n * HOP
    metrics = {
        "n_windows": n,
        "accepted_windows": int(decisions.sum()),
        "accepted_windows_per_min": float(decisions.sum() / duration_s * 60) if duration_s else np.nan,
        "acceptance_duty_cycle": float(decisions.mean()) if n else np.nan,
        "median_inter_acceptance_s": float(np.median(intervals)) if intervals else np.nan,
        "p95_inter_acceptance_s": float(np.percentile(intervals, 95)) if intervals else np.nan,
        "longest_feedback_free_s": max(withhold_durations, default=0.0),
        "gaps_gt_5s": int(sum(value > 5 for value in withhold_durations)),
        "gaps_gt_10s": int(sum(value > 10 for value in withhold_durations)),
        "gaps_gt_20s": int(sum(value > 20 for value in withhold_durations)),
        "gaps_gt_30s": int(sum(value > 30 for value in withhold_durations)),
        "any_gap_gt_20s": bool(any(value > 20 for value in withhold_durations)),
        "any_gap_gt_30s": bool(any(value > 30 for value in withhold_durations)),
        "median_accept_run_s": float(np.median(accept_durations)) if accept_durations else 0.0,
        "median_withhold_run_s": float(np.median(withhold_durations)) if withhold_durations else 0.0,
        "state_transitions_per_min": float(transitions / duration_s * 60) if duration_s else np.nan,
        "time_to_first_accepted_s": float(first_accepted),
    }
    return metrics, run_rows


def analyze_calibration_session(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame = pd.read_csv(path)
    dataset, participant, session = identity(frame)
    key = key_from_path(path)
    rest = frame[frame.condition == "rest"].reset_index(drop=True)
    task = frame[frame.condition == "task"].sort_values("window_start_s").reset_index(drop=True)
    stability_rows: list[dict[str, object]] = []
    threshold_rows: list[dict[str, object]] = []
    decision_rows: list[dict[str, object]] = []
    duration_rows: list[dict[str, object]] = []
    for split_name, (left_rest, right_rest) in split_samples(rest, key).items():
        if len(left_rest) < 10 or len(right_rest) < 10:
            continue
        for monitor in MONITORS:
            left, left_reasons, left_limits = monitor_fit_and_apply(task, left_rest, monitor)
            right, right_reasons, right_limits = monitor_fit_and_apply(task, right_rest, monitor)
            row = {"dataset": dataset, "participant": participant, "session": session, "monitor": monitor, "split_type": split_name, "left_rest_windows": len(left_rest), "right_rest_windows": len(right_rest)}
            row.update(enrich_agreement(left, right))
            stability_rows.append(row)
            for side, limits in (("left", left_limits), ("right", right_limits)):
                for feature, value in limits.items():
                    threshold_rows.append({"dataset": dataset, "participant": participant, "session": session, "monitor": monitor, "split_type": split_name, "side": side, "feature": feature, "threshold_value": value})
            for index, window_id in enumerate(task.window_id):
                decision_rows.append(
                    {
                        "dataset": dataset, "participant": participant, "session": session, "monitor": monitor,
                        "split_type": split_name, "task_window_index": index, "window_id": window_id,
                        "left_decision": bool(left[index]), "right_decision": bool(right[index]),
                        "left_reason_codes": left_reasons[index], "right_reason_codes": right_reasons[index],
                    }
                )
    for monitor in MONITORS:
        full, _full_reasons, _full_limits = monitor_fit_and_apply(task, rest, monitor)
        for duration in DURATIONS:
            n = int(duration / HOP)
            if n > len(rest) or n < 10:
                continue
            partial, _reasons, limits = monitor_fit_and_apply(task, rest.iloc[:n].reset_index(drop=True), monitor)
            row = {"dataset": dataset, "participant": participant, "session": session, "monitor": monitor, "duration_s": duration, "rest_windows": n, "full_rest_windows": len(rest)}
            row.update(enrich_agreement(partial, full))
            duration_rows.append(row)
            for feature, value in limits.items():
                threshold_rows.append({"dataset": dataset, "participant": participant, "session": session, "monitor": monitor, "split_type": f"duration_{duration}s", "side": "partial", "feature": feature, "threshold_value": value})
    return pd.DataFrame(stability_rows), pd.DataFrame(threshold_rows), pd.DataFrame(decision_rows), pd.DataFrame(duration_rows)


def grouped_bootstrap_summary(subject: pd.DataFrame, group_columns: list[str], metrics: list[str], draws: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(20260716)
    rows = []
    for keys, group in subject.groupby(group_columns, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        group = group.sort_values(["dataset", "participant"]).reset_index(drop=True)
        participants = group[["dataset", "participant"]].drop_duplicates()
        row = dict(zip(group_columns, keys))
        row["participants"] = len(participants)
        for metric in metrics:
            row[f"median_{metric}"] = float(group[metric].median())
        indices = rng.integers(0, len(group), size=(draws, len(group)))
        for metric in metrics:
            values = group[metric].to_numpy(float)
            simulations = np.nanmedian(values[indices], axis=1)
            low, high = np.percentile(simulations, [2.5, 97.5])
            row[f"{metric}_ci_low"] = float(low)
            row[f"{metric}_ci_high"] = float(high)
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_calibration(stability: pd.DataFrame, thresholds: pd.DataFrame, decisions: pd.DataFrame, durations: pd.DataFrame) -> None:
    CAL_OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            ("first_half_second_half", "chronological first half of all usable rest windows", "chronological second half of all usable rest windows"),
            ("odd_even_nonoverlap", "odd members of 1 s nonoverlapping rest sequence", "even members of 1 s nonoverlapping rest sequence"),
            ("temporal_block_bootstrap_pair", "first 10 s block-bootstrap rest draw", "second independent 10 s block-bootstrap rest draw"),
        ],
        columns=["split_type", "left_definition", "right_definition"],
    ).to_csv(CAL_OUT / "calibration_splits.csv", index=False)
    thresholds.to_csv(CAL_OUT / "thresholds_by_split.csv", index=False)
    decisions.to_csv(CAL_OUT / "decisions_by_split.csv", index=False)
    stability.to_csv(CAL_OUT / "stability_by_session.csv", index=False)
    subject = stability.groupby(["dataset", "participant", "monitor", "split_type"], as_index=False).median(numeric_only=True)
    subject.to_csv(CAL_OUT / "stability_by_subject.csv", index=False)
    dataset = subject.groupby(["dataset", "monitor", "split_type"], as_index=False).median(numeric_only=True)
    dataset.to_csv(CAL_OUT / "stability_by_dataset.csv", index=False)
    pooled = grouped_bootstrap_summary(subject, ["monitor", "split_type"], ["accepted_set_jaccard", "overall_agreement", "positive_agreement", "negative_agreement", "mutual_withholding_fraction"])
    session_rates = stability.groupby(["monitor", "split_type"], as_index=False).agg(
        sessions=("session", "size"),
        percent_sessions_jaccard_ge_0_80=("accepted_set_jaccard", lambda values: 100 * float(np.mean(values >= 0.80))),
        percent_high_agreement_low_jaccard=("overall_agreement", lambda values: np.nan),
    )
    conceal = stability.assign(conceal=(stability.overall_agreement >= 0.95) & (stability.accepted_set_jaccard < 0.80)).groupby(["monitor", "split_type"])["conceal"].mean().mul(100).rename("percent_high_agreement_low_jaccard").reset_index()
    session_rates = session_rates.drop(columns="percent_high_agreement_low_jaccard").merge(conceal, on=["monitor", "split_type"])
    pooled = pooled.merge(session_rates, on=["monitor", "split_type"])
    pooled.to_csv(CAL_OUT / "stability_pooled.csv", index=False)
    durations.to_csv(CAL_OUT / "duration_sensitivity_by_session.csv", index=False)
    duration_subject = durations.groupby(["dataset", "participant", "monitor", "duration_s"], as_index=False).median(numeric_only=True)
    duration_summary = grouped_bootstrap_summary(duration_subject, ["monitor", "duration_s"], ["accepted_set_jaccard", "overall_agreement", "positive_agreement"])
    duration_rates = durations.groupby(["monitor", "duration_s"], as_index=False).agg(sessions=("session", "size"), percent_sessions_jaccard_ge_0_80=("accepted_set_jaccard", lambda values: 100 * float(np.mean(values >= 0.80))))
    duration_summary.merge(duration_rates, on=["monitor", "duration_s"]).to_csv(CAL_OUT / "duration_sensitivity.csv", index=False)
    threshold_pivot = thresholds.pivot_table(index=["dataset", "participant", "session", "monitor", "split_type", "feature"], columns="side", values="threshold_value", aggfunc="first").reset_index()
    if {"left", "right"}.issubset(threshold_pivot.columns):
        threshold_pivot["relative_difference"] = np.abs(threshold_pivot.left - threshold_pivot.right) / ((np.abs(threshold_pivot.left) + np.abs(threshold_pivot.right)) / 2 + 1e-12)
    threshold_pivot.to_csv(CAL_OUT / "feature_threshold_variability.csv", index=False)
    stability.groupby(["monitor", "split_type"], as_index=False).agg(
        acceptance_to_withhold_flips=("acceptance_to_withhold_flips", "sum"),
        withhold_to_acceptance_flips=("withhold_to_acceptance_flips", "sum"),
        median_mutual_withholding_fraction=("mutual_withholding_fraction", "median"),
    ).to_csv(CAL_OUT / "acceptance_flip_summary.csv", index=False)
    calibrated = pooled[pooled.monitor.isin(CALIBRATED)]
    ranked = calibrated.groupby("monitor", as_index=False).agg(median_split_jaccard=("median_accepted_set_jaccard", "median"), median_overall_agreement=("median_overall_agreement", "median"), percent_sessions_ge_0_80=("percent_sessions_jaccard_ge_0_80", "mean"), conceal_percent=("percent_high_agreement_low_jaccard", "mean")).sort_values("median_split_jaccard", ascending=False)
    lines = ["# Calibration stability report", "", f"Sessions: {stability[['dataset','participant','session']].drop_duplicates().shape[0]}. Participant is the inferential unit.", ""]
    for row in ranked.itertuples():
        lines.append(f"- {row.monitor}: median independent-split accepted-set Jaccard {row.median_split_jaccard:.3f}; median overall agreement {row.median_overall_agreement:.3f}; mean split-specific sessions >=0.80 {row.percent_sessions_ge_0_80:.1f}%; high-agreement/low-Jaccard cases {row.conceal_percent:.1f}%.")
    (CAL_OUT / "calibration_stability_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_transport_pair(paths: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = [pd.read_csv(path) for path in sorted(paths, key=lambda value: value.name)]
    frames.sort(key=lambda frame: str(frame.session.iloc[0]))
    rows = []
    reason_rows = []
    for source, target, direction in ((frames[0], frames[-1], "first_to_final"), (frames[-1], frames[0], "final_to_first")):
        dataset, participant, source_session = identity(source)
        target_session = str(target.session.iloc[0])
        source_rest = source[source.condition == "rest"].reset_index(drop=True)
        target_rest = target[target.condition == "rest"].reset_index(drop=True)
        task = target[target.condition == "task"].sort_values("window_start_s").reset_index(drop=True)
        for monitor in MONITORS:
            transported, transported_reasons, source_limits = monitor_fit_and_apply(task, source_rest, monitor)
            local, local_reasons, local_limits = monitor_fit_and_apply(task, target_rest, monitor)
            temporal, _ = segmented_temporal_metrics(task, transported)
            row = {"dataset": dataset, "participant": participant, "source_session": source_session, "target_session": target_session, "direction": direction, "monitor": monitor}
            row.update(enrich_agreement(transported, local))
            row.update({"transported_accepted_windows_per_min": temporal["accepted_windows_per_min"], "transported_longest_feedback_free_s": temporal["longest_feedback_free_s"], "transported_transitions_per_min": temporal["state_transitions_per_min"]})
            shifts = [abs(source_limits[name] - local_limits[name]) / (abs(local_limits[name]) + 1e-12) for name in source_limits if name in local_limits]
            row["median_relative_threshold_shift"] = float(np.median(shifts)) if shifts else 0.0
            rows.append(row)
            for index in np.flatnonzero(transported != local):
                left = set(filter(None, transported_reasons[index].split(";")))
                right = set(filter(None, local_reasons[index].split(";")))
                reason_rows.append({"dataset": dataset, "participant": participant, "source_session": source_session, "target_session": target_session, "direction": direction, "monitor": monitor, "task_window_index": int(index), "transported_only_reasons": ";".join(sorted(left - right)), "local_only_reasons": ";".join(sorted(right - left))})
    reason_columns = ["dataset", "participant", "source_session", "target_session", "direction", "monitor", "task_window_index", "transported_only_reasons", "local_only_reasons"]
    return pd.DataFrame(rows), pd.DataFrame(reason_rows, columns=reason_columns)


def aggregate_transport(rows: pd.DataFrame, reasons: pd.DataFrame) -> None:
    TRANSPORT_OUT.mkdir(parents=True, exist_ok=True)
    rows.to_csv(TRANSPORT_OUT / "transport_by_session_pair.csv", index=False)
    subject = rows.groupby(["dataset", "participant", "monitor", "direction"], as_index=False).median(numeric_only=True)
    subject.to_csv(TRANSPORT_OUT / "transport_by_subject.csv", index=False)
    subject.groupby(["dataset", "monitor", "direction"], as_index=False).median(numeric_only=True).to_csv(TRANSPORT_OUT / "transport_by_dataset.csv", index=False)
    pooled = grouped_bootstrap_summary(subject, ["monitor", "direction"], ["accepted_set_jaccard", "overall_agreement", "acceptance_rate_difference", "transported_longest_feedback_free_s", "transported_transitions_per_min"])
    pooled.to_csv(TRANSPORT_OUT / "transport_pooled.csv", index=False)
    reasons.to_csv(TRANSPORT_OUT / "transport_disagreement_reasons.csv", index=False)
    primary = pooled[pooled.direction == "first_to_final"].sort_values("median_accepted_set_jaccard", ascending=False)
    lines = ["# Cross-session transport report", ""] + [f"- {row.monitor}: median accepted-set Jaccard {row.median_accepted_set_jaccard:.3f}; median overall agreement {row.median_overall_agreement:.3f}; median transported longest feedback-free interval {row.median_transported_longest_feedback_free_s:.1f} s." for row in primary.itertuples()]
    (TRANSPORT_OUT / "cross_session_transport_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_availability_session(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.read_csv(path)
    dataset, participant, session = identity(frame)
    task = frame[frame.condition == "task"].sort_values("window_start_s").reset_index(drop=True)
    metrics_rows = []
    run_rows = []
    for monitor in MONITORS:
        decisions = task[monitor].astype(bool).to_numpy()
        metrics, runs = segmented_temporal_metrics(task, decisions)
        metrics_rows.append({"dataset": dataset, "participant": participant, "session": session, "monitor": monitor, **metrics})
        for run in runs:
            run_rows.append({"dataset": dataset, "participant": participant, "session": session, "monitor": monitor, **run})
    return pd.DataFrame(metrics_rows), pd.DataFrame(run_rows)


def aggregate_availability(metrics: pd.DataFrame, runs: pd.DataFrame) -> None:
    AVAIL_OUT.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(AVAIL_OUT / "metrics_by_session.csv", index=False)
    subject = metrics.groupby(["dataset", "participant", "monitor"], as_index=False).median(numeric_only=True)
    subject.to_csv(AVAIL_OUT / "metrics_by_subject.csv", index=False)
    subject.groupby(["dataset", "monitor"], as_index=False).median(numeric_only=True).to_csv(AVAIL_OUT / "metrics_by_dataset.csv", index=False)
    pooled = grouped_bootstrap_summary(subject, ["monitor"], ["accepted_windows_per_min", "acceptance_duty_cycle", "longest_feedback_free_s", "state_transitions_per_min", "time_to_first_accepted_s"])
    rates = metrics.groupby("monitor", as_index=False).agg(sessions=("session", "size"), percent_sessions_gap_gt_20s=("any_gap_gt_20s", lambda values: 100 * float(np.mean(values))), percent_sessions_gap_gt_30s=("any_gap_gt_30s", lambda values: 100 * float(np.mean(values))))
    pooled.merge(rates, on="monitor").to_csv(AVAIL_OUT / "metrics_pooled.csv", index=False)
    runs.to_csv(AVAIL_OUT / "run_length_distributions.csv", index=False)
    runs[(runs.state == "withhold") & (runs.duration_s > 5)].to_csv(AVAIL_OUT / "starvation_events.csv", index=False)
    summary = pooled.merge(rates, on="monitor").sort_values("median_longest_feedback_free_s")
    lines = ["# Operational availability report", ""] + [f"- {row.monitor}: accepted windows/min {row.median_accepted_windows_per_min:.1f}; median longest feedback-free interval {row.median_longest_feedback_free_s:.1f} s; sessions with gap >30 s {row.percent_sessions_gap_gt_30s:.1f}%; transitions/min {row.median_state_transitions_per_min:.1f}." for row in summary.itertuples()]
    (AVAIL_OUT / "operational_availability_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    for path in (CAL_CKPT, TEMP_CKPT, LOG_DIR, CAL_OUT, TRANSPORT_OUT, AVAIL_OUT):
        path.mkdir(parents=True, exist_ok=True)
    feature_paths = sorted(FEATURE_CKPT.glob("*_canonical.csv.gz"))
    errors = []
    all_stability, all_thresholds, all_decisions, all_durations = [], [], [], []
    all_availability, all_runs = [], []
    progress = pd.read_csv(OUT / "execution_progress.csv").to_dict("records") if (OUT / "execution_progress.csv").exists() else []
    for sequence, path in enumerate(feature_paths, 1):
        key = key_from_path(path)
        cal_paths = {name: CAL_CKPT / f"{key}_{name}.csv.gz" for name in ("stability", "thresholds", "decisions", "durations")}
        avail_path = TEMP_CKPT / f"{key}_availability_v2.csv.gz"
        runs_path = TEMP_CKPT / f"{key}_runs_v2.csv.gz"
        try:
            if all(value.exists() and value.stat().st_size > 100 for value in cal_paths.values()):
                stability, thresholds, decisions, durations = (pd.read_csv(cal_paths[name]) for name in ("stability", "thresholds", "decisions", "durations"))
                cal_status = "reused"
            else:
                stability, thresholds, decisions, durations = analyze_calibration_session(path)
                for name, frame in (("stability", stability), ("thresholds", thresholds), ("decisions", decisions), ("durations", durations)):
                    atomic_csv(frame, cal_paths[name], "gzip")
                cal_status = "created"
            if avail_path.exists() and runs_path.exists() and avail_path.stat().st_size > 100 and runs_path.stat().st_size > 100:
                availability, runs = pd.read_csv(avail_path), pd.read_csv(runs_path)
                avail_status = "reused"
            else:
                availability, runs = analyze_availability_session(path)
                atomic_csv(availability, avail_path, "gzip")
                atomic_csv(runs, runs_path, "gzip")
                avail_status = "created"
            all_stability.append(stability); all_thresholds.append(thresholds); all_decisions.append(decisions); all_durations.append(durations)
            all_availability.append(availability); all_runs.append(runs)
            progress.append({"stage": "stability_and_availability", "sequence": sequence, "total": len(feature_paths), "dataset": stability.dataset.iloc[0], "participant": stability.participant.iloc[0], "session": stability.session.iloc[0], "status": f"calibration_{cal_status};availability_{avail_status}", "timestamp": now()})
            pd.DataFrame(progress).to_csv(OUT / "execution_progress.csv", index=False)
            log(f"[session {sequence}/114] {key}")
        except Exception as exc:
            errors.append({"timestamp": now(), "stage": "stability_and_availability", "checkpoint": key, "error": repr(exc)})
            (LOG_DIR / f"{key}_comparative_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            log(f"[error {sequence}/114] {key}: {exc!r}")
    if errors:
        pd.DataFrame(errors).to_csv(OUT / "execution_errors.csv", mode="a", index=False, header=False)
        raise RuntimeError(f"Comparative session errors: {len(errors)}")
    aggregate_calibration(pd.concat(all_stability, ignore_index=True), pd.concat(all_thresholds, ignore_index=True), pd.concat(all_decisions, ignore_index=True), pd.concat(all_durations, ignore_index=True))
    aggregate_availability(pd.concat(all_availability, ignore_index=True), pd.concat(all_runs, ignore_index=True))
    grouped: dict[tuple[str, str], list[Path]] = {}
    for path in feature_paths:
        frame = pd.read_csv(path, usecols=["dataset", "participant"], nrows=1)
        grouped.setdefault((str(frame.dataset.iloc[0]), str(frame.participant.iloc[0])), []).append(path)
    transport_rows, reason_rows = [], []
    for sequence, ((dataset, participant), paths) in enumerate(sorted(grouped.items()), 1):
        checkpoint = CAL_CKPT / f"transport_v2_{dataset}_{participant}.csv.gz"
        reasons_checkpoint = CAL_CKPT / f"transport_v2_{dataset}_{participant}_reasons.csv.gz"
        if checkpoint.exists() and reasons_checkpoint.exists() and checkpoint.stat().st_size > 100 and reasons_checkpoint.stat().st_size > 20:
            rows, reasons = pd.read_csv(checkpoint), pd.read_csv(reasons_checkpoint)
        else:
            rows, reasons = analyze_transport_pair(paths)
            atomic_csv(rows, checkpoint, "gzip")
            atomic_csv(reasons, reasons_checkpoint, "gzip")
        transport_rows.append(rows)
        if not reasons.empty:
            reason_rows.append(reasons)
        log(f"[transport {sequence}/{len(grouped)}] {dataset}_{participant}")
    aggregate_transport(pd.concat(transport_rows, ignore_index=True), pd.concat(reason_rows, ignore_index=True) if reason_rows else pd.DataFrame())
    log("[done] M0-M4 stability, transport, and availability")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
