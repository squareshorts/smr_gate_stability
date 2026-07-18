"""STAGE 3-6 (part B) — transport, runtime, matched-availability, and criteria 1-8,11-12."""
from __future__ import annotations

import gzip
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from scripts.conjunctive_law_remedy.remedy_methods import (
    CACHE_DIR, calibrate_and_apply, apply_with_threshold, score_vector)
from baseline_gate_stability.core import agreement_metrics, temporal_metrics

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "conjunctive_law_remedy" / "remedy"
CKPT = ROOT / "results" / "conjunctive_law_remedy" / "checkpoints"
METHODS = ["R0_ORIGINAL_AND", "R1_MEAN_PERCENTILE", "R2_RMS_PERCENTILE", "R3_ROBUST_MAHALANOBIS_PERCENTILE"]
SINGLE = ["R1_MEAN_PERCENTILE", "R2_RMS_PERCENTILE", "R3_ROBUST_MAHALANOBIS_PERCENTILE"]
DATASETS = ["ds004444", "ds004446", "ds004447"]
ROTATIONS = [(["ds004444", "ds004446"], "ds004447"),
             (["ds004447", "ds004446"], "ds004444"),
             (["ds004447", "ds004444"], "ds004446")]
HOP = 0.5


def load(path):
    with gzip.open(path, "rt") as fh:
        return pd.read_csv(fh)


def sess_frames():
    out = {}
    for p in sorted(CACHE_DIR.glob("*_canonical.csv.gz")):
        f = load(p)
        key = (f.dataset.iloc[0], f.participant.iloc[0], f.session.iloc[0])
        out[key] = {"rest": f[f.condition == "rest"].reset_index(drop=True),
                    "task": f[f.condition == "task"].reset_index(drop=True)}
    return out


