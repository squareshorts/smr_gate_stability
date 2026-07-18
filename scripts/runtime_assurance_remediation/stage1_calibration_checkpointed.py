#!/usr/bin/env python3
"""Checkpointed Stage 1 calibration remediation.

This script is intentionally session-at-a-time. It never keeps the full raw
OpenNeuro collection in memory and can be restarted safely.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import mne
import numpy as np
import pandas as pd
from scipy.stats import beta as beta_dist

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for p in (ROOT, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from scripts.runtime_assurance.reference_interlock import evaluate
from scripts.runtime_assurance.run_all import DATASETS, HOP, LIMIT_NAMES, cache_features, task_segments

mne.set_log_level("ERROR")

OUT = ROOT / "results" / "runtime_assurance_remediation"
CAL = OUT / "calibration"
CKPT = OUT / "checkpoints"
FEATURE_CKPT = CKPT / "feature_cache"
CAL_CKPT = CKPT / "calibration"
LOG_DIR = CKPT / "logs"

METHODS = {
    "C0_CURRENT_OVERLAP_EMPIRICAL": {"step": 1, "estimator": "EMPIRICAL", "prior": False},
    "C1_NONOVERLAP_EMPIRICAL": {"step": 2, "estimator": "EMPIRICAL", "prior": False},
    "C2_NONOVERLAP_HARRELL_DAVIS": {"step": 2, "estimator": "HARRELL_DAVIS", "prior": False},
    "C3_BLOCK_SUBSAMPLE_EMPIRICAL": {"step": 4, "estimator": "EMPIRICAL", "prior": False},
    "C4_LOSO_SHRINKAGE": {"step": 2, "estimator": "EMPIRICAL", "prior": True},
}
CHECKPOINTS = (15, 30, 60, 90, 120)
FEATURES = ("smr_snr", "high_beta_power", "broadband_power", "noise_floor_power", "transient_score", "channel_inconsistency")
FEATURE_TO_LIMIT = {
    "smr_snr": "smr_snr_min",
    "high_beta_power": "high_beta_max",
    "broadband_power": "broadband_max",
    "noise_floor_power": "noise_floor_max",
    "transient_score": "transient_max",
    "channel_inconsistency": "channel_inconsistency_max",
}
LIMIT_TO_FEATURE = {v: k for k, v in FEATURE_TO_LIMIT.items()}
PERCENTILES = {
    "smr_snr": 75.0,
    "high_beta_power": 75.0,
    "broadband_power": 75.0,
    "noise_floor_power": 75.0,
    "transient_score": 90.0,
    "channel_inconsistency": 75.0,
}
BANDS = ("smr", "beta", "broadband", "noise")
SEED = 20260719
BOOTSTRAP_DRAWS = 100
BOOTSTRAP_BLOCK_SECONDS = 10.0


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def session_id(dataset: str, subject: str, session: str) -> str:
    return f"{dataset}_{subject}_{session}"


def write_log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "stage1_calibration.log").open("a", encoding="utf-8") as f:
        f.write(f"{now()} {message}\n")
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ensure_dirs() -> None:
    for path in (OUT, CAL, CKPT, FEATURE_CKPT, CAL_CKPT, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def atomic_to_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write a checkpoint atomically so interruption cannot leave a valid-looking partial file."""
    tmp = path.with_name(f"{path.name}.tmp")
    frame.to_csv(tmp, index=False)
    tmp.replace(path)


def checkpoint_sidecar(path: Path, kind: str) -> Path:
    return path.with_name(f"{path.stem}__{kind}.csv")


def calibration_checkpoint_paths(path: Path) -> dict[str, Path]:
    return {
        "results": path,
        "thresholds": checkpoint_sidecar(path, "thresholds"),
        "split_half": checkpoint_sidecar(path, "split_half"),
        "odd_even": checkpoint_sidecar(path, "odd_even"),
        "bootstrap": checkpoint_sidecar(path, "bootstrap"),
    }


def calibration_checkpoint_complete(path: Path) -> bool:
    paths = calibration_checkpoint_paths(path)
    return all(p.exists() and p.stat().st_size > 1 for p in paths.values())


