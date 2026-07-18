#!/usr/bin/env python3
"""Reproduce released batch gate counts using the canonical feature function.

The wrapper keeps all generated products isolated while importing the released
window feature implementation verbatim. It evaluates only the 1-second,
0.5-second-hop representation used in the published count checks.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import mne
import numpy as np
import pandas as pd
from scipy.stats import median_abs_deviation

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from empirical.nf_sqi_common import SENSORIMOTOR_CHANNELS, read_events_for_edf  # noqa: E402
from empirical.nf_sqi_t1_features import extract_window_features  # noqa: E402

mne.set_log_level("ERROR")


def session_features(edf_path: Path) -> pd.DataFrame:
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    channels = [channel for channel in SENSORIMOTOR_CHANNELS if channel in raw.ch_names]
    if len(channels) != len(SENSORIMOTOR_CHANNELS):
        raise ValueError(f"Missing canonical channels in {edf_path}: {channels}")
    raw.pick_channels(channels)
    fs = float(raw.info["sfreq"])
    events = read_events_for_edf(edf_path, raw.times[-1])
    event_arr = np.zeros(raw.n_times, dtype=np.int8)
    for _, row in events.loc[events["instruction"].astype(str) == "task"].iterrows():
        start = int(round(float(row["onset_s"]) * fs))
        stop = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
        event_arr[max(0, start): min(raw.n_times, max(start, stop))] = 1
    data = raw.get_data()
    win = int(fs)
    hop = int(fs * 0.5)
    subject, session = edf_path.parts[-4], edf_path.parts[-3]
    rows: list[dict[str, object]] = []
    previous_smr = np.nan
    for start in np.arange(0, data.shape[1] - win, hop):
        stop = int(start + win)
        values = extract_window_features(data[:, int(start):stop], fs)
        if not values["valid"]:
            continue
        del values["valid"]
        smr = float(values["smr_power"])
        values.update(
            subject=subject,
            session=session,
            time_s=float(start / fs),
            condition="task" if float(np.mean(event_arr[int(start):stop])) > 0.5 else "rest",
            nonstationarity=float(abs(smr - previous_smr)) if np.isfinite(previous_smr) else 0.0,
            window_size=1.0,
        )
        previous_smr = smr
        rows.append(values)
    frame = pd.DataFrame(rows)
    rest = frame["condition"] == "rest"
    for band in ("smr", "beta", "broadband", "noise"):
        columns = [f"ch_{index}_{band}" for index in range(len(channels))]
        standardized = (frame[columns] - frame.loc[rest, columns].mean()) / frame.loc[rest, columns].std().replace(0, 1e-9)
        frame[f"ch_inc_{band}_sd"] = standardized.std(axis=1)
        frame[f"ch_inc_{band}_mad"] = standardized.apply(lambda row: median_abs_deviation(row.dropna()), axis=1)
    frame["channel_inconsistency"] = frame[[f"ch_inc_{band}_sd" for band in ("smr", "beta", "broadband", "noise")]].mean(axis=1)
    frame["channel_inconsistency_mad"] = frame[[f"ch_inc_{band}_mad" for band in ("smr", "beta", "broadband", "noise")]].mean(axis=1)
    return frame.drop(columns=[column for column in frame if column.startswith("ch_") and not column.startswith("ch_inc")])


def counts(frame: pd.DataFrame) -> dict[str, int]:
    thresholds = (
        frame.loc[frame["condition"] == "rest"]
        .groupby(["subject", "session"])[["smr_snr", "high_beta_power", "broadband_power", "noise_floor_power", "transient_score", "channel_inconsistency"]]
        .quantile([0.75, 0.90])
        .unstack()
    )
    task = frame.loc[frame["condition"] == "task"].copy()
    for metric, percentile, name in (
        ("smr_snr", 0.75, "smr"),
        ("high_beta_power", 0.75, "hb"),
        ("broadband_power", 0.75, "bb"),
        ("noise_floor_power", 0.75, "hf"),
        ("transient_score", 0.90, "tr"),
        ("channel_inconsistency", 0.75, "ci"),
    ):
        task[name] = [thresholds.loc[(sub, ses), (metric, percentile)] for sub, ses in zip(task.subject, task.session)]
    gate_a = task.smr_snr > task.smr
    gate_b = gate_a & (task.high_beta_power < task.hb)
    quality_strict = (
        (task.broadband_power < task.bb)
        & (task.noise_floor_power < task.hf)
        & (task.transient_score < task.tr)
        & (task.channel_inconsistency < task.ci)
    )
    quality_inclusive = (
        (task.broadband_power <= task.bb)
        & (task.noise_floor_power <= task.hf)
        & (task.transient_score <= task.tr)
        & (task.channel_inconsistency <= task.ci)
    )
    return {
        "task_windows": int(len(task)),
        "gate_a": int(gate_a.sum()),
        "gate_b": int(gate_b.sum()),
        "gate_c_strict": int((gate_b & quality_strict).sum()),
        "gate_c_inclusive": int((gate_b & quality_inclusive).sum()),
        "high_beta_blocks": int((gate_a & ~gate_b).sum()),
        "strict_vs_inclusive_ties": int((gate_b & quality_inclusive & ~quality_strict).sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out-json", required=True)
    args = parser.parse_args()
    root = ROOT / "data" / "raw" / "openneuro" / args.dataset
    features = [session_features(path) for path in sorted(root.rglob("sub-*/ses-*/eeg/*_task-smrbmi_eeg.edf"))]
    frame = pd.concat(features, ignore_index=True)
    result = counts(frame)
    result["dataset"] = args.dataset
    result["sessions"] = int(frame[["subject", "session"]].drop_duplicates().shape[0])
    output = Path(args.out_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
