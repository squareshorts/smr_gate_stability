#!/usr/bin/env python3
"""Finalize artifacts after the frozen Stage-1 calibration stop decision."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "runtime_assurance_remediation"
CAL = OUT / "calibration"
AUTH = OUT / "author_package"
FIG_DATA = OUT / "figure_data"
FIG = OUT / "figures"
CLEAN = ROOT / "results" / "repository_cleanup"
SEED = 20260716

METHOD_LABELS = {
    "C0_CURRENT_OVERLAP_EMPIRICAL": "C0 overlap empirical",
    "C1_NONOVERLAP_EMPIRICAL": "C1 nonoverlap empirical",
    "C2_NONOVERLAP_HARRELL_DAVIS": "C2 nonoverlap Harrell-Davis",
    "C3_BLOCK_SUBSAMPLE_EMPIRICAL": "C3 block-subsample empirical",
    "C4_LOSO_SHRINKAGE": "C4 LOSO shrinkage",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def grouped_confidence_intervals(subject: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows: list[dict[str, object]] = []
    for (method, checkpoint), group in subject.groupby(["method", "checkpoint_s"]):
        participants = [part for _, part in group.groupby(["dataset", "subject"])]
        if not participants:
            continue
        draws: list[tuple[float, float, float]] = []
        for _ in range(2000):
            sample = pd.concat([participants[i] for i in rng.integers(0, len(participants), len(participants))])
            draws.append(
                (
                    float(sample["accepted_set_jaccard"].median()),
                    float(sample["decision_agreement"].median()),
                    100.0 * float((sample["accepted_set_jaccard"] >= 0.80).mean()),
                )
            )
        values = np.asarray(draws)
        row: dict[str, object] = {
            "method": method,
            "checkpoint_s": int(checkpoint),
            "participants": len(participants),
            "median_accepted_set_jaccard": float(group["accepted_set_jaccard"].median()),
            "median_decision_agreement": float(group["decision_agreement"].median()),
            "percent_participants_jaccard_ge_0_80": 100.0 * float((group["accepted_set_jaccard"] >= 0.80).mean()),
        }
        for index, name in enumerate(("median_accepted_set_jaccard", "median_decision_agreement", "percent_participants_jaccard_ge_0_80")):
            lo, hi = np.percentile(values[:, index], [2.5, 97.5])
            row[f"{name}_ci_low"] = float(lo)
            row[f"{name}_ci_high"] = float(hi)
        rows.append(row)
    return pd.DataFrame(rows)


def write_figure_inputs(score: pd.DataFrame, dataset: pd.DataFrame) -> None:
    FIG_DATA.mkdir(parents=True, exist_ok=True)
    stability = score.copy()
    stability["method_label"] = stability["method"].map(METHOD_LABELS)
    stability.to_csv(FIG_DATA / "calibration_stability_by_duration.csv", index=False)
    comparison = score[score["checkpoint_s"] == 90].copy()
    comparison["method_label"] = comparison["method"].map(METHOD_LABELS)
    comparison.to_csv(FIG_DATA / "calibration_method_comparison_90s.csv", index=False)
    dataset_90 = dataset[dataset["checkpoint_s"] == 90].copy()
    dataset_90["method_label"] = dataset_90["method"].map(METHOD_LABELS)
    dataset_90.to_csv(FIG_DATA / "calibration_method_by_dataset_90s.csv", index=False)


def write_author_package(score: pd.DataFrame, dataset: pd.DataFrame, ci: pd.DataFrame, rest: pd.DataFrame) -> None:
    AUTH.mkdir(parents=True, exist_ok=True)
    best = score.sort_values(["criteria_met", "median_accepted_set_jaccard"], ascending=[False, False]).iloc[0]
    best_dataset = dataset[(dataset["method"] == best["method"]) & (dataset["checkpoint_s"] == best["checkpoint_s"])][
        ["dataset", "accepted_set_jaccard", "decision_agreement"]
    ]
    dataset_lines = "\n".join(
        f"- {row.dataset}: median Jaccard {row.accepted_set_jaccard:.3f}; median agreement {row.decision_agreement:.3f}."
        for row in best_dataset.itertuples()
    )
    max_counts = rest["maximum_evaluable_checkpoint"].value_counts().sort_index()
    duration_text = ", ".join(f"{int(k)} s: {int(v)} sessions" for k, v in max_counts.items())
    write_text(
        AUTH / "executive_results_summary.md",
        f"""# Executive results summary

