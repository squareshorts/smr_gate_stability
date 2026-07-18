"""STAGE 2-5 — controlled degradation campaign (checkpointed, one session at a time)."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for c in (ROOT, ROOT / "src"):
    if str(c) not in sys.path:
        sys.path.insert(0, str(c))
from scripts.conjunctive_gate_stability.degradation_common import (
    FAMILIES, load_canonical, load_raw_task_windows, features_from_window, degrade)
from scripts.conjunctive_law_remedy.remedy_methods import (
    calibrate_and_apply, score_vector, feature_matrix, fit_channel_baseline, percentile_scores, CRIT, FEATURES)

OUTD = ROOT / "results" / "conjunctive_gate_final" / "degradation"
CKPT = ROOT / "results" / "conjunctive_gate_final" / "checkpoints" / "degradation"
LOGD = ROOT / "results" / "conjunctive_gate_final" / "checkpoints" / "logs"
for d in (OUTD, CKPT, LOGD):
    d.mkdir(parents=True, exist_ok=True)
FEATCOLS = ["high_beta_power", "broadband_power", "noise_floor_power", "transient_score"] + \
           [f"channel_{b}_{i}" for i in range(3) for b in ("smr", "beta", "broadband", "noise")]
METHODS = ["R0_ORIGINAL_AND", "R1_MEAN_PERCENTILE", "R2_RMS_PERCENTILE"]


def now():
    return datetime.now().isoformat(timespec="seconds")


def variants():
    v = [("D0_unchanged", 0)]
    for fam in FAMILIES[1:9]:
        for lvl in (1, 2, 3, 4):
            v.append((fam, lvl))
    v.append(("D9_missing_channel", 1))
    return v


def r1_threshold_and_scores(rest, df):
    thr = np.percentile(score_vector(rest, rest, "R1_MEAN_PERCENTILE"), 75)
    sc = score_vector(rest, df, "R1_MEAN_PERCENTILE")
    return float(thr), sc


def process(dataset, subject, session, key):
    can = load_canonical(key)
    rest = can[can.condition == "rest"].reset_index(drop=True)
    task = can[can.condition == "task"].reset_index(drop=True)
    fs, wins = load_raw_task_windows(dataset, subject, session)
    task["t"] = task.window_start_s.round(3)
    cand = task[task.t.isin(wins.keys())].reset_index(drop=True)
    if cand.empty:
        return None, {"session": key, "eligible": 0, "reason": "no aligned windows"}
    # eligibility: valid & accepted by both R0 and R1 (p75)
    r0 = calibrate_and_apply(rest, cand, "R0_ORIGINAL_AND", 75.0)
    r1 = calibrate_and_apply(rest, cand, "R1_MEAN_PERCENTILE", 75.0)
    elig = cand[(cand.raw_feature_valid.astype(bool)) & r0 & r1].reset_index(drop=True)
    n_elig = len(elig)
    if n_elig == 0:
        return None, {"session": key, "eligible": 0, "reason": "none accepted by both"}
    # deterministic even selection of <=10
    idx = np.linspace(0, n_elig - 1, min(10, n_elig)).round().astype(int)
    idx = sorted(set(idx.tolist()))
    sel = elig.iloc[idx].reset_index(drop=True)

    # build degraded feature table
    rows_meta = []
    feat_rows = []
    repro = []
    for _, r in sel.iterrows():
        t = float(r.t); gindex = int(r.overall_window_index)
        w0 = wins[round(t, 3)]
        ch = gindex % 3
        # reproduction on unchanged
        f0 = features_from_window(w0, fs)
        rel = max(abs(f0.get(c, np.nan) - r[c]) / (abs(r[c]) + 1e-20) for c in ["high_beta_power", "broadband_power", "noise_floor_power", "transient_score"])
        repro.append({"session": key, "window_start_s": t, "max_rel_feature_diff": float(rel)})
        for fam, lvl in variants():
            wd = degrade(w0, fs, fam, lvl, ch, gindex)
            fd = features_from_window(wd, fs)
            row = {c: fd.get(c, np.nan) for c in FEATCOLS}
            row["raw_feature_valid"] = bool(fd.get("raw_feature_valid", False))
            row["peak_to_peak_uv"] = fd.get("peak_to_peak_uv", np.nan)
            feat_rows.append(row)
            rows_meta.append({"dataset": dataset, "subject": subject, "session": session, "session_key": key,
                              "window_start_s": t, "affected_channel_index": ch, "family": fam, "severity": lvl,
                              "hb_before": r.high_beta_power, "bb_before": r.broadband_power,
                              "nf_before": r.noise_floor_power, "tr_before": r.transient_score,
                              "hb_after": row["high_beta_power"], "bb_after": row["broadband_power"],
                              "nf_after": row["noise_floor_power"], "tr_after": row["transient_score"]})
    fdf = pd.DataFrame(feat_rows).reindex(columns=FEATCOLS + ["raw_feature_valid", "peak_to_peak_uv"])
    meta = pd.DataFrame(rows_meta)
    # gate decisions (batched)
    for m in METHODS:
        meta[f"accept_{m}"] = calibrate_and_apply(rest, fdf, m, 75.0)
        meta[f"response_{m}"] = ~meta[f"accept_{m}"].astype(bool)
    thr, sc = r1_threshold_and_scores(rest, fdf)
    meta["r1_score_after"] = sc
    meta["r1_threshold"] = thr
    meta["r1_distance_to_threshold"] = thr - sc
    meta["structurally_invalid"] = ~fdf.raw_feature_valid.astype(bool).to_numpy()
    return (meta, pd.DataFrame(repro)), {"session": key, "eligible": n_elig, "selected": len(sel),
                                         "flag_lt5": n_elig < 5, "reason": ""}


def main():
    sessions = sorted(load_manifest())
    progress, errors, excl, reprod = [], [], [], []
    for seq, (dataset, subject, session, key) in enumerate(sessions, 1):
        cp = CKPT / f"{key}.parquet"
        rp = CKPT / f"{key}_repro.parquet"
        if cp.exists():
            progress.append({"seq": seq, "session_key": key, "status": "reused", "timestamp": now()}); continue
        try:
            res, info = process(dataset, subject, session, key)
            if res is None:
                excl.append(info); progress.append({"seq": seq, "session_key": key, "status": "excluded", "timestamp": now()}); continue
            meta, repro = res
            meta.to_parquet(cp, index=False); repro.to_parquet(rp, index=False)
            if info["flag_lt5"]:
                excl.append(info)
            progress.append({"seq": seq, "session_key": key, "status": "computed", "timestamp": now(),
                             "eligible": info["eligible"], "selected": info["selected"]})
        except Exception as exc:  # noqa
            errors.append({"timestamp": now(), "session_key": key, "error": repr(exc)[:300]})
            progress.append({"seq": seq, "session_key": key, "status": "error", "timestamp": now()})
        if seq % 20 == 0:
            print(f"[degradation {seq}/{len(sessions)}]", flush=True)
    pd.DataFrame(progress).to_csv(OUTD.parent / "execution_progress.csv", index=False)
    pd.DataFrame(errors, columns=["timestamp", "session_key", "error"]).to_csv(OUTD.parent / "execution_errors.csv", index=False)
    pd.DataFrame(excl).to_csv(OUTD / "source_window_exclusions.csv", index=False)
    print(f"done sessions={len(sessions)} errors={len(errors)} excluded={len(excl)}")


def load_manifest():
    out = []
    for p in sorted((ROOT / "results" / "baseline_gate_stability" / "checkpoints" / "features").glob("*_canonical.csv.gz")):
        key = p.name.removesuffix("_canonical.csv.gz")
        parts = key.split("_")
        out.append((parts[0], parts[1], parts[2], key))
    return out


if __name__ == "__main__":
    main()
