"""Frozen numerical primitives for the baseline-gate stability study."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd


FEATURES = ("high_beta_power", "broadband_power", "noise_floor_power", "transient_score", "channel_inconsistency")
MONITORS = ("M0_NO_GATE", "M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY")
PERCENTILES = {
    "smr_snr": 75.0,
    "high_beta_power": 75.0,
    "broadband_power": 75.0,
    "noise_floor_power": 75.0,
    "transient_score": 90.0,
    "channel_inconsistency": 75.0,
}
BANDS = ("smr", "beta", "broadband", "noise")


@dataclass(frozen=True)
class ChannelBaseline:
    means: dict[str, np.ndarray]
    stds: dict[str, np.ndarray]


def channel_columns(band: str) -> list[str]:
    return [f"channel_{band}_{index}" for index in range(3)]


def fit_channel_baseline(rest: pd.DataFrame) -> ChannelBaseline:
    means: dict[str, np.ndarray] = {}
    stds: dict[str, np.ndarray] = {}
    for band in BANDS:
        values = rest[channel_columns(band)].to_numpy(float)
        means[band] = np.nanmean(values, axis=0)
        sd = np.nanstd(values, axis=0, ddof=1 if len(values) > 1 else 0)
        stds[band] = np.where(np.isfinite(sd) & (sd > 0), sd, 1e-12)
    return ChannelBaseline(means, stds)


def channel_inconsistency(frame: pd.DataFrame, baseline: ChannelBaseline) -> np.ndarray:
    band_scores = []
    for band in BANDS:
        values = frame[channel_columns(band)].to_numpy(float)
        z = (values - baseline.means[band]) / baseline.stds[band]
        band_scores.append(np.nanstd(z, axis=1, ddof=1))
    return np.nanmean(np.vstack(band_scores), axis=0)


def fit_quality_thresholds(rest: pd.DataFrame) -> tuple[dict[str, float], ChannelBaseline]:
    baseline = fit_channel_baseline(rest)
    limits = {
        "smr_snr": float(np.nanpercentile(rest["smr_snr"], PERCENTILES["smr_snr"])),
        "high_beta_power": float(np.nanpercentile(rest["high_beta_power"], PERCENTILES["high_beta_power"])),
        "broadband_power": float(np.nanpercentile(rest["broadband_power"], PERCENTILES["broadband_power"])),
        "noise_floor_power": float(np.nanpercentile(rest["noise_floor_power"], PERCENTILES["noise_floor_power"])),
        "transient_score": float(np.nanpercentile(rest["transient_score"], PERCENTILES["transient_score"])),
        "channel_inconsistency": float(np.nanpercentile(channel_inconsistency(rest, baseline), PERCENTILES["channel_inconsistency"])),
    }
    return limits, baseline


def prepare_with_baseline(frame: pd.DataFrame, baseline: ChannelBaseline) -> pd.DataFrame:
    prepared = frame.copy()
    prepared["channel_inconsistency"] = channel_inconsistency(prepared, baseline)
    return prepared


def apply_monitor(frame: pd.DataFrame, monitor: str, thresholds: Mapping[str, float] | None = None) -> tuple[np.ndarray, list[str]]:
    if monitor not in MONITORS:
        raise ValueError(f"Unknown monitor: {monitor}")
    required = ["high_beta_power", "broadband_power", "noise_floor_power", "transient_score", "channel_inconsistency", "peak_to_peak_uv"]
    values = frame[required].apply(pd.to_numeric, errors="coerce")
    base = frame["raw_feature_valid"].astype(bool).to_numpy() & np.isfinite(values.to_numpy()).all(axis=1)
    decisions = base.copy()
    reasons: list[str] = []
    for position, (_index, row) in enumerate(values.iterrows()):
        row_reasons: list[str] = []
        if not base[position]:
            row_reasons.append("invalid_input")
        if monitor in {"M1_HIGH_BETA", "M4_NFSQI_FULL_QUALITY"} and float(row["high_beta_power"]) >= float(thresholds["high_beta_power"]):
            decisions[position] = False
            row_reasons.append("high_beta")
        if monitor in {"M2_BROADBAND_HIGH_FREQUENCY", "M4_NFSQI_FULL_QUALITY"}:
            if float(row["broadband_power"]) >= float(thresholds["broadband_power"]):
                decisions[position] = False
                row_reasons.append("broadband")
            if float(row["noise_floor_power"]) >= float(thresholds["noise_floor_power"]):
                decisions[position] = False
                row_reasons.append("noise_floor")
        if monitor == "M3_AMPLITUDE_150" and float(row["peak_to_peak_uv"]) >= 150.0:
            decisions[position] = False
            row_reasons.append("amplitude_150")
        if monitor == "M4_NFSQI_FULL_QUALITY":
            if float(row["transient_score"]) >= float(thresholds["transient_score"]):
                decisions[position] = False
                row_reasons.append("transient")
            if float(row["channel_inconsistency"]) >= float(thresholds["channel_inconsistency"]):
                decisions[position] = False
                row_reasons.append("channel_inconsistency")
        reasons.append(";".join(row_reasons))
    return decisions.astype(bool), reasons


def agreement_metrics(left: np.ndarray, right: np.ndarray) -> dict[str, float | int]:
    left = np.asarray(left, dtype=bool)
    right = np.asarray(right, dtype=bool)
    if left.shape != right.shape:
        raise ValueError("Decision vectors must use identical evaluation windows")
    tp = int(np.sum(left & right))
    tn = int(np.sum(~left & ~right))
    fp = int(np.sum(left & ~right))
    fn = int(np.sum(~left & right))
    n = len(left)
    observed = (tp + tn) / n if n else np.nan
    p_left = (tp + fp) / n if n else np.nan
    p_right = (tp + fn) / n if n else np.nan
    expected = p_left * p_right + (1 - p_left) * (1 - p_right) if n else np.nan
    union_accept = tp + fp + fn
    union_withhold = tn + fp + fn
    return {
        "n_windows": n,
        "overall_agreement": observed,
        "accepted_set_jaccard": tp / union_accept if union_accept else 1.0,
        "withheld_set_jaccard": tn / union_withhold if union_withhold else 1.0,
        "cohens_kappa": (observed - expected) / (1 - expected) if n and expected < 1 else 1.0,
        "positive_agreement": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 1.0,
        "negative_agreement": 2 * tn / (2 * tn + fp + fn) if (2 * tn + fp + fn) else 1.0,
        "acceptance_rate_left": float(np.mean(left)) if n else np.nan,
        "acceptance_rate_right": float(np.mean(right)) if n else np.nan,
        "acceptance_rate_difference": float(np.mean(left) - np.mean(right)) if n else np.nan,
        "acceptance_to_withhold_flips": fn,
        "withhold_to_acceptance_flips": fp,
    }


def temporal_metrics(decisions: np.ndarray, hop_s: float = 0.5) -> tuple[dict[str, float | int | bool], list[dict[str, float | int | str]]]:
    values = np.asarray(decisions, dtype=bool)
    n = len(values)
    duration_s = n * hop_s
    accepted = np.flatnonzero(values)
    intervals = np.diff(accepted) * hop_s if len(accepted) > 1 else np.array([], dtype=float)
    runs: list[tuple[bool, int, int]] = []
    if n:
        start = 0
        state = bool(values[0])
        for index, value in enumerate(values[1:], 1):
            if bool(value) != state:
                runs.append((state, start, index - start))
                start, state = index, bool(value)
        runs.append((state, start, n - start))
    withhold = [length * hop_s for state, _, length in runs if not state]
    accept = [length * hop_s for state, _, length in runs if state]
    events = [
        {"state": "accept" if state else "withhold", "start_window": start, "length_windows": length, "duration_s": length * hop_s}
        for state, start, length in runs
    ]
    metrics = {
        "n_windows": n,
        "accepted_windows": int(values.sum()),
        "accepted_windows_per_min": float(values.sum() / duration_s * 60) if duration_s else np.nan,
        "acceptance_duty_cycle": float(values.mean()) if n else np.nan,
        "median_inter_acceptance_s": float(np.median(intervals)) if len(intervals) else np.nan,
        "p95_inter_acceptance_s": float(np.percentile(intervals, 95)) if len(intervals) else np.nan,
        "longest_feedback_free_s": max(withhold, default=0.0),
        "gaps_gt_5s": int(sum(value > 5 for value in withhold)),
        "gaps_gt_10s": int(sum(value > 10 for value in withhold)),
        "gaps_gt_20s": int(sum(value > 20 for value in withhold)),
        "gaps_gt_30s": int(sum(value > 30 for value in withhold)),
        "any_gap_gt_20s": bool(any(value > 20 for value in withhold)),
        "any_gap_gt_30s": bool(any(value > 30 for value in withhold)),
        "median_accept_run_s": float(np.median(accept)) if accept else 0.0,
        "median_withhold_run_s": float(np.median(withhold)) if withhold else 0.0,
        "state_transitions_per_min": float(max(0, len(runs) - 1) / duration_s * 60) if duration_s else np.nan,
        "time_to_first_accepted_s": float(accepted[0] * hop_s) if len(accepted) else np.nan,
    }
    return metrics, events


def regularize_covariance(covariance: np.ndarray, alpha: float = 0.10) -> np.ndarray:
    covariance = np.asarray(covariance, dtype=float)
    if covariance.shape != (3, 3) or not np.isfinite(covariance).all():
        raise ValueError("Covariance must be finite 3x3")
    target = np.trace(covariance) / 3.0
    regularized = (1.0 - alpha) * covariance + alpha * target * np.eye(3)
    eigenvalues = np.linalg.eigvalsh(regularized)
    if np.any(eigenvalues <= 0):
        raise ValueError("Regularized covariance is not positive definite")
    return regularized


def log_covariance_vector(covariance: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eigh(regularize_covariance(covariance))
    log_matrix = (vectors * np.log(values)) @ vectors.T
    return np.asarray([log_matrix[0, 0], np.sqrt(2) * log_matrix[0, 1], np.sqrt(2) * log_matrix[0, 2], log_matrix[1, 1], np.sqrt(2) * log_matrix[1, 2], log_matrix[2, 2]])
