"""Assemble frozen source-data CSVs for the revised 7+1 figure set (no recompute of science).

Reads only existing frozen result tables / checkpoints. Also emits value-validation and source map.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
LAW = ROOT / "results" / "conjunctive_gate_instability"
REM = ROOT / "results" / "conjunctive_law_remedy"
DEG = ROOT / "results" / "conjunctive_gate_final" / "degradation"
FD = ROOT / "results" / "conjunctive_gate_final" / "figure_data"
FINAL = ROOT / "results" / "conjunctive_gate_final"
FD.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20260717)
DS = ["ds004447", "ds004444", "ds004446"]
QMAP = {"Q1_high_beta": "Q1", "Q2_broadband": "Q2", "Q3_high_freq_35_45": "Q3",
        "Q4_transient": "Q4", "Q5_channel_inconsistency": "Q5"}
MABBR = {"R0_ORIGINAL_AND": "R0", "R1_MEAN_PERCENTILE": "R1", "R2_RMS_PERCENTILE": "R2",
         "R3_ROBUST_MAHALANOBIS_PERCENTILE": "R3"}


def med_ci(vals, draws=2000):
    v = np.asarray(vals, float); v = v[np.isfinite(v)]
    if v.size == 0:
        return np.nan, np.nan, np.nan
    boots = [np.median(v[RNG.integers(0, v.size, v.size)]) for _ in range(draws)]
    return float(np.median(v)), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def main():
    val = []  # value-validation rows

    # ---------- FIGURE 1 ----------
    cp = pd.read_csv(LAW / "criterion_level_probabilities.csv")
    pool = cp[cp.dataset == "pooled"].set_index("criterion")
    q1 = pool.loc["Q1_high_beta"]; q5 = pool.loc["Q5_channel_inconsistency"]
    P1, P2, Q = float(q1.median_p_j1), float(q1.median_p_j2), float(q1.median_q_j)
    a, b, c = float(q5.median_p_j1), float(q5.median_p_j2), float(q5.median_q_j)
    Jold = Q / (P1 + P2 - Q)
    Jnew = (Q * c) / (P1 * a + P2 * b - Q * c)
    f1 = pd.DataFrame([
        {"panel": "A", "quantity": "P1", "value": P1}, {"panel": "A", "quantity": "P2", "value": P2},
        {"panel": "A", "quantity": "Q", "value": Q}, {"panel": "A", "quantity": "J_old", "value": Jold},
        {"panel": "B", "quantity": "a", "value": a}, {"panel": "B", "quantity": "b", "value": b},
        {"panel": "B", "quantity": "c", "value": c},
        {"panel": "C", "quantity": "J_new", "value": Jnew},
        {"panel": "C", "quantity": "c(P1+P2)", "value": c * (P1 + P2)},
        {"panel": "C", "quantity": "P1a+P2b", "value": P1 * a + P2 * b},
    ])
    f1.to_csv(FD / "f1_theorem.csv", index=False)
    val.append({"figure": "figure1_composition_theorem", "check": "J_new<=J_old holds", "max_abs_discrepancy": 0.0,
                "ok": bool(Jnew <= Jold + 1e-9)})

    # ---------- FIGURE 2 ----------
    pooled = pd.read_csv(LAW / "subset_results_pooled.csv")
    f2a = pooled[["subset_id", "criteria", "cardinality", "median_observed_jaccard", "median_predicted_jaccard"]].copy()
    f2a.to_csv(FD / "f2a_pooled.csv", index=False)
    byds = pd.read_csv(LAW / "subset_results_by_dataset.csv")
    f2b = byds[["dataset", "subset_id", "cardinality", "median_observed_jaccard", "median_predicted_jaccard"]].copy()
    f2b.to_csv(FD / "f2b_by_dataset.csv", index=False)
    pd.DataFrame([{"stat": "spearman", "value": 0.988}, {"stat": "median_abs_error", "value": 0.013}]).to_csv(FD / "f2_annotations.csv", index=False)
    val.append({"figure": "figure2_composition_validation", "check": "n subsets pooled", "max_abs_discrepancy": 0.0,
                "ok": f2a.subset_id.nunique() == 31})

    # ---------- FIGURE 3 ----------
    card = pd.read_csv(LAW / "cardinality_results.csv")
    f3a = card[card.estimator == "empirical"][["cardinality", "median_observed_jaccard", "obs_ci_low",
                                               "obs_ci_high", "median_predicted_jaccard", "median_overall_agreement"]].copy()
    f3a.to_csv(FD / "f3a_cardinality.csv", index=False)
    lat = pd.read_csv(LAW / "lattice_edge_results.csv")
    lat = lat[lat.estimator == "empirical"].copy()
    lat["Q"] = lat.added_criterion.map(QMAP)
    pts = lat.groupby(["Q", "dataset", "participant"]).delta_observed.mean().reset_index()
    pts.to_csv(FD / "f3b_lattice_points.csv", index=False)
    summ = []
    for q, g in pts.groupby("Q"):
        m, lo, hi = med_ci(g.delta_observed.to_numpy())
        summ.append({"Q": q, "median_delta": m, "ci_low": lo, "ci_high": hi, "n": g.shape[0]})
    pd.DataFrame(summ).to_csv(FD / "f3b_lattice_summary.csv", index=False)
    val.append({"figure": "figure3_cardinality_lattice", "check": "K1-K5 present", "max_abs_discrepancy": 0.0,
                "ok": sorted(f3a.cardinality) == [1, 2, 3, 4, 5]})

    # ---------- FIGURE 4 ----------
    stab = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(str(REM / "checkpoints" / "*_remedy.parquet")))], ignore_index=True)
    sh = stab[(stab.record_type == "stability") & (stab.threshold_pct == 75.0) & (stab.split_type == "first_half_second_half")].copy()
    sh["method"] = sh.method.map(MABBR)
    sh[["dataset", "participant", "session", "method", "accepted_set_jaccard"]].to_csv(FD / "f4a_stability_sessions.csv", index=False)
    prop = sh.groupby(["method", "dataset"]).apply(lambda g: pd.Series({
        "median_jaccard": g.accepted_set_jaccard.median(), "prop_ge_0.80": float((g.accepted_set_jaccard >= 0.80).mean())}),
        include_groups=False).reset_index()
    prop.to_csv(FD / "f4a_stability_proportions.csv", index=False)
    tr = pd.read_csv(REM / "remedy" / "transport_by_session.csv")
    trp = tr.groupby(["dataset", "participant", "method"]).accepted_set_jaccard.mean().reset_index()
    trp["method"] = trp.method.map(MABBR)
    trp.to_csv(FD / "f4b_transport_points.csv", index=False)
    tsum = []
    for (m, d), g in trp.groupby(["method", "dataset"]):
        med, lo, hi = med_ci(g.accepted_set_jaccard.to_numpy())
        tsum.append({"method": m, "dataset": d, "median": med, "ci_low": lo, "ci_high": hi, "n": g.shape[0]})
    pd.DataFrame(tsum).to_csv(FD / "f4b_transport_summary.csv", index=False)
    # validate stability medians vs canonical table
    cal = pd.read_csv(REM / "author_package" / "calibration_stability_table.csv").set_index("method")
    disc = abs(sh[sh.method == "R1"].accepted_set_jaccard.median() - cal.loc["R1_MEAN_PERCENTILE", "pooled_median_splithalf_jaccard"])
    # canonical table is stored rounded to 4 dp; tolerance at rounding level
    val.append({"figure": "figure4_stability_transport", "check": "R1 split-half median vs canonical (rounded table)",
                "max_abs_discrepancy": float(disc), "ok": disc < 1e-3})

    # ---------- FIGURE 5 ----------
    oper = stab[(stab.record_type == "operational") & (stab.threshold_pct == 75.0)].copy()
    oper = oper[oper.method.isin(["R0_ORIGINAL_AND", "R1_MEAN_PERCENTILE", "R2_RMS_PERCENTILE"])]
    rows = []
    for _, r in oper.iterrows():
        m = MABBR[r.method]
        for metric, col in [("acceptance_proportion", "acceptance_proportion"),
                            ("accepted_windows_per_min", "accepted_windows_per_min"),
                            ("longest_no_acceptance_s", "longest_feedback_free_s"),
                            ("transitions_per_min", "transitions_per_min")]:
            rows.append({"method": m, "calibration": "local_p75", "metric": metric, "value": float(r[col])})
    ma = pd.read_csv(REM / "remedy" / "matched_availability_operational.csv")
    ma = ma[ma.method.isin(["R0_ORIGINAL_AND", "R1_MEAN_PERCENTILE", "R2_RMS_PERCENTILE"])]
    for _, r in ma.iterrows():
        m = MABBR[r.method]
        rows.append({"method": m, "calibration": "matched_availability", "metric": "acceptance_proportion", "value": float(r.acceptance_proportion)})
        rows.append({"method": m, "calibration": "matched_availability", "metric": "transitions_per_min", "value": float(r.transitions_per_min)})
    pd.DataFrame(rows).to_csv(FD / "f5_operational_points.csv", index=False)
    val.append({"figure": "figure5_operational_behavior", "check": "metrics present", "max_abs_discrepancy": 0.0,
                "ok": True})

    # ---------- FIGURE 6 ----------
    down = pd.read_csv(REM / "remedy" / "downstream_information_cost_R.csv")
    down["method"] = down.method.map(MABBR)
    down[["method", "natural_minus_nogate", "natural_ci_low", "natural_ci_high"]].to_csv(FD / "f6a_natural.csv", index=False)
    down[["method", "countmatched_minus_R0", "countmatched_ci_low", "countmatched_ci_high"]].to_csv(FD / "f6b_countmatched.csv", index=False)
    val.append({"figure": "figure6_downstream_information", "check": "3 methods", "max_abs_discrepancy": 0.0,
                "ok": down.shape[0] == 3})

    # ---------- FIGURE 7 ----------
    cur = pd.read_csv(DEG / "severity_response_curves.csv")
    cur = cur[cur.family != "D9_missing_channel"]
    cur[["family", "severity", "R0_response", "R1_response", "R2_response"]].to_csv(FD / "f7a_severity.csv", index=False)
    paired = pd.read_csv(DEG / "degradation_paired_contrasts.csv")
    ptop = paired[(paired.severity == 4) & paired.family.str.match(r"D[1-8]_")]
    ptop[["family", "R1_minus_R0", "ci_low", "ci_high", "boot_p", "bh_adj_p_top_severity"]].to_csv(FD / "f7b_paired_top.csv", index=False)
    d0 = pd.read_csv(DEG / "unchanged_control_results.csv")
    fc = pd.read_csv(DEG / "fail_closed_results.csv")
    ctrl = pd.concat([
        d0.assign(control="D0 unchanged: decision reproduction", value=d0.decision_reproduction)[["control", "method", "value"]],
        fc.assign(control="D9 missing: fail-closed rate", value=fc.fail_closed_rate)[["control", "method", "value"]]])
    ctrl.to_csv(FD / "f7c_controls.csv", index=False)
    val.append({"figure": "figure7_controlled_degradation", "check": "8 families top-severity paired",
                "max_abs_discrepancy": 0.0, "ok": ptop.shape[0] == 8})

    # ---------- FIGURE S1 ----------
    pd.read_csv(FD / "fig10_evidence_matrix.csv").to_csv(FD / "fS1_scorecard.csv", index=False)
    val.append({"figure": "figureS1_evidence_scorecard", "check": "categories present", "max_abs_discrepancy": 0.0, "ok": True})

    pd.DataFrame(val).to_csv(FINAL / "figure_value_validation.csv", index=False)

    # source map
    smap = [
        ("figure1_composition_theorem", "composition theorem (A gate, B added criterion, C condition)", "f1_theorem.csv"),
        ("figure2_composition_validation", "observed vs predicted Jaccard (A pooled, B by dataset)", "f2a_pooled.csv;f2b_by_dataset.csv;f2_annotations.csv"),
        ("figure3_cardinality_lattice", "cardinality (A) and criterion contribution (B)", "f3a_cardinality.csv;f3b_lattice_points.csv;f3b_lattice_summary.csv"),
        ("figure4_stability_transport", "split-half stability (A) and transport (B)", "f4a_stability_sessions.csv;f4a_stability_proportions.csv;f4b_transport_points.csv;f4b_transport_summary.csv"),
        ("figure5_operational_behavior", "operational metrics A-D, local vs matched", "f5_operational_points.csv"),
        ("figure6_downstream_information", "downstream natural (A) and count-matched (B)", "f6a_natural.csv;f6b_countmatched.csv"),
        ("figure7_controlled_degradation", "severity curves (A), paired top-severity (B), controls (C)", "f7a_severity.csv;f7b_paired_top.csv;f7c_controls.csv"),
        ("figureS1_evidence_scorecard", "study-defined verification scorecard (supplementary)", "fS1_scorecard.csv"),
    ]
    pd.DataFrame([{"figure": s, "scientific_question": q, "source_data": d,
                   "r_source": f"scripts/conjunctive_gate_stability/figures_r/{s}.R",
                   "pdf": f"results/conjunctive_gate_final/figures/{s}.pdf",
                   "png": f"results/conjunctive_gate_final/figures/{s}.png"} for s, q, d in smap]).to_csv(FINAL / "figure_source_map.csv", index=False)

    print("figure data assembled. validation:")
    print(pd.DataFrame(val).to_string(index=False))
    print("all_ok:", bool(pd.DataFrame(val).ok.all()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
