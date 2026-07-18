"""Phase: PER-SESSION LAW TEST (checkpointed, one session at a time).

Reads only the verified canonical feature cache. For each session builds two
independent baseline calibration replicates, computes per-criterion pass
probabilities, and for all 31 nonempty subsets the observed vs parameter-free
independence-predicted accepted-set Jaccard, under both the empirical (primary)
and Harrell-Davis (secondary) quantile estimators. Writes one parquet checkpoint
per session and resumes by skipping valid checkpoints.
"""
from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats.mstats import hdquantiles

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts.conjunctive_gate_instability.common import (
    CACHE_DIR, CKPT, CRITERIA, CRIT_ORDER, OUT, WINDOW_S, channel_inconsistency,
    fit_channel_baseline, load_session, nonempty_subsets, session_key_from_path, subset_id,
)
from baseline_gate_stability.core import agreement_metrics

EPS = 1e-12


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def greedy_nonoverlap(rest: pd.DataFrame) -> pd.DataFrame:
    """Select nonoverlapping 1 s windows from rest in time order."""
    rest = rest.sort_values("window_start_s").reset_index(drop=True)
    keep = []
    last = -np.inf
    for i, t in enumerate(rest["window_start_s"].to_numpy(float)):
        if t >= last + WINDOW_S - 1e-9:
            keep.append(i)
            last = t
    return rest.iloc[keep].reset_index(drop=True)


def empirical_threshold(values: np.ndarray, pct: float) -> float:
    v = values[np.isfinite(values)]
    return float(np.nanpercentile(v, pct)) if v.size else np.nan


def hd_threshold(values: np.ndarray, pct: float) -> float:
    v = values[np.isfinite(values)]
    if v.size == 0:
        return np.nan
    if v.size == 1:
        return float(v[0])
    return float(np.asarray(hdquantiles(v, prob=[pct / 100.0]))[0])


def criterion_thresholds(block: pd.DataFrame, estimator: str):
    """Return (thresholds dict, channel_baseline) for one calibration replicate."""
    means, stds = fit_channel_baseline(block)
    ci_block = channel_inconsistency(block, means, stds)
    fn = empirical_threshold if estimator == "empirical" else hd_threshold
    thr = {}
    for crit, (col, pct) in CRITERIA.items():
        if crit == "Q5_channel_inconsistency":
            thr[crit] = fn(ci_block, pct)
        else:
            thr[crit] = fn(block[col].to_numpy(float), pct)
    return thr, (means, stds)


def pass_indicators(task: pd.DataFrame, thr, baseline, valid) -> dict[str, np.ndarray]:
    means, stds = baseline
    ci_task = channel_inconsistency(task, means, stds)
    out = {}
    for crit, (col, _pct) in CRITERIA.items():
        feat = ci_task if crit == "Q5_channel_inconsistency" else task[col].to_numpy(float)
        t = thr[crit]
        ok = valid & np.isfinite(feat) & (feat < t)
        out[crit] = ok.astype(bool)
    return out


def predicted_jaccard(p1: float, p2: float, q: float) -> float:
    denom = p1 + p2 - q
    if denom <= EPS:
        return 1.0
    return q / denom