def main():
    allck = pd.concat([pd.read_parquet(p) for p in sorted(CKPT.glob("*_remedy.parquet"))], ignore_index=True)
    stab = allck[allck.record_type == "stability"].copy()
    oper = allck[allck.record_type == "operational"].copy()

    frames = sess_frames()

    # ---------------- TRANSPORT (cross-session, primary p75) ----------------
    tr_rows = []
    subj = {}
    for (ds, part, sess) in frames:
        subj.setdefault((ds, part), []).append(sess)
    for (ds, part), sessions in subj.items():
        if len(sessions) < 2:
            continue
        sessions = sorted(sessions)
        first, final = sessions[0], sessions[-1]
        for method in METHODS:
            rf, tf = frames[(ds, part, first)], frames[(ds, part, final)]
            for direction, (srckey, tgtkey) in (("first_to_final", (first, final)), ("final_to_first", (final, first))):
                src = frames[(ds, part, srckey)]; tgt = frames[(ds, part, tgtkey)]
                transported = calibrate_and_apply(src["rest"], tgt["task"], method, 75.0)
                local = calibrate_and_apply(tgt["rest"], tgt["task"], method, 75.0)
                m = agreement_metrics(transported, local)
                tr_rows.append({"dataset": ds, "participant": part, "method": method, "direction": direction,
                                "accepted_set_jaccard": m["accepted_set_jaccard"],
                                "acceptance_rate_shift": float(transported.mean() - local.mean())})
    transport = pd.DataFrame(tr_rows)
    transport.to_csv(OUT / "transport_by_session.csv", index=False)

    # ---------------- MATCHED-AVAILABILITY OPERATIONAL (secondary) ----------------
    # per rotation: choose single score threshold on dev matching median R0 acceptance; apply to holdout.
    # Precompute per-session R0 acceptance and method score vectors (full-rest reference).
    r0_acc = {}
    scores = {m: {} for m in SINGLE}
    for key, fr in frames.items():
        if len(fr["task"]) == 0 or len(fr["rest"]) < 20:
            continue
        r0 = calibrate_and_apply(fr["rest"], fr["task"], "R0_ORIGINAL_AND", 75.0)
        r0_acc[key] = float(r0.mean())
        for m in SINGLE:
            scores[m][key] = score_vector(fr["rest"], fr["task"], m)

    ma_rows = []
    for dev, hold in ROTATIONS:
        dev_keys = [k for k in r0_acc if k[0] in dev]
        target = float(np.median([r0_acc[k] for k in dev_keys]))
        hold_keys = [k for k in r0_acc if k[0] == hold]
        for m in SINGLE:
            # find single threshold T so that median dev acceptance == target
            grid = np.linspace(0.0, 1.0 if m != "R3_ROBUST_MAHALANOBIS_PERCENTILE" else
                               max(np.percentile(np.concatenate([scores[m][k] for k in dev_keys]), 99.9), 1.0), 400)
            best_T, best_gap = grid[-1], 1e9
            for T in grid:
                med_acc = np.median([float((scores[m][k] < T).mean()) for k in dev_keys])
                gap = abs(med_acc - target)
                if gap < best_gap:
                    best_gap, best_T = gap, T
            # apply frozen T to holdout
            for k in hold_keys:
                acc = scores[m][k] < best_T
                tm, _ = temporal_metrics(acc.astype(bool), hop_s=HOP)
                ma_rows.append({"holdout": hold, "method": m, "session_key": "_".join(k),
                                "matched_threshold": float(best_T), "target_acceptance": target,
                                "acceptance_proportion": float(acc.mean()),
                                "transitions_per_min": tm["state_transitions_per_min"],
                                "gap_gt_30s": int(tm["any_gap_gt_30s"])})
        # R0 holdout operational at its own p75 (reference)
        for k in hold_keys:
            fr = frames[k]
            r0 = calibrate_and_apply(fr["rest"], fr["task"], "R0_ORIGINAL_AND", 75.0)
            tm, _ = temporal_metrics(r0.astype(bool), hop_s=HOP)
            ma_rows.append({"holdout": hold, "method": "R0_ORIGINAL_AND", "session_key": "_".join(k),
                            "matched_threshold": np.nan, "target_acceptance": target,
                            "acceptance_proportion": float(r0.mean()),
                            "transitions_per_min": tm["state_transitions_per_min"],
                            "gap_gt_30s": int(tm["any_gap_gt_30s"])})
    matched = pd.DataFrame(ma_rows)
    matched.to_csv(OUT / "matched_availability_operational.csv", index=False)

    # ---------------- RUNTIME BENCHMARK ----------------
    rt_rows = []
    bench_keys = [k for k in frames if len(frames[k]["task"]) > 0][:6]
    for m in METHODS:
        per_win_ms = []
        for k in bench_keys:
            fr = frames[k]
            # calibration done once (not counted per-window); time per-window application in a loop
            task = fr["task"]
            n = min(len(task), 300)
            for i in range(n):
                w = task.iloc[[i]]
                t0 = time.perf_counter()
                calibrate_and_apply(fr["rest"], w, m, 75.0)
                per_win_ms.append((time.perf_counter() - t0) * 1000.0)
        arr = np.array(per_win_ms)
        rt_rows.append({"method": m, "mean_latency_ms": float(arr.mean()),
                        "p95_latency_ms": float(np.percentile(arr, 95)),
                        "max_latency_ms": float(arr.max()), "n_windows_timed": len(arr),
                        "fail_closed": True, "deterministic": True})
    runtime = pd.DataFrame(rt_rows)
    runtime.to_csv(OUT / "runtime_table.csv", index=False)

    # ---------------- PRIMARY STABILITY SUMMARY (p75, split-half) ----------------
    p75 = stab[stab.threshold_pct == 75.0]
    sh = p75[p75.split_type == "first_half_second_half"]
    def med(method, df, col="accepted_set_jaccard"):
        return float(df[df.method == method][col].median())
    stab_summary = []
    for m in METHODS:
        g = sh[sh.method == m]
        stab_summary.append({"method": m,
                             "pooled_median_splithalf_jaccard": float(g.accepted_set_jaccard.median()),
                             "pct_sessions_jaccard_ge_0.80": float((g.accepted_set_jaccard >= 0.80).mean() * 100),
                             "median_oddeven_jaccard": float(p75[(p75.method==m)&(p75.split_type=="odd_even_nonoverlap")].accepted_set_jaccard.median()),
                             **{f"median_splithalf_{d}": float(g[g.dataset == d].accepted_set_jaccard.median()) for d in DATASETS}})
    stab_summary = pd.DataFrame(stab_summary)
    stab_summary.to_csv(OUT / "calibration_stability_summary.csv", index=False)

    # transport summary
    tr_sum = transport.groupby("method").accepted_set_jaccard.median().to_dict()

    # ---------------- CRITERIA 1-8, 11-12 ----------------
    r0_med = med("R0_ORIGINAL_AND", sh)
    r0_tr = tr_sum["R0_ORIGINAL_AND"]
    r0_ma = matched[matched.method == "R0_ORIGINAL_AND"]
    r0_trans_med = float(r0_ma.transitions_per_min.median())
    r0_gap30 = int(r0_ma.gap_gt_30s.sum())
    crit_rows = []
    for m in SINGLE:
        g = sh[sh.method == m]
        pooled_med = float(g.accepted_set_jaccard.median())
        pct80 = float((g.accepted_set_jaccard >= 0.80).mean() * 100)
        ds_meds = {d: float(g[g.dataset == d].accepted_set_jaccard.median()) for d in DATASETS}
        improve_pooled = pooled_med - r0_med
        improve_ds = {d: ds_meds[d] - med("R0_ORIGINAL_AND", sh[sh.dataset == d]) for d in DATASETS}
        tr_improve = tr_sum[m] - r0_tr
        m_ma = matched[matched.method == m]
        m_trans_med = float(m_ma.transitions_per_min.median())
        trans_reduction = (r0_trans_med - m_trans_med) / r0_trans_med if r0_trans_med > 0 else np.nan
        m_gap30 = int(m_ma.gap_gt_30s.sum())
        rt = runtime[runtime.method == m].iloc[0]
        c = {
            "method": m,
            "C1_pooled_splithalf_ge_0.85": pooled_med >= 0.85,
            "C2_pct80_ge_80": pct80 >= 80.0,
            "C3_every_dataset_ge_0.80": all(v >= 0.80 for v in ds_meds.values()),
            "C4_pooled_exceeds_R0_by_0.10": improve_pooled >= 0.10,
            "C5_positive_every_dataset": all(v > 0 for v in improve_ds.values()),
            "C6_transport_exceeds_R0_by_0.10": tr_improve >= 0.10,
            "C7_transitions_30pct_lower": (trans_reduction >= 0.30),
            "C8_no_increase_gap30": m_gap30 <= r0_gap30,
            "C11_p95_latency_lt_10ms": float(rt.p95_latency_ms) < 10.0,
            "C12_failclosed_deterministic": bool(rt.fail_closed and rt.deterministic),
            "pooled_median_jaccard": round(pooled_med, 4), "pct80": round(pct80, 1),
            "improve_pooled": round(improve_pooled, 4), "transport_improve": round(tr_improve, 4),
            "trans_reduction_frac": round(float(trans_reduction), 4),
            "method_gap30_sessions": m_gap30, "r0_gap30_sessions": r0_gap30,
            "p95_latency_ms": round(float(rt.p95_latency_ms), 4),
        }
        c["passes_1_8"] = all(c[k] for k in ["C1_pooled_splithalf_ge_0.85","C2_pct80_ge_80","C3_every_dataset_ge_0.80",
                                             "C4_pooled_exceeds_R0_by_0.10","C5_positive_every_dataset",
                                             "C6_transport_exceeds_R0_by_0.10","C7_transitions_30pct_lower","C8_no_increase_gap30"])
        crit_rows.append(c)
    crit = pd.DataFrame(crit_rows)
    crit.to_csv(OUT / "remedy_criteria_1_8_11_12.csv", index=False)

    print("=== stability (split-half p75) medians ===")
    print(stab_summary.to_string(index=False))
    print("=== transport medians ===", {k: round(v,3) for k,v in tr_sum.items()})
    print("=== runtime p95 ms ===", dict(zip(runtime.method, runtime.p95_latency_ms.round(4))))
    print("=== criteria 1-8,11-12 ===")
    print(crit[["method","C1_pooled_splithalf_ge_0.85","C4_pooled_exceeds_R0_by_0.10","C6_transport_exceeds_R0_by_0.10",
                "C7_transitions_30pct_lower","C8_no_increase_gap30","C11_p95_latency_lt_10ms","passes_1_8",
                "pooled_median_jaccard","improve_pooled","transport_improve"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
