import numpy as np
import pandas as pd
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.external_validation.engine import (
    CRITERIA, CRIT_ORDER, nonempty_subsets, subset_id, jaccard, pass_indicators,
    empirical_threshold, channel_inconsistency
)

CACHE_DIR = Path(__file__).parent / "cache"
OUT_DIR = ROOT / "results" / "external_validation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BANDS = ("smr", "beta", "broadband", "noise")
FROZEN_PCT = {c: p for c, (_, p) in CRITERIA.items()}

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

def criterion_thresholds(block: pd.DataFrame, pct_map: dict[str, float]):
    means, stds = fit_channel_baseline(block)
    ci_block = channel_inconsistency(block, means, stds)
    thr = {}
    for crit, (col, _) in CRITERIA.items():
        if col == "channel_inconsistency":
            thr[crit] = empirical_threshold(ci_block, pct_map[crit])
        else:
            thr[crit] = empirical_threshold(block[col].to_numpy(float), pct_map[crit])
    return thr, (means, stds)

def pass_indicators_local(task: pd.DataFrame, thr, base, valid: np.ndarray) -> dict[str, np.ndarray]:
    means, stds = base
    ci_task = channel_inconsistency(task, means, stds)
    out = {}
    for crit, (col, _) in CRITERIA.items():
        if col == "channel_inconsistency":
            out[crit] = valid & (ci_task <= thr[crit])
        else:
            out[crit] = valid & (task[col].to_numpy(float) <= thr[crit])
    return out

def aggregate_scores(task: pd.DataFrame, thr, base) -> dict[str, np.ndarray]:
    means, stds = base
    ci_task = channel_inconsistency(task, means, stds)
    n = len(task)
    scores = np.zeros((n, 5), dtype=float)
    for i, (crit, (col, _)) in enumerate(CRITERIA.items()):
        val = ci_task if col == "channel_inconsistency" else task[col].to_numpy(float)
        scores[:, i] = val / (thr[crit] + 1e-12)
    return {
        "mean": np.nanmean(scores, axis=1),
        "rms": np.sqrt(np.nanmean(scores**2, axis=1))
    }