def process_session(path: Path):
    frame = load_session(path)
    dataset = str(frame["dataset"].iloc[0])
    participant = str(frame["participant"].iloc[0])
    session = str(frame["session"].iloc[0])
    rest = frame[frame["condition"] == "rest"].reset_index(drop=True)
    task = frame[frame["condition"] == "task"].reset_index(drop=True)

    nonov = greedy_nonoverlap(rest)
    L = len(nonov)
    b = min(60, L // 2)
    excluded = b < 30
    n_task = len(task)
    if excluded or n_task == 0:
        return None, {"session_key": session_key_from_path(path), "dataset": dataset,
                      "participant": participant, "session": session,
                      "reason": f"insufficient baseline (nonoverlap_s={L}, block={b})" if excluded else "no task windows",
                      "nonoverlap_baseline_s": L, "block_s": b, "task_windows": n_task}

    block1 = nonov.iloc[:b].reset_index(drop=True)
    block2 = nonov.iloc[L - b:].reset_index(drop=True)
    valid = (task["raw_feature_valid"].astype(bool).to_numpy()
             & np.isfinite(task[[c for c, _ in CRITERIA.values() if c != "channel_inconsistency"]].to_numpy(float)).all(axis=1))

    rows = []
    subsets = nonempty_subsets()
    # feature-value matrix on task windows (for dependence), using block1 baseline for Q5
    for estimator in ("empirical", "hd"):
        thr1, base1 = criterion_thresholds(block1, estimator)
        thr2, base2 = criterion_thresholds(block2, estimator)
        A1 = pass_indicators(task, thr1, base1, valid)
        A2 = pass_indicators(task, thr2, base2, valid)
        p1 = {c: float(A1[c].mean()) for c in CRIT_ORDER}
        p2 = {c: float(A2[c].mean()) for c in CRIT_ORDER}
        q = {c: float((A1[c] & A2[c]).mean()) for c in CRIT_ORDER}

        # dependence: pairwise correlations among criterion features (task) and pass-indicators (rep1)
        feat_mat = []
        means1, stds1 = base1
        ci_task1 = channel_inconsistency(task, means1, stds1)
        for c in CRIT_ORDER:
            col = CRITERIA[c][0]
            feat_mat.append(ci_task1 if c == "Q5_channel_inconsistency" else task[col].to_numpy(float))
        feat_mat = np.vstack(feat_mat)
        with np.errstate(invalid="ignore"):
            fcorr = np.corrcoef(feat_mat)
        iu = np.triu_indices(5, k=1)
        mean_abs_feat_corr = float(np.nanmean(np.abs(fcorr[iu])))
        pass_mat = np.vstack([A1[c].astype(float) for c in CRIT_ORDER])
        with np.errstate(invalid="ignore"):
            pcorr = np.corrcoef(pass_mat)
        mean_abs_pass_corr = float(np.nanmean(np.abs(pcorr[iu]))) if np.isfinite(pcorr[iu]).any() else np.nan

        for s in subsets:
            g1 = np.ones(n_task, dtype=bool)
            g2 = np.ones(n_task, dtype=bool)
            for c in s:
                g1 &= A1[c]
                g2 &= A2[c]
            m = agreement_metrics(g1, g2)
            prod_p1 = float(np.prod([p1[c] for c in s]))
            prod_p2 = float(np.prod([p2[c] for c in s]))
            prod_q = float(np.prod([q[c] for c in s]))
            j_pred = predicted_jaccard(prod_p1, prod_p2, prod_q)
            obs_joint = float((g1 & g2).mean())
            dep_ratio = obs_joint / prod_q if prod_q > EPS else np.nan
            tn = int(np.sum(~g1 & ~g2))
            rows.append({
                "record_type": "subset",
                "session_key": session_key_from_path(path), "dataset": dataset,
                "participant": participant, "session": session,
                "estimator": estimator, "subset_id": subset_id(s), "criteria": "+".join(s),
                "cardinality": len(s), "n_task_windows": n_task,
                "observed_jaccard": m["accepted_set_jaccard"],
                "predicted_jaccard": j_pred,
                "residual": m["accepted_set_jaccard"] - j_pred,
                "obs_accept_g1": m["acceptance_rate_left"], "obs_accept_g2": m["acceptance_rate_right"],
                "pred_accept_g1": prod_p1, "pred_accept_g2": prod_p2,
                "obs_joint_accept": obs_joint, "pred_joint_accept": prod_q,
                "dependence_ratio": dep_ratio,
                "overall_agreement": m["overall_agreement"],
                "positive_agreement": m["positive_agreement"], "negative_agreement": m["negative_agreement"],
                "acceptance_flips": m["acceptance_to_withhold_flips"] + m["withhold_to_acceptance_flips"],
                "mutual_withholding_fraction": tn / n_task if n_task else np.nan,
                "mean_abs_pairwise_feature_corr": mean_abs_feat_corr,
                "mean_abs_pairwise_passind_corr": mean_abs_pass_corr,
                "block1_s": b, "block2_s": b, "nonoverlap_baseline_s": L,
            })
        # criterion-level rows
        for c in CRIT_ORDER:
            rows.append({
                "record_type": "criterion",
                "session_key": session_key_from_path(path), "dataset": dataset,
                "participant": participant, "session": session, "estimator": estimator,
                "criterion": c, "p_j1": p1[c], "p_j2": p2[c], "q_j": q[c],
                "reproducibility_r_j": q[c] / max(p1[c], p2[c], EPS),
                "n_task_windows": n_task, "block1_s": b, "block2_s": b,
            })
        # pairwise dependence rows (feature + pass-indicator correlations)
        for a in range(5):
            for bb in range(a + 1, 5):
                rows.append({
                    "record_type": "pair",
                    "session_key": session_key_from_path(path), "dataset": dataset,
                    "participant": participant, "session": session, "estimator": estimator,
                    "criterion_a": CRIT_ORDER[a], "criterion_b": CRIT_ORDER[bb],
                    "feature_corr": float(fcorr[a, bb]),
                    "passind_corr": float(pcorr[a, bb]) if np.isfinite(pcorr[a, bb]) else np.nan,
                })
    result = pd.DataFrame(rows)
    del frame, rest, task
    return result, None


def main() -> int:
    CKPT.mkdir(parents=True, exist_ok=True)
    files = sorted(CACHE_DIR.glob("*_canonical.csv.gz"))
    progress, errors, manifest, excluded = [], [], [], []
    for seq, path in enumerate(files, 1):
        key = session_key_from_path(path)
        ckpt_path = CKPT / f"{key}.parquet"
        if ckpt_path.exists():
            try:
                pd.read_parquet(ckpt_path)
                manifest.append({"session_key": key, "status": "reused", "checkpoint": ckpt_path.name})
                progress.append({"seq": seq, "total": len(files), "session_key": key, "status": "reused", "timestamp": now()})
                continue
            except Exception:
                pass  # corrupt -> recompute
        try:
            result, excl = process_session(path)
            if excl is not None:
                excluded.append(excl)
                progress.append({"seq": seq, "total": len(files), "session_key": key, "status": "excluded", "timestamp": now()})
                continue
            result.to_parquet(ckpt_path, index=False)
            manifest.append({"session_key": key, "status": "computed", "checkpoint": ckpt_path.name,
                             "rows": len(result)})
            progress.append({"seq": seq, "total": len(files), "session_key": key, "status": "computed", "timestamp": now()})
        except Exception as exc:  # noqa: BLE001
            errors.append({"timestamp": now(), "session_key": key, "error": repr(exc), "trace": traceback.format_exc()[-500:]})
            progress.append({"seq": seq, "total": len(files), "session_key": key, "status": "error", "timestamp": now()})

    pd.DataFrame(progress).to_csv(OUT / "execution_progress.csv", index=False)
    pd.DataFrame(errors, columns=["timestamp", "session_key", "error", "trace"]).to_csv(OUT / "execution_errors.csv", index=False)
    pd.DataFrame(manifest).to_csv(OUT / "completed_checkpoint_manifest.csv", index=False)
    pd.DataFrame(excluded).to_csv(OUT / "excluded_sessions.csv", index=False)
    print(f"computed/reused={len(manifest)} excluded={len(excluded)} errors={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
