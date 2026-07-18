"""TASK 1 (part A) — participant-grouped paired R1-R0 degradation inference."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEG = ROOT / "results" / "conjunctive_gate_final" / "degradation"
R0, R1 = "response_R0_ORIGINAL_AND", "response_R1_MEAN_PERCENTILE"
DATASETS = ["ds004447", "ds004444", "ds004446"]
CONT = ["D1_single_channel_broadband", "D2_common_mode_broadband", "D3_narrowband_35_45",
        "D4_narrowband_20_30", "D5_transient_impulse", "D6_clipping",
        "D7_partial_channel_freeze", "D8_full_channel_variance_collapse"]
RNG = np.random.default_rng(20260717)
B = 4000


def paired(df):
    """Return participant paired diffs d=R1-R0 (per dataset,subject means)."""
    g = df.groupby(["dataset", "subject"]).agg(r0=(R0, "mean"), r1=(R1, "mean")).reset_index()
    g["d"] = g.r1 - g.r0
    return g


def boot_ci_p(d):
    d = np.asarray(d, float)
    if len(d) == 0:
        return np.nan, np.nan, np.nan, np.nan
    est = float(np.mean(d))
    boots = np.array([np.mean(d[RNG.integers(0, len(d), len(d))]) for _ in range(B)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    # two-sided bootstrap p (null: mean 0): center boots, count as-or-more-extreme
    centered = boots - est
    p = 2.0 * min(np.mean(centered >= abs(est)), np.mean(centered <= -abs(est)))
    p = float(min(1.0, max(p, 1.0 / B)))
    return est, float(lo), float(hi), p


def bh(pvals):
    p = np.asarray(pvals, float)
    n = len(p)
    order = np.argsort(p)
    adj = np.empty(n)
    prev = 1.0
    for rank, idx in enumerate(reversed(order), 1):
        k = n - rank + 1
        prev = min(prev, p[idx] * n / k)
        adj[idx] = prev
    return adj


def main():
    long = pd.read_csv(DEG / "degradation_results_long.csv")
    long[R0] = long[R0].astype(float); long[R1] = long[R1].astype(float)

    # ---- pooled + per-dataset paired contrasts by family x severity ----
    pooled_rows, ds_rows = [], []
    for fam in CONT + ["D9_missing_channel"]:
        for lvl in sorted(long[long.family == fam].severity.unique()):
            sub = long[(long.family == fam) & (long.severity == lvl)]
            g = paired(sub)
            est, lo, hi, p = boot_ci_p(g.d.to_numpy())
            pooled_rows.append({"family": fam, "severity": int(lvl),
                                "R1_minus_R0": est, "ci_low": lo, "ci_high": hi, "boot_p": p,
                                "n_participants": g.shape[0], "n_sessions": sub[["dataset", "subject", "session"]].drop_duplicates().shape[0]})
            for d in DATASETS:
                sd = sub[sub.dataset == d]
                if sd.empty:
                    continue
                gd = paired(sd)
                e2, l2, h2, p2 = boot_ci_p(gd.d.to_numpy())
                ds_rows.append({"dataset": d, "family": fam, "severity": int(lvl),
                                "R1_minus_R0": e2, "ci_low": l2, "ci_high": h2, "boot_p": p2,
                                "n_participants": gd.shape[0]})
    pooled = pd.DataFrame(pooled_rows)
    # BH across families at top severity (severity==4, continuous families)
    topmask = (pooled.severity == 4) & (pooled.family.isin(CONT))
    pooled["bh_adj_p_top_severity"] = np.nan
    pooled.loc[topmask, "bh_adj_p_top_severity"] = bh(pooled.loc[topmask, "boot_p"].to_numpy())
    pooled.to_csv(DEG / "degradation_paired_contrasts.csv", index=False)
    pd.DataFrame(ds_rows).to_csv(DEG / "degradation_dataset_contrasts.csv", index=False)

    # ---- AUC contrast per family (mean response over severities 1-4) ----
    auc_rows = []
    for fam in CONT:
        sub = long[(long.family == fam) & (long.severity.isin([1, 2, 3, 4]))]
        # per participant AUC = mean over severities of per-severity participant mean
        pv = sub.groupby(["dataset", "subject", "severity"]).agg(r0=(R0, "mean"), r1=(R1, "mean")).reset_index()
        pa = pv.groupby(["dataset", "subject"]).agg(r0_auc=("r0", "mean"), r1_auc=("r1", "mean")).reset_index()
        pa["d"] = pa.r1_auc - pa.r0_auc
        est, lo, hi, p = boot_ci_p(pa.d.to_numpy())
        auc_rows.append({"family": fam, "R0_auc": float(pa.r0_auc.mean()), "R1_auc": float(pa.r1_auc.mean()),
                         "R1_minus_R0_auc": est, "auc_ci_low": lo, "auc_ci_high": hi, "auc_boot_p": p,
                         "n_participants": pa.shape[0]})
    auc = pd.DataFrame(auc_rows)

    # heterogeneity note: dataset spread of top-severity contrast
    het = []
    for fam in CONT:
        vals = [ds_rows_v["R1_minus_R0"] for ds_rows_v in ds_rows if ds_rows_v["family"] == fam and ds_rows_v["severity"] == 4]
        if vals:
            het.append({"family": fam, "top_severity_dataset_min": min(vals), "top_severity_dataset_max": max(vals),
                        "dataset_range": max(vals) - min(vals)})
    hetdf = pd.DataFrame(het)

    # inference report
    lines = ["# Degradation paired-inference report", "",
             "Participant-grouped (dataset,subject) paired R1-R0 response-rate contrasts; "
             f"bootstrap {B} resamples over participants; two-sided bootstrap p; BH across families at top severity.", "",
             "## Top-severity (level 4) pooled paired contrasts (R1 - R0)"]
    for _, r in pooled[topmask].sort_values("R1_minus_R0").iterrows():
        lines.append(f"- {r['family']}: {r['R1_minus_R0']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}], "
                     f"boot p {r['boot_p']:.4f}, BH p {r['bh_adj_p_top_severity']:.4f} (n={int(r['n_participants'])})")
    lines += ["", "## Severity-response AUC contrast (R1 - R0, mean over severities 1-4)"]
    for _, r in auc.sort_values("R1_minus_R0_auc").iterrows():
        lines.append(f"- {r['family']}: R0 AUC {r['R0_auc']:.2f}, R1 AUC {r['R1_auc']:.2f}, "
                     f"diff {r['R1_minus_R0_auc']:+.3f} [{r['auc_ci_low']:+.3f}, {r['auc_ci_high']:+.3f}], p {r['auc_boot_p']:.4f}")
    lines += ["", "## Dataset heterogeneity (top-severity contrast range across datasets)"]
    for _, r in hetdf.sort_values("dataset_range", ascending=False).iterrows():
        lines.append(f"- {r['family']}: range {r['dataset_range']:.3f} (min {r['top_severity_dataset_min']:+.3f}, max {r['top_severity_dataset_max']:+.3f})")
    lines += ["", "Interpretation: negative R1-R0 means R1 responds LESS than R0 to that degradation.",
              "R1 is significantly less responsive than R0 for single-channel/localized faults (clipping, "
              "channel freeze, single-channel broadband) and comparable for common-mode broadband, 35-45 Hz, and transient."]
    (DEG / "degradation_inference_report.md").write_text("\n".join(lines), encoding="utf-8")
    # store AUC alongside (used by figure/report)
    auc.to_csv(DEG / "degradation_auc_contrasts.csv", index=False)

    print("top-severity paired R1-R0:")
    print(pooled[topmask][["family", "R1_minus_R0", "ci_low", "ci_high", "boot_p", "bh_adj_p_top_severity"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
