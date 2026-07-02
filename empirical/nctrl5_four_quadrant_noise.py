"""NCTRL5: Four-quadrant noise-control classification.

Classifies each subject (ses-01 → ses-08 change) into:
  A: SMR SNR improves AND noise/burstiness decreases  (both)
  B: SMR SNR improves, noise does NOT decrease         (acq only)
  C: Noise decreases, SMR SNR does NOT improve         (damp only)
  D: Neither improves                                  (neither)

Uses multiple definitions to test sensitivity:
  - SMR power change (raw)
  - SMR SNR change (preferred)
  - HB power change (absolute)
  - HB residual-above-1/f change
  - HB burst-rate change
  - SMR diffusion coefficient change

Outputs:
  outputs/tables/nctrl5_four_quadrant_noise_classification.csv
  outputs/tables/nctrl5_definition_sensitivity.csv
  outputs/figures/nctrl5_four_quadrant_noise_panel.*
  outputs/figures/nctrl5_definition_sensitivity_panel.*
  outputs/reports/nctrl5_results.md
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style

TBL = ROOT / "outputs" / "tables"
QUAD_COLORS = {
    "A_both": "#1ABC9C",
    "B_acq_only": "#3498DB",
    "C_damp_only": "#E74C3C",
    "D_neither": "#95A5A6",
}

CONDITIONS = ["rest", "task"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_quadrant(smr_improve: bool, noise_damp: bool) -> str:
    if smr_improve and noise_damp:
        return "A_both"
    if smr_improve and not noise_damp:
        return "B_acq_only"
    if not smr_improve and noise_damp:
        return "C_damp_only"
    return "D_neither"


def compute_subject_classifications(noise_df: pd.DataFrame,
                                     burst_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-subject classification using multiple metrics."""
    # Use rest condition and mean channel for PSD features
    n3_rest = noise_df[(noise_df["condition"] == "rest") & (noise_df["channel"] == "mean")]
    n4_rest = burst_df[burst_df["condition"] == "rest"]

    rows = []
    subjects = sorted(n3_rest["subject"].unique())

    for sub in subjects:
        s01 = n3_rest[(n3_rest["subject"] == sub) & (n3_rest["session"] == "ses-01")]
        s08 = n3_rest[(n3_rest["subject"] == sub) & (n3_rest["session"] == "ses-08")]
        b01 = n4_rest[(n4_rest["subject"] == sub) & (n4_rest["session"] == "ses-01")]
        b08 = n4_rest[(n4_rest["subject"] == sub) & (n4_rest["session"] == "ses-08")]

        if s01.empty or s08.empty:
            continue

        # ---------- SMR improvement metrics ----------
        # 1. SMR power (raw log change)
        delta_smr_power = (
            np.log10(float(s08["p_smr"].values[0]) + 1e-30) -
            np.log10(float(s01["p_smr"].values[0]) + 1e-30)
        )
        # 2. SMR SNR change (log)
        delta_smr_snr = (
            np.log10(float(s08["smr_snr_abs"].values[0]) + 1e-30) -
            np.log10(float(s01["smr_snr_abs"].values[0]) + 1e-30)
        )
        # 3. SMR relative power change
        delta_smr_rel = float(s08["smr_rel"].values[0]) - float(s01["smr_rel"].values[0]) \
            if "smr_rel" in s01.columns else np.nan

        # ---------- Noise damping metrics ----------
        # 4. HB power change (negative = damped)
        delta_hb_power = (
            np.log10(float(s08["p_hb"].values[0]) + 1e-30) -
            np.log10(float(s01["p_hb"].values[0]) + 1e-30)
        )
        # 5. HB residual-above-1/f change
        delta_hb_resid = (
            float(s08["hb_residual_above_1f"].values[0]) -
            float(s01["hb_residual_above_1f"].values[0])
        ) if "hb_residual_above_1f" in s01.columns else np.nan

        # 6. HB burst-rate change
        delta_hb_burst = np.nan
        if not b01.empty and not b08.empty:
            delta_hb_burst = (float(b08["hb_burst_rate_per_min"].values[0]) -
                               float(b01["hb_burst_rate_per_min"].values[0]))

        # 7. SMR diffusion change (negative = more stable = improvement)
        delta_smr_diff = np.nan
        if not b01.empty and not b08.empty:
            delta_smr_diff = (float(b08["smr_diffusion_coef"].values[0]) -
                               float(b01["smr_diffusion_coef"].values[0]))

        # ---------- Classifications ----------
        # Primary: SMR SNR vs HB power
        quad_primary = classify_quadrant(
            smr_improve=(delta_smr_snr > 0),
            noise_damp=(delta_hb_power < 0),
        )
        # Alt 1: SMR power vs HB burst rate
        quad_burst = classify_quadrant(
            smr_improve=(delta_smr_power > 0),
            noise_damp=(delta_hb_burst < 0 if not np.isnan(delta_hb_burst) else False),
        )
        # Alt 2: SMR SNR vs HB residual
        quad_resid = classify_quadrant(
            smr_improve=(delta_smr_snr > 0),
            noise_damp=(delta_hb_resid < 0 if not np.isnan(delta_hb_resid) else False),
        )
        # Alt 3: SMR SNR vs SMR diffusion (stability improvement)
        quad_diff = classify_quadrant(
            smr_improve=(delta_smr_snr > 0),
            noise_damp=(delta_smr_diff < 0 if not np.isnan(delta_smr_diff) else False),
        )

        rows.append({
            "subject": sub,
            "delta_smr_power_log": delta_smr_power,
            "delta_smr_snr_log": delta_smr_snr,
            "delta_smr_rel": delta_smr_rel,
            "delta_hb_power_log": delta_hb_power,
            "delta_hb_resid": delta_hb_resid,
            "delta_hb_burst_rate": delta_hb_burst,
            "delta_smr_diffusion": delta_smr_diff,
            # Primary quadrant
            "quadrant_primary": quad_primary,
            # Alternative definitions
            "quadrant_burst": quad_burst,
            "quadrant_resid": quad_resid,
            "quadrant_diff": quad_diff,
        })

    return pd.DataFrame(rows)


