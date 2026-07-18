#!/usr/bin/env python3
"""Build a resumable canonical window cache for the stability study."""
from __future__ import annotations

import hashlib
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import mne
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from baseline_gate_stability.core import apply_monitor, fit_quality_thresholds, prepare_with_baseline
from empirical.nf_sqi_common import SENSORIMOTOR_CHANNELS, read_events_for_edf
from scripts.runtime_assurance.reference_interlock import evaluate
from scripts.runtime_assurance.run_all import DATASETS, HOP


mne.set_log_level("ERROR")
OUT = ROOT / "results" / "baseline_gate_stability"
DATA_OUT = OUT / "data"
CKPT = OUT / "checkpoints"
FEATURE_CKPT = CKPT / "features"
DECISION_CKPT = CKPT / "monitor_decisions"
LOG_DIR = CKPT / "logs"
SOURCE_FEATURES = ROOT / "results" / "runtime_assurance_remediation" / "checkpoints" / "feature_cache"
REFERENCE = ROOT / "results" / "runtime_assurance" / "batch_streaming_conformance_by_window.csv"
CONFIG = {
    "channels": SENSORIMOTOR_CHANNELS,
    "window_s": 1.0,
    "hop_s": HOP,
    "task_majority_rule": 0.5,
    "source_feature_cache": "runtime_assurance_remediation/checkpoints/feature_cache",
    "m3_peak_to_peak_uv": 150.0,
    "m4_gate_a_included": False,
    "covariance": "sample covariance of three canonical channels per 1 s window",
}
CONFIG_HASH = hashlib.sha256(json.dumps(CONFIG, sort_keys=True).encode()).hexdigest()
REQUIRED_COLUMNS = {
    "dataset", "participant", "session", "window_id", "window_start_s", "condition", "segment_id",
    "smr_snr", "high_beta_power", "broadband_power", "noise_floor_power", "transient_score",
    "channel_inconsistency", "peak_to_peak_uv", "gate_a", "M0_NO_GATE", "M1_HIGH_BETA",
    "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY",
    "raw_feature_valid", "fs", "channel_availability", "canonical_config_hash",
    "cov_00", "cov_01", "cov_02", "cov_11", "cov_12", "cov_22",
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_dirs() -> None:
    for path in (OUT, DATA_OUT, CKPT, FEATURE_CKPT, DECISION_CKPT, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "canonical_cache.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{now()} {message}\n")
    print(message, flush=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_csv(frame: pd.DataFrame, path: Path, *, compression: str | None = None) -> None:
    tmp = path.with_name(path.name + ".tmp")
    frame.to_csv(tmp, index=False, compression=compression)
    tmp.replace(path)


def session_key(dataset: str, participant: str, session: str) -> str:
    return f"{dataset}_{participant}_{session}"


def list_source_sessions() -> list[tuple[str, str, str, Path, Path]]:
    rows = []
    for dataset in DATASETS:
        raw_root = ROOT / "data" / "raw" / "openneuro" / dataset
        for edf in sorted(raw_root.rglob("sub-*/ses-*/eeg/*_task-smrbmi_eeg.edf")):
            participant = edf.parts[-4]
            session = edf.parts[-3]
            source = SOURCE_FEATURES / f"{session_key(dataset, participant, session)}_features.csv.gz"
            rows.append((dataset, participant, session, edf, source))
    return rows


def raw_window_rows(edf: Path) -> tuple[pd.DataFrame, float, str]:
    raw = mne.io.read_raw_edf(edf, preload=True, include=SENSORIMOTOR_CHANNELS, verbose=False)
    channels = [channel for channel in SENSORIMOTOR_CHANNELS if channel in raw.ch_names]
    if channels != SENSORIMOTOR_CHANNELS:
        raise ValueError(f"Canonical channels missing or reordered: {channels}")
    raw.pick_channels(channels)
    raw.reorder_channels(channels)
    fs = float(raw.info["sfreq"])
    events = read_events_for_edf(edf, raw.times[-1])
    task_event = np.full(raw.n_times, -1, dtype=np.int32)
    for event_index, event in events.loc[events["instruction"].astype(str) == "task"].iterrows():
        start = max(0, int(round(float(event.onset_s) * fs)))
        stop = min(raw.n_times, int(round((float(event.onset_s) + float(event.duration_s)) * fs)))
        task_event[start:max(start, stop)] = int(event_index)
    data = raw.get_data()
    nwin = int(fs)
    hop = int(round(HOP * fs))
    rows: list[dict[str, object]] = []
    prior_condition = None
    rest_segment = -1
    for overall_index, start in enumerate(range(0, data.shape[1] - nwin, hop)):
        labels = task_event[start : start + nwin]
        task_fraction = float(np.mean(labels >= 0))
        condition = "task" if task_fraction > 0.5 else "rest"
        if condition == "rest" and prior_condition != "rest":
            rest_segment += 1
        if condition == "task":
            valid_labels = labels[labels >= 0]
            segment_id = f"task_event_{int(np.bincount(valid_labels).argmax())}" if len(valid_labels) else "task_event_unknown"
        else:
            segment_id = f"rest_segment_{rest_segment}"
        window = data[:, start : start + nwin]
        covariance = np.cov(window, rowvar=True, ddof=1)
        rows.append(
            {
                "overall_window_index": overall_index,
                "window_start_s": start / fs,
                "condition": condition,
                "segment_id": segment_id,
                "peak_to_peak_uv": float(np.max(np.ptp(window, axis=1)) * 1e6),
                "raw_feature_valid": bool(np.isfinite(window).all() and covariance.shape == (3, 3) and np.isfinite(covariance).all()),
                "cov_00": float(covariance[0, 0]),
                "cov_01": float(covariance[0, 1]),
                "cov_02": float(covariance[0, 2]),
                "cov_11": float(covariance[1, 1]),
                "cov_12": float(covariance[1, 2]),
                "cov_22": float(covariance[2, 2]),
            }
        )
        prior_condition = condition
    del data, raw
    frame = pd.DataFrame(rows)
    frame["condition_index"] = frame.groupby("condition").cumcount()
    return frame, fs, ";".join(channels)


def build_session(dataset: str, participant: str, session: str, edf: Path, source: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    if not source.exists():
        raise FileNotFoundError(f"Missing reusable feature cache: {source}")
    features = pd.read_csv(source)
    features = features.rename(columns={"subject": "participant", "window_index_within_condition": "condition_index"})
    raw_rows, fs, channel_availability = raw_window_rows(edf)
    merged = raw_rows.merge(
        features.drop(columns=["dataset", "participant", "session", "fs"], errors="ignore"),
        on=["condition", "condition_index"],
        how="left",
        validate="one_to_one",
    )
    if merged["valid"].isna().any() or len(merged) != len(features):
        raise ValueError(f"Raw/reusable feature window mismatch: raw={len(merged)} reusable={len(features)}")
    merged.insert(0, "dataset", dataset)
    merged.insert(1, "participant", participant)
    merged.insert(2, "session", session)
    merged["window_id"] = [f"{session_key(dataset, participant, session)}_w{index:06d}" for index in merged["overall_window_index"]]
    merged["fs"] = fs
    merged["channel_availability"] = channel_availability
    merged["canonical_config_hash"] = CONFIG_HASH
    merged["raw_feature_valid"] &= merged["valid"].astype(bool)
    rest = merged[merged["condition"] == "rest"].reset_index(drop=True)
    thresholds, baseline = fit_quality_thresholds(rest)
    merged = prepare_with_baseline(merged, baseline)
    merged["gate_a"] = merged["raw_feature_valid"] & (merged["smr_snr"] > thresholds["smr_snr"])
    for monitor in ("M0_NO_GATE", "M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY"):
        decisions, reasons = apply_monitor(merged.reset_index(drop=True), monitor, thresholds)
        merged[monitor] = decisions
        merged[f"{monitor}_reason_codes"] = reasons
    merged["reference_gate_b"] = merged["gate_a"] & merged["M1_HIGH_BETA"]
    merged["reference_gate_c"] = merged["gate_a"] & merged["M4_NFSQI_FULL_QUALITY"]
    task = merged[merged["condition"] == "task"].copy().reset_index(drop=True)
    task["task_window_index"] = np.arange(len(task))
    reference_limits = {
        "smr_snr_min": thresholds["smr_snr"],
        "high_beta_max": thresholds["high_beta_power"],
        "broadband_max": thresholds["broadband_power"],
        "noise_floor_max": thresholds["noise_floor_power"],
        "transient_max": thresholds["transient_score"],
        "channel_inconsistency_max": thresholds["channel_inconsistency"],
    }
    reference_reasons = []
    reference_decisions = []
    for row in task.itertuples(index=False):
        result = evaluate(
            {
                "smr_snr": float(row.smr_snr),
                "high_beta_power": float(row.high_beta_power),
                "broadband_power": float(row.broadband_power),
                "noise_floor_power": float(row.noise_floor_power),
                "transient_score": float(row.transient_score),
                "channel_inconsistency": float(row.channel_inconsistency),
            },
            reference_limits,
        )
        reference_decisions.append(result.gate_c_allowed)
        reference_reasons.append(";".join(result.reason_codes))
    task["recomputed_reference_gate_c"] = reference_decisions
    task["recomputed_reference_reason_codes"] = reference_reasons
    threshold_rows = [{"threshold": name, "value": value} for name, value in thresholds.items()]
    decision_columns = [
        "dataset", "participant", "session", "task_window_index", "window_id", "window_start_s", "gate_a",
        "M0_NO_GATE", "M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY",
        "M0_NO_GATE_reason_codes", "M1_HIGH_BETA_reason_codes", "M2_BROADBAND_HIGH_FREQUENCY_reason_codes",
        "M3_AMPLITUDE_150_reason_codes", "M4_NFSQI_FULL_QUALITY_reason_codes", "reference_gate_b", "reference_gate_c",
        "recomputed_reference_gate_c", "recomputed_reference_reason_codes",
    ]
    validation = {
        "dataset": dataset,
        "participant": participant,
        "session": session,
        "rows": len(merged),
        "rest_windows": int((merged["condition"] == "rest").sum()),
        "task_windows": len(task),
        "raw_feature_valid": int(merged["raw_feature_valid"].sum()),
        "config_hash": CONFIG_HASH,
        "thresholds": json.dumps(threshold_rows, sort_keys=True),
    }
    return merged, task[decision_columns], validation


def checkpoint_valid(feature_path: Path, decision_path: Path) -> bool:
    if not feature_path.exists() or not decision_path.exists() or feature_path.stat().st_size <= 100 or decision_path.stat().st_size <= 100:
        return False
    try:
        sample = pd.read_csv(feature_path, nrows=3)
        return REQUIRED_COLUMNS.issubset(sample.columns) and set(sample["canonical_config_hash"]) == {CONFIG_HASH}
    except Exception:
        return False


def write_progress(rows: list[dict[str, object]], errors: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_csv(OUT / "execution_progress.csv", index=False)
    pd.DataFrame(errors, columns=["timestamp", "stage", "dataset", "participant", "session", "error"]).to_csv(OUT / "execution_errors.csv", index=False)


def main() -> int:
    ensure_dirs()
    sessions = list_source_sessions()
    reusable_rows = []
    for dataset, participant, session, _edf, source in sessions:
        reusable_rows.append(
            {
                "dataset": dataset,
                "participant": participant,
                "session": session,
                "source": source.relative_to(ROOT).as_posix(),
                "exists": source.exists(),
                "sha256": sha256(source) if source.exists() else "",
                "reused_fields": "canonical NF-SQI scalar and per-channel bandpower features",
                "missing_fields_requiring_raw_read": "window_start;segment_id;peak_to_peak;covariance",
            }
        )
    pd.DataFrame(reusable_rows).to_csv(OUT / "reusable_data_inventory.csv", index=False)
    reference = pd.read_csv(REFERENCE)
    progress: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    validations: list[dict[str, object]] = []
    manifest: list[dict[str, object]] = []
    all_decisions: list[pd.DataFrame] = []
    for sequence, (dataset, participant, session, edf, source) in enumerate(sessions, 1):
        key = session_key(dataset, participant, session)
        feature_path = FEATURE_CKPT / f"{key}_canonical.csv.gz"
        decision_path = DECISION_CKPT / f"{key}_decisions.csv.gz"
        try:
            if checkpoint_valid(feature_path, decision_path):
                canonical = pd.read_csv(feature_path)
                decisions = pd.read_csv(decision_path)
                status = "reused"
                log(f"[skip {sequence}/114] {key}")
            else:
                canonical, decisions, validation = build_session(dataset, participant, session, edf, source)
                atomic_csv(canonical, feature_path, compression="gzip")
                atomic_csv(decisions, decision_path, compression="gzip")
                status = "created"
                validations.append(validation)
                log(f"[write {sequence}/114] {key} task={len(decisions)} total={len(canonical)}")
            if not validations or validations[-1].get("dataset") != dataset or validations[-1].get("participant") != participant or validations[-1].get("session") != session:
                validations.append(
                    {
                        "dataset": dataset,
                        "participant": participant,
                        "session": session,
                        "rows": len(canonical),
                        "rest_windows": int((canonical["condition"] == "rest").sum()),
                        "task_windows": int((canonical["condition"] == "task").sum()),
                        "raw_feature_valid": int(canonical["raw_feature_valid"].sum()),
                        "config_hash": CONFIG_HASH,
                        "thresholds": "reused checkpoint" if status == "reused" else validations[-1]["thresholds"],
                    }
                )
            progress.append({"stage": "canonical_cache", "sequence": sequence, "total": len(sessions), "dataset": dataset, "participant": participant, "session": session, "status": status, "timestamp": now()})
            manifest.append(
                {
                    "dataset": dataset,
                    "participant": participant,
                    "session": session,
                    "feature_checkpoint": feature_path.relative_to(ROOT).as_posix(),
                    "decision_checkpoint": decision_path.relative_to(ROOT).as_posix(),
                    "feature_sha256": sha256(feature_path),
                    "decision_sha256": sha256(decision_path),
                    "rows": len(canonical),
                    "task_windows": len(decisions),
                    "canonical_config_hash": CONFIG_HASH,
                    "status": status,
                }
            )
            all_decisions.append(decisions)
            del canonical, decisions
        except Exception as exc:
            errors.append({"timestamp": now(), "stage": "canonical_cache", "dataset": dataset, "participant": participant, "session": session, "error": repr(exc)})
            (LOG_DIR / f"{key}_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            log(f"[error {sequence}/114] {key}: {exc!r}")
        write_progress(progress, errors)
    pd.DataFrame(manifest).to_csv(DATA_OUT / "canonical_window_cache_manifest.csv", index=False)
    pd.DataFrame(manifest).to_csv(OUT / "checkpoint_inventory.csv", index=False)
    pd.DataFrame(validations).to_csv(DATA_OUT / "canonical_window_cache_validation.csv", index=False)
    if errors or len(manifest) != 114:
        raise RuntimeError(f"Canonical cache incomplete: sessions={len(manifest)} errors={len(errors)}")
    decisions = pd.concat(all_decisions, ignore_index=True)
    reference = reference.rename(columns={"subject": "participant", "window_index": "task_window_index"})
    comparison = decisions.merge(reference, on=["dataset", "participant", "session", "task_window_index"], how="outer", validate="one_to_one", indicator=True)
    comparison["verified_reason"] = comparison["batch_reason_codes"].fillna("")
    comparison["recomputed_reason"] = comparison["recomputed_reference_reason_codes"].fillna("")
    comparison["decision_difference"] = comparison["recomputed_reference_gate_c"].astype(bool) != comparison["batch_gate_c"].astype(bool)
    comparison["reason_difference"] = comparison["recomputed_reason"] != comparison["verified_reason"]
    reproduction = comparison.groupby("dataset", as_index=False).agg(
        compared_windows=("task_window_index", "size"),
        merge_failures=("_merge", lambda values: int(np.sum(values != "both"))),
        decision_differences=("decision_difference", "sum"),
        reason_code_differences=("reason_difference", "sum"),
    )
    reproduction.loc[len(reproduction)] = {
        "dataset": "pooled",
        "compared_windows": len(comparison),
        "merge_failures": int(np.sum(comparison["_merge"] != "both")),
        "decision_differences": int(comparison["decision_difference"].sum()),
        "reason_code_differences": int(comparison["reason_difference"].sum()),
    }
    reproduction.to_csv(DATA_OUT / "count_reproduction.csv", index=False)
    (DATA_OUT / "feature_definition_map.md").write_text(
        "# Feature definition map\n\nCanonical NF-SQI scalar and per-channel bandpower features are reused unchanged from the verified runtime-assurance cache. Window start, condition/segment, maximum three-channel peak-to-peak amplitude, and six unique covariance entries are appended from a single session-level EDF read using the identical 1 s window and 0.5 s hop. M4 is the quality-only full monitor and deliberately excludes Gate A; `reference_gate_c` retains Gate A for exact conformance reproduction.\n",
        encoding="utf-8",
    )
    pooled = reproduction[reproduction["dataset"] == "pooled"].iloc[0]
    if int(pooled["compared_windows"]) != 22418 or int(pooled["merge_failures"]) or int(pooled["decision_differences"]) or int(pooled["reason_code_differences"]):
        raise RuntimeError(f"Mandatory canonical reproduction failed: {pooled.to_dict()}")
    progress.append({"stage": "canonical_reproduction", "sequence": 114, "total": 114, "dataset": "pooled", "participant": "", "session": "", "status": "complete_22418_zero_differences", "timestamp": now()})
    write_progress(progress, errors)
    log("[done] 114 sessions; 22,418 task windows; zero decision/reason differences")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