def write_frozen_specs() -> None:
    (CAL / "stage1_frozen_specification.md").write_text(
        "# Stage 1 frozen calibration specification\n\n"
        "Written before Stage 1 checkpoint aggregation. Methods: C0 current overlapping empirical, "
        "C1 nonoverlap empirical, C2 nonoverlap Harrell-Davis, C3 block-subsample empirical, "
        "C4 leave-one-subject-out dataset-prior shrinkage. Reference is complete usable rest baseline "
        "for the same method. Checkpoints are 15, 30, 60, 90, 120 s and full usable baseline when available. "
        "The full row is the reference only and is excluded from pass/fail scoring. Numeric method-duration rows "
        "are scored against the full usable baseline. Temporal uncertainty uses 100 resamples of nonoverlapping "
        "10 s rest blocks. No task outcomes, decoder results, or future participant data enter calibration priors.\n",
        encoding="utf-8",
    )
    (CAL / "stage1_success_criteria.md").write_text(
        "# Stage 1 frozen success criteria\n\n"
        "A calibration method passes only if: pooled median accepted-set Jaccard >= 0.85; at least 80% "
        "of sessions have accepted-set Jaccard >= 0.80; pooled median overall decision agreement >= 0.97; "
        "no dataset has median accepted-set Jaccard < 0.75; and no dataset loses more than 25% of sessions "
        "because calibration is nonviable. The stronger target Jaccard 0.90 is descriptive, not the minimum GO criterion.\n",
        encoding="utf-8",
    )
    (CAL / "calibration_method_definitions.yaml").write_text(
        "C0_CURRENT_OVERLAP_EMPIRICAL:\n  rest_windows: 1 s\n  hop: 0.5 s\n  estimator: empirical p75/p90\n"
        "C1_NONOVERLAP_EMPIRICAL:\n  rest_windows: 1 s\n  hop: 1 s\n  estimator: empirical p75/p90\n"
        "C2_NONOVERLAP_HARRELL_DAVIS:\n  rest_windows: 1 s\n  hop: 1 s\n  estimator: Harrell-Davis quantile; weights are beta CDF differences over order statistics\n"
        "C3_BLOCK_SUBSAMPLE_EMPIRICAL:\n  rest_windows: 1 s\n  selection: one window per nonoverlapping 2 s block\n  estimator: empirical p75/p90\n"
        "C4_LOSO_SHRINKAGE:\n  rest_windows: 1 s\n  hop: 1 s\n  prior: dataset-level leave-one-subject-out rest prior\n  formula: theta = w * theta_session + (1 - w) * theta_prior, w = n / (n + 20)\n",
        encoding="utf-8",
    )


def list_sessions() -> list[tuple[str, Path, str, str]]:
    sessions: list[tuple[str, Path, str, str]] = []
    for dataset in DATASETS:
        root = ROOT / "data" / "raw" / "openneuro" / dataset
        for edf in sorted(root.rglob("sub-*/ses-*/eeg/*_task-smrbmi_eeg.edf")):
            subject = edf.parts[-4]
            session = edf.parts[-3]
            sessions.append((dataset, edf, subject, session))
    return sessions


def feature_checkpoint_path(dataset: str, subject: str, session: str) -> Path:
    return FEATURE_CKPT / f"{session_id(dataset, subject, session)}_features.csv.gz"


def features_to_rows(features, condition: str) -> list[dict[str, object]]:
    rows = []
    for i, feat in enumerate(features):
        row = {
            "condition": condition,
            "window_index_within_condition": i,
            "valid": bool(feat.valid),
            "smr_snr": float(feat.smr_snr),
            "high_beta_power": float(feat.high_beta_power),
            "broadband_power": float(feat.broadband_power),
            "noise_floor_power": float(feat.noise_floor_power),
            "transient_score": float(feat.transient_score),
        }
        for band in BANDS:
            values = np.asarray(feat.channel_bandpowers[band], dtype=float)
            for c, value in enumerate(values):
                row[f"channel_{band}_{c}"] = float(value)
        rows.append(row)
    return rows