def make_quadrant_figure(classif_df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))

    def scatter_quadrant(ax, df, x_col, y_col, quad_col, x_lab, y_lab, title):
        for sub_row in df.itertuples():
            q = getattr(sub_row, quad_col)
            x = getattr(sub_row, x_col)
            y = getattr(sub_row, y_col)
            if np.isnan(x) or np.isnan(y):
                continue
            ax.scatter(x, y, color=QUAD_COLORS.get(q, "gray"), s=140,
                       edgecolors="black", linewidths=0.8, zorder=5)
            ax.annotate(sub_row.subject[:7], (x, y), fontsize=7,
                        ha="center", va="bottom", xytext=(0, 4), textcoords="offset points")
        ax.axhline(0, color="black", ls="--", lw=0.8)
        ax.axvline(0, color="black", ls="--", lw=0.8)
        ax.set_xlabel(x_lab, fontsize=8)
        ax.set_ylabel(y_lab, fontsize=8)
        ax.set_title(title, fontsize=9)
        # Legend
        patches = [mpatches.Patch(color=c, label=q) for q, c in QUAD_COLORS.items()]
        ax.legend(handles=patches, fontsize=6, framealpha=0.7)

    scatter_quadrant(axes[0, 0], classif_df, "delta_hb_power_log", "delta_smr_snr_log",
                      "quadrant_primary",
                      "Δ log(P_HB) ses-01→08 [−=damped]",
                      "Δ log(SMR SNR) ses-01→08 [+=improved]",
                      "(A) Primary: SMR SNR vs HB power")

    scatter_quadrant(axes[0, 1], classif_df, "delta_hb_burst_rate", "delta_smr_power_log",
                      "quadrant_burst",
                      "Δ HB burst rate [−=damped]",
                      "Δ log(P_SMR) [+=improved]",
                      "(B) Alt: SMR power vs HB burst rate")

    scatter_quadrant(axes[1, 0], classif_df, "delta_hb_resid", "delta_smr_snr_log",
                      "quadrant_resid",
                      "Δ HB residual above 1/f [−=less band-specific]",
                      "Δ log(SMR SNR) [+=improved]",
                      "(C) Alt: SMR SNR vs HB 1/f residual")

    scatter_quadrant(axes[1, 1], classif_df, "delta_smr_diffusion", "delta_smr_snr_log",
                      "quadrant_diff",
                      "Δ SMR diffusion [−=more stable]",
                      "Δ log(SMR SNR) [+=improved]",
                      "(D) Alt: SMR SNR vs stability (diffusion)")

    fig.suptitle("NCTRL5: Four-quadrant noise-control classification (ses-01→ses-08)",
                  fontsize=10, fontweight="bold")
    plt.tight_layout()
    save_csv_backed_figure(fig, classif_df, "nctrl5_four_quadrant_noise_panel", root)


