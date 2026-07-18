"""Shared frozen primitives for the conjunctive-gate-instability feasibility study.

Scope-limited: reads ONLY the verified canonical per-window feature cache from the
baseline-gate-stability study. No raw EDF, no downloads, no heavy model deps.
"""
from __future__ import annotations

import gzip
import hashlib
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

# Repo layout ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "results" / "baseline_gate_stability" / "checkpoints" / "features"
OUT = ROOT / "results" / "conjunctive_gate_instability"
CKPT = OUT / "checkpoints"

# Frozen five quality criteria (upper-bound rejections) ---------------------
# Q_j : criterion label -> (cache feature column, calibration percentile)
CRITERIA = {
    "Q1_high_beta": ("high_beta_power", 75.0),
    "Q2_broadband": ("broadband_power", 75.0),
    "Q3_high_freq_35_45": ("noise_floor_power", 75.0),
    "Q4_transient": ("transient_score", 90.0),
    "Q5_channel_inconsistency": ("channel_inconsistency", 75.0),
}
CRIT_ORDER = list(CRITERIA.keys())
BANDS = ("smr", "beta", "broadband", "noise")

HOP_S = 0.5          # canonical hop
WINDOW_S = 1.0       # canonical window length
CALIB_TARGET_S = 60.0
CALIB_MIN_S = 30.0
MATERIAL_DELTA = 0.02


def channel_columns(band: str) -> list[str]:
    return [f"channel_{band}_{i}" for i in range(3)]


def fit_channel_baseline(rest: pd.DataFrame):
    means, stds = {}, {}
    for band in BANDS:
        values = rest[channel_columns(band)].to_numpy(float)
        means[band] = np.nanmean(values, axis=0)
        sd = np.nanstd(values, axis=0, ddof=1 if len(values) > 1 else 0)
        stds[band] = np.where(np.isfinite(sd) & (sd > 0), sd, 1e-12)
    return means, stds


def channel_inconsistency(frame: pd.DataFrame, means, stds) -> np.ndarray:
    band_scores = []
    for band in BANDS:
        values = frame[channel_columns(band)].to_numpy(float)
        z = (values - means[band]) / stds[band]
        band_scores.append(np.nanstd(z, axis=1, ddof=1))
    return np.nanmean(np.vstack(band_scores), axis=0)


def nonempty_subsets():
    """All 31 nonempty subsets of Q1..Q5 as tuples of criterion labels."""
    subsets = []
    for k in range(1, len(CRIT_ORDER) + 1):
        for combo in combinations(CRIT_ORDER, k):
            subsets.append(combo)
    return subsets


def subset_id(subset) -> str:
    idx = [str(CRIT_ORDER.index(c) + 1) for c in subset]
    return "Q" + "".join(idx)


def load_session(path: Path) -> pd.DataFrame:
    with gzip.open(path, "rt") as fh:
        return pd.read_csv(fh)


def session_key_from_path(path: Path) -> str:
    return path.name.removesuffix("_canonical.csv.gz")


def sha256_bytes(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