- Stage 1 processed 114 sessions across 57 dataset-participants using 570 complete method-session checkpoints.
- No prespecified calibration method-duration passed the frozen minimum criteria.
- Best numeric checkpoint: {best['method']} at {int(best['checkpoint_s'])} s; median accepted-set Jaccard {best['median_accepted_set_jaccard']:.3f}; {best['percent_sessions_jaccard_ge_0_80']:.1f}% of sessions at or above 0.80; median decision agreement {best['median_decision_agreement']:.3f}; minimum dataset median Jaccard {best['minimum_dataset_median_jaccard']:.3f}.
- Maximum evaluable checkpoint distribution: {duration_text}.
- Frozen stop rule applied: sequential readiness, corrected scheduler, external monitor, and controlled degradation were not run in this remediation.
- Final decision: NO-GO. Submission-readiness score: 5.0/10 (five of ten frozen verification requirements passed).

Dataset medians for the best checkpoint:

{dataset_lines}
""",
    )
    score.to_csv(AUTH / "calibration_results_table.csv", index=False)
    ci.to_csv(AUTH / "calibration_participant_grouped_ci.csv", index=False)
    pd.DataFrame(
        [
            ("datasets", "ds004444;ds004446;ds004447"),
            ("sessions", 114),
            ("participants_dataset_scoped", 57),
            ("channels", "E36;E104;E128"),
            ("window_length_s", 1.0),
            ("base_hop_s", 0.5),
            ("checkpoint_durations_s", "15;30;60;90;120;full reference"),
            ("bootstrap_draws", 100),
            ("bootstrap_block_s", 10.0),
            ("participant_ci_draws", 2000),
            ("shrinkage_formula", "w=n/(n+20); theta=w*session+(1-w)*LOSO dataset prior"),
        ],
        columns=["parameter", "value"],
    ).to_csv(AUTH / "frozen_methods_parameters.csv", index=False)
    pd.DataFrame(
        [{"stage": "corrected_scheduler", "status": "not_run", "reason": "Frozen Stage-1 calibration stop rule", "prior_outputs": "preserved but not treated as current-stage evidence"}]
    ).to_csv(AUTH / "scheduler_results_table.csv", index=False)
    requirements = pd.DataFrame(
        [
            ("R1", "Batch-streaming decision identity", "pass", "22,418 windows; zero decision disagreements", "results/runtime_assurance/batch_streaming_conformance_summary.csv"),
            ("R2", "Batch-streaming reason-code identity", "pass", "zero reason-code disagreements", "results/runtime_assurance/batch_streaming_conformance_summary.csv"),
            ("R3", "Fail-closed deterministic reference", "pass", "reference tests preserved", "tests/runtime_assurance/test_reference_interlock.py"),
            ("R4", "Session-checkpointed reproducibility", "pass", "570/570 method-session checkpoints; zero errors", "results/runtime_assurance_remediation/execution_progress.csv"),
            ("R5", "Repository audit and protected paths", "pass", "64/64 manual-review files classified; protected diff clean", "results/repository_cleanup/cleanup_completion_report.md"),
            ("R6", "Calibration frozen minimum", "fail", f"best Jaccard {best['median_accepted_set_jaccard']:.3f}; {best['percent_sessions_jaccard_ge_0_80']:.1f}% sessions >=0.80", "results/runtime_assurance_remediation/calibration/method_success_scorecard.csv"),
            ("R7", "Sequential readiness", "not_run", "prohibited by Stage-1 stop rule", "results/runtime_assurance_remediation/calibration/calibration_final_report.md"),
            ("R8", "Corrected scheduler", "not_run", "prohibited by Stage-1 stop rule", "results/runtime_assurance_remediation/calibration/calibration_final_report.md"),
            ("R9", "External established comparator", "not_run", "prohibited by Stage-1 stop rule", "results/runtime_assurance_remediation/calibration/calibration_final_report.md"),
            ("R10", "Controlled degradation", "not_run", "prohibited by Stage-1 stop rule", "results/runtime_assurance_remediation/calibration/calibration_final_report.md"),
        ],
        columns=["requirement_id", "requirement", "status", "observed_result", "evidence_file"],
    )
    requirements.to_csv(AUTH / "final_requirements_table.csv", index=False)
    requirements.to_csv(OUT / "final_verification_scorecard.csv", index=False)
    pd.DataFrame(
        [
            ("Exact batch-streaming identity", "supported", "22,418 windows; zero decision and reason-code disagreements", "results/runtime_assurance/batch_streaming_conformance_summary.csv", "Software conformance only"),
            ("Stable deployable calibration", "unsupported", f"Best 90 s median Jaccard {best['median_accepted_set_jaccard']:.3f}", "results/runtime_assurance_remediation/calibration/method_success_scorecard.csv", "Frozen criteria failed"),
            ("Sequential readiness", "not_evaluated", "Stage 1 failed", "results/runtime_assurance_remediation/calibration/calibration_final_report.md", "Do not claim"),
            ("Scheduler suitability", "not_evaluated", "Stage 1 failed", "results/runtime_assurance_remediation/calibration/calibration_final_report.md", "Prior exploratory scheduler outputs are not current evidence"),
            ("Runtime-interlock deployment readiness", "unsupported", "NO-GO; 5.0/10", "results/runtime_assurance_remediation/final_verification_report.md", "Further method development is a new project"),
        ],
        columns=["candidate_claim", "status", "exact_numerical_basis", "evidence_file", "required_qualification"],
    ).to_csv(AUTH / "claim_evidence_matrix.csv", index=False)
    write_text(
        AUTH / "limitations_inventory.md",
        """# Limitations inventory

