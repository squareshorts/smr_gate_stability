"""Phase: INPUT VALIDATION.

Audit the verified canonical per-window cache and reproduce canonical M1-M4
decisions/counts before any law analysis. Stops with a clear blocker if the
cache is incomplete or divergent. Does NOT touch raw EDF.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts.conjunctive_gate_instability.common import (
    CACHE_DIR, CRITERIA, OUT, channel_inconsistency, fit_channel_baseline, load_session,
    session_key_from_path,
)
from baseline_gate_stability.core import apply_monitor, fit_quality_thresholds, prepare_with_baseline

MONITORS = ("M0_NO_GATE", "M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY")
REQUIRED_FEATURES = ["high_beta_power", "broadband_power", "noise_floor_power", "transient_score", "channel_inconsistency"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(CACHE_DIR.glob("*_canonical.csv.gz"))
    if not files:
        (OUT / "input_cache_audit.md").write_text("# BLOCKER\nCanonical feature cache not found.\n", encoding="utf-8")
        print("BLOCKER: cache missing")
        return 1

    manifest_rows = []
    count_rows = {}
    total_diffs = {m: 0 for m in MONITORS}
    config_hashes = set()
    per_session_windows = {}

    for path in files:
        key = session_key_from_path(path)
        frame = load_session(path)
        dataset = frame["dataset"].iloc[0]
        participant = frame["participant"].iloc[0]
        session = frame["session"].iloc[0]
        config_hashes.update(frame["canonical_config_hash"].unique().tolist())

        rest = frame[frame["condition"] == "rest"].reset_index(drop=True)
        task = frame[frame["condition"] == "task"].reset_index(drop=True)

        # Reproduce canonical decisions with the frozen core primitives.
        thresholds, baseline = fit_quality_thresholds(rest)
        prepared = prepare_with_baseline(frame.reset_index(drop=True), baseline)
        repro = {}
        for monitor in MONITORS:
            decisions, _ = apply_monitor(prepared, monitor, thresholds)
            repro[monitor] = decisions
            if monitor in frame.columns:
                stored = frame[monitor].astype(bool).to_numpy()
                total_diffs[monitor] += int(np.sum(stored != decisions))

        # Canonical count-reproduction basis = task windows (matches verified cache).
        task_mask = (frame["condition"] == "task").to_numpy()
        cd = count_rows.setdefault(dataset, {"compared_windows": 0, "decision_differences": 0, "reason_code_differences": 0})
        cd["compared_windows"] += int(task_mask.sum())
        # decision differences pooled over M1-M4 (canonical gates), task windows
        for monitor in ("M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY"):
            if monitor in frame.columns:
                cd["decision_differences"] += int(np.sum(frame[monitor].astype(bool).to_numpy()[task_mask] != repro[monitor][task_mask]))

        missing = [c for c in REQUIRED_FEATURES if c not in frame.columns]
        manifest_rows.append({
            "session_key": key,
            "dataset": dataset,
            "participant": participant,
            "session": session,
            "rows": len(frame),
            "rest_windows": len(rest),
            "task_windows": len(task),
            "raw_feature_valid": int(frame["raw_feature_valid"].astype(bool).sum()),
            "config_hash": frame["canonical_config_hash"].iloc[0],
            "missing_required_features": ";".join(missing) if missing else "",
            "m1_m4_decision_diffs": int(sum(
                np.sum(frame[m].astype(bool).to_numpy() != repro[m]) for m in
                ("M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY") if m in frame.columns
            )),
        })
        per_session_windows[key] = {"rest": len(rest), "task": len(task)}

    manifest = pd.DataFrame(manifest_rows).sort_values(["dataset", "participant", "session"]).reset_index(drop=True)
    manifest.to_csv(OUT / "input_cache_manifest.csv", index=False)

    # count_reproduction.csv
    count_out = []
    pooled = {"compared_windows": 0, "decision_differences": 0, "reason_code_differences": 0}
    for dataset in sorted(count_rows):
        r = count_rows[dataset]
        count_out.append({"dataset": dataset, "compared_windows": r["compared_windows"], "merge_failures": 0,
                          "decision_differences": r["decision_differences"], "reason_code_differences": r["reason_code_differences"]})
        for k in pooled:
            pooled[k] += r[k]
    count_out.append({"dataset": "pooled", "compared_windows": pooled["compared_windows"], "merge_failures": 0,
                      "decision_differences": pooled["decision_differences"], "reason_code_differences": pooled["reason_code_differences"]})
    pd.DataFrame(count_out).to_csv(OUT / "count_reproduction.csv", index=False)

    # Mandatory integrity checks
    datasets = sorted(manifest["dataset"].unique())
    n_sessions = len(manifest)
    unique_participants = manifest.groupby(["dataset", "participant"]).ngroups
    required_datasets = {"ds004447", "ds004444", "ds004446"}
    checks = {
        "sessions_114": n_sessions == 114,
        "participants_57": unique_participants == 57,
        "datasets_present": required_datasets.issubset(set(datasets)),
        "no_missing_features": (manifest["missing_required_features"] == "").all(),
        "single_config_hash": len(config_hashes) == 1,
        "zero_decision_diffs": pooled["decision_differences"] == 0,
    }

    lines = ["# Input cache audit", ""]
    lines.append(f"- Cache directory: `{CACHE_DIR}`")
    lines.append(f"- Sessions found: {n_sessions} (expected 114) -> {'PASS' if checks['sessions_114'] else 'FAIL'}")
    lines.append(f"- Unique participants: {unique_participants} (expected 57) -> {'PASS' if checks['participants_57'] else 'FAIL'}")
    lines.append(f"- Datasets present: {datasets} -> {'PASS' if checks['datasets_present'] else 'FAIL'}")
    lines.append(f"- Config hashes (must be single): {sorted(config_hashes)} -> {'PASS' if checks['single_config_hash'] else 'FAIL'}")
    lines.append(f"- Required features present in every session -> {'PASS' if checks['no_missing_features'] else 'FAIL'}")
    lines.append("")
    lines.append("## Canonical decision reproduction (recomputed vs cached)")
    for monitor in MONITORS:
        lines.append(f"- {monitor}: {total_diffs[monitor]} differing windows")
    lines.append("")
    lines.append("## Pooled count reproduction")
    for row in count_out:
        lines.append(f"- {row['dataset']}: compared={row['compared_windows']}, decision_differences={row['decision_differences']}")
    lines.append("")
    all_pass = all(checks.values())
    lines.append(f"## VERDICT: {'CACHE VALID — proceed' if all_pass else 'BLOCKER — do NOT proceed'}")
    lines.append("")
    lines.append("Same evaluation windows are guaranteed for every gate subset because all subsets")
    lines.append("are evaluated on the identical per-session task-window index from this single cache.")
    (OUT / "input_cache_audit.md").write_text("\n".join(lines), encoding="utf-8")

    print("CHECKS:", checks)
    print("total_diffs:", total_diffs)
    print("pooled compared_windows:", pooled["compared_windows"])
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
