"""Frozen single-score remedy methods (R0-R3) and percentile-score transforms."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "results" / "baseline_gate_stability" / "checkpoints" / "features"

FEATURES = {
    "Q1_high_beta": ("high_beta_power", 75.0),
    "Q2_broadband": ("broadband_power", 75.0),
    "Q3_high_freq_35_45": ("noise_floor_power", 75.0),
    "Q4_transient": ("transient_score", 90.0),
    "Q5_channel_inconsistency": ("channel_inconsistency", 75.0),
}
CRIT = list(FEATURES)
BANDS = ("smr", "beta", "broadband", "noise")
ALPHA = 0.10  # frozen covariance shrinkage
EPS = 1e-12


def channel_columns(band):
    return [f"channel_{band}_{i}" for i in range(3)]


def fit_channel_baseline(rest):
    means, stds = {}, {}
    for band in BANDS:
        v = rest[channel_columns(band)].to_numpy(float)
        means[band] = np.nanmean(v, axis=0)
        sd = np.nanstd(v, axis=0, ddof=1 if len(v) > 1 else 0)
        stds[band] = np.where(np.isfinite(sd) & (sd > 0), sd, 1e-12)
    return means, stds


def channel_inconsistency(frame, baseline):
    means, stds = baseline
    scores = []
    for band in BANDS:
        v = frame[channel_columns(band)].to_numpy(float)
        z = (v - means[band]) / stds[band]
        scores.append(np.nanstd(z, axis=1, ddof=1))
    return np.nanmean(np.vstack(scores), axis=0)


def feature_matrix(frame, baseline):
    """Return (n,5) feature matrix in CRIT order using given channel baseline for Q5."""
    cols = []
    for c in CRIT:
        if c == "Q5_channel_inconsistency":
            cols.append(channel_inconsistency(frame, baseline))
        else:
            cols.append(frame[FEATURES[c][0]].to_numpy(float))
    return np.column_stack(cols)


def validity(frame):
    return frame["raw_feature_valid"].astype(bool).to_numpy()


def percentile_scores(task_feat, rest_feat):
    """u_j for each task row: empirical CDF vs rest column (mean(rest<=x))."""
    n_task = task_feat.shape[0]
    U = np.zeros_like(task_feat)
    for j in range(task_feat.shape[1]):
        rc = rest_feat[:, j]
        rc = rc[np.isfinite(rc)]
        if rc.size == 0:
            U[:, j] = 1.0
            continue
        rc_sorted = np.sort(rc)
        U[:, j] = np.searchsorted(rc_sorted, task_feat[:, j], side="right") / rc_sorted.size
    return U


def regularized_cov(U_rest):
    cov = np.cov(U_rest, rowvar=False)
    if cov.ndim == 0:
        cov = np.array([[float(cov)]])
    d = cov.shape[0]
    target = np.trace(cov) / d
    reg = (1 - ALPHA) * cov + ALPHA * target * np.eye(d)
    reg += 1e-9 * np.eye(d)
    return reg


def calibrate_and_apply(rest_block, task, method, threshold_pct):
    """Return boolean accept vector on task windows for a method calibrated on rest_block.

    R0 uses original per-criterion percentile thresholds joined by AND.
    R1-R3 build percentile scores vs rest_block and threshold at threshold_pct of rest score.
    """
    baseline = fit_channel_baseline(rest_block)
    rest_feat = feature_matrix(rest_block, baseline)
    task_feat = feature_matrix(task, baseline)
    valid = validity(task)
    finite = np.isfinite(task_feat).all(axis=1)
    base = valid & finite

    if method == "R0_ORIGINAL_AND":
        accept = base.copy()
        for j, c in enumerate(CRIT):
            pct = FEATURES[c][1]
            col = rest_feat[:, j]
            col = col[np.isfinite(col)]
            thr = np.nanpercentile(col, pct) if col.size else np.inf
            accept &= (task_feat[:, j] < thr)
        return accept.astype(bool)

    # percentile-score methods
    U_task = percentile_scores(task_feat, rest_feat)
    U_rest = percentile_scores(rest_feat, rest_feat)
    if method == "R1_MEAN_PERCENTILE":
        s_task = U_task.mean(axis=1)
        s_rest = U_rest.mean(axis=1)
    elif method == "R2_RMS_PERCENTILE":
        s_task = np.sqrt((U_task ** 2).mean(axis=1))
        s_rest = np.sqrt((U_rest ** 2).mean(axis=1))
    elif method == "R3_ROBUST_MAHALANOBIS_PERCENTILE":
        center = np.median(U_rest, axis=0)
        cov = regularized_cov(U_rest)
        inv = np.linalg.inv(cov)
        def maha(U):
            d = U - center
            return np.sqrt(np.einsum("ij,jk,ik->i", d, inv, d))
        s_task = maha(U_task)
        s_rest = maha(U_rest)
    else:
        raise ValueError(method)
    thr = np.percentile(s_rest, threshold_pct)
    accept = base & (s_task < thr)
    return accept.astype(bool)


def apply_with_threshold(rest_block, task, method, abs_threshold):
    """Apply a method with an externally frozen absolute score threshold (matched-availability)."""
    baseline = fit_channel_baseline(rest_block)
    rest_feat = feature_matrix(rest_block, baseline)
    task_feat = feature_matrix(task, baseline)
    base = validity(task) & np.isfinite(task_feat).all(axis=1)
    U_task = percentile_scores(task_feat, rest_feat)
    U_rest = percentile_scores(rest_feat, rest_feat)
    if method == "R1_MEAN_PERCENTILE":
        s_task = U_task.mean(axis=1)
    elif method == "R2_RMS_PERCENTILE":
        s_task = np.sqrt((U_task ** 2).mean(axis=1))
    elif method == "R3_ROBUST_MAHALANOBIS_PERCENTILE":
        center = np.median(U_rest, axis=0)
        inv = np.linalg.inv(regularized_cov(U_rest))
        d = U_task - center
        s_task = np.sqrt(np.einsum("ij,jk,ik->i", d, inv, d))
    else:
        raise ValueError(method)
    return (base & (s_task < abs_threshold)).astype(bool)


def score_vector(rest_block, task, method):
    """Return the raw single-score vector on task (for matched-availability threshold search)."""
    baseline = fit_channel_baseline(rest_block)
    rest_feat = feature_matrix(rest_block, baseline)
    task_feat = feature_matrix(task, baseline)
    U_task = percentile_scores(task_feat, rest_feat)
    U_rest = percentile_scores(rest_feat, rest_feat)
    if method == "R1_MEAN_PERCENTILE":
        return U_task.mean(axis=1)
    if method == "R2_RMS_PERCENTILE":
        return np.sqrt((U_task ** 2).mean(axis=1))
    center = np.median(U_rest, axis=0)
    inv = np.linalg.inv(regularized_cov(U_rest))
    d = U_task - center
    return np.sqrt(np.einsum("ij,jk,ik->i", d, inv, d))