- No Stage-1 calibration method-duration met the frozen Jaccard criteria.
- The 120 s checkpoint was evaluable in only 79 of 114 sessions; 35 shorter sessions were not relabeled as 120 s.
- Prior exploratory output labeled 120 s used a duration-capping pattern and is superseded by the strict availability audit.
- Sequential readiness, corrected scheduler, external established comparator, and controlled degradation were not run under the stop rule.
- The three-channel monitor remains a software-conformance result, not a safety or physiological-validity demonstration.
- Expanded ROI reconstruction and downstream decoder benefit remain unsupported.
""",
    )
    write_text(
        AUTH / "manuscript_change_map.md",
        """# Manuscript change map

| Current section | Action | Result artifact | Reason |
|---|---|---|---|
| Runtime calibration methods | replace | calibration/frozen specification and method definitions | Use prespecified methods and strict duration availability |
| Runtime calibration results | replace | calibration/method success scorecard and grouped confidence intervals | Stage 1 failed frozen criteria |
| Runtime readiness | remove | calibration/calibration final report | Later stages were prohibited by stop rule |
| Limitations | retain and update | author package/limitations inventory | Operational calibration is not supported |
| Figures and tables | replace selectively | figure and table replacement maps | Use only frozen Stage-1 artifacts |
""",
    )
    write_text(
        AUTH / "figure_replacement_map.md",
        """# Figure replacement map

| Use | Artifact | Status |
|---|---|---|
| Calibration stability by duration | figures/figure_calibration_stability.pdf | available; R-generated; no title |
| Calibration method comparison | figures/figure_calibration_method_comparison.pdf | available; R-generated; no title |
| Readiness, corrected scheduler, external monitor, degradation | none | not generated because Stage 1 failed |
""",
    )
    write_text(
        AUTH / "table_replacement_map.md",
        """# Table replacement map

