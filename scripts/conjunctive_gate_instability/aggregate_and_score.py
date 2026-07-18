"""Phase: AGGREGATION + FROZEN SCORING.

Reads per-session parquet checkpoints and produces all result tables, the
leave-one-dataset-out validation, the Harrell-Davis sensitivity, and the frozen
GO/PARTIAL/NO-GO scorecard. Purely aggregation over verified checkpoints.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.conjunctive_gate_instability.common import CKPT, OUT, CRIT_ORDER

RNG = np.random.default_rng(20260717)
MATERIAL = 0.02
DATASETS = ["ds004444", "ds004446", "ds004447"]


def load_all() -> pd.DataFrame:
    frames = [pd.read_parquet(p) for p in sorted(CKPT.glob("*.parquet"))]
    return pd.concat(frames, ignore_index=True)


def grouped_median_ci(df: pd.DataFrame, value: str, draws: int = 400):
    """Participant-grouped bootstrap CI for the median of `value`."""
    d = df.dropna(subset=[value])
    if d.empty:
        return (np.nan, np.nan, np.nan)
    groups = [g[value].to_numpy() for _, g in d.groupby(["dataset", "participant"])]
    med = float(np.median(d[value]))
    boots = []
    n = len(groups)
    for _ in range(draws):
        idx = RNG.integers(0, n, n)
        pooled = np.concatenate([groups[i] for i in idx])
        boots.append(np.median(pooled))
    return med, float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def logit(x, eps=1e-6):
    x = np.clip(x, eps, 1 - eps)
    return np.log(x / (1 - x))


# --------------------------------------------------------------------------
def main() -> int:
    allrows = load_all()
    sub = allrows[allrows.record_type == "subset"].copy()
    crit = allrows[allrows.record_type == "criterion"].copy()
    pair = allrows[allrows.record_type == "pair"].copy()

    emp = sub[sub.estimator == "empirical"].copy()
    hd = sub[sub.estimator == "hd"].copy()

    # 1. subset_results_by_session --------------------------------------
    emp.to_csv(OUT / "subset_results_by_session.csv", index=False)

    # by_subject / by_dataset / pooled (empirical)
    def summarize(group_cols, name, ci=True):
        recs = []
        for keys, g in emp.groupby(group_cols):
            keys = keys if isinstance(keys, tuple) else (keys,)
            if ci:
                med_o, lo_o, hi_o = grouped_median_ci(g, "observed_jaccard")
                med_p, lo_p, hi_p = grouped_median_ci(g, "predicted_jaccard")
            else:
                med_o = float(g["observed_jaccard"].median()); lo_o = hi_o = np.nan
                med_p = float(g["predicted_jaccard"].median()); lo_p = hi_p = np.nan
            rec = dict(zip(group_cols, keys))
            rec.update({
                "n_rows": len(g),
                "median_observed_jaccard": med_o, "obs_ci_low": lo_o, "obs_ci_high": hi_o,
                "median_predicted_jaccard": med_p, "pred_ci_low": lo_p, "pred_ci_high": hi_p,
                "median_residual": float(np.median(g["residual"])),
                "median_abs_error": float(np.median(np.abs(g["residual"]))),
            })
            recs.append(rec)
        pd.DataFrame(recs).to_csv(OUT / name, index=False)

    summarize(["participant", "dataset", "subset_id", "criteria", "cardinality"], "subset_results_by_subject.csv", ci=False)
    summarize(["dataset", "subset_id", "criteria", "cardinality"], "subset_results_by_dataset.csv")
    summarize(["subset_id", "criteria", "cardinality"], "subset_results_pooled.csv")

    # 2. criterion_level_probabilities ----------------------------------
    cemp = crit[crit.estimator == "empirical"]
    crecs = []
    for keys, g in cemp.groupby(["dataset", "criterion"]):
        crecs.append({"dataset": keys[0], "criterion": keys[1],
                      "median_p_j1": float(g.p_j1.median()), "median_p_j2": float(g.p_j2.median()),
                      "median_q_j": float(g.q_j.median()), "median_reproducibility_r_j": float(g.reproducibility_r_j.median()),
                      "n_sessions": len(g)})
    for keys, g in cemp.groupby(["criterion"]):
        crit_name = keys[0] if isinstance(keys, tuple) else keys
        crecs.append({"dataset": "pooled", "criterion": crit_name,
                      "median_p_j1": float(g.p_j1.median()), "median_p_j2": float(g.p_j2.median()),
                      "median_q_j": float(g.q_j.median()), "median_reproducibility_r_j": float(g.reproducibility_r_j.median()),
                      "n_sessions": len(g)})
    pd.DataFrame(crecs).to_csv(OUT / "criterion_level_probabilities.csv", index=False)

    # gate_subset_definitions (mirror frozen, with pooled medians)
    emp.groupby(["subset_id", "criteria", "cardinality"]).size().reset_index(name="n_sessions").to_csv(
        OUT / "gate_subset_definitions.csv", index=False)

    # 3. lattice_edge_results -------------------------------------------
    # build per (session,estimator) subset -> jaccard lookup
    lat = []
    subsets_by_card = {}
    idx = {}
    for (sid, crits, card), _g in emp.groupby(["subset_id", "criteria", "cardinality"]):
        subsets_by_card.setdefault(card, []).append((sid, tuple(crits.split("+"))))
    # map criteria-set -> subset_id
    setmap = {frozenset(c.split("+")): sid for sid, c in emp[["subset_id", "criteria"]].drop_duplicates().itertuples(index=False)}
    for estimator, block in (("empirical", emp), ("hd", hd)):
        look = {(r.session_key, r.subset_id): r for r in block.itertuples(index=False)}
        crit_look = {(r.session_key, r.criterion): r for r in crit[crit.estimator == estimator].itertuples(index=False)}
        for r in block.itertuples(index=False):
            cur = set(r.criteria.split("+"))
            for j in CRIT_ORDER:
                if j in cur:
                    continue
                nxt = frozenset(cur | {j})
                sid2 = setmap.get(nxt)
                if sid2 is None:
                    continue
                r2 = look.get((r.session_key, sid2))
                if r2 is None:
                    continue
                dobs = r2.observed_jaccard - r.observed_jaccard
                dpred = r2.predicted_jaccard - r.predicted_jaccard
                cj = crit_look.get((r.session_key, j))
                lat.append({
                    "session_key": r.session_key, "dataset": r.dataset, "participant": r.participant,
                    "estimator": estimator, "from_subset": r.subset_id, "to_subset": sid2,
                    "added_criterion": j, "from_cardinality": r.cardinality,
                    "jaccard_before": r.observed_jaccard, "jaccard_after": r2.observed_jaccard,
                    "delta_observed": dobs, "delta_predicted": dpred,
                    "acceptance_change": r2.obs_accept_g1 - r.obs_accept_g1,
                    "added_criterion_reproducible": bool(cj.reproducibility_r_j >= 0.999) if cj else False,
                    "direction_match": bool(np.sign(dobs) == np.sign(dpred)) if (abs(dobs) >= MATERIAL or abs(dpred) >= MATERIAL) else np.nan,
                    "material": bool(abs(dobs) >= MATERIAL),
                    "predicted_decrease": bool(dpred < 0),
                    "observed_decrease": bool(dobs < 0),
                })
    latdf = pd.DataFrame(lat)
    latdf.to_csv(OUT / "lattice_edge_results.csv", index=False)

    # 4. cardinality_results --------------------------------------------
    crecs = []
    for estimator, block in (("empirical", emp), ("hd", hd)):
        for K in range(1, 6):
            g = block[block.cardinality == K]
            med_o, lo_o, hi_o = grouped_median_ci(g, "observed_jaccard")
            med_p, _, _ = grouped_median_ci(g, "predicted_jaccard")
            crecs.append({
                "estimator": estimator, "cardinality": K, "n_rows": len(g),
                "median_observed_jaccard": med_o, "obs_ci_low": lo_o, "obs_ci_high": hi_o,
                "median_predicted_jaccard": med_p,
                "median_acceptance_proportion": float(np.median((g.obs_accept_g1 + g.obs_accept_g2) / 2)),
                "median_overall_agreement": float(g.overall_agreement.median()),
                "median_positive_agreement": float(g.positive_agreement.median()),
                "median_negative_agreement": float(g.negative_agreement.median()),
                "median_acceptance_flips": float(g.acceptance_flips.median()),
                "median_mutual_withholding_fraction": float(g.mutual_withholding_fraction.median()),
            })
    pd.DataFrame(crecs).to_csv(OUT / "cardinality_results.csv", index=False)

    # 5. dependence_analysis --------------------------------------------
    prc = pair[pair.estimator == "empirical"]
    depp = []
    for keys, g in prc.groupby(["criterion_a", "criterion_b"]):
        depp.append({"criterion_a": keys[0], "criterion_b": keys[1],
                     "median_feature_corr": float(g.feature_corr.median()),
                     "median_passind_corr": float(g.passind_corr.median())})
    dep_pairs = pd.DataFrame(depp)
    dep_card = emp.groupby("cardinality").agg(
        median_obs_joint=("obs_joint_accept", "median"),
        median_pred_joint=("pred_joint_accept", "median"),
        median_dependence_ratio=("dependence_ratio", "median"),
        median_residual=("residual", "median"),
        median_abs_residual=("residual", lambda s: float(np.median(np.abs(s)))),
        median_mean_abs_feature_corr=("mean_abs_pairwise_feature_corr", "median"),
    ).reset_index()
    dep_pairs.to_csv(OUT / "dependence_analysis.csv", index=False)
    dep_card.to_csv(OUT / "dependence_by_cardinality.csv", index=False)

    # prediction_residuals ----------------------------------------------
    emp[["session_key", "dataset", "participant", "subset_id", "criteria", "cardinality",
         "observed_jaccard", "predicted_jaccard", "residual", "dependence_ratio",
         "mean_abs_pairwise_feature_corr"]].to_csv(OUT / "prediction_residuals.csv", index=False)

    # 6. leave_one_dataset_out ------------------------------------------
    lodo = []
    for holdout in DATASETS:
        dev = emp[emp.dataset != holdout]
        test = emp[emp.dataset == holdout]
        o, p = test.observed_jaccard.to_numpy(), test.predicted_jaccard.to_numpy()
        sp = spearmanr(p, o).statistic
        pr = pearsonr(p, o).statistic
        mae = float(np.mean(np.abs(o - p)))
        medae = float(np.median(np.abs(o - p)))
        slope, intercept = np.polyfit(p, o, 1)
        # rank ordering of subsets (subset-median obs vs pred)
        sm = test.groupby("subset_id").agg(o=("observed_jaccard", "median"), p=("predicted_jaccard", "median"))
        rank_sp = spearmanr(sm.p, sm.o).statistic
        # direction accuracy on material one-criterion additions in holdout
        le = latdf[(latdf.estimator == "empirical") & (latdf.dataset == holdout) & (latdf.direction_match.notna())]
        dir_acc = float(le.direction_match.mean()) if len(le) else np.nan
        # optional linear dependence correction (fit on dev, apply to holdout)
        Xdev = np.column_stack([logit(dev.predicted_jaccard), dev.mean_abs_pairwise_feature_corr])
        Xdev = np.column_stack([np.ones(len(Xdev)), Xdev])
        ydev = logit(dev.observed_jaccard)
        beta, *_ = np.linalg.lstsq(Xdev, ydev, rcond=None)
        Xte = np.column_stack([np.ones(len(test)), logit(test.predicted_jaccard), test.mean_abs_pairwise_feature_corr])
        corr_pred = 1 / (1 + np.exp(-(Xte @ beta)))
        mae_corr = float(np.mean(np.abs(o - corr_pred)))
        lodo.append({"holdout": holdout, "n_test_rows": len(test),
                     "spearman": sp, "pearson": pr, "mae": mae, "median_ae": medae,
                     "calibration_slope": float(slope), "calibration_intercept": float(intercept),
                     "subset_rank_spearman": rank_sp, "direction_accuracy": dir_acc,
                     "corrected_mae": mae_corr,
                     "correction_beta0": float(beta[0]), "correction_beta_logitpred": float(beta[1]),
                     "correction_beta_corr": float(beta[2])})
    lodo_df = pd.DataFrame(lodo)
    lodo_df.to_csv(OUT / "leave_one_dataset_out_results.csv", index=False)

    # 7. harrell_davis_sensitivity --------------------------------------
    hdrows = []
    for estimator, block in (("empirical", emp), ("hd", hd)):
        o, p = block.observed_jaccard.to_numpy(), block.predicted_jaccard.to_numpy()
        hdrows.append({"estimator": estimator, "pooled_spearman": spearmanr(p, o).statistic,
                       "pooled_mae": float(np.mean(np.abs(o - p))), "pooled_median_ae": float(np.median(np.abs(o - p))),
                       "median_jaccard_K1": float(block[block.cardinality == 1].observed_jaccard.median()),
                       "median_jaccard_K5": float(block[block.cardinality == 5].observed_jaccard.median())})
    hd_df = pd.DataFrame(hdrows)
    hd_df.to_csv(OUT / "harrell_davis_sensitivity.csv", index=False)

    # ---- FROZEN SCORECARD ----------------------------------------------
    o, p = emp.observed_jaccard.to_numpy(), emp.predicted_jaccard.to_numpy()
    pooled_spearman = spearmanr(p, o).statistic
    pooled_mae = float(np.median(np.abs(o - p)))
    ds_spear, ds_mae = {}, {}
    for d in DATASETS:
        b = emp[emp.dataset == d]
        ds_spear[d] = spearmanr(b.predicted_jaccard, b.observed_jaccard).statistic
        ds_mae[d] = float(np.median(np.abs(b.observed_jaccard - b.predicted_jaccard)))

    le = latdf[latdf.estimator == "empirical"]
    pred_dec = le[le.predicted_decrease]
    cond5 = float((pred_dec.observed_decrease).mean())

    # cardinality drop per dataset
    cond6_ok = True
    card_drop = {}
    for d in DATASETS:
        b = emp[emp.dataset == d]
        m1 = b[b.cardinality == 1].observed_jaccard.median()
        m5 = b[b.cardinality == 5].observed_jaccard.median()
        card_drop[d] = float(m1 - m5)
        if not (m1 - m5 >= 0.15):
            cond6_ok = False

    # cond7: >=3 criteria with reproducible negative contribution on >=1 lower subset
    neg_contrib = {}
    for j in CRIT_ORDER:
        ej = le[(le.added_criterion == j)]
        # reproducible negative contribution: median observed delta < 0 and materially so on at least one from-subset
        by_from = ej.groupby("from_subset").delta_observed.median()
        neg_contrib[j] = bool((by_from <= -MATERIAL).any())
    cond7_count = sum(neg_contrib.values())

    # cond8 LODO direction accuracy per dataset
    cond8_ok = all((lodo_df.set_index("holdout").direction_accuracy >= 0.75).values)

    # cond9 empirical vs HD qualitative agreement: both show K5<<K1 and positive spearman
    emp_drop = emp[emp.cardinality == 1].observed_jaccard.median() - emp[emp.cardinality == 5].observed_jaccard.median()
    hd_drop = hd[hd.cardinality == 1].observed_jaccard.median() - hd[hd.cardinality == 5].observed_jaccard.median()
    cond9_ok = (emp_drop > 0.15) and (hd_drop > 0.15) and (hd_df.pooled_spearman > 0).all()

    conds = {
        "C1_pooled_spearman_ge_0.80": pooled_spearman >= 0.80,
        "C2_each_dataset_spearman_ge_0.70": all(v >= 0.70 for v in ds_spear.values()),
        "C3_pooled_median_ae_le_0.05": pooled_mae <= 0.05,
        "C4_dataset_median_ae_le_0.08": all(v <= 0.08 for v in ds_mae.values()),
        "C5_pred_decrease_direction_ge_0.80": cond5 >= 0.80,
        "C6_K5_at_least_0.15_below_K1_each_dataset": cond6_ok,
        "C7_at_least_3_criteria_negative": cond7_count >= 3,
        "C8_lodo_direction_ge_0.75_each": bool(cond8_ok),
        "C9_empirical_hd_agree": bool(cond9_ok),
    }
    core_pass = all(conds[c] for c in list(conds)[:6])
    if not core_pass:
        verdict = "NO-GO-LAW"
    elif all(conds.values()):
        verdict = "GO-LAW"
    else:
        verdict = "PARTIAL-LAW"

    score_rows = [{"condition": k, "passed": bool(v)} for k, v in conds.items()]
    score_rows += [
        {"condition": "pooled_spearman", "passed": round(float(pooled_spearman), 4)},
        {"condition": "pooled_median_abs_error", "passed": round(pooled_mae, 4)},
        {"condition": "dataset_spearman", "passed": str({k: round(v, 3) for k, v in ds_spear.items()})},
        {"condition": "dataset_median_abs_error", "passed": str({k: round(v, 3) for k, v in ds_mae.items()})},
        {"condition": "cond5_pred_decrease_direction_frac", "passed": round(cond5, 4)},
        {"condition": "cardinality_drop_by_dataset", "passed": str({k: round(v, 3) for k, v in card_drop.items()})},
        {"condition": "cond7_negative_criteria", "passed": str({k: neg_contrib[k] for k in CRIT_ORDER}) + f" count={cond7_count}"},
        {"condition": "lodo_direction_accuracy", "passed": str({r.holdout: round(r.direction_accuracy, 3) for r in lodo_df.itertuples()})},
        {"condition": "empirical_K1_minus_K5", "passed": round(float(emp_drop), 4)},
        {"condition": "hd_K1_minus_K5", "passed": round(float(hd_drop), 4)},
        {"condition": "VERDICT", "passed": verdict},
    ]
    pd.DataFrame(score_rows).to_csv(OUT / "law_success_scorecard.csv", index=False)

    print("VERDICT:", verdict)
    print("pooled_spearman=%.4f pooled_median_ae=%.4f" % (pooled_spearman, pooled_mae))
    print("dataset_spearman:", {k: round(v, 3) for k, v in ds_spear.items()})
    print("dataset_median_ae:", {k: round(v, 3) for k, v in ds_mae.items()})
    print("cond5 pred-decrease direction:", round(cond5, 4))
    print("cardinality drop:", {k: round(v, 3) for k, v in card_drop.items()})
    print("cond7 negative criteria:", neg_contrib, "count", cond7_count)
    print("K1/K5 empirical:", round(emp[emp.cardinality==1].observed_jaccard.median(),4), round(emp[emp.cardinality==5].observed_jaccard.median(),4))
    print("conds:", conds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
