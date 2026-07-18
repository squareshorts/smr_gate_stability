"""STAGE 3-6 (part A) — per-session remedy calibration-stability + operational behaviour.

Checkpointed one session at a time. Transport (cross-session) and runtime are separate.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from scripts.conjunctive_law_remedy.remedy_methods import CACHE_DIR, calibrate_and_apply
from baseline_gate_stability.core import agreement_metrics, temporal_metrics

OUT = Path(__file__).resolve().parents[2] / "results" / "conjunctive_law_remedy" / "remedy"
CKPT = Path(__file__).resolve().parents[2] / "results" / "conjunctive_law_remedy" / "checkpoints"
CKPT.mkdir(parents=True, exist_ok=True)
METHODS = ["R0_ORIGINAL_AND", "R1_MEAN_PERCENTILE", "R2_RMS_PERCENTILE", "R3_ROBUST_MAHALANOBIS_PERCENTILE"]
THRESHOLDS = [75.0, 80.0]
HOP = 0.5
WIN = 1.0


def now():
    return datetime.now().isoformat(timespec="seconds")


def greedy_nonoverlap_idx(times):
    keep, last = [], -np.inf
    for i, t in enumerate(times):
        if t >= last + WIN - 1e-9:
            keep.append(i); last = t
    return np.array(keep, dtype=int)


def load(path):
    import gzip
    with gzip.open(path, "rt") as fh:
        return pd.read_csv(fh)


def session_splits(rest):
    rest = rest.sort_values("window_start_s").reset_index(drop=True)
    n = len(rest)
    fh = rest.iloc[: n // 2].reset_index(drop=True)
    sh = rest.iloc[n // 2:].reset_index(drop=True)
    nov = greedy_nonoverlap_idx(rest["window_start_s"].to_numpy(float))
    odd = rest.iloc[nov[1::2]].reset_index(drop=True)
    even = rest.iloc[nov[0::2]].reset_index(drop=True)
    return {"first_half_second_half": (fh, sh), "odd_even_nonoverlap": (even, odd)}


def process(path):
    frame = load(path)
    ds, part, sess = frame.dataset.iloc[0], frame.participant.iloc[0], frame.session.iloc[0]
    rest = frame[frame.condition == "rest"].reset_index(drop=True)
    task = frame[frame.condition == "task"].reset_index(drop=True)
    if len(task) == 0 or len(rest) < 20:
        return None
    splits = session_splits(rest)
    rows = []
    for method in METHODS:
        for thr in THRESHOLDS:
            # calibration stability across the two split types
            for split_name, (h1, h2) in splits.items():
                a1 = calibrate_and_apply(h1, task, method, thr)
                a2 = calibrate_and_apply(h2, task, method, thr)
                m = agreement_metrics(a1, a2)
                rows.append({
                    "record_type": "stability", "dataset": ds, "participant": part, "session": sess,
                    "method": method, "threshold_pct": thr, "split_type": split_name,
                    "n_task": len(task), "accepted_set_jaccard": m["accepted_set_jaccard"],
                    "overall_agreement": m["overall_agreement"], "positive_agreement": m["positive_agreement"],
                    "negative_agreement": m["negative_agreement"],
                    "accept_to_withhold_flips": m["acceptance_to_withhold_flips"],
                    "withhold_to_accept_flips": m["withhold_to_acceptance_flips"],
                    "acceptance_rate_1": m["acceptance_rate_left"], "acceptance_rate_2": m["acceptance_rate_right"],
                })
            # operational behaviour under full-rest local calibration
            acc = calibrate_and_apply(rest, task, method, thr)
            tm, _ = temporal_metrics(acc, hop_s=HOP)
            rows.append({
                "record_type": "operational", "dataset": ds, "participant": part, "session": sess,
                "method": method, "threshold_pct": thr, "n_task": len(task),
                "acceptance_proportion": float(acc.mean()),
                "accepted_windows_per_min": tm["accepted_windows_per_min"],
                "transitions_per_min": tm["state_transitions_per_min"],
                "longest_feedback_free_s": tm["longest_feedback_free_s"],
                "gap_gt_20s": int(tm["any_gap_gt_20s"]), "gap_gt_30s": int(tm["any_gap_gt_30s"]),
            })
    del frame, rest, task
    return pd.DataFrame(rows)


def main():
    files = sorted(CACHE_DIR.glob("*_canonical.csv.gz"))
    progress, errors, manifest = [], [], []
    for seq, path in enumerate(files, 1):
        key = path.name.removesuffix("_canonical.csv.gz")
        cp = CKPT / f"{key}_remedy.parquet"
        if cp.exists():
            try:
                pd.read_parquet(cp); manifest.append({"session_key": key, "status": "reused"})
                progress.append({"seq": seq, "session_key": key, "status": "reused", "timestamp": now()}); continue
            except Exception:
                pass
        try:
            res = process(path)
            if res is None:
                progress.append({"seq": seq, "session_key": key, "status": "skipped", "timestamp": now()}); continue
            res.to_parquet(cp, index=False)
            manifest.append({"session_key": key, "status": "computed", "rows": len(res)})
            progress.append({"seq": seq, "session_key": key, "status": "computed", "timestamp": now()})
        except Exception as exc:
            errors.append({"timestamp": now(), "session_key": key, "error": repr(exc)})
            progress.append({"seq": seq, "session_key": key, "status": "error", "timestamp": now()})
    pd.DataFrame(progress).to_csv(OUT / "remedy_execution_progress.csv", index=False)
    pd.DataFrame(errors, columns=["timestamp", "session_key", "error"]).to_csv(OUT / "remedy_execution_errors.csv", index=False)
    pd.DataFrame(manifest).to_csv(OUT / "remedy_checkpoint_manifest.csv", index=False)
    print(f"done: {len(manifest)} sessions, {len(errors)} errors")


if __name__ == "__main__":
    main()