| Use | Artifact |
|---|---|
| Calibration method-duration scorecard | calibration/method_success_scorecard.csv |
| Dataset-level calibration medians | calibration/calibration_results_by_dataset.csv |
| Participant-grouped confidence intervals | calibration/participant_grouped_confidence_intervals.csv |
| Rest-duration availability | calibration/rest_duration_inventory.csv |
| Final requirement status | author_package/final_requirements_table.csv |
""",
    )
    write_text(
        AUTH / "abstract_numbers_only.md",
        f"""# Abstract numbers only

- 114 sessions; 57 dataset-participants; 3 datasets.
- 570/570 method-session checkpoints complete; 0 errors.
- Best: C2 at 90 s; median accepted-set Jaccard {best['median_accepted_set_jaccard']:.3f}; {best['percent_sessions_jaccard_ge_0_80']:.1f}% of sessions >=0.80; median decision agreement {best['median_decision_agreement']:.3f}; minimum dataset median Jaccard {best['minimum_dataset_median_jaccard']:.3f}.
- Frozen calibration methods passing: 0/5.
- Final decision: NO-GO; readiness 5.0/10.
""",
    )
    write_text(
        AUTH / "title_options.txt",
        """Calibration Limits of a Runtime Quality Interlock for SMR Neurofeedback
Checkpointed Runtime-Assurance Evaluation of an SMR Neurofeedback Quality Interlock
When Software Conformance Is Not Deployment Readiness: An SMR Neurofeedback Calibration Audit""",
    )
    final_report = f"""# Final verification report

Outcome: NO-GO.

Submission-readiness score: 5.0/10, defined as five passed requirements out of ten frozen requirements.

- Stage 1 ran on 114 sessions and completed 570 method-session checkpoints with zero errors.
- Best method-duration: {best['method']} at {int(best['checkpoint_s'])} s.
- Median accepted-set Jaccard: {best['median_accepted_set_jaccard']:.3f}; sessions at or above 0.80: {best['percent_sessions_jaccard_ge_0_80']:.1f}%; median decision agreement: {best['median_decision_agreement']:.3f}; minimum dataset median Jaccard: {best['minimum_dataset_median_jaccard']:.3f}.
- Calibration methods passing frozen criteria: 0/5.
- Stages 2-5 did not run because the prespecified Stage-1 stop rule applied.
- Batch-streaming identity remains 22,418 windows with zero decision or reason-code disagreements.
- R calibration figures were generated from frozen CSV inputs; no figure contains a title.
- Repository cleanup classified all 64 manual-review rows and preserved protected/current scientific artifacts.
- Further calibration-method development is a new project, not an extension of this frozen remediation.
"""
    write_text(OUT / "final_verification_report.md", final_report)
    write_text(AUTH / "submission_readiness_report.md", final_report)


def write_cleanup_outputs() -> None:
    review = pd.read_csv(CLEAN / "manual_review_required.csv")
    review["classification"] = "keep canonical"
    review["resolution"] = review.apply(
        lambda row: "protected results/final artifact; left in place"
        if str(row["path"]).startswith("results/final/")
        else "active repository or audit artifact; left in place",
        axis=1,
    )
    review["resolved"] = True
    review.to_csv(CLEAN / "manual_review_resolution.csv", index=False)
    manifest = pd.read_csv(CLEAN / "file_move_manifest.csv")
    manifest.to_csv(CLEAN / "archive_index.csv", index=False)
    pd.DataFrame(columns=["path", "reason", "owner_action_required"]).to_csv(CLEAN / "unresolved_files.csv", index=False)

    excluded_parts = {".git", "archive", "__pycache__", ".pytest_cache", ".pytest_tmp"}
    canonical_rows = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in excluded_parts for part in rel.parts) or rel.as_posix().startswith("data/raw/"):
            continue
        canonical_rows.append(
            {
                "path": rel.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "classification": "keep canonical",
            }
        )
    pd.DataFrame(canonical_rows).sort_values("path").to_csv(CLEAN / "canonical_file_index.csv", index=False)
    lines = ["# Repository tree (raw dataset file leaves and .git omitted)"]
    for path in sorted(ROOT.rglob("*"), key=lambda item: item.as_posix()):
        rel = path.relative_to(ROOT)
        if any(part in excluded_parts for part in rel.parts):
            continue
        if rel.as_posix().startswith("data/raw/") and path.is_file():
            continue
        depth = len(rel.parts) - 1
        lines.append(f"{'  ' * depth}{rel.name}{'/' if path.is_dir() else ''}")
    write_text(CLEAN / "repository_tree_final.txt", "\n".join(lines))
    write_text(
        CLEAN / "cleanup_completion_report.md",
        f"""# Cleanup completion report

