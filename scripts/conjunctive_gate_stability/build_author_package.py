"""STAGE 10 — assemble the final author package (structured artifacts only; no prose paragraphs)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAW = ROOT / "results" / "conjunctive_gate_instability"
REM = ROOT / "results" / "conjunctive_law_remedy"
DEGF = ROOT / "results" / "conjunctive_gate_final"
DEG = DEGF / "degradation"
AP = DEGF / "author_package"
AP.mkdir(parents=True, exist_ok=True)


def r(x, n=4):
    try:
        return round(float(x), n)
    except Exception:
        return x


def main():
    cal = pd.read_csv(REM / "author_package" / "calibration_stability_table.csv").set_index("method")
    trans = pd.read_csv(REM / "author_package" / "transport_table.csv").set_index("method")
    down = pd.read_csv(REM / "remedy" / "downstream_information_cost_R.csv").set_index("method")
    runtime = pd.read_csv(REM / "remedy" / "runtime_table.csv")
    card = pd.read_csv(LAW / "cardinality_results.csv")
    ce = card[card.estimator == "empirical"]
    top = pd.read_csv(DEG / "top_severity_comparison.csv")
    dsc = pd.read_csv(DEG / "degradation_success_scorecard.csv")
    d0 = pd.read_csv(DEG / "unchanged_control_results.csv").set_index("method")
    fc = pd.read_csv(DEG / "fail_closed_results.csv").set_index("method")
    verdict_deg = dsc.loc[dsc.condition == "VERDICT", "passed"].iloc[0]

    # 3 theorem evidence
    pd.DataFrame([
        {"item": "symbolic_identity", "result": "exact (sympy)"},
        {"item": "factorized_identity_match", "result": 1.0},
        {"item": "independence_nonincrease_fraction", "result": 0.9998},
        {"item": "dependence_increase_cases", "result": 9693},
    ]).to_csv(AP / "theorem_evidence_table.csv", index=False)
    # 4 composition validation
    pd.read_csv(REM / "validation" / "leave_one_dataset_out_composition_results.csv").to_csv(AP / "composition_validation_table.csv", index=False)
    # 5 cardinality
    ce[["cardinality", "median_observed_jaccard", "obs_ci_low", "obs_ci_high", "median_predicted_jaccard",
        "median_overall_agreement", "median_mutual_withholding_fraction"]].to_csv(AP / "cardinality_results_table.csv", index=False)
    # 6 lattice
    pd.read_csv(LAW / "author_package" / "lattice_effect_table.csv").to_csv(AP / "lattice_edge_results_table.csv", index=False)
    # 7 remedy primary
    pd.read_csv(REM / "remedy" / "remedy_full_scorecard.csv").to_csv(AP / "remedy_primary_results_table.csv", index=False)
    # 8 remedy sensitivity (R2)
    cal.reset_index()[cal.reset_index().method.isin(["R0_ORIGINAL_AND", "R2_RMS_PERCENTILE"])].to_csv(AP / "remedy_sensitivity_results_table.csv", index=False)
    # 9 transport
    trans.reset_index().to_csv(AP / "transport_results_table.csv", index=False)
    # 10 operational
    pd.read_csv(REM / "author_package" / "operational_behavior_table.csv").to_csv(AP / "operational_results_table.csv", index=False)
    # 11 downstream
    down.reset_index().to_csv(AP / "downstream_results_table.csv", index=False)
    # 12 degradation
    top.to_csv(AP / "degradation_results_table.csv", index=False)
    # 13 runtime
    runtime.to_csv(AP / "runtime_results_table.csv", index=False)

    R1s = float(cal.loc["R1_MEAN_PERCENTILE", "pooled_median_splithalf_jaccard"])
    R0s = float(cal.loc["R0_ORIGINAL_AND", "pooled_median_splithalf_jaccard"])
    R1t = float(trans.loc["R1_MEAN_PERCENTILE", "median_transport_jaccard"])
    R1dn = float(down.loc["R1_MEAN_PERCENTILE", "natural_minus_nogate"])
    r1_fw = float(d0.loc["R1", "false_withhold_rate"]); r1_fc = float(fc.loc["R1", "fail_closed_rate"])

    # 14 final claim-evidence matrix
    claims = [
        ("Composition theorem holds", "PROVEN", "J_new<=J_old iff c(P1+P2)<=P1a+P2b; symbolic exact", "theory/formal_theorem.md", "independence assumption", "not a universal biological law"),
        ("Parameter-free composition predicts subset Jaccard", "STRONG", "pooled Spearman 0.988, median|err| 0.013, LODO 0.980-0.991", "conjunctive_gate_instability/", "composition, not prospective forecast", "not artifact ground truth"),
        ("Global agreement can conceal accepted-set instability", "SHOWN", f"K5 overall agreement {r(ce[ce.cardinality==5].median_overall_agreement.iloc[0],3)} vs Jaccard {r(ce[ce.cardinality==5].median_observed_jaccard.iloc[0],3)}", "cardinality_results_table.csv", "accepted-set metric", "do not equate agreement with reproducibility"),
        ("R1 single-score improves calibration stability", "STRONG", f"split-half Jaccard {r(R0s,3)} -> {r(R1s,3)}", "calibration_stability_table.csv", "retrospective replay", "not clinical/efficacy"),
        ("R1 improves cross-session transport", "STRONG", f"transport Jaccard {r(float(trans.loc['R0_ORIGINAL_AND','median_transport_jaccard']),3)} -> {r(R1t,3)}", "transport_results_table.csv", "3-dataset scope", "not prospective"),
        ("R1 preserves downstream information", "PASS", f"natural vs no-gate {r(R1dn)} [{r(float(down.loc['R1_MEAN_PERCENTILE','natural_ci_low']))},{r(float(down.loc['R1_MEAN_PERCENTILE','natural_ci_high']))}]", "downstream_results_table.csv", "reused decoder", "not efficacy"),
        ("R1 does not reduce transitions >=30% at matched availability", "LIMIT", "~15% reduction", "operational_results_table.csv", "temporal switching remains", "do not claim smoothness solved"),
        ("R1 fails closed on invalid input; no false withholding on unchanged", "PASS", f"D9 fail-closed {r(r1_fc,3)}, D0 false-withhold {r(r1_fw,3)}", "degradation/fail_closed_results.csv", "engineering test", "not artifact detection accuracy"),
        ("R1 is insensitive to some single-channel degradations", "NEGATIVE", "clipping/frozen-channel top response ~0.0; single-ch broadband 0.54", "degradation_results_table.csv", "blind spots documented", "do not claim general robustness"),
        ("Controlled degradation is engineering verification", "QUALIFIED", f"DEGRADATION verdict {verdict_deg}", "degradation/degradation_final_report.md", "not natural-artifact validation", "no clinical/regulatory claim"),
    ]
    pd.DataFrame(claims, columns=["candidate_claim", "evidence_status", "exact_numerical_support", "source_artifact", "required_qualification", "prohibited_overclaim"]).to_csv(AP / "final_claim_evidence_matrix.csv", index=False)

    # 19 abstract numbers only
    (AP / "abstract_numbers_only.md").write_text("\n".join([
        "sessions: 114", "participants: 57", "datasets: 3",
        "theorem: J_new<=J_old iff c(P1+P2)<=P1a+P2b",
        "composition_pooled_spearman: 0.988", "composition_pooled_median_ae: 0.013",
        "K1_jaccard: 0.915", "K5_jaccard: 0.630",
        f"R0_splithalf_jaccard: {r(R0s,3)}", f"R1_splithalf_jaccard: {r(R1s,3)}",
        f"R1_transport_jaccard: {r(R1t,3)}", f"R1_natural_vs_nogate: {r(R1dn)}",
        f"R1_unchanged_false_withhold: {r(r1_fw,3)}", f"R1_fail_closed_missing: {r(r1_fc,3)}",
        f"R1_top_severity_common_mode_broadband: {r(float(top[top.family=='D2_common_mode_broadband'].R1_top.iloc[0]),2)}",
        f"R1_top_severity_clipping: {r(float(top[top.family=='D6_clipping'].R1_top.iloc[0]),2)}",
        f"R1_top_severity_full_freeze: {r(float(top[top.family=='D8_full_channel_variance_collapse'].R1_top.iloc[0]),2)}",
        f"degradation_verdict: {verdict_deg}",
        "package_decision: PACKAGE-GO-B", "readiness: 8.0",
    ]) + "\n", encoding="utf-8")

    print("author package tables written to", AP)
    print(f"R0->R1 splithalf {r(R0s,3)}->{r(R1s,3)}; degradation {verdict_deg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
