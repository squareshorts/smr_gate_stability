#!/usr/bin/env python3
"""Build the comparative scorecard, frozen figure data, and author package."""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "baseline_gate_stability"
CAL = OUT / "calibration"
TRA = OUT / "transport"
AVA = OUT / "availability"
EXT = OUT / "external_monitor"
DOWN = OUT / "downstream"
RUN = OUT / "runtime"
FIGDATA = OUT / "figure_data"
AUTHOR = OUT / "author_package"
MONITORS = [
    "M0_NO_GATE", "M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY",
    "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY", "M5_RIEMANNIAN_POTATO",
]
DATASETS = ["ds004447", "ds004444", "ds004446"]


def first(frame: pd.DataFrame, monitor: str, **conditions: str) -> pd.Series:
    subset = frame.loc[frame.monitor == monitor]
    for column, value in conditions.items():
        subset = subset.loc[subset[column] == value]
    if len(subset) != 1:
        raise ValueError(f"Expected one row for {monitor} {conditions}; got {len(subset)}")
    return subset.iloc[0]


def write_md(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    FIGDATA.mkdir(parents=True, exist_ok=True)
    AUTHOR.mkdir(parents=True, exist_ok=True)
    stability = pd.concat([
        pd.read_csv(CAL / "stability_pooled.csv"), pd.read_csv(EXT / "stability_results.csv")
    ], ignore_index=True, sort=False)
    transport = pd.concat([
        pd.read_csv(TRA / "transport_pooled.csv"), pd.read_csv(EXT / "transport_results.csv")
    ], ignore_index=True, sort=False)
    availability = pd.concat([
        pd.read_csv(AVA / "metrics_pooled.csv"), pd.read_csv(EXT / "availability_results.csv")
    ], ignore_index=True, sort=False)
    latency = pd.read_csv(RUN / "latency_by_session.csv")
    latency_summary = latency.groupby("monitor", as_index=False).agg(
        mean_latency_ms=("mean_latency_ms", "mean"),
        p95_latency_ms=("mean_latency_ms", lambda values: float(np.percentile(values, 95))),
        maximum_latency_ms=("max_latency_ms", "max"),
    )
    properties = pd.read_csv(RUN / "software_property_matrix.csv")
    downstream = pd.read_csv(DOWN / "monitor_decoder_results.csv")
    downstream_subject = downstream.loc[downstream.status == "valid"].groupby(
        ["dataset", "subject", "monitor", "analysis"], as_index=False
    ).balanced_accuracy.mean()
    wide = downstream_subject.pivot_table(index=["dataset", "subject", "analysis"], columns="monitor", values="balanced_accuracy")
    difference_rows = []
    for (dataset, subject, analysis), row in wide.iterrows():
        for monitor in MONITORS:
            if monitor in row and "M0_NO_GATE" in row and pd.notna(row[monitor]) and pd.notna(row["M0_NO_GATE"]):
                difference_rows.append({"dataset": dataset, "participant": subject, "analysis": analysis, "monitor": monitor, "balanced_accuracy_difference_vs_m0": row[monitor] - row["M0_NO_GATE"]})
    differences = pd.DataFrame(difference_rows)
    diff_summary = differences.groupby(["monitor", "analysis"], as_index=False).balanced_accuracy_difference_vs_m0.mean()

    calibrations = {
        "M0_NO_GATE": "none", "M1_HIGH_BETA": "rest p75 high beta",
        "M2_BROADBAND_HIGH_FREQUENCY": "rest p75 broadband and 35-45 Hz",
        "M3_AMPLITUDE_150": "fixed 150 uV peak-to-peak",
        "M4_NFSQI_FULL_QUALITY": "rest p75/p90 five-feature conjunction",
        "M5_RIEMANNIAN_POTATO": "rest Riemannian center, z<3",
    }
    advantages = {
        "M0_NO_GATE": "maximum availability and deterministic control",
        "M1_HIGH_BETA": "best stability among nontrivial percentile gates",
        "M2_BROADBAND_HIGH_FREQUENCY": "transparent two-feature spectral screen",
        "M3_AMPLITUDE_150": "stable fixed physical threshold",
        "M4_NFSQI_FULL_QUALITY": "broadest transparent reason-code coverage",
        "M5_RIEMANNIAN_POTATO": "established covariance-distance architecture",
    }
    limitations = {
        "M0_NO_GATE": "does not screen quality",
        "M1_HIGH_BETA": "session-dependent threshold",
        "M2_BROADBAND_HIGH_FREQUENCY": "weaker split and transport stability",
        "M3_AMPLITUDE_150": "rarely active in these data",
        "M4_NFSQI_FULL_QUALITY": "lowest calibration and transport stability",
        "M5_RIEMANNIAN_POTATO": "z=3 accepted all observed windows",
    }
    rows = []
    for monitor in MONITORS:
        split = first(stability, monitor, split_type="first_half_second_half")
        odd = first(stability, monitor, split_type="odd_even_nonoverlap")
        trans = first(transport, monitor, direction="first_to_final")
        avail = availability.loc[availability.monitor == monitor].iloc[0]
        runtime = latency_summary.loc[latency_summary.monitor == monitor].iloc[0]
        prop = properties.loc[properties.monitor == monitor].iloc[0]
        getdiff = lambda analysis: float(diff_summary.loc[(diff_summary.monitor == monitor) & (diff_summary.analysis == analysis), "balanced_accuracy_difference_vs_m0"].iloc[0])
        rows.append({
            "monitor": monitor, "calibration_method": calibrations[monitor],
            "median_split_half_accepted_set_jaccard": split.median_accepted_set_jaccard,
            "median_odd_even_accepted_set_jaccard": odd.median_accepted_set_jaccard,
            "proportion_sessions_jaccard_ge_0_80": split.percent_sessions_jaccard_ge_0_80 / 100,
            "overall_agreement": split.median_overall_agreement,
            "cross_session_accepted_set_jaccard": trans.median_accepted_set_jaccard,
            "accepted_windows_per_min": avail.median_accepted_windows_per_min,
            "median_longest_feedback_free_interval_s": avail.median_longest_feedback_free_s,
            "sessions_with_gap_gt_30_s": int(round(float(avail.percent_sessions_gap_gt_30s) / 100 * 114)),
            "transitions_per_min": avail.median_state_transitions_per_min,
            "downstream_natural_balanced_accuracy_difference_vs_no_gate": getdiff("natural"),
            "downstream_count_matched_difference_vs_no_gate": getdiff("count_matched"),
            "p95_latency_ms": runtime.p95_latency_ms,
            "nonviable_sessions": int(pd.read_csv(EXT / "nonviable_sessions.csv").shape[0]) if monitor.startswith("M5") else 0,
            "fail_closed_status": "pass" if bool(prop.invalid_fails_closed) else "fail",
            "reason_code_transparency": "yes" if bool(prop.reason_code_transparency) else "no",
            "main_advantage": advantages[monitor], "main_limitation": limitations[monitor],
        })
    scorecard = pd.DataFrame(rows)
    scorecard.to_csv(OUT / "primary_monitor_scorecard.csv", index=False)

    claims = pd.DataFrame([
        ("deterministic conformance is sufficient for operational reliability", "rejected", "M1-M4 conformed exactly but differed in calibration/transport stability"),
        ("baseline-calibrated gate instability is general", "not supported", "only M4 had median split-half Jaccard below 0.80; M1, M2, and M5 did not"),
        ("greater conjunction complexity improves stability", "rejected", "M4 was least stable; M5 behaved as no gate"),
        ("high overall agreement broadly hides low accepted-set agreement", "not supported", "high-agreement/low-Jaccard sessions were absent or rare"),
        ("quality filtering can remove decoder information", "supported for M4 in this decoder", "M4 minus M1 natural difference -0.0148; CI excludes zero"),
        ("any monitor detects true artifacts", "unsupported", "no independent artifact ground truth"),
    ], columns=["claim", "assessment", "evidence"])
    claims.to_csv(OUT / "claim_evidence_matrix.csv", index=False)
    write_md(OUT / "limitations_inventory.md", [
        "# Limitations inventory", "", "- No independent artifact ground truth; quality decisions cannot be interpreted as true artifact labels.",
        "- Three sensorimotor channels constrain covariance structure and external-monitor generalization.",
        "- The faithful Potato z=3 comparator accepted every observed window; this is a retained null result, not evidence of universal suitability.",
        "- Overlapping windows were summarized at participant level, but window-level temporal dependence remains descriptive.",
        "- The downstream endpoint is one simple rest-versus-task decoder and does not establish equivalence or learning effects.",
        "- Fixed M3 was rarely active, limiting inference about amplitude-threshold behavior under severe contamination.",
    ])
    write_md(OUT / "comparative_results_report.md", [
        "# Comparative results report", "",
        "1. Most stable accepted set: M0, M3, and M5 tied at split-half Jaccard 1.000; M1 was the most stable active percentile gate (0.925).",
        "2. Least stable accepted set: M4 (split-half Jaccard 0.687).",
        "3. Complexity did not improve stability: the five-feature conjunction was worse, while Potato accepted all windows.",
        "4. High global agreement did not broadly conceal poor positive agreement; the prespecified pattern was rare.",
        "5. M4 caused the most starvation, but its median longest gap was only 3.0 s and no session exceeded 30 s.",
        "6. M4 caused the most state switching (42.1 transitions/min).",
        "7. M4 had the largest downstream information cost versus no gate (natural balanced accuracy -0.0164).",
        "8. Instability was NF-SQI-specific in this comparison, not general across baseline-calibrated gates.",
        "9. Potato materially weakens the general thesis because it reproduced the no-gate decision set at z=3.",
        "10. Minimum reporting: accepted-set Jaccard, positive/negative agreement, independent calibration splits, duration sensitivity, cross-session transport, temporal gaps/transitions, downstream retention/cost, latency, fail-closed behavior, and reason codes.",
        "", "Decision: NO-GO for a paper claiming general baseline-gate instability. Readiness: 7.5/10 for a transparent comparative engineering report.",
    ])

    concept = pd.DataFrame([
        (1, "Computational\nconformance", 1), (2, "Calibration\nstability", 2),
        (3, "Accepted-set\nstability", 3), (4, "Operational\navailability", 4),
        (5, "Downstream\ninformation cost", 5),
    ], columns=["order", "label", "x"])
    concept.to_csv(FIGDATA / "figure1_conceptual.csv", index=False)
    session_stability = pd.concat([
        pd.read_csv(CAL / "stability_by_session.csv"), pd.read_csv(EXT / "stability_results_by_session.csv")
    ], ignore_index=True, sort=False)
    session_stability.loc[session_stability.split_type == "first_half_second_half", [
        "dataset", "participant", "session", "monitor", "overall_agreement", "accepted_set_jaccard", "positive_agreement"
    ]].to_csv(FIGDATA / "figure2_agreement.csv", index=False)
    duration = pd.concat([
        pd.read_csv(CAL / "duration_sensitivity_by_session.csv"), pd.read_csv(EXT / "duration_results.csv")
    ], ignore_index=True, sort=False)
    duration[["dataset", "participant", "session", "monitor", "duration_s", "accepted_set_jaccard", "overall_agreement"]].to_csv(FIGDATA / "figure3_duration.csv", index=False)
    transport_session = pd.concat([
        pd.read_csv(TRA / "transport_by_session_pair.csv"), pd.read_csv(EXT / "transport_results_by_pair.csv")
    ], ignore_index=True, sort=False)
    transport_session.loc[transport_session.direction == "first_to_final", [
        "dataset", "participant", "source_session", "target_session", "monitor", "accepted_set_jaccard", "overall_agreement"
    ]].to_csv(FIGDATA / "figure4_transport.csv", index=False)
    availability_session = pd.concat([
        pd.read_csv(AVA / "metrics_by_session.csv"), pd.read_csv(EXT / "availability_results_by_session.csv")
    ], ignore_index=True, sort=False)
    availability_session[["dataset", "participant", "session", "monitor", "longest_feedback_free_s", "state_transitions_per_min", "accepted_windows_per_min"]].to_csv(FIGDATA / "figure5_availability.csv", index=False)
    differences.to_csv(FIGDATA / "figure6_downstream.csv", index=False)
    scorecard.to_csv(FIGDATA / "figure7_scorecard.csv", index=False)

    methods = pd.DataFrame([(monitor, calibrations[monitor]) for monitor in MONITORS], columns=["monitor", "frozen_calibration_method"])
    methods.to_csv(AUTHOR / "frozen_methods_parameters.csv", index=False)
    scorecard.to_csv(AUTHOR / "primary_results_table.csv", index=False)
    stability.to_csv(AUTHOR / "calibration_stability_table.csv", index=False)
    transport.to_csv(AUTHOR / "cross_session_transport_table.csv", index=False)
    availability.to_csv(AUTHOR / "operational_availability_table.csv", index=False)
    pd.read_csv(DOWN / "monitor_decoder_contrasts.csv").to_csv(AUTHOR / "downstream_information_cost_table.csv", index=False)
    properties.merge(latency_summary, on="monitor").to_csv(AUTHOR / "runtime_property_table.csv", index=False)
    scorecard.to_csv(AUTHOR / "monitor_scorecard_table.csv", index=False)
    claims.to_csv(AUTHOR / "claim_evidence_matrix.csv", index=False)
    shutil.copy2(OUT / "limitations_inventory.md", AUTHOR / "limitations_inventory.md")
    write_md(AUTHOR / "executive_results_summary.md", [
        "# Executive results summary", "", "Decision: NO-GO for the proposed general-instability thesis.",
        "", "Compared six monitors across 114 sessions and 57 participants in three datasets. M4 was unstable; M1, M2, and M5 did not meet the frozen general-instability criterion. M5 accepted all observed windows. M4 retained the verified downstream information-cost result.",
    ])
    pd.DataFrame([
        ("Current claims", "replace", "claim_evidence_matrix.csv", "General instability was not supported"),
        ("Current methods", "replace", "frozen_methods_parameters.csv", "Comparative monitor definitions and endpoints"),
        ("Current results", "replace", "primary_results_table.csv", "Six-monitor numerical comparison"),
        ("Current discussion", "replace", "limitations_inventory.md", "Null and implementation-specific findings"),
    ], columns=["current section", "action", "replacement artifact", "reason"]).to_csv(AUTHOR / "manuscript_change_map.md", index=False)
    pd.DataFrame([(f"Existing figure {i}", "replace", f"Figure {i}", f"results/baseline_gate_stability/figures/figure{i}.pdf") for i in range(1, 8)], columns=["current_figure", "action", "replacement_figure", "artifact"]).to_csv(AUTHOR / "figure_replacement_map.md", index=False)
    pd.DataFrame([
        ("Current primary table", "replace", "primary_results_table.csv"),
        ("Current methods table", "replace", "frozen_methods_parameters.csv"),
        ("Current limitations table", "replace", "claim_evidence_matrix.csv"),
    ], columns=["current_table", "action", "replacement_artifact"]).to_csv(AUTHOR / "table_replacement_map.md", index=False)
    write_md(AUTHOR / "abstract_numbers_only.md", [
        "sessions: 114", "participants: 57", "datasets: 3", "monitors: 6",
        "split_half_jaccard_M1: 0.925", "split_half_jaccard_M2: 0.842", "split_half_jaccard_M4: 0.687", "split_half_jaccard_M5: 1.000",
        "transport_jaccard_M1: 0.922", "transport_jaccard_M2: 0.845", "transport_jaccard_M4: 0.614", "transport_jaccard_M5: 1.000",
        "M4_minus_HB_natural: -0.0148", "M4_minus_HB_natural_CI: [-0.0234,-0.0065]", "M4_minus_HB_natural_p: 0.0008",
        "M4_minus_HB_count_matched: -0.0058", "M4_minus_HB_count_matched_CI: [-0.0134,+0.0012]", "M4_minus_HB_count_matched_p: 0.1300",
    ])
    (AUTHOR / "title_options.txt").write_text(
        "Calibration Stability and Operational Cost of EEG Quality Gates\n"
        "Accepted-Set Reproducibility in Baseline-Calibrated EEG Gating\n"
        "From Conformance to Availability in EEG Quality Monitoring\n"
        "A Comparative Engineering Audit of EEG Quality Gates\n"
        "Stability, Transport, and Information Cost of EEG Quality Screens\n",
        encoding="utf-8",
    )
    write_md(AUTHOR / "journal_positioning_report.md", ["# Journal positioning report", "", "Format: comparative engineering methods report.", "", "Central result: mixed and implementation-specific; unsuitable for a broad general-instability claim.", "", "Required framing: accepted-set reproducibility and operational behavior, without artifact-validity claims."])
    write_md(AUTHOR / "submission_readiness_report.md", ["# Submission readiness report", "", "Readiness: 7.5/10.", "", "Decision: NO-GO for the proposed general-instability thesis.", "", "Complete: six monitors, external comparator, downstream boundary, runtime audit, R figure data, reproducible checkpoints.", "", "Limiting: null external comparator, implementation-specific instability, no artifact ground truth, manuscript intentionally frozen."])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
