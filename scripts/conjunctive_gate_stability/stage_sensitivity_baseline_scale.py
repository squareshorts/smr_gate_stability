"""TASK 1 (part B) — prespecified sensitivity: robust scale from session rest baseline.

Reuses the SAME selected source windows, degradation transforms, methods, thresholds, and severity
ordering as the primary per-window-scale campaign; only the robust scale changes (rest baseline).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for c in (ROOT, ROOT / "src"):
    if str(c) not in sys.path:
        sys.path.insert(0, str(c))
from scripts.conjunctive_gate_stability.degradation_common import (
    load_canonical, load_raw_task_windows, features_from_window, degrade)
from scripts.conjunctive_gate_stability.stage2_5_degradation import variants, FEATCOLS, METHODS
from scripts.conjunctive_law_remedy.remedy_methods import calibrate_and_apply

DEG = ROOT / "results" / "conjunctive_gate_final" / "degradation"
PCK = ROOT / "results" / "conjunctive_gate_final" / "checkpoints" / "degradation"
SCK = ROOT / "results" / "conjunctive_gate_final" / "checkpoints" / "degradation_baseline_scale"
SCK.mkdir(parents=True, exist_ok=True)


def process(key):
    parts = key.split("_"); dataset, subject, session = parts[0], parts[1], parts[2]
    prim = pd.read_parquet(PCK / f"{key}.parquet")
    sel = prim[prim.family == "D0_unchanged"][["window_start_s", "affected_channel_index"]].drop_duplicates()
    if sel.empty:
        return None
    can = load_canonical(key)
    rest = can[can.condition == "rest"].reset_index(drop=True)
    task = can[can.condition == "task"].reset_index(drop=True)
    task["t"] = task.window_start_s.round(3)
    tmap = dict(zip(task.t, task.overall_window_index))
    fs, wins, rest_sigma = load_raw_task_windows(dataset, subject, session, with_rest_sigma=True)
    if rest_sigma is None:
        return None
    meta, feat_rows = [], []
    for _, s in sel.iterrows():
        t = round(float(s.window_start_s), 3)
        if t not in wins:
            continue
        gindex = int(tmap.get(t, 0)); ch = gindex % 3
        w0 = wins[t]
        for fam, lvl in variants():
            wd = degrade(w0, fs, fam, lvl, ch, gindex, sigma_override=rest_sigma)
            fd = features_from_window(wd, fs)
            row = {c: fd.get(c, np.nan) for c in FEATCOLS}
            row["raw_feature_valid"] = bool(fd.get("raw_feature_valid", False))
            row["peak_to_peak_uv"] = fd.get("peak_to_peak_uv", np.nan)
            feat_rows.append(row)
            meta.append({"dataset": dataset, "subject": subject, "session": session,
                         "window_start_s": t, "family": fam, "severity": lvl})
    fdf = pd.DataFrame(feat_rows).reindex(columns=FEATCOLS + ["raw_feature_valid", "peak_to_peak_uv"])
    m = pd.DataFrame(meta)
    for method in METHODS:
        m[f"response_{method}"] = ~calibrate_and_apply(rest, fdf, method, 75.0).astype(bool)
    return m


def main():
    keys = [p.name.removesuffix(".parquet") for p in sorted(PCK.glob("*.parquet")) if not p.name.endswith("_repro.parquet")]
    done = 0
    for key in keys:
        cp = SCK / f"{key}.parquet"
        if cp.exists():
            done += 1; continue
        r = process(key)
        if r is not None:
            r.to_parquet(cp, index=False)
        done += 1
    print(f"baseline-scale sessions processed/reused: {done}/{len(keys)}")
    # aggregate comparison when all done
    if len(list(SCK.glob("*.parquet"))) >= len(keys):
        base = pd.concat([pd.read_parquet(p) for p in SCK.glob("*.parquet")], ignore_index=True)
        prim = pd.concat([pd.read_parquet(p) for p in PCK.glob("*.parquet") if not p.name.endswith("_repro.parquet")], ignore_index=True)
        CONT = ["D1_single_channel_broadband", "D2_common_mode_broadband", "D3_narrowband_35_45",
                "D4_narrowband_20_30", "D5_transient_impulse", "D6_clipping",
                "D7_partial_channel_freeze", "D8_full_channel_variance_collapse"]
        rows = []
        for fam in CONT:
            for lvl in (1, 2, 3, 4):
                pv = prim[(prim.family == fam) & (prim.severity == lvl)]
                bv = base[(base.family == fam) & (base.severity == lvl)]
                rows.append({"family": fam, "severity": lvl,
                             "R1_perwindow": float(pv.response_R1_MEAN_PERCENTILE.astype(float).mean()),
                             "R1_baseline": float(bv.response_R1_MEAN_PERCENTILE.astype(float).mean()),
                             "R0_perwindow": float(pv.response_R0_ORIGINAL_AND.astype(float).mean()),
                             "R0_baseline": float(bv.response_R0_ORIGINAL_AND.astype(float).mean())})
        sens = pd.DataFrame(rows)
        sens["R1_delta_scale"] = sens.R1_baseline - sens.R1_perwindow
        sens.to_csv(DEG / "degradation_scale_sensitivity.csv", index=False)
        # qualitative check: do blind spots persist at top severity?
        top = sens[sens.severity == 4]
        blind_pw = set(top[top.R1_perwindow < 0.6].family)
        blind_bl = set(top[top.R1_baseline < 0.6].family)
        print("top-severity R1 blind (per-window):", sorted(blind_pw))
        print("top-severity R1 blind (baseline):", sorted(blind_bl))
        print("blind-spot set changes:", blind_pw != blind_bl)
        return sens
    return None


if __name__ == "__main__":
    main()