def make_sensitivity_figure(classif_df: pd.DataFrame, root: Path) -> None:
    set_style()
    quad_cols = ["quadrant_primary", "quadrant_burst", "quadrant_resid", "quadrant_diff"]
    labels = ["Primary\n(SNR vs HB power)", "Alt (SMR power\nvs HB burst)",
               "Alt (SNR vs\nHB 1/f resid.)", "Alt (SNR vs\nSMR diffusion)"]

    fig, ax = plt.subplots(figsize=(9, 5))
    x_pos = np.arange(len(quad_cols))
    quads = ["A_both", "B_acq_only", "C_damp_only", "D_neither"]
    bottoms = np.zeros(len(quad_cols))
    for q in quads:
        counts = [classif_df[col].value_counts().get(q, 0) for col in quad_cols]
        ax.bar(x_pos, counts, bottom=bottoms, color=QUAD_COLORS[q], label=q, alpha=0.85)
        for xi, (cnt, bot) in enumerate(zip(counts, bottoms)):
            if cnt > 0:
                ax.text(xi, bot + cnt / 2, str(cnt), ha="center", va="center",
                         fontsize=9, fontweight="bold", color="white")
        bottoms += np.array(counts, dtype=float)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("N subjects")
    ax.set_title("NCTRL5: Quadrant assignment sensitivity to metric definition (n=5 subjects)")
    ax.legend(fontsize=7, framealpha=0.8)
    plt.tight_layout()

    # Make a sensitivity table
    sens_rows = []
    for col in quad_cols:
        for q in quads:
            sens_rows.append({"definition": col, "quadrant": q,
                               "count": classif_df[col].value_counts().get(q, 0)})
    sens_df = pd.DataFrame(sens_rows)
    save_csv_backed_figure(fig, sens_df, "nctrl5_definition_sensitivity_panel", root)
    sens_df.to_csv(TBL / "nctrl5_definition_sensitivity.csv", index=False)


def write_report(classif_df: pd.DataFrame) -> None:
    primary = classif_df["quadrant_primary"].value_counts().to_dict()
    n_A = primary.get("A_both", 0)
    n_B = primary.get("B_acq_only", 0)
    n_C = primary.get("C_damp_only", 0)
    n_D = primary.get("D_neither", 0)
    n = len(classif_df)

    sep_ok = (n_B > 0 and n_C > 0)

    report = f"""# NCTRL5 Results: Four-Quadrant Noise-Control Classification

Generated: {utc_now()}

## Method

Classification based on ses-01 → ses-08 change (rest condition, mean channel):
- SMR improvement: Δ log(SMR SNR) > 0 (primary)
- Noise damping: Δ log(P_HB) < 0 (primary)

Four alternative definitions also tested (see sensitivity table).

## Primary classification (n={n} subjects)

| Quadrant | Label | N |
|---|---|---|
| A_both | SMR SNR + AND noise − | {n_A} |
| B_acq_only | SMR SNR + only | {n_B} |
| C_damp_only | Noise − only | {n_C} |
| D_neither | Neither | {n_D} |

Mechanistic separability: {sep_ok} (B>0 and C>0)

## Per-subject primary quadrant
{classif_df[["subject","quadrant_primary","delta_smr_snr_log","delta_hb_power_log"]].to_string(index=False)}

## Sensitivity to metric definition
(See nctrl5_definition_sensitivity.csv for all definitions)

## Interpretation

{"Quadrants B and C are both populated (separability confirmed): some subjects show SMR SNR improvement without HB reduction (B), and others show HB reduction without SMR SNR improvement (C). This empirically demonstrates that target acquisition and noise damping are separable." if sep_ok else "Quadrant B or C has zero members under the primary definition. The separability pattern is sensitive to metric choice. See alternative definitions."}

Note: n=5 is very small. These classifications are descriptive only and cannot be
statistically confirmed. Results depend on definition of 'SMR improvement' and
'noise damping' (see sensitivity panel). All definitions should be reported to avoid
cherry-picking.

Generated: {utc_now()}
"""
    (ROOT / "outputs" / "reports" / "nctrl5_results.md").write_text(report, encoding="utf-8")


def main() -> None:
    ensure_repo_structure(ROOT)

    noise_path = TBL / "nctrl3_empirical_noise_features.csv"
    burst_path = TBL / "nctrl4_burst_instability_features.csv"

    if not noise_path.exists() or not burst_path.exists():
        print("NCTRL5: Dependency tables not found. Run NCTRL3 and NCTRL4 first.")
        return

    noise_df = pd.read_csv(noise_path)
    burst_df = pd.read_csv(burst_path)

    classif_df = compute_subject_classifications(noise_df, burst_df)
    classif_df.to_csv(TBL / "nctrl5_four_quadrant_noise_classification.csv", index=False)

    print(f"NCTRL5: {len(classif_df)} subjects classified.")
    print(classif_df[["subject", "quadrant_primary"]].to_string(index=False))

    make_quadrant_figure(classif_df, ROOT)
    make_sensitivity_figure(classif_df, ROOT)
    write_report(classif_df)
    print("NCTRL5 done.")


if __name__ == "__main__":
    main()
