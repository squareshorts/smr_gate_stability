#!/usr/bin/env python3
"""Real-data pseudo-online replay of the NF-SQI gate on OpenNeuro EDF recordings.

This closes the gap noted in the manuscript boundary conditions: the deployment
CLI previously ran only on synthetic CSV input, so the pseudo-online path had
never been exercised end-to-end on the real OpenNeuro recordings.

For each session (one EDF = one subject/session):
  1. Load the EDF, pick the three central SMR channels (E36, E104, E128).
  2. Label task samples from the events.tsv (instruction == "task").
  3. Window the full recording at 1 s / 0.5 s hop, exactly as the batch
     feature extractor does; windows that are >50% task samples are "task"
     (replay) windows, the rest are the rest-baseline calibration windows.
  4. Calibrate NF-SQI limits + channel baseline from the rest windows via the
     deployment realtime module (calibrate_nf_sqi_bundle).
  5. Stream the task windows through evaluate_nf_sqi_window (the same code path
     NFSQIRealtime.push uses), recording Gate A/B/C decisions, rejection flags,
     and per-window compute latency.

Outputs Gate A/B/C counts, yields, feedback density (windows/min), rejection
counts, and latency stats -- per session, per subject, and pooled per dataset.

Usage:
  python scripts/run_nfsqi_pseudo_online_real_edf.py --dataset ds004447 \
      --subjects sub-001 --out-prefix results/final/nfsqi_pseudo_online_real
  # omit --subjects to run all subjects in the dataset
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import mne  # noqa: E402
import pandas as pd  # noqa: E402

mne.set_log_level("ERROR")

from empirical.nf_sqi_common import (  # noqa: E402
    SENSORIMOTOR_CHANNELS,
    read_events_for_edf,
)
from empirical.nf_sqi_realtime import (  # noqa: E402
    ThresholdConfig,
    calibrate_nf_sqi_bundle,
    evaluate_nf_sqi_window,
)

WIN_S = 1.0
STEP_S = 0.5
HOP_MIN = STEP_S / 60.0  # minutes advanced per accepted window slot


def dataset_dir(dataset: str) -> Path:
    return ROOT / "archive/stale_pending_delete/data/data/raw/openneuro" / dataset


def segment_windows(data: np.ndarray, event_arr: np.ndarray, fs: float):
    """Split a recording into rest (calibration) and task (replay) windows.

    Returns (rest_windows, task_windows) where each is a list of
    (n_channels, win_samples) float arrays, using 1 s / 0.5 s hop windows and
    the >50% task-sample rule, matching the batch feature extractor.
    """
    win = int(WIN_S * fs)
    step = int(STEP_S * fs)
    n = data.shape[1]
    rest, task = [], []
    for start in range(0, n - win, step):
        stop = start + win
        w = data[:, start:stop]
        if np.mean(event_arr[start:stop]) > 0.5:
            task.append(w)
        else:
            rest.append(w)
    return rest, task


def process_session(edf_path: Path):
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    channels = [c for c in SENSORIMOTOR_CHANNELS if c in raw.ch_names]
    if len(channels) < 1:
        return None
    raw.pick_channels(channels)
    fs = float(raw.info["sfreq"])
    dur = raw.times[-1]
    events = read_events_for_edf(edf_path, dur)

    data = raw.get_data()  # (n_channels, n_samples)
    event_arr = np.zeros(raw.n_times, dtype=int)
    for _, row in events[events["instruction"].astype(str) == "task"].iterrows():
        s = int(round(float(row["onset_s"]) * fs))
        e = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
        s = max(0, min(s, raw.n_times))
        e = max(s, min(e, raw.n_times))
        event_arr[s:e] = 1

    rest_windows, task_windows = segment_windows(data, event_arr, fs)
    if len(rest_windows) < ThresholdConfig().min_valid_windows or not task_windows:
        return {
            "fs": fs, "skipped": True,
            "n_rest": len(rest_windows), "n_task": len(task_windows),
        }

    # --- Calibrate on rest windows via the deployment module ---
    calib, _ = calibrate_nf_sqi_bundle(
        rest_windows, fs, window_s=WIN_S, step_s=STEP_S, config=ThresholdConfig()
    )

    # --- Stream task windows through the online evaluation code path ---
    gate_a = gate_b = gate_c = 0
    rej = Counter()
    latencies = []
    prev_smr = None
    for w in task_windows:
        t0 = time.perf_counter()
        res = evaluate_nf_sqi_window(
            w, fs, calib.limits, calib.channel_baseline, previous_smr_power=prev_smr
        )
        latencies.append((time.perf_counter() - t0) * 1000.0)
        if res.features.valid:
            prev_smr = res.features.smr_power
        gate_a += int(res.gate_A)
        gate_b += int(res.gate_B)
        gate_c += int(res.gate_C)
        for f in res.rejection_flags:
            rej[f] += 1

    n_task = len(task_windows)
    lat = np.asarray(latencies)
    return {
        "fs": fs, "skipped": False,
        "n_rest": len(rest_windows), "n_task": n_task,
        "gate_a": gate_a, "gate_b": gate_b, "gate_c": gate_c,
        "gate_a_yield": gate_a / n_task,
        "gate_b_yield": gate_b / n_task,
        "gate_c_yield": gate_c / n_task,
        "gate_c_windows_per_min": gate_c / (n_task * HOP_MIN),
        "rejection_counts": dict(rej),
        "latency_ms_mean": float(lat.mean()),
        "latency_ms_median": float(np.median(lat)),
        "latency_ms_p95": float(np.percentile(lat, 95)),
        "latency_ms_max": float(lat.max()),
        "limits": calib.limits.to_dict(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ds004447")
    ap.add_argument("--subjects", nargs="*", default=None,
                    help="e.g. sub-001 sub-002; default = all subjects")
    ap.add_argument("--out-prefix", default="results/final/nfsqi_pseudo_online_real")
    args = ap.parse_args()

    ddir = dataset_dir(args.dataset)
    edfs = sorted(ddir.rglob("sub-*/ses-*/eeg/*_task-smrbmi_eeg.edf"))
    if args.subjects:
        keep = set(args.subjects)
        edfs = [p for p in edfs if p.parts[-4] in keep]
    if not edfs:
        raise SystemExit(f"No EDFs found for {args.dataset} subjects={args.subjects}")

    session_rows = []
    for edf in edfs:
        subject, session = edf.parts[-4], edf.parts[-3]
        try:
            r = process_session(edf)
        except Exception as e:  # noqa: BLE001
            print(f"[ERR] {subject} {session}: {e}", flush=True)
            continue
        if r is None:
            print(f"[skip-nochan] {subject} {session}", flush=True)
            continue
        r.update({"dataset": args.dataset, "subject": subject, "session": session})
        session_rows.append(r)
        if r.get("skipped"):
            print(f"[skip-short] {subject} {session} rest={r['n_rest']} task={r['n_task']}",
                  flush=True)
        else:
            print(f"[ok] {subject} {session}: task={r['n_task']} "
                  f"A={r['gate_a']} B={r['gate_b']} C={r['gate_c']} "
                  f"({r['gate_c_windows_per_min']:.2f} win/min) "
                  f"lat_p95={r['latency_ms_p95']:.2f}ms", flush=True)

    used = [r for r in session_rows if not r.get("skipped")]
    tot_task = sum(r["n_task"] for r in used)
    tot_a = sum(r["gate_a"] for r in used)
    tot_b = sum(r["gate_b"] for r in used)
    tot_c = sum(r["gate_c"] for r in used)
    all_lat_p95 = [r["latency_ms_p95"] for r in used]
    all_lat_mean = [r["latency_ms_mean"] for r in used]
    pooled_rej = Counter()
    for r in used:
        pooled_rej.update(r["rejection_counts"])

    pooled = {
        "dataset": args.dataset,
        "n_sessions_used": len(used),
        "n_subjects": len({r["subject"] for r in used}),
        "total_task_windows": tot_task,
        "gate_a": tot_a, "gate_b": tot_b, "gate_c": tot_c,
        "gate_a_yield_pct": 100.0 * tot_a / tot_task if tot_task else float("nan"),
        "gate_b_yield_pct": 100.0 * tot_b / tot_task if tot_task else float("nan"),
        "gate_c_yield_pct": 100.0 * tot_c / tot_task if tot_task else float("nan"),
        "gate_c_windows_per_min": tot_c / (tot_task * HOP_MIN) if tot_task else float("nan"),
        "hb_blocks_of_gate_a_pct": 100.0 * (tot_a - tot_b) / tot_a if tot_a else float("nan"),
        "latency_ms_mean_of_session_means": float(np.mean(all_lat_mean)) if all_lat_mean else float("nan"),
        "latency_ms_p95_max_over_sessions": float(np.max(all_lat_p95)) if all_lat_p95 else float("nan"),
        "pooled_rejection_counts": dict(pooled_rej),
    }

    out_prefix = ROOT / args.out_prefix
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    suffix = args.dataset if not args.subjects else f"{args.dataset}_{'_'.join(args.subjects)}"
    json_path = out_prefix.with_name(out_prefix.name + f"_{suffix}.json")
    csv_path = out_prefix.with_name(out_prefix.name + f"_{suffix}_sessions.csv")

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump({"pooled": pooled, "sessions": session_rows}, fh, indent=2)
    pd.DataFrame([{k: v for k, v in r.items()
                   if k not in ("rejection_counts", "limits")} for r in session_rows]).to_csv(
        csv_path, index=False)

    print("\n===== POOLED (" + suffix + ") =====")
    print(json.dumps(pooled, indent=2))
    print(f"\nWrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
