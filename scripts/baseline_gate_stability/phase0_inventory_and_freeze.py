#!/usr/bin/env python3
"""Inventory the repository and freeze the baseline-gate stability study."""
from __future__ import annotations

import hashlib
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "baseline_gate_stability"
CLEAN = ROOT / "results" / "repository_cleanup_stability"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def write_once(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def textual_corpus(paths: list[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        try:
            if path.stat().st_size <= 2_000_000:
                parts.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(parts)


def freeze_study() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_once(
        OUT / "frozen_analysis_plan.md",
        """# Frozen comparative analysis plan

Frozen before comparative monitor outcomes were computed on this branch.

Operational unit: dataset-participant-session. Inferential unit: dataset-participant. Task windows are evaluated identically across calibration variants. All calibration uses rest windows only. No task label, decoder outcome, or held-out session enters threshold fitting.

Monitors: M0 no quality gate; M1 high beta; M2 broadband/high-frequency; M3 fixed 150 microvolt peak-to-peak screen; M4 full NF-SQI quality criteria without the independent Gate-A reward-request criterion; M5 faithful Riemannian Potato if verified, otherwise the frozen ROBUST_COV_DISTANCE fallback.

Primary analysis: accepted-set Jaccard across first/second rest halves, odd/even nonoverlapping rest blocks, paired independent temporal block-bootstrap draws, and available duration versus full rest. Secondary analyses: cross-session transport, inherent operational availability, downstream decoder information cost, latency, fail-closed behavior, and reason-code transparency.

Negative, null, and mixed findings are retained. No monitor is treated as an artifact detector without independent ground truth.
""",
    )
    write_once(
        OUT / "frozen_monitor_definitions.yaml",
        """M0_NO_GATE:
  calibration: none
  accept: finite_and_structurally_valid
M1_HIGH_BETA:
  calibration: subject_session_rest_only
  threshold: empirical_p75
  accept: high_beta_power_below_threshold
M2_BROADBAND_HIGH_FREQUENCY:
  calibration: subject_session_rest_only
  thresholds: broadband_power_p75; noise_floor_35_45Hz_p75
  accept: both_features_below_thresholds
M3_AMPLITUDE_150:
  calibration: none
  threshold_peak_to_peak_volts: 0.000150
  accept: all_three_channels_peak_to_peak_below_threshold
M4_NFSQI_FULL_QUALITY:
  calibration: subject_session_rest_only
  thresholds: high_beta_p75; broadband_p75; noise_floor_p75; transient_p90; channel_inconsistency_p75
  accept: all_quality_criteria_pass
  gate_a_included: false
M5_ROBUST_COV_DISTANCE_FALLBACK:
  use_only_if_faithful_rpotato_unavailable: true
  covariance_regularization: cov_reg=(1-0.10)*cov+0.10*trace(cov)/3*I
  representation: matrix_log_upper_triangle_with_sqrt2_off_diagonals
  robust_center: coordinatewise_median_of_rest_log_covariance_vectors
  distance: euclidean_log_space
  threshold: empirical_rest_p97.5
  invalid_or_singular_input: fail_closed
""",
    )
    write_once(
        OUT / "frozen_endpoints.md",
        """# Frozen endpoints

Primary endpoint: participant-grouped median accepted-set Jaccard on identical task windows across independent rest-calibration samples.

Secondary stability endpoints: overall agreement, withheld-set Jaccard, Cohen's kappa, positive agreement, negative agreement, acceptance-rate difference, accepted-windows/min difference, and directional flips.

Transport endpoints: local-versus-transported accepted-set Jaccard, agreement, acceptance-rate shift, accepted windows/min, threshold shift, longest feedback-free interval, transitions/min, and disagreement reason.

Availability endpoints: accepted windows/min, duty cycle, inter-acceptance intervals, longest feedback-free period, starvation counts, run durations, transitions/min, and time to first acceptance.

Downstream endpoints: natural-retention and count-matched held-out-session balanced accuracy, retained proportions, nonviable folds, and participant-paired contrasts.

Runtime endpoints: mean/p95/max latency, invalid/missing/flat/nonfinite/equality behavior, parameter count, reason-code transparency, and batch-stream conformance where defined.
""",
    )
    write_once(
        OUT / "frozen_success_and_failure_criteria.md",
        """# Frozen success and failure criteria

- Stable calibration: participant-grouped median accepted-set Jaccard >=0.80 and >=80% of sessions at Jaccard >=0.80.
- Stable transport: participant-grouped median accepted-set Jaccard >=0.75.
- Operationally usable: median longest feedback-free interval <=20 s and <10% of sessions with any gap >30 s.
- High global agreement conceals poor accepted-set stability when overall agreement >=0.95 while accepted-set Jaccard or positive agreement <0.80.
- General instability is supported when at least three calibrated monitor families have median independent-split Jaccard <0.80 in at least two datasets. M0 and fixed M3 are controls, not calibrated families.
- Complexity is associated with improved stability only if the more complex monitor has a higher participant median Jaccard with a grouped 95% interval excluding zero for the paired difference.
- Downstream null results are not equivalence; all confidence intervals and nonviable folds are retained.
- M5 is a faithful established monitor only after environment, API, covariance, metric, threshold, and online-use checks pass. Otherwise it is labeled ROBUST_COV_DISTANCE.
""",
    )


def inventory() -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)
    tracked = set(git("ls-files").splitlines())
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    code_files = [p for folder in ("src", "scripts", "tests", "configs", "docs") for p in (ROOT / folder).rglob("*") if p.is_file()]
    manuscript_files = [p for p in (ROOT / "manuscript").rglob("*") if p.is_file()]
    code_text = textual_corpus(code_files)
    manuscript_text = textual_corpus(manuscript_files)
    rows: list[dict[str, object]] = []
    skip_roots = {".git"}
    for path in sorted(ROOT.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.split("/", 1)[0] in skip_roots:
            continue
        parts = set(path.relative_to(ROOT).parts)
        cache = bool(parts & {"__pycache__", ".pytest_cache", ".pytest_tmp"}) or path.suffix == ".pyc"
        temporary = cache or path.suffix in {".tmp", ".temp"} or path.name.lower() in {"stdout.log", "stderr.log"}
        protected = rel.startswith("manuscript/") or rel.startswith("results/final/") or path.suffix in {".tex", ".bib"}
        referenced_code = rel in code_text or path.name in code_text
        referenced_manuscript = rel in manuscript_text or path.name in manuscript_text
        canonical = protected or rel in tracked or referenced_code or referenced_manuscript
        uncertain = not cache and not temporary and not canonical
        rows.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "modified_date": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "tracked_or_untracked": "tracked" if rel in tracked else "untracked_or_ignored",
                "sha256": sha256(path),
                "referenced_by_code": referenced_code,
                "referenced_by_manuscript": referenced_manuscript,
                "canonical": canonical,
                "stale": temporary,
                "duplicate": False,
                "cache": cache,
                "temporary": temporary,
                "uncertain": uncertain,
            }
        )
    frame = pd.DataFrame(rows)
    counts = frame.groupby("sha256")["path"].transform("size")
    frame["duplicate"] = counts > 1
    frame.to_csv(CLEAN / "full_inventory_before.csv", index=False)
    frame[frame["stale"] | frame["temporary"]].to_csv(CLEAN / "stale_candidates.csv", index=False)
    frame[frame["duplicate"]].sort_values(["sha256", "path"]).to_csv(CLEAN / "duplicate_hashes.csv", index=False)
    frame[frame["uncertain"]].to_csv(CLEAN / "manual_review_required.csv", index=False)
    pd.DataFrame(columns=["original_path", "archive_path", "hash_before", "hash_after", "reason", "references_checked", "reversible", "status"]).to_csv(
        CLEAN / "file_move_manifest.csv", index=False
    )
    sizes = []
    for top in sorted({Path(p).parts[0] for p in frame["path"]}):
        group = frame[frame["path"].str.startswith(f"{top}/") | (frame["path"] == top)]
        sizes.append({"directory": top, "file_count": len(group), "bytes": int(group["size"].sum())})
    pd.DataFrame(sizes).to_csv(CLEAN / "directory_sizes_before.csv", index=False)
    (CLEAN / "untracked_files_before.txt").write_text("\n".join(untracked) + "\n", encoding="utf-8")
    (CLEAN / "repository_state_before.txt").write_text(git("status", "--short", "--branch"), encoding="utf-8")
    (CLEAN / "protected_paths.txt").write_text(
        "manuscript/\nresults/final/\n*.tex\n*.bib\nrelease metadata\nZenodo metadata\nverified runtime-assurance outputs\n",
        encoding="utf-8",
    )


def main() -> int:
    freeze_study()
    inventory()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