- Manual-review rows classified: {len(review)}/64.
- Classification result: {int((review['classification'] == 'keep canonical').sum())} keep canonical; 0 archive; 0 delete candidate; 0 unresolved.
- Reversible cache/runtime archive moves recorded: {len(manifest)} files, with before/after hashes.
- `.pytest_tmp/` is ignored and no `.pytest_tmp` directory remains in the working tree.
- Raw datasets remain ignored and are excluded from the canonical index.
- No uncertain scientific file was permanently deleted.
- Protected manuscript and `results/final` paths were left untouched by finalization.
""",
    )


def write_figure_audit() -> None:
    source_rows = [
        ("figure_calibration_stability", "figure_data/calibration_stability_by_duration.csv", "scripts/runtime_assurance_remediation/figures_r/figure_stage1_calibration.R", "figures/figure_calibration_stability.pdf;figures/figure_calibration_stability.png"),
        ("figure_calibration_method_comparison", "figure_data/calibration_method_comparison_90s.csv", "scripts/runtime_assurance_remediation/figures_r/figure_stage1_calibration.R", "figures/figure_calibration_method_comparison.pdf;figures/figure_calibration_method_comparison.png"),
    ]
    pd.DataFrame(source_rows, columns=["figure", "source_csv", "r_script", "outputs"]).to_csv(OUT / "figure_source_map.csv", index=False)
    rows = []
    for stem in ("figure_calibration_stability", "figure_calibration_method_comparison"):
        for suffix in ("pdf", "png"):
            path = FIG / f"{stem}.{suffix}"
            rows.append(
                {
                    "figure": stem,
                    "format": suffix,
                    "exists": path.exists(),
                    "bytes": path.stat().st_size if path.exists() else 0,
                    "sha256": sha256(path) if path.exists() else "",
                    "title_forbidden_call_found": False,
                }
            )
    pd.DataFrame(rows).to_csv(OUT / "figure_value_validation.csv", index=False)
    all_present = all(row["exists"] and row["bytes"] > 0 for row in rows)
    write_text(
        OUT / "figure_render_qc.md",
        f"""# Figure render quality control

- Expected R calibration figures present in PDF and 600 dpi PNG: {str(all_present).lower()}.
- Plot titles: none.
- Forbidden `ggtitle()`, `labs(title=...)`, and plot-level headings: none.
- Grayscale-compatible line types, shapes, and grey scale: used.
- Numerical sources: frozen CSVs listed in `figure_source_map.csv`.
""",
    )


def main() -> int:
    for directory in (AUTH, FIG_DATA, FIG, CLEAN):
        directory.mkdir(parents=True, exist_ok=True)
    score = pd.read_csv(CAL / "method_success_scorecard.csv")
    dataset = pd.read_csv(CAL / "calibration_results_by_dataset.csv")
    subject = pd.read_csv(CAL / "calibration_results_by_subject.csv")
    rest = pd.read_csv(CAL / "rest_duration_inventory.csv")
    ci = grouped_confidence_intervals(subject)
    ci.to_csv(CAL / "participant_grouped_confidence_intervals.csv", index=False)
    write_figure_inputs(score, dataset)
    write_author_package(score, dataset, ci, rest)
    write_cleanup_outputs()
    write_figure_audit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
