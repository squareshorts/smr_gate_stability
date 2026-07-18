#!/usr/bin/env python3
"""Preflight gate for the isolated downstream decoder validation.

The frozen analysis plan requires current-code reproduction of released gate
counts before any decoder modeling.  This entry point inventories required raw
inputs and writes an explicit blocker package if they are unavailable.  It
never substitutes stored manuscript summaries for raw-window reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "downstream_decoder_validation"
DATASETS = ("ds004447", "ds004444", "ds004446")
EXPECTED = {
    "ds004447": {"task_windows": 5218, "high_beta_blocks": 126, "gate_c_retained": 472},
    "ds004444": {"task_windows": 14400, "high_beta_blocks": 644, "gate_c_retained": 933},
    "ds004446": {"task_windows": 2800, "high_beta_blocks": 96, "gate_c_retained": 215},
}


def git(command: list[str]) -> str:
    return subprocess.check_output(["git", *command], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(name: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    with (RESULTS / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_static_not_run_artifacts(reason: str) -> None:
    empty_tables = {
        "event_label_audit.csv": ["dataset", "subject", "session", "event_label", "number_of_trials_or_segments", "usable_windows", "excluded_transition_windows", "ambiguous_windows", "final_rest_windows", "final_task_windows", "status"],
        "fold_definition.csv": ["dataset", "subject", "train_session", "test_session", "direction", "status", "reason"],
        "retention_by_fold.csv": ["dataset", "subject", "train_session", "test_session", "policy", "class", "retained_windows", "available_windows", "retention_proportion", "status"],
        "retention_by_subject.csv": ["dataset", "subject", "policy", "class", "retained_windows", "available_windows", "retention_proportion", "status"],
        "decoder_results_all_folds.csv": ["dataset", "subject", "train_session", "test_session", "policy", "analysis", "balanced_accuracy", "roc_auc", "accuracy", "macro_f1", "sensitivity", "specificity", "log_loss", "brier_score", "status"],
        "decoder_results_by_subject.csv": ["dataset", "subject", "policy", "analysis", "balanced_accuracy", "status"],
        "primary_contrasts.csv": ["dataset", "contrast", "analysis", "mean_paired_difference", "median_paired_difference", "bootstrap_ci_low", "bootstrap_ci_high", "p_value", "n_participants", "status"],
        "count_matched_results.csv": ["dataset", "subject", "train_session", "test_session", "policy", "seed", "balanced_accuracy", "status"],
        "expanded_roi_results.csv": ["dataset", "subject", "policy", "analysis", "balanced_accuracy", "status"],
        "leave_one_subject_out_sensitivity.csv": ["omitted_subject", "contrast", "mean_paired_difference", "status"],
        "leave_one_dataset_out_sensitivity.csv": ["omitted_dataset", "contrast", "mean_paired_difference", "status"],
        "nonviable_folds.csv": ["dataset", "subject", "train_session", "test_session", "policy", "reason", "status"],
    }
    for name, fields in empty_tables.items():
        write_csv(name, fields, [])
    (RESULTS / "quality_policy_definitions.md").write_text(
        "# Quality-only policy definitions\n\n"
        "All policies apply to finite, correctly labelled *training* windows only and are applied symmetrically to rest and task. Thresholds are fit from the training session rest baseline using the released p75/p90 policy.\n\n"
        "- `ALL`: no quality filter.\n"
        "- `HB`: high-beta pass only.\n"
        "- `BBHF`: broadband and high-frequency-reference pass.\n"
        "- `NFSQI_NO_HB`: broadband, high-frequency-reference, transient, and channel-consistency pass.\n"
        "- `NFSQI_FULL`: high-beta, broadband, high-frequency-reference, transient, and channel-consistency pass.\n"
        "- `AMPLITUDE_150`: existing 150 microvolt peak-to-peak baseline.\n\n"
        "No policy contains Gate A, an SMR threshold, target positivity, reward candidacy, decoder output, or a task label.\n",
        encoding="utf-8",
    )
    (RESULTS / "rpf_implementation_report.md").write_text(
        "# Riemannian Potato / Riemannian Potato Field implementation report\n\n"
        f"Status: not attempted because Priority 1 is blocked. {reason}\n",
        encoding="utf-8",
    )
    (RESULTS / "manuscript_update_notes.md").write_text(
        "# Manuscript update notes\n\n"
        "No manuscript update is supported: the independent downstream analysis was not run. No existing rule-defined classifier analysis should be reclassified, removed, or replaced on the basis of this blocked run. The title, abstract, and scientific claims cannot be evaluated by this validation until raw data and released feature caches are supplied.\n",
        encoding="utf-8",
    )
    (RESULTS / "analysis_report.md").write_text(
        "# Downstream decoder validation report\n\n"
        "## Status\n\n"
        f"**BLOCKED BEFORE MODELING.** {reason}\n\n"
        "The frozen plan prohibits using stored rule-defined summaries as a substitute for raw-window reproduction and prohibits modeling if reconciliation fails. Therefore no independent event labels, held-out-session folds, decoder fits, retention estimates, primary contrast, count-matched result, dataset result, expanded-ROI result, RPF result, or synthetic-perturbation result exists.\n\n"
        "Consequently, the requested questions about whether NF-SQI improves downstream decoding, whether it removes useful neural information, and whether the manuscript claim should be retained cannot be answered from this checkout. This is absence of required data, not evidence of a null or negative decoder effect.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight downstream decoder validation; no modeling occurs until count reconciliation passes.")
    parser.add_argument("--allow-blocked", action="store_true", help="Return zero after writing the blocker package when raw inputs are absent.")
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "figures").mkdir(exist_ok=True)

    rows: list[dict[str, object]] = []
    missing: list[str] = []
    for dataset in DATASETS:
        root = ROOT / "data" / "raw" / "openneuro" / dataset
        edfs = sorted(root.rglob("*_task-smrbmi_eeg.edf")) if root.exists() else []
        events = sorted(root.rglob("*_task-smrbmi_events.tsv")) if root.exists() else []
        feature_cache = ROOT / "outputs" / "tables" / "nf_sqi_window_features.csv"
        # A canonical cache is regenerated in memory from the raw window path;
        # it is not required to exist before the count-reproduction gate.
        present = bool(edfs and events)
        if not present:
            missing.append(dataset)
        rows.append({
            "dataset": dataset,
            "raw_root": str(root.relative_to(ROOT)),
            "raw_root_present": root.exists(),
            "edf_count": len(edfs),
            "events_count": len(events),
            "released_feature_cache": str(feature_cache.relative_to(ROOT)),
            "released_feature_cache_present": feature_cache.exists(),
            "required_task_windows": EXPECTED[dataset]["task_windows"],
            "required_high_beta_blocks": EXPECTED[dataset]["high_beta_blocks"],
            "required_gate_c_retained": EXPECTED[dataset]["gate_c_retained"],
            "reconciliation_status": "NOT_RUN_MISSING_INPUTS" if not present else "PENDING_RAW_REPLAY",
        })
    write_csv("data_inventory.csv", list(rows[0]), rows)
    inventory = ["# Data inventory and reconciliation gate", "", "The checked-out release code requires raw EDF/event sidecars under `data/raw/openneuro/` and the derived feature cache `outputs/tables/nf_sqi_window_features.csv` for current-code count reproduction.", "", "| Dataset | EDFs | events | feature cache | reconciliation |", "|---|---:|---:|---|---|"]
    for row in rows:
        inventory.append(f"| {row['dataset']} | {row['edf_count']} | {row['events_count']} | {row['released_feature_cache_present']} | {row['reconciliation_status']} |")
    inventory.extend(["", "The stored files in `results/final/` report released counts but cannot satisfy this gate because they are summaries rather than replayable raw-window inputs. The repository's own `results/figure_corrections/figure_correction_report.md` also records that raw EDF and `nf_sqi_window_features.csv` are absent."])
    (RESULTS / "data_inventory.md").write_text("\n".join(inventory) + "\n", encoding="utf-8")

    if missing:
        reason = ("Raw EDF/event inputs and the released feature cache are absent for " + ", ".join(missing) +
                  "; current-code reproduction of the mandatory released counts is impossible.")
        (RESULTS / "blocker_report.md").write_text(
            "# Blocker report: mandatory count reconciliation\n\n"
            f"{reason}\n\n"
            "Expected released checks are ds004447: 5218 task windows, 126 high-beta blocks, 472 Gate C retained; ds004444: 14400, 644, 933; ds004446: 2800, 96, 215. These values appear in released summaries but were not treated as reproduced. Per the frozen analysis plan, all downstream modeling is stopped.\n\n"
            "To unblock: place the three original OpenNeuro dataset trees (EDF plus events sidecars) at `data/raw/openneuro/<dataset>` and regenerate or provide the exact released feature cache. Then rerun this command and perform the prescribed raw replay before enabling decoder fitting.\n",
            encoding="utf-8",
        )
        write_static_not_run_artifacts(reason)
        manifest = {
            "status": "BLOCKED_MISSING_REQUIRED_INPUTS",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "command": " ".join([sys.executable, *sys.argv]),
            "repository_commit": git(["rev-parse", "HEAD"]),
            "python": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "seeds": {"model": 20260715, "count_matching": 20260716, "bootstrap": 20260717, "permutation": 20260718, "synthetic": 20260719},
            "input_hashes": {},
            "missing_datasets": missing,
        }
        (RESULTS / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (RESULTS / "environment.txt").write_text(
            f"Python: {sys.version}\nOS: {platform.platform()}\nCPU: {platform.processor()}\nCommit: {manifest['repository_commit']}\nStatus: {manifest['status']}\n",
            encoding="utf-8",
        )
        return 0 if args.allow_blocked else 2

    # Count reproduction is deliberately rerun before every downstream model
    # execution; no stored result is accepted as a substitute.
    for dataset in DATASETS:
        subprocess.check_call([
            sys.executable, str(ROOT / "scripts" / "downstream_decoder_validation" / "reproduce_batch_counts.py"),
            "--dataset", dataset,
            "--out-json", str(RESULTS / f"batch_reproduction_{dataset}.json"),
        ], cwd=ROOT)
        subprocess.check_call([
            sys.executable, str(ROOT / "scripts" / "run_nfsqi_pseudo_online_real_edf.py"),
            "--dataset", dataset,
            "--out-prefix", "results/downstream_decoder_validation/replay",
        ], cwd=ROOT)
    for dataset, expected in EXPECTED.items():
        batch = json.loads((RESULTS / f"batch_reproduction_{dataset}.json").read_text(encoding="utf-8"))
        required = {
            "task_windows": expected["task_windows"],
            "gate_a": {"ds004447": 905, "ds004444": 2455, "ds004446": 451}[dataset],
            "gate_b": {"ds004447": 779, "ds004444": 1811, "ds004446": 355}[dataset],
            "gate_c_inclusive": expected["gate_c_retained"],
            "high_beta_blocks": expected["high_beta_blocks"],
        }
        if any(batch[key] != value for key, value in required.items()):
            raise RuntimeError(f"Mandatory batch count reproduction failed for {dataset}: {batch}")
        if dataset == "ds004444" and not (batch["gate_c_strict"] == 932 and batch["strict_vs_inclusive_ties"] == 1):
            raise RuntimeError(f"Expected ds004444 threshold-tie localization failed: {batch}")
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "downstream_decoder_validation" / "run_decoder_validation.py")], cwd=ROOT)
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "downstream_decoder_validation" / "summarize_decoder_validation.py")], cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
