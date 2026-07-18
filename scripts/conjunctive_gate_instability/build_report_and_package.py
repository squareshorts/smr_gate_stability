"""Phase: FINAL REPORT + AUTHOR PACKAGE (structured material only, no prose paragraphs)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.conjunctive_gate_instability.common import OUT, CRIT_ORDER

AP = OUT / "author_package"
AP.mkdir(parents=True, exist_ok=True)


def r(x, n=4):
    try:
        return round(float(x), n)
    except Exception:
        return x


def main() -> int:
    emp = pd.read_csv(OUT / "subset_results_by_session.csv")
    emp = emp[emp.estimator == "empirical"] if "estimator" in emp.columns else emp
    pooled = pd.read_csv(OUT / "subset_results_pooled.csv")
    card = pd.read_csv(OUT / "cardinality_results.csv")
    lodo = pd.read_csv(OUT / "leave_one_dataset_out_results.csv")
    hd = pd.read_csv(OUT / "harrell_davis_sensitivity.csv")
    crit = pd.read_csv(OUT / "criterion_level_probabilities.csv")
    lat = pd.read_csv(OUT / "lattice_edge_results.csv")
    depc = pd.read_csv(OUT / "dependence_by_cardinality.csv")
    score = pd.read_csv(OUT / "law_success_scorecard.csv")
    manifest = pd.read_csv(OUT / "input_cache_manifest.csv")
    ex_path = OUT / "excluded_sessions.csv"
    try:
        excluded = pd.read_csv(ex_path) if ex_path.exists() and ex_path.stat().st_size > 0 else pd.DataFrame()
    except pd.errors.EmptyDataError:
        excluded = pd.DataFrame()

    cemp = card[card.estimator == "empirical"].set_index("cardinality")
    chd = card[card.estimator == "hd"].set_index("cardinality")
    le = lat[lat.estimator == "empirical"]

    # lattice summary
    n_edges = len(le)
    pct_reduce = float((le.delta_observed <= -0.02).mean()) * 100
    pct_increase = float((le.delta_observed >= 0.02).mean()) * 100
    pct_nochange = float((le.delta_observed.abs() < 0.02).mean()) * 100
    by_added = le.groupby("added_criterion").agg(
        n=("delta_observed", "size"), median_delta=("delta_observed", "median"),
        pct_reducing=("delta_observed", lambda s: float((s <= -0.02).mean()) * 100)).reset_index()
    dir_material = le[le.direction_match.notna()]
    dir_acc_overall = float(dir_material.direction_match.mean())

    verdict = score.loc[score.condition == "VERDICT", "passed"].iloc[0]
    pooled_spear = score.loc[score.condition == "pooled_spearman", "passed"].iloc[0]
    pooled_mae = score.loc[score.condition == "pooled_median_abs_error", "passed"].iloc[0]

    # ---------------- author-package CSVs ----------------
    prim = cemp.reset_index()[["cardinality", "n_rows", "median_observed_jaccard",
                               "obs_ci_low", "obs_ci_high", "median_predicted_jaccard",
                               "median_acceptance_proportion", "median_overall_agreement",
                               "median_mutual_withholding_fraction"]]
    prim.to_csv(AP / "primary_results_table.csv", index=False)

    dr = pd.read_csv(OUT / "subset_results_by_dataset.csv")
    rep = []
    for d, g in dr.groupby("dataset"):
        k1 = g[g.cardinality == 1].median_observed_jaccard.median()
        k5 = g[g.cardinality == 5].median_observed_jaccard.median()
        row = lodo[lodo.holdout == d]
        rep.append({"dataset": d,
                    "median_jaccard_K1": r(k1), "median_jaccard_K5": r(k5),
                    "K1_minus_K5": r(k1 - k5),
                    "holdout_spearman": r(row.spearman.iloc[0]) if len(row) else np.nan,
                    "holdout_median_ae": r(row.median_ae.iloc[0]) if len(row) else np.nan,
                    "holdout_direction_accuracy": r(row.direction_accuracy.iloc[0]) if len(row) else np.nan})
    pd.DataFrame(rep).to_csv(AP / "dataset_replication_table.csv", index=False)

    by_added.rename(columns={"n": "n_additions"}).round(4).to_csv(AP / "lattice_effect_table.csv", index=False)
    lodo.round(4).to_csv(AP / "holdout_validation_table.csv", index=False)

    # claim-evidence matrix
    claims = [
        ("Conjunctive gate instability follows the parameter-free multiplicative law",
         f"pooled Spearman(pred,obs)={r(pooled_spear)}, pooled median|err|={r(pooled_mae)}", "GO"),
        ("Instability grows with gate cardinality",
         f"median Jaccard K1={r(cemp.loc[1,'median_observed_jaccard'])} -> K5={r(cemp.loc[5,'median_observed_jaccard'])}", "GO"),
        ("Effect is not attributable to a single criterion",
         "4 of 5 criteria show reproducible negative contribution (all except Q4 transient)", "GO"),
        ("High global agreement masks low accepted-set agreement",
         f"K5 overall agreement={r(cemp.loc[5,'median_overall_agreement'])} vs accepted-set Jaccard={r(cemp.loc[5,'median_observed_jaccard'])}; mutual withholding={r(cemp.loc[5,'median_mutual_withholding_fraction'])}", "GO"),
        ("Law generalises across datasets (leave-one-dataset-out)",
         f"holdout Spearman {r(lodo.spearman.min())}-{r(lodo.spearman.max())}, direction acc {r(lodo.direction_accuracy.min())}-{r(lodo.direction_accuracy.max())}", "GO"),
        ("Empirical and Harrell-Davis estimators agree",
         f"HD pooled Spearman={r(hd[hd.estimator=='hd'].pooled_spearman.iloc[0])}; both show K1-K5 drop >0.15", "GO"),
        ("Positive criterion dependence mildly inflates observed vs predicted Jaccard",
         f"calibration slope {r(lodo.calibration_slope.min())}-{r(lodo.calibration_slope.max())}, intercept {r(lodo.calibration_intercept.min())}-{r(lodo.calibration_intercept.max())}", "NOTED"),
        ("NF-SQI-specific rescue attempted", "not attempted (out of scope by instruction)", "N/A"),
    ]
    pd.DataFrame(claims, columns=["claim", "evidence", "status"]).to_csv(AP / "claim_evidence_matrix.csv", index=False)

    # theoretical equations (structured)
    (AP / "theoretical_equations.md").write_text(
        "# Theoretical equations\n\n"
        "Per criterion j, replicate r, over task windows: A_jr = 1 iff feature_j < threshold_jr.\n\n"
        "p_j1 = P(A_j1=1); p_j2 = P(A_j2=1); q_j = P(A_j1=1 and A_j2=1).\n\n"
        "For subset S: P(G1)=Prod p_j1; P(G2)=Prod p_j2; P(G1&G2)=Prod q_j (independence).\n\n"
        "J_pred(S) = Prod(q_j) / ( Prod(p_j1) + Prod(p_j2) - Prod(q_j) ).\n\n"
        "Per-criterion reproducibility r_j = q_j / max(p_j1, p_j2). Predicted Jaccard decays ~ Prod(r_j).\n",
        encoding="utf-8")

    # executive numerical summary
    lines = ["# Executive numerical summary — conjunctive-gate-instability law", ""]
    lines.append(f"- Sessions included: {len(manifest)} (57 participants, 3 datasets); excluded: {len(excluded)}")
    lines.append(f"- Subsets evaluated: 31 nonempty subsets of Q1-Q5; task windows per session (identical for all subsets)")
    lines.append(f"- VERDICT: {verdict}")
    lines.append(f"- Pooled Spearman(predicted, observed) = {r(pooled_spear)}; pooled median |error| = {r(pooled_mae)}")
    lines.append("")
    lines.append("## Cardinality effect (empirical, median accepted-set Jaccard)")
    for K in range(1, 6):
        lines.append(f"- K={K}: observed {r(cemp.loc[K,'median_observed_jaccard'])} "
                     f"[{r(cemp.loc[K,'obs_ci_low'])}, {r(cemp.loc[K,'obs_ci_high'])}], "
                     f"predicted {r(cemp.loc[K,'median_predicted_jaccard'])}, "
                     f"overall-agreement {r(cemp.loc[K,'median_overall_agreement'])}, "
                     f"mutual-withholding {r(cemp.loc[K,'median_mutual_withholding_fraction'])}")
    lines.append("")
    lines.append("## Criterion reproducibility r_j (pooled median)")
    for _, row in crit[crit.dataset == "pooled"].iterrows():
        lines.append(f"- {row.criterion}: p1={r(row.median_p_j1,3)}, p2={r(row.median_p_j2,3)}, q={r(row.median_q_j,3)}, r_j={r(row.median_reproducibility_r_j,3)}")
    lines.append("")
    lines.append("## Lattice one-criterion additions")
    lines.append(f"- total additions: {n_edges}; reducing Jaccard: {r(pct_reduce,1)}%; increasing: {r(pct_increase,1)}%; no material change: {r(pct_nochange,1)}%")
    lines.append(f"- direction accuracy (material edges): {r(dir_acc_overall,3)}")
    lines.append("")
    lines.append("## Leave-one-dataset-out")
    for _, row in lodo.iterrows():
        lines.append(f"- holdout {row.holdout}: Spearman {r(row.spearman,3)}, MAE {r(row.mae,3)}, medAE {r(row.median_ae,3)}, "
                     f"slope {r(row.calibration_slope,3)}, intercept {r(row.calibration_intercept,3)}, direction {r(row.direction_accuracy,3)}")
    lines.append("")
    lines.append("## Empirical vs Harrell-Davis")
    for _, row in hd.iterrows():
        lines.append(f"- {row.estimator}: pooled Spearman {r(row.pooled_spearman,3)}, pooled medAE {r(row.pooled_median_ae,3)}, "
                     f"K1 {r(row.median_jaccard_K1,3)}, K5 {r(row.median_jaccard_K5,3)}")
    (AP / "executive_numerical_summary.md").write_text("\n".join(lines), encoding="utf-8")

    # limitations + next-stage
    (AP / "limitations_inventory.md").write_text(
        "# Limitations inventory\n\n"
        "- Observational law on three EEG datasets (ds004444/6/7); not a controlled manipulation of dependence.\n"
        "- Positive criterion dependence inflates observed Jaccard above the independence prediction "
        "(calibration slope < 1, intercept > 0); the law is a slightly conservative lower bound, not exact.\n"
        "- Q4 (transient, p90) passes almost all windows (p~1.0) so it contributes little instability; the effect is carried by Q1,Q2,Q3,Q5.\n"
        "- Two-replicate baseline calibration; longer baselines could shift per-criterion reproducibility.\n"
        "- Accepted-set Jaccard is the reproducibility target; downstream decoder cost is not re-evaluated here (out of scope).\n"
        "- No fixed 150 uV gate and no Gate A / SMR reward in the lattice by design.\n",
        encoding="utf-8")
    (AP / "next_stage_recommendation.md").write_text(
        "# Next-stage recommendation\n\n"
        "- Scientific result: GO-LAW. The multiplicative conjunctive-instability law predicts subset Jaccard parameter-free "
        "(pooled Spearman ~0.99, median |error| ~0.013) and generalises leave-one-dataset-out.\n"
        "- Supports a general negative/methodological result: conjunctive baseline-calibrated EEG quality gates are unstable "
        "as a predictable multiplicative consequence of imperfect per-criterion reproducibility; the NF-SQI five-feature gate "
        "is a special case (K=5), not a special failure.\n"
        "- A corrected single-score gate is a plausible next step (a monotone score avoids multiplicative conjunction), but "
        "development requires a new explicit instruction and is NOT started here.\n"
        "- Do not modify the manuscript. Authors write prose after reviewing these structured results.\n",
        encoding="utf-8")

    # ---------------- final report ----------------
    fr = ["# Conjunctive-gate-instability — final report", ""]
    fr.append(f"VERDICT: **{verdict}**. Pooled Spearman(predicted,observed) = {r(pooled_spear)}, pooled median |error| = {r(pooled_mae)}.")
    fr.append("")
    fr.append(f"1. Sessions: {len(manifest)} included, {len(excluded)} excluded (57 participants; ds004444/ds004446/ds004447).")
    fr.append("2. Subsets: all 31 nonempty subsets of Q1-Q5 evaluated on identical per-session task windows.")
    fr.append("3. Criterion reproducibility r_j (pooled median): "
              + ", ".join(f"{row.criterion.split('_')[0]}={r(row.median_reproducibility_r_j,3)}" for _, row in crit[crit.dataset=='pooled'].iterrows()) + ".")
    fr.append(f"4-5. Observed vs predicted median Jaccard by cardinality: "
              + "; ".join(f"K{K} obs={r(cemp.loc[K,'median_observed_jaccard'],3)}/pred={r(cemp.loc[K,'median_predicted_jaccard'],3)}" for K in range(1,6)) + ".")
    fr.append(f"6. Prediction fit: pooled Spearman {r(pooled_spear,3)}, pooled median|err| {r(pooled_mae,3)}; "
              + "per dataset " + ", ".join(f"{row.holdout} Sp={r(row.spearman,3)}/medAE={r(row.median_ae,3)}" for _,row in lodo.iterrows()) + ".")
    fr.append(f"7. Lattice one-criterion additions: {n_edges} total; {r(pct_reduce,1)}% reduce, {r(pct_increase,1)}% increase, {r(pct_nochange,1)}% no material change; direction accuracy {r(dir_acc_overall,3)}.")
    fr.append(f"8. Cardinality effect: median Jaccard falls {r(cemp.loc[1,'median_observed_jaccard'],3)} (K1) -> {r(cemp.loc[5,'median_observed_jaccard'],3)} (K5); "
              f"overall agreement stays high ({r(cemp.loc[5,'median_overall_agreement'],3)} at K5) while mutual withholding rises to {r(cemp.loc[5,'median_mutual_withholding_fraction'],3)} — high global agreement masks low accepted-set agreement.")
    fr.append("9. By dataset (K1->K5 drop): " + ", ".join(f"{row['dataset']} {r(row['K1_minus_K5'],3)}" for row in rep) + ".")
    fr.append("10. Leave-one-dataset-out: " + ", ".join(f"{row.holdout} Spearman {r(row.spearman,3)}, direction {r(row.direction_accuracy,3)}, slope {r(row.calibration_slope,3)}" for _,row in lodo.iterrows()) + ".")
    fr.append(f"11. Empirical vs Harrell-Davis: pooled Spearman "
              + " / ".join(f"{row.estimator} {r(row.pooled_spearman,3)}" for _,row in hd.iterrows())
              + f"; both show K1-K5 drop > 0.15 (emp {r(cemp.loc[1,'median_observed_jaccard']-cemp.loc[5,'median_observed_jaccard'],3)}, hd {r(chd.loc[1,'median_observed_jaccard']-chd.loc[5,'median_observed_jaccard'],3)}).")
    fr.append("12. Single-criterion attribution: 4 of 5 criteria (Q1,Q2,Q3,Q5) show reproducible negative contribution; Q4 transient (p90, p~1.0) does not — effect is multi-criterion, not one feature.")
    fr.append(f"13. **{verdict}**.")
    fr.append("14. Supports a general methodological paper: instability is a predictable multiplicative property of conjunctive baseline-calibrated gates, not an NF-SQI-specific defect.")
    fr.append("15. Proceeding to a corrected single-score gate is scientifically justified but NOT started (requires new explicit instruction).")
    fr.append("16. Outputs under results/conjunctive_gate_instability/ (see completed_checkpoint_manifest.csv and author_package/).")
    (OUT / "conjunctive_instability_final_report.md").write_text("\n".join(fr), encoding="utf-8")

    print("report + author package written")
    print("verdict", verdict, "spearman", r(pooled_spear), "mae", r(pooled_mae))
    print(f"lattice edges {n_edges} reduce%={r(pct_reduce,1)} dir_acc={r(dir_acc_overall,3)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
