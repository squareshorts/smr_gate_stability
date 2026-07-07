"""
Task 1 – Gate A harmonisation analysis.
Runs SMR-SNR primary and SMR-power sensitivity variants for
ds004447, ds004444, and ds004446 from existing feature CSVs.

Outputs (all in results/submission_readiness/):
  snr_primary_replication_table.csv
  snr_primary_summary.md
  power_sensitivity_replication_table.csv
  power_sensitivity_summary.md
  predictions/<dataset>_<model>_<variant>_predictions.csv
  snr_primary_bootstrap_ci.csv
  power_sensitivity_bootstrap_ci.csv
"""

import os, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import median_abs_deviation
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[2]
OUT  = ROOT / "results" / "submission_readiness"
PRED = OUT / "predictions"
PRED.mkdir(parents=True, exist_ok=True)

SEED = 20260702
N_BOOT = 5000

DATASET_FEAT_PATHS = {
    "ds004447": ROOT / "outputs/tables/nf_sqi_window_features.csv",
    "ds004444": ROOT / "outputs/replication_tables/ds004444_window_features.csv",
    "ds004446": ROOT / "outputs/replication_tables/ds004446_window_features.csv",
}

MODELS = {
    "Broadband_Noise_Floor_Only":         ["broadband_power", "noise_floor_power"],
    "High_Beta_Only":                      ["high_beta_power"],
    "Broadband_Noise_Floor_+_High_Beta":  ["broadband_power", "noise_floor_power", "high_beta_power"],
    "Full_NF-SQI":                         ["broadband_power", "noise_floor_power", "high_beta_power",
                                            "transient_score", "channel_inconsistency", "nonstationarity"],
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def compute_thresholds(df_rest, features_p75, features_p90=None):
    """Compute per-(subject, session) percentile thresholds from rest rows."""
    thr = {}
    for (sub, ses), grp in df_rest.groupby(["subject", "session"]):
        t = {}
        for feat in features_p75:
            vals = grp[feat].dropna()
            t[feat] = np.percentile(vals, 75) if len(vals) >= 3 else np.nan
        if features_p90:
            for feat in features_p90:
                vals = grp[feat].dropna()
                t[feat + "_p90"] = np.percentile(vals, 90) if len(vals) >= 3 else np.nan
        thr[(sub, ses)] = t
    return thr


def apply_thresh(df, feat, thr_dict, key=None, op=">"):
    key = key or feat
    result = np.full(len(df), False)
    for (sub, ses), t in thr_dict.items():
        mask = (df["subject"] == sub) & (df["session"] == ses)
        v = t.get(key, np.nan)
        if np.isnan(v):
            continue
        idx = df.index[mask]
        if op == ">":
            result[df.index.get_indexer(idx)] = df.loc[idx, feat] > v
        else:
            result[df.index.get_indexer(idx)] = df.loc[idx, feat] < v
    return result.astype(bool)


def build_labeled(df_full, gate_a_feat, dataset_id):
    """Gate pipeline + contamination flags from a feature dataframe."""
    if "window_size" in df_full.columns:
        df = df_full[df_full["window_size"] == 1.0].copy().reset_index(drop=True)
    else:
        df = df_full.copy().reset_index(drop=True)

    df_rest = df[df["condition"] == "rest"]
    df_task = df[df["condition"] == "task"].copy().reset_index(drop=True)

    p75_feats = [gate_a_feat, "high_beta_power", "broadband_power",
                 "noise_floor_power", "channel_inconsistency"]
    thr = compute_thresholds(df_rest, p75_feats, features_p90=["transient_score"])

    # Gate A
    df_task["gate_A"] = apply_thresh(df_task, gate_a_feat, thr, key=gate_a_feat, op=">")

    # Contamination flags (independent of Gate A scalar)
    df_task["is_hb_contam"]       = apply_thresh(df_task, "high_beta_power",       thr, key="high_beta_power",       op=">")
    df_task["is_bb_contam"]       = apply_thresh(df_task, "broadband_power",        thr, key="broadband_power",        op=">")
    df_task["is_noise_contam"]    = apply_thresh(df_task, "noise_floor_power",       thr, key="noise_floor_power",       op=">")
    df_task["is_transient_contam"]= apply_thresh(df_task, "transient_score",         thr, key="transient_score_p90",    op=">")
    df_task["is_ch_inc_contam"]   = apply_thresh(df_task, "channel_inconsistency",   thr, key="channel_inconsistency",   op=">")

    df_task["is_contaminated"] = (
        df_task["is_bb_contam"] | df_task["is_noise_contam"] |
        df_task["is_transient_contam"] | df_task["is_ch_inc_contam"]
    )
    # Gate B: Gate A + HB ok
    df_task["gate_B"] = df_task["gate_A"] & (~df_task["is_hb_contam"])
    # Gate C: Gate B + no contamination
    df_task["gate_C"] = df_task["gate_B"] & (~df_task["is_contaminated"])

    return df_task


def contamination_overlap(df_task):
    """Aggregate contamination-overlap table (per subject/session)."""
    rows = []
    cands = df_task[df_task["gate_A"]].copy()
    for (sub, ses), grp in cands.groupby(["subject", "session"]):
        total = len(grp)
        if total == 0:
            continue
        bbnf = grp["is_bb_contam"] | grp["is_noise_contam"]
        clean      = grp[~grp["is_contaminated"] & ~grp["is_hb_contam"]]
        hb_only    = grp[ grp["is_hb_contam"]       & ~grp["is_contaminated"]]
        bb_only    = grp[ bbnf & ~grp["is_hb_contam"] & ~grp["is_transient_contam"] & ~grp["is_ch_inc_contam"]]
        ch_only    = grp[ grp["is_ch_inc_contam"]    & ~grp["is_hb_contam"] & ~bbnf & ~grp["is_transient_contam"]]
        tr_only    = grp[ grp["is_transient_contam"] & ~grp["is_hb_contam"] & ~bbnf & ~grp["is_ch_inc_contam"]]
        n_flags    = (grp["is_hb_contam"].astype(int) + bbnf.astype(int) +
                      grp["is_ch_inc_contam"].astype(int) + grp["is_transient_contam"].astype(int))
        multi      = grp[n_flags > 1]

        fa = grp[grp["is_contaminated"] | grp["is_hb_contam"]]
        fa_total = len(fa)
        blk_hb   = fa["is_hb_contam"].sum()
        blk_bbnf = bbnf[fa.index].sum()
        blk_ch   = fa["is_ch_inc_contam"].sum()
        blk_full = fa_total  # all flagged windows are blocked by full NF-SQI by definition

        rows.append(dict(
            subject=sub, session=ses, total_candidates=total,
            clean=len(clean), high_beta_excl=len(hb_only),
            broadband_noise_excl=len(bb_only), channel_inc_excl=len(ch_only),
            transient_excl=len(tr_only), multi_contam=len(multi),
            contaminated=fa_total,
            blocked_by_hb_single=blk_hb, blocked_by_bbnf_single=blk_bbnf,
            blocked_by_ch_single=blk_ch, blocked_by_full=blk_full,
        ))
    return pd.DataFrame(rows)


def run_loso(df_task, dataset_id, variant_label):
    """LOSO logistic regression for all models; return summary + per-model prediction CSVs."""
    cands = df_task[df_task["gate_A"]].copy()
    cands["target"] = cands["is_contaminated"].astype(int)
    subjects = cands["subject"].unique()

    summary_rows = []
    for mname, mfeats in MODELS.items():
        y_true, y_pred, y_proba, sub_col = [], [], [], []
        for test_sub in subjects:
            tr = cands[cands["subject"] != test_sub]
            te = cands[cands["subject"] == test_sub]
            if len(tr) == 0 or len(te) == 0 or tr["target"].nunique() < 2:
                continue
            scaler = StandardScaler()
            X_tr = scaler.fit_transform(tr[mfeats].replace([np.inf, -np.inf], np.nan).fillna(0))
            X_te = scaler.transform(te[mfeats].replace([np.inf, -np.inf], np.nan).fillna(0))
            clf = LogisticRegression(class_weight="balanced", random_state=SEED,
                                     solver="liblinear", max_iter=1000)
            clf.fit(X_tr, tr["target"])
            proba = clf.predict_proba(X_te)[:, 1]
            y_true.extend(te["target"].values)
            y_pred.extend((proba > 0.5).astype(int))
            y_proba.extend(proba)
            sub_col.extend([test_sub] * len(te))

        if len(y_true) < 2 or len(np.unique(y_true)) < 2:
            continue

        auc  = roc_auc_score(y_true, y_proba)
        bacc = balanced_accuracy_score(y_true, y_pred)
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec  = recall_score(y_true, y_pred, zero_division=0)

        # Save predictions
        pred_df = pd.DataFrame({"subject": sub_col, "y_true": y_true,
                                 "y_pred": y_pred, "y_pred_proba": y_proba})
        pred_path = PRED / f"{dataset_id}_{mname}_{variant_label}_predictions.csv"
        pred_df.to_csv(pred_path, index=False)

        summary_rows.append(dict(dataset=dataset_id, variant=variant_label,
                                  model=mname, AUC=auc, BACC=bacc,
                                  Precision=prec, Recall=rec, n_candidates=len(y_true)))

    return pd.DataFrame(summary_rows)


def bootstrap_ci(df_ov, pred_dir, dataset_id, variant_label, n=N_BOOT, seed=SEED):
    """Subject-grouped bootstrap for contamination-overlap + AUC metrics."""
    subjects = df_ov["subject"].unique()
    rng = np.random.RandomState(seed)
    sub_data = {s: df_ov[df_ov["subject"] == s] for s in subjects}

    boot = {k: [] for k in ["Clean_Pct", "HB_Only_Pct", "BB_Only_Pct",
                             "Ch_Inc_Only_Pct", "Multi_Contam_Pct",
                             "Blk_HB_Pct", "Blk_BBNF_Pct", "Blk_Full_Pct"]}

    for _ in range(n):
        bs = rng.choice(subjects, size=len(subjects), replace=True)
        tot = sum(sub_data[s]["total_candidates"].sum() for s in bs)
        if tot == 0:
            continue
        boot["Clean_Pct"].append(sum(sub_data[s]["clean"].sum() for s in bs) / tot * 100)
        boot["HB_Only_Pct"].append(sum(sub_data[s]["high_beta_excl"].sum() for s in bs) / tot * 100)
        boot["BB_Only_Pct"].append(sum(sub_data[s]["broadband_noise_excl"].sum() for s in bs) / tot * 100)
        boot["Ch_Inc_Only_Pct"].append(sum(sub_data[s]["channel_inc_excl"].sum() for s in bs) / tot * 100)
        boot["Multi_Contam_Pct"].append(sum(sub_data[s]["multi_contam"].sum() for s in bs) / tot * 100)
        fa_tot = sum(sub_data[s]["contaminated"].sum() for s in bs)
        if fa_tot > 0:
            boot["Blk_HB_Pct"].append(sum(sub_data[s]["blocked_by_hb_single"].sum() for s in bs) / fa_tot * 100)
            boot["Blk_BBNF_Pct"].append(sum(sub_data[s]["blocked_by_bbnf_single"].sum() for s in bs) / fa_tot * 100)
            boot["Blk_Full_Pct"].append(sum(sub_data[s]["blocked_by_full"].sum() for s in bs) / fa_tot * 100)

    # AUC metrics
    mnames = list(MODELS.keys())
    preds = {}
    for mn in mnames:
        p = pred_dir / f"{dataset_id}_{mn}_{variant_label}_predictions.csv"
        if p.exists():
            preds[mn] = pd.read_csv(p)

    auc_boots = {mn: [] for mn in mnames}
    delta_c_a, delta_a_b, delta_d_b = [], [], []

    if len(preds) == len(mnames):
        subs = preds[mnames[0]]["subject"].unique()
        sub_idx  = {mn: {s: np.where(preds[mn]["subject"] == s)[0] for s in subs} for mn in mnames}
        y_true_d = {mn: preds[mn]["y_true"].values for mn in mnames}
        y_pred_d = {mn: preds[mn]["y_pred_proba"].values for mn in mnames}

        for _ in range(n):
            bs = rng.choice(subs, size=len(subs), replace=True)
            aucs = {}
            for mn in mnames:
                idx = np.concatenate([sub_idx[mn][s] for s in bs])
                yt, yp = y_true_d[mn][idx], y_pred_d[mn][idx]
                if len(np.unique(yt)) > 1:
                    aucs[mn] = roc_auc_score(yt, yp)
                    auc_boots[mn].append(aucs[mn])
                else:
                    aucs[mn] = np.nan
            m_a = "Broadband_Noise_Floor_Only"
            m_b = "High_Beta_Only"
            m_c = "Broadband_Noise_Floor_+_High_Beta"
            m_d = "Full_NF-SQI"
            delta_c_a.append(aucs.get(m_c, np.nan) - aucs.get(m_a, np.nan))
            delta_a_b.append(aucs.get(m_a, np.nan) - aucs.get(m_b, np.nan))
            delta_d_b.append(aucs.get(m_d, np.nan) - aucs.get(m_b, np.nan))

    results = []
    def add(metric, vals):
        v = [x for x in vals if not np.isnan(x)]
        if v:
            results.append(dict(Dataset=dataset_id, Variant=variant_label, Metric=metric,
                                 Mean=np.mean(v),
                                 CI_Lower=np.percentile(v, 2.5),
                                 CI_Upper=np.percentile(v, 97.5)))

    for k, v in boot.items():
        add(k, v)
    for mn, v in auc_boots.items():
        add(f"{mn}_AUC", v)
    add("Delta_AUC_C_minus_A", delta_c_a)
    add("Delta_AUC_A_minus_B", delta_a_b)
    add("Delta_AUC_D_minus_B", delta_d_b)

    return pd.DataFrame(results)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    variants = [
        ("smr_snr",   "snr_primary"),
        ("smr_power", "power_sensitivity"),
    ]

    all_loso    = []
    all_overlap = []
    all_boot    = []

    for gate_a_feat, variant_label in variants:
        print(f"\n=== Variant: {variant_label} (Gate A = {gate_a_feat}) ===")
        for ds_id, feat_path in DATASET_FEAT_PATHS.items():
            if not feat_path.exists():
                print(f"  [{ds_id}] Feature CSV missing — skipping.")
                continue
            print(f"  [{ds_id}] Loading features …")
            df_full = pd.read_csv(feat_path)

            if gate_a_feat not in df_full.columns:
                print(f"  [{ds_id}] Column {gate_a_feat!r} not found — skipping variant.")
                continue

            print(f"  [{ds_id}] Building gate labels …")
            df_task = build_labeled(df_full, gate_a_feat, ds_id)

            print(f"  [{ds_id}] Computing contamination overlap …")
            df_ov = contamination_overlap(df_task)
            df_ov["dataset"] = ds_id
            df_ov["variant"] = variant_label
            all_overlap.append(df_ov)

            df_ov.to_csv(
                OUT / f"{ds_id}_{variant_label}_contamination_overlap.csv",
                index=False,
            )

            print(f"  [{ds_id}] LOSO model comparison …")
            loso_df = run_loso(df_task, ds_id, variant_label)
            all_loso.append(loso_df)

            print(f"  [{ds_id}] Bootstrap CI …")
            boot_df = bootstrap_ci(df_ov, PRED, ds_id, variant_label)
            all_boot.append(boot_df)

    # ── Aggregate ──
    df_loso_all = pd.concat(all_loso, ignore_index=True) if all_loso else pd.DataFrame()
    df_boot_all = pd.concat(all_boot, ignore_index=True) if all_boot else pd.DataFrame()

    df_loso_all.to_csv(OUT / "loso_model_comparison_all_variants.csv", index=False)
    df_boot_all.to_csv(OUT / "bootstrap_ci_all_variants.csv", index=False)

    # ── Per-variant summary tables ──
    for variant_label in ["snr_primary", "power_sensitivity"]:
        vb = df_boot_all[df_boot_all["Variant"] == variant_label] if not df_boot_all.empty and "Variant" in df_boot_all.columns else pd.DataFrame(columns=["Dataset", "Variant", "Metric"])
        vl = df_loso_all[df_loso_all["variant"] == variant_label] if not df_loso_all.empty and "variant" in df_loso_all.columns else pd.DataFrame(columns=["dataset", "variant", "model"])

        rows = []
        for ds_id in DATASET_FEAT_PATHS:
            row = {"Dataset": ds_id, "Variant": variant_label}
            for metric in ["Clean_Pct", "Blk_HB_Pct", "Blk_BBNF_Pct", "Blk_Full_Pct",
                           "Broadband_Noise_Floor_Only_AUC", "High_Beta_Only_AUC",
                           "Delta_AUC_A_minus_B", "Delta_AUC_C_minus_A"]:
                sub = vb[(vb["Dataset"] == ds_id) & (vb["Metric"] == metric)]
                if len(sub) > 0:
                    r = sub.iloc[0]
                    row[f"{metric}_mean"] = round(r["Mean"], 4)
                    row[f"{metric}_ci"]   = f"[{r['CI_Lower']:.3f}, {r['CI_Upper']:.3f}]"
            # LOSO direct values
            lv = vl[vl["dataset"] == ds_id]
            for mn in MODELS:
                sub = lv[lv["model"] == mn]
                if len(sub) > 0:
                    row[f"{mn}_AUC_direct"]  = round(sub.iloc[0]["AUC"], 4)
                    row[f"{mn}_BACC_direct"] = round(sub.iloc[0]["BACC"], 4)
            rows.append(row)

        df_rep = pd.DataFrame(rows)
        df_rep.to_csv(OUT / f"{variant_label}_replication_table.csv", index=False)
        print(f"\nSaved {variant_label}_replication_table.csv")

    # ── Write summary markdowns ──
    _write_summary(df_boot_all, df_loso_all, "snr_primary",   OUT)
    _write_summary(df_boot_all, df_loso_all, "power_sensitivity", OUT)

    print("\n[OK] run_snr_harmonization.py complete.")


def _ci(row):
    return f"{row['Mean']:.3f} [{row['CI_Lower']:.3f}, {row['CI_Upper']:.3f}]"


def _write_summary(df_boot, df_loso, variant_label, out_dir):
    fname = "snr_primary_summary.md" if variant_label == "snr_primary" else "power_sensitivity_summary.md"
    gate_scalar = "SMR SNR" if variant_label == "snr_primary" else "SMR power"

    vb = df_boot[df_boot["Variant"] == variant_label] if len(df_boot) > 0 else pd.DataFrame()
    vl = df_loso[df_loso["variant"] == variant_label] if len(df_loso) > 0 else pd.DataFrame()

    datasets = list(DATASET_FEAT_PATHS.keys())

    def get(ds, metric):
        sub = vb[(vb["Dataset"] == ds) & (vb["Metric"] == metric)]
        return sub.iloc[0] if len(sub) > 0 else None

    lines = [
        f"# {variant_label.replace('_', ' ').title()} Analysis",
        "",
        f"Gate A scalar: **{gate_scalar}** (p75 of subject/session rest baseline)",
        "Gates B and C: unchanged from primary analysis.",
        "Bootstrap: 5000 subject-grouped resamples, seed=20260702.",
        "",
        "## Main Ordering Check",
        "",
        "| Dataset | Full NF-SQI blocks (%) | BB/noise blocks (%) | HB blocks (%) | Ordering holds? |",
        "|---------|------------------------|---------------------|---------------|-----------------|",
    ]

    ordering_holds_all = True
    for ds in datasets:
        r_full = get(ds, "Blk_Full_Pct")
        r_bb   = get(ds, "Blk_BBNF_Pct")
        r_hb   = get(ds, "Blk_HB_Pct")
        if r_full is None:
            lines.append(f"| {ds} | N/A | N/A | N/A | — |")
            continue
        full_m = r_full["Mean"]; bb_m = r_bb["Mean"]; hb_m = r_hb["Mean"]
        ok = (full_m > bb_m) and (full_m > hb_m)
        ordering_holds_all = ordering_holds_all and ok
        lines.append(f"| {ds} | {_ci(r_full)} | {_ci(r_bb)} | {_ci(r_hb)} | {'✓' if ok else '✗'} |")

    lines += ["", "## AUC Model Comparison", "",
              "| Dataset | BB/noise AUC | HB AUC | Delta(BB/noise − HB) | Delta(added HB) |",
              "|---------|-------------|--------|----------------------|-----------------|"]

    auc_ordering_all = True
    for ds in datasets:
        r_bb  = get(ds, "Broadband_Noise_Floor_Only_AUC")
        r_hb  = get(ds, "High_Beta_Only_AUC")
        r_da  = get(ds, "Delta_AUC_A_minus_B")
        r_dc  = get(ds, "Delta_AUC_C_minus_A")
        if r_bb is None:
            lines.append(f"| {ds} | N/A | N/A | N/A | N/A |")
            continue
        auc_ok = r_da["Mean"] > 0  # BB/noise AUC > HB AUC
        auc_ordering_all = auc_ordering_all and auc_ok
        lines.append(f"| {ds} | {_ci(r_bb)} | {_ci(r_hb)} | {_ci(r_da)} | {_ci(r_dc)} |")

    lines += ["",
              "## Conclusion",
              "",
              f"- **Full NF-SQI > BB/noise > HB** (blocking ordering): {'**CONFIRMED** across all datasets' if ordering_holds_all else '**NOT fully confirmed** — check individual datasets'}",
              f"- **BB/noise AUC > HB AUC**: {'**CONFIRMED**' if auc_ordering_all else '**NOT fully confirmed**'}",
              "- **Adding HB does not materially improve BB/noise AUC**: see Delta(added HB) — CI should include zero or be negative.",
              "",
              f"## Direct LOSO Model Performance ({variant_label})",
              "",
              "| Dataset | Model | AUC | BACC |",
              "|---------|-------|-----|------|",
              ]

    for ds in datasets:
        dsub = vl[vl["dataset"] == ds]
        for _, row in dsub.iterrows():
            lines.append(f"| {ds} | {row['model']} | {row['AUC']:.4f} | {row['BACC']:.4f} |")

    lines += ["", f"*Generated by run_snr_harmonization.py — {variant_label}*"]

    (out_dir / fname).write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote {fname}")


if __name__ == "__main__":
    main()