def build_feature_checkpoints() -> pd.DataFrame:
    rows = []
    for dataset, edf, subject, session in list_sessions():
        sid = session_id(dataset, subject, session)
        path = feature_checkpoint_path(dataset, subject, session)
        if path.exists() and path.stat().st_size > 0:
            df = pd.read_csv(path, usecols=["condition"])
            rows.append(
                {
                    "dataset": dataset,
                    "subject": subject,
                    "session": session,
                    "checkpoint": path.relative_to(ROOT).as_posix(),
                    "status": "reused",
                    "rest_windows": int((df["condition"] == "rest").sum()),
                    "task_windows": int((df["condition"] == "task").sum()),
                    "sha256": sha256_file(path),
                }
            )
            write_log(f"[feature skip] {sid}")
            continue
        try:
            fs, rest, task, _task_times = task_segments(edf)
            rest_features, _ = cache_features(rest, fs)
            task_features, _ = cache_features(task, fs)
            out = features_to_rows(rest_features, "rest") + features_to_rows(task_features, "task")
            df = pd.DataFrame(out)
            df.insert(0, "dataset", dataset)
            df.insert(1, "subject", subject)
            df.insert(2, "session", session)
            df.insert(3, "fs", float(fs))
            df.to_csv(path, index=False, compression="gzip")
            rows.append(
                {
                    "dataset": dataset,
                    "subject": subject,
                    "session": session,
                    "checkpoint": path.relative_to(ROOT).as_posix(),
                    "status": "created",
                    "rest_windows": len(rest_features),
                    "task_windows": len(task_features),
                    "sha256": sha256_file(path),
                }
            )
            write_log(f"[feature wrote] {sid} rest={len(rest_features)} task={len(task_features)}")
            del rest, task, rest_features, task_features, df
        except Exception as exc:
            rows.append(
                {
                    "dataset": dataset,
                    "subject": subject,
                    "session": session,
                    "checkpoint": path.relative_to(ROOT).as_posix(),
                    "status": "error",
                    "rest_windows": np.nan,
                    "task_windows": np.nan,
                    "sha256": "",
                    "error": repr(exc),
                }
            )
            write_log(f"[feature error] {sid} {exc!r}")
            (LOG_DIR / f"{sid}_feature_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
    inventory = pd.DataFrame(rows)
    inventory.to_csv(OUT / "checkpoint_inventory.csv", index=False)
    inventory.to_csv(OUT / "reusable_feature_inventory.csv", index=False)
    return inventory


def channel_columns(band: str) -> list[str]:
    return [f"channel_{band}_{i}" for i in range(3)]


@dataclass
class Baseline:
    means: dict[str, np.ndarray]
    stds: dict[str, np.ndarray]


def fit_baseline(rest: pd.DataFrame) -> Baseline:
    means: dict[str, np.ndarray] = {}
    stds: dict[str, np.ndarray] = {}
    for band in BANDS:
        arr = rest[channel_columns(band)].to_numpy(float)
        means[band] = np.nanmean(arr, axis=0)
        sd = np.nanstd(arr, axis=0, ddof=1 if len(arr) > 1 else 0)
        stds[band] = np.where(np.isfinite(sd) & (sd > 0), sd, 1e-9)
    return Baseline(means, stds)


def channel_inconsistency(frame: pd.DataFrame, baseline: Baseline) -> np.ndarray:
    band_scores = []
    for band in BANDS:
        values = frame[channel_columns(band)].to_numpy(float)
        z = (values - baseline.means[band]) / baseline.stds[band]
        band_scores.append(np.nanstd(z, axis=1, ddof=1 if z.shape[1] > 1 else 0))
    return np.nanmean(np.vstack(band_scores), axis=0)


def harrell_davis(values: np.ndarray, q: float) -> float:
    x = np.sort(np.asarray(values, dtype=float)[np.isfinite(values)])
    n = x.size
    if n == 0:
        return float("nan")
    if n == 1:
        return float(x[0])
    a = (n + 1) * q
    b = (n + 1) * (1 - q)
    edges = np.arange(n + 1, dtype=float) / n
    weights = beta_dist.cdf(edges[1:], a, b) - beta_dist.cdf(edges[:-1], a, b)
    return float(np.sum(weights * x))


def estimate_thresholds(rest_subset: pd.DataFrame, method: str, prior_values: dict[str, float] | None = None) -> tuple[dict[str, float], Baseline, float]:
    baseline = fit_baseline(rest_subset)
    rest_values = {
        "smr_snr": rest_subset["smr_snr"].to_numpy(float),
        "high_beta_power": rest_subset["high_beta_power"].to_numpy(float),
        "broadband_power": rest_subset["broadband_power"].to_numpy(float),
        "noise_floor_power": rest_subset["noise_floor_power"].to_numpy(float),
        "transient_score": rest_subset["transient_score"].to_numpy(float),
        "channel_inconsistency": channel_inconsistency(rest_subset, baseline),
    }
    info = METHODS[method]
    limits: dict[str, float] = {}
    n = len(rest_subset)
    weight = n / (n + 20.0)
    for feature, values in rest_values.items():
        q = PERCENTILES[feature] / 100.0
        if info["estimator"] == "HARRELL_DAVIS":
            val = harrell_davis(values, q)
        else:
            val = float(np.nanpercentile(values, PERCENTILES[feature]))
        if info["prior"] and prior_values is not None and feature in prior_values:
            val = float(weight * val + (1.0 - weight) * prior_values[feature])
        limits[FEATURE_TO_LIMIT[feature]] = val
    return limits, baseline, weight


def evaluate_task(task: pd.DataFrame, limits: dict[str, float], baseline: Baseline) -> np.ndarray:
    task_values = task.copy()
    task_values["channel_inconsistency"] = channel_inconsistency(task_values, baseline)
    values = task_values[list(FEATURES)].to_numpy(float)
    finite = np.isfinite(values).all(axis=1)
    return (
        finite
        & (task_values["smr_snr"].to_numpy(float) > limits["smr_snr_min"])
        & (task_values["high_beta_power"].to_numpy(float) < limits["high_beta_max"])
        & (task_values["broadband_power"].to_numpy(float) < limits["broadband_max"])
        & (task_values["noise_floor_power"].to_numpy(float) < limits["noise_floor_max"])
        & (task_values["transient_score"].to_numpy(float) < limits["transient_max"])
        & (task_values["channel_inconsistency"].to_numpy(float) < limits["channel_inconsistency_max"])
    )


def temporal_block_bootstrap_sample(rest: pd.DataFrame, effective_hop: float, rng: np.random.Generator) -> pd.DataFrame:
    block_rows = max(1, int(round(BOOTSTRAP_BLOCK_SECONDS / effective_hop)))
    blocks = [rest.iloc[start : start + block_rows] for start in range(0, len(rest), block_rows)]
    selected: list[pd.DataFrame] = []
    total = 0
    while total < len(rest):
        block = blocks[int(rng.integers(0, len(blocks)))]
        selected.append(block)
        total += len(block)
    return pd.concat(selected, ignore_index=True).iloc[: len(rest)].reset_index(drop=True)


def binary_runs(values: np.ndarray) -> list[tuple[bool, int]]:
    if len(values) == 0:
        return []
    out: list[tuple[bool, int]] = []
    current = bool(values[0])
    length = 1
    for value in values[1:]:
        value = bool(value)
        if value == current:
            length += 1
        else:
            out.append((current, length))
            current = value
            length = 1
    out.append((current, length))
    return out


def longest_withhold(decision: np.ndarray) -> float:
    return max((n * HOP for state, n in binary_runs(decision) if not state), default=0.0)


def compare_decisions(current: np.ndarray, reference: np.ndarray) -> dict[str, object]:
    union_accept = int(np.sum(current | reference))
    union_withhold = int(np.sum((~current) | (~reference)))
    agreement = float(np.mean(current == reference)) if len(reference) else np.nan
    return {
        "decision_agreement": agreement,
        "accepted_set_jaccard": float(np.sum(current & reference) / union_accept) if union_accept else 1.0,
        "withheld_set_jaccard": float(np.sum((~current) & (~reference)) / union_withhold) if union_withhold else 1.0,
        "accepted_count_difference": int(current.sum() - reference.sum()),
        "gate_c_windows_per_min_difference": float((current.sum() - reference.sum()) / (len(reference) * HOP / 60.0)) if len(reference) else np.nan,
        "longest_feedback_free_period_difference_s": float(longest_withhold(current) - longest_withhold(reference)),
        "acceptance_to_withhold_flips": int(np.sum(reference & ~current)),
        "withhold_to_acceptance_flips": int(np.sum(~reference & current)),
    }


def prior_table(feature_files: list[Path]) -> dict[tuple[str, str, str], dict[str, float]]:
    # Keyed by dataset, held-out subject, feature. Values come from other
    # subjects' full nonoverlap rest windows only.
    by_dataset: dict[str, dict[str, list[pd.DataFrame]]] = {}
    for path in feature_files:
        df = pd.read_csv(path)
        rest = df[df["condition"] == "rest"].iloc[::2].copy()
        if rest.empty:
            continue
        dataset = str(rest["dataset"].iloc[0])
        subject = str(rest["subject"].iloc[0])
        by_dataset.setdefault(dataset, {}).setdefault(subject, []).append(rest)
    priors: dict[tuple[str, str, str], dict[str, float]] = {}
    for dataset, subj_map in by_dataset.items():
        for held_out in subj_map:
            others = [frame for subject, frames in subj_map.items() if subject != held_out for frame in frames]
            if not others:
                continue
            rest = pd.concat(others, ignore_index=True)
            limits, _baseline, _weight = estimate_thresholds(rest, "C1_NONOVERLAP_EMPIRICAL")
            priors[(dataset, held_out, "C4_LOSO_SHRINKAGE")] = {LIMIT_TO_FEATURE[k]: v for k, v in limits.items()}
    return priors


def session_available_durations(n_rest: int, step: int) -> list[int | str]:
    available = []
    effective_hop = HOP * step
    for seconds in CHECKPOINTS:
        if math.floor(seconds / effective_hop) <= n_rest:
            available.append(seconds)
    available.append("full")
    return available


def threshold_relative_errors(current: dict[str, float], reference: dict[str, float]) -> dict[str, float]:
    return {f"rel_error_{LIMIT_TO_FEATURE[name]}": abs(current[name] - reference[name]) / (abs(reference[name]) + 1e-12) for name in LIMIT_NAMES}


def process_calibration(feature_inventory: pd.DataFrame) -> None:
    ok = feature_inventory[feature_inventory["status"].isin(["created", "reused"])].copy()
    feature_files = [ROOT / path for path in ok["checkpoint"]]
    priors = prior_table(feature_files)
    result_rows = []
    threshold_rows = []
    split_rows = []
    odd_even_rows = []
    bootstrap_rows = []
    failed_rows = []
    rest_rows = []
    rng = np.random.default_rng(SEED)

    for path in feature_files:
        df = pd.read_csv(path)
        dataset = str(df["dataset"].iloc[0])
        subject = str(df["subject"].iloc[0])
        session = str(df["session"].iloc[0])
        sid = session_id(dataset, subject, session)
        task = df[df["condition"] == "task"].reset_index(drop=True)
        rest_all = df[df["condition"] == "rest"].reset_index(drop=True)
        usable_rest_duration = float(1.0 + max(0, len(rest_all) - 1) * HOP) if len(rest_all) else 0.0
        rest_rows.append(
            {
                "dataset": dataset,
                "subject": subject,
                "session": session,
                "raw_rest_duration_s": usable_rest_duration,
                "usable_rest_duration_s": usable_rest_duration,
                "usable_nonoverlapping_windows": int(len(rest_all.iloc[::2])),
                "maximum_evaluable_checkpoint": max([x for x in CHECKPOINTS if x <= usable_rest_duration], default=0),
            }
        )
        for method, spec in METHODS.items():
            out_path = CAL_CKPT / f"{sid}_{method}.csv"
            checkpoint_paths = calibration_checkpoint_paths(out_path)
            if calibration_checkpoint_complete(out_path):
                result_rows.extend(pd.read_csv(checkpoint_paths["results"]).to_dict("records"))
                threshold_rows.extend(pd.read_csv(checkpoint_paths["thresholds"]).to_dict("records"))
                split_rows.extend(pd.read_csv(checkpoint_paths["split_half"]).to_dict("records"))
                odd_even_rows.extend(pd.read_csv(checkpoint_paths["odd_even"]).to_dict("records"))
                bootstrap_rows.extend(pd.read_csv(checkpoint_paths["bootstrap"]).to_dict("records"))
                write_log(f"[cal skip] {sid} {method}")
                continue
            try:
                rest = rest_all.iloc[:: int(spec["step"])].reset_index(drop=True)
                if len(rest) < 10 or task.empty:
                    failed_rows.append({"dataset": dataset, "subject": subject, "session": session, "method": method, "reason": "insufficient_rest_or_task"})
                    continue
                prior = priors.get((dataset, subject, method))
                full_limits, full_baseline, full_weight = estimate_thresholds(rest, method, prior)
                full_decision = evaluate_task(task, full_limits, full_baseline)
                session_rows = []
                session_threshold_rows = []
                session_split_rows = []
                session_odd_even_rows = []
                session_bootstrap_rows = []
                for duration in session_available_durations(len(rest), int(spec["step"])):
                    if duration == "full":
                        subset = rest
                    else:
                        n = int(math.floor(float(duration) / (HOP * int(spec["step"]))))
                        if n < 10 or n > len(rest):
                            continue
                        subset = rest.iloc[:n].reset_index(drop=True)
                    limits, baseline, weight = estimate_thresholds(subset, method, prior)
                    decision = evaluate_task(task, limits, baseline)
                    row = {
                        "dataset": dataset,
                        "subject": subject,
                        "session": session,
                        "method": method,
                        "checkpoint_s": duration,
                        "rest_windows_used": len(subset),
                        "effective_shrinkage_weight": weight if spec["prior"] else np.nan,
                    }
                    row.update(compare_decisions(decision, full_decision))
                    row.update(threshold_relative_errors(limits, full_limits))
                    session_rows.append(row)
                    for name in LIMIT_NAMES:
                        threshold_row = {
                            "dataset": dataset,
                            "subject": subject,
                            "session": session,
                            "method": method,
                            "checkpoint_s": duration,
                            "threshold_name": name,
                            "feature": LIMIT_TO_FEATURE[name],
                            "threshold_value": limits[name],
                            "full_threshold_value": full_limits[name],
                            "relative_error": abs(limits[name] - full_limits[name]) / (abs(full_limits[name]) + 1e-12),
                        }
                        session_threshold_rows.append(threshold_row)
                # Split-half and odd/even checks.
                half = len(rest) // 2
                if half >= 10:
                    left_limits, left_base, _ = estimate_thresholds(rest.iloc[:half], method, prior)
                    right_limits, right_base, _ = estimate_thresholds(rest.iloc[half:], method, prior)
                    split = {"dataset": dataset, "subject": subject, "session": session, "method": method}
                    split.update(compare_decisions(evaluate_task(task, left_limits, left_base), evaluate_task(task, right_limits, right_base)))
                    session_split_rows.append(split)
                odd = rest.iloc[::2].reset_index(drop=True)
                even = rest.iloc[1::2].reset_index(drop=True)
                if len(odd) >= 10 and len(even) >= 10:
                    odd_limits, odd_base, _ = estimate_thresholds(odd, method, prior)
                    even_limits, even_base, _ = estimate_thresholds(even, method, prior)
                    odd_even = {"dataset": dataset, "subject": subject, "session": session, "method": method}
                    odd_even.update(compare_decisions(evaluate_task(task, odd_limits, odd_base), evaluate_task(task, even_limits, even_base)))
                    session_odd_even_rows.append(odd_even)
                # Temporal block bootstrap from nonoverlapping 10 s rest blocks.
                if len(rest) >= 10:
                    draws = []
                    threshold_draws: dict[str, list[float]] = {name: [] for name in LIMIT_NAMES}
                    effective_hop = HOP * int(spec["step"])
                    for _draw in range(BOOTSTRAP_DRAWS):
                        sample = temporal_block_bootstrap_sample(rest, effective_hop, rng)
                        boot_limits, boot_base, _ = estimate_thresholds(sample, method, prior)
                        draws.append(evaluate_task(task, boot_limits, boot_base))
                        for name in LIMIT_NAMES:
                            threshold_draws[name].append(float(boot_limits[name]))
                    matrix = np.vstack(draws)
                    stability = np.maximum(matrix.mean(axis=0), 1 - matrix.mean(axis=0))
                    boot_row = {
                        "dataset": dataset,
                        "subject": subject,
                        "session": session,
                        "method": method,
                        "bootstrap_draws": BOOTSTRAP_DRAWS,
                        "block_seconds": BOOTSTRAP_BLOCK_SECONDS,
                        "stable_decision_proportion": float(np.mean(stability >= 0.95)),
                        "mean_decision_stability": float(stability.mean()),
                        "unstable_windows": int(np.sum(stability < 0.95)),
                    }
                    for name, values in threshold_draws.items():
                        values_array = np.asarray(values, dtype=float)
                        lo, med, hi = np.nanpercentile(values_array, [2.5, 50.0, 97.5])
                        boot_row[f"{name}_median"] = float(med)
                        boot_row[f"{name}_p025"] = float(lo)
                        boot_row[f"{name}_p975"] = float(hi)
                        boot_row[f"{name}_relative_interval_width"] = float((hi - lo) / (abs(med) + 1e-12))
                    session_bootstrap_rows.append(boot_row)
                atomic_to_csv(pd.DataFrame(session_threshold_rows), checkpoint_paths["thresholds"])
                atomic_to_csv(pd.DataFrame(session_split_rows), checkpoint_paths["split_half"])
                atomic_to_csv(pd.DataFrame(session_odd_even_rows), checkpoint_paths["odd_even"])
                atomic_to_csv(pd.DataFrame(session_bootstrap_rows), checkpoint_paths["bootstrap"])
                atomic_to_csv(pd.DataFrame(session_rows), checkpoint_paths["results"])
                result_rows.extend(session_rows)
                threshold_rows.extend(session_threshold_rows)
                split_rows.extend(session_split_rows)
                odd_even_rows.extend(session_odd_even_rows)
                bootstrap_rows.extend(session_bootstrap_rows)
                write_log(f"[cal wrote] {sid} {method}")
            except Exception as exc:
                failed_rows.append({"dataset": dataset, "subject": subject, "session": session, "method": method, "reason": repr(exc)})
                write_log(f"[cal error] {sid} {method} {exc!r}")
                (LOG_DIR / f"{sid}_{method}_error.txt").write_text(traceback.format_exc(), encoding="utf-8")

    pd.DataFrame(rest_rows).to_csv(CAL / "rest_duration_inventory.csv", index=False)
    results = pd.DataFrame(result_rows)
    results.to_csv(CAL / "calibration_results_by_session.csv", index=False)
    pd.DataFrame(threshold_rows).to_csv(CAL / "calibration_thresholds_long.csv", index=False)
    pd.DataFrame(split_rows).to_csv(CAL / "split_half_results.csv", index=False)
    pd.DataFrame(odd_even_rows).to_csv(CAL / "odd_even_results.csv", index=False)
    pd.DataFrame(bootstrap_rows).to_csv(CAL / "block_bootstrap_results.csv", index=False)
    pd.DataFrame(failed_rows).to_csv(CAL / "failed_sessions.csv", index=False)
    if results.empty:
        raise RuntimeError("No calibration results generated")
    numeric = results[results["checkpoint_s"].astype(str) != "full"].copy()
    numeric["checkpoint_s"] = pd.to_numeric(numeric["checkpoint_s"], errors="raise").astype(int)
    subject = numeric.groupby(["dataset", "subject", "method", "checkpoint_s"], as_index=False).median(numeric_only=True)
    subject.to_csv(CAL / "calibration_results_by_subject.csv", index=False)
    dataset = numeric.groupby(["dataset", "method", "checkpoint_s"], as_index=False).median(numeric_only=True)
    dataset.to_csv(CAL / "calibration_results_by_dataset.csv", index=False)
    pooled = numeric.groupby(["method", "checkpoint_s"], as_index=False).agg(
        sessions=("session", "size"),
        median_accepted_set_jaccard=("accepted_set_jaccard", "median"),
        median_decision_agreement=("decision_agreement", "median"),
        percent_sessions_jaccard_ge_0_80=("accepted_set_jaccard", lambda x: 100.0 * float(np.mean(x >= 0.80))),
        median_withheld_set_jaccard=("withheld_set_jaccard", "median"),
        median_abs_count_difference=("accepted_count_difference", lambda x: float(np.median(np.abs(x)))),
    )
    min_dataset = dataset.groupby(["method", "checkpoint_s"])["accepted_set_jaccard"].min().rename("minimum_dataset_median_jaccard").reset_index()
    pooled = pooled.merge(min_dataset, on=["method", "checkpoint_s"], how="left")
    expected_by_dataset = pd.DataFrame(rest_rows).groupby("dataset")["session"].count().rename("expected_sessions").reset_index()
    viable_by_dataset = numeric.groupby(["dataset", "method", "checkpoint_s"])["session"].count().rename("viable_sessions").reset_index()
    combinations = pooled[["method", "checkpoint_s"]].drop_duplicates().assign(_key=1)
    viability = combinations.merge(expected_by_dataset.assign(_key=1), on="_key").drop(columns="_key")
    viability = viability.merge(viable_by_dataset, on=["dataset", "method", "checkpoint_s"], how="left")
    viability["viable_sessions"] = viability["viable_sessions"].fillna(0)
    viability["loss_pct"] = 100.0 * (1.0 - viability["viable_sessions"] / viability["expected_sessions"])
    max_loss = viability.groupby(["method", "checkpoint_s"])["loss_pct"].max().rename("max_dataset_session_loss_pct").reset_index()
    pooled = pooled.merge(max_loss, on=["method", "checkpoint_s"], how="left")
    pooled["criteria_met"] = (
        (pooled["median_accepted_set_jaccard"] >= 0.85).astype(int)
        + (pooled["percent_sessions_jaccard_ge_0_80"] >= 80.0).astype(int)
        + (pooled["median_decision_agreement"] >= 0.97).astype(int)
        + (pooled["minimum_dataset_median_jaccard"] >= 0.75).astype(int)
        + (pooled["max_dataset_session_loss_pct"] <= 25.0).astype(int)
    )
    pooled["passes_frozen_minimum"] = (
        (pooled["median_accepted_set_jaccard"] >= 0.85)
        & (pooled["percent_sessions_jaccard_ge_0_80"] >= 80.0)
        & (pooled["median_decision_agreement"] >= 0.97)
        & (pooled["minimum_dataset_median_jaccard"] >= 0.75)
        & (pooled["max_dataset_session_loss_pct"] <= 25.0)
    )
    pooled.to_csv(CAL / "calibration_results_pooled.csv", index=False)
    score = pooled[
        [
            "method",
            "checkpoint_s",
            "sessions",
            "median_accepted_set_jaccard",
            "percent_sessions_jaccard_ge_0_80",
            "median_decision_agreement",
            "minimum_dataset_median_jaccard",
            "max_dataset_session_loss_pct",
            "criteria_met",
            "passes_frozen_minimum",
        ]
    ].copy()
    score.to_csv(CAL / "method_success_scorecard.csv", index=False)
    threshold_cols = [c for c in results.columns if c.startswith("rel_error_")]
    instability = results.groupby(["method", "checkpoint_s"], as_index=False)[threshold_cols].median(numeric_only=True)
    instability.to_csv(CAL / "feature_instability_summary.csv", index=False)
    best = pooled.sort_values(
        ["passes_frozen_minimum", "criteria_met", "median_accepted_set_jaccard", "checkpoint_s"],
        ascending=[False, False, False, True],
    ).iloc[0]
    if bool(best["passes_frozen_minimum"]):
        conclusion = f"Selected primary method-duration: {best['method']} at {int(best['checkpoint_s'])} s."
        outcome = "Stage 1 PASS"
    else:
        conclusion = "No calibration method passed the frozen minimum criteria."
        outcome = "Stage 1 FAIL / scientific remediation stop"
    (CAL / "calibration_final_report.md").write_text(
        "# Calibration final report\n\n"
        f"Outcome: {outcome}.\n\n"
        f"{conclusion}\n\n"
        f"Best observed numeric checkpoint: {best['method']} at {int(best['checkpoint_s'])} s; "
        f"median accepted-set Jaccard={best['median_accepted_set_jaccard']:.3f}; "
        f"sessions with Jaccard >=0.80={best['percent_sessions_jaccard_ge_0_80']:.1f}%; "
        f"median decision agreement={best['median_decision_agreement']:.3f}; "
        f"minimum dataset median Jaccard={best['minimum_dataset_median_jaccard']:.3f}; "
        f"max dataset session loss={best['max_dataset_session_loss_pct']:.1f}%.\n\n"
        "Full-baseline rows are reference-only and were not used for pass/fail scoring. If Stage 1 fails, later "
        "scientific remediation stages are not executed under the frozen stop rule.\n",
        encoding="utf-8",
    )


def write_progress(status: str) -> None:
    rows = []
    for path in FEATURE_CKPT.glob("*_features.csv.gz"):
        rows.append({"stage": "feature_cache", "checkpoint": path.relative_to(ROOT).as_posix(), "status": "present", "bytes": path.stat().st_size})
    for path in CAL_CKPT.glob("*.csv"):
        rows.append({"stage": "calibration", "checkpoint": path.relative_to(ROOT).as_posix(), "status": "present", "bytes": path.stat().st_size})
    rows.append({"stage": "overall", "checkpoint": "", "status": status, "bytes": ""})
    pd.DataFrame(rows).to_csv(OUT / "execution_progress.csv", index=False)


def main() -> int:
    ensure_dirs()
    write_frozen_specs()
    write_log("[start] Stage 1 checkpointed calibration")
    inventory = build_feature_checkpoints()
    process_calibration(inventory)
    write_progress("stage1_complete")
    write_log("[done] Stage 1 checkpointed calibration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
