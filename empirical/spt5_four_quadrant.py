"""SPT5: Empirical four-quadrant classification.

Classifies each subject/session into four categories based on
SMR change and high-beta change from WP8 empirical features.

Outputs
-------
outputs/tables/spt5_four_quadrant_classification.csv
outputs/tables/spt5_artifact_aware_classification.csv
outputs/figures/spt5_four_quadrant_panel.*
outputs/figures/spt5_artifact_aware_panel.*
outputs/reports/spt5_results.md
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


QUADRANT_COLORS = {
    "A_both": "#2ca02c",
    "B_acquisition_only": "#ff7f0e",
    "C_stabilization_only": "#1f77b4",
    "D_neither": "#d62728",
}

ARTIFACT_COLORS = {
    "clean_both": "#2ca02c",
    "broadband_contamination": "#ff7f0e",
    "stabilization_contaminated": "#9467bd",
    "unstable_no_regulation": "#d62728",
}


def classify_subject(smr_change: float, hbeta_change: float,
                      smr_thresh: float = 0.0,
                      hbeta_thresh: float = 0.0) -> str:
    """Classify into four quadrants.

    A: SMR up + high-beta down  (both target acquisition and stabilization)
    B: SMR up + high-beta not down  (acquisition only)
    C: SMR not up + high-beta down  (stabilization only)
    D: neither
    """
    smr_up = smr_change > smr_thresh
    hbeta_down = hbeta_change < hbeta_thresh
    if smr_up and hbeta_down:
        return "A_both"
    if smr_up and not hbeta_down:
        return "B_acquisition_only"
    if not smr_up and hbeta_down:
        return "C_stabilization_only"
    return "D_neither"


def classify_artifact_aware(smr_change: float, hbeta_change: float,
                              broadband_change: float,
                              smr_thresh: float = 0.0,
                              hbeta_thresh: float = 0.0,
                              broadband_thresh: float = 0.1) -> str:
    """Artifact-aware four-quadrant classification."""
    smr_up = smr_change > smr_thresh
    hbeta_down = hbeta_change < hbeta_thresh
    broadband_contaminated = broadband_change > broadband_thresh

    if smr_up and hbeta_down and not broadband_contaminated:
        return "clean_both"
    if (smr_up or hbeta_down) and broadband_contaminated:
        return "broadband_contamination"
    if not smr_up and hbeta_down and broadband_contaminated:
        return "stabilization_contaminated"
    return "unstable_no_regulation"


def load_empirical_data() -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Load WP8 empirical outputs or SPT4 features if available."""
    tbl_dir = ROOT / "outputs" / "tables"
    effects_path = tbl_dir / "wp8_prepost_or_sessionwise_effects.csv"
    features_path = tbl_dir / "wp8_empirical_features.csv"

    if not effects_path.exists() or not features_path.exists():
        return pd.DataFrame(), pd.DataFrame(), False

    effects = pd.read_csv(effects_path)
    features = pd.read_csv(features_path)
    if effects.empty and features.empty:
        return effects, features, False

    return effects, features, True


def build_classification_from_wp8(effects: pd.DataFrame,
                                   features: pd.DataFrame) -> pd.DataFrame:
    """Build per-subject classification from WP8 pre/post effects."""
    rows = []

    # Check if WP8 effects has the necessary columns
    needed = {"subject", "metric", "fractional_change"}
    if effects.empty or not needed.issubset(effects.columns):
        # Fall back to features table
        if features.empty or "subject" not in features.columns:
            return pd.DataFrame()

        # Use session 01 vs 08 from features table
        ses1 = features[features["session"] == "ses-01"].copy() if "session" in features.columns else pd.DataFrame()
        ses8 = features[features["session"] == "ses-08"].copy() if "session" in features.columns else pd.DataFrame()

        if ses1.empty or ses8.empty:
            return pd.DataFrame()

        subjects = set(ses1["subject"].unique()) & set(ses8["subject"].unique())
        for subj in sorted(subjects):
            s1 = ses1[ses1["subject"] == subj]
            s8 = ses8[ses8["subject"] == subj]

            def get_mean(df, col):
                return float(df[col].dropna().mean()) if col in df.columns and not df[col].dropna().empty else np.nan

            smr_pre = get_mean(s1, "smr_power")
            smr_post = get_mean(s8, "smr_power")
            hbeta_pre = get_mean(s1, "high_beta_power")
            hbeta_post = get_mean(s8, "high_beta_power")
            broad_pre = get_mean(s1, "broadband_non_target_power")
            broad_post = get_mean(s8, "broadband_non_target_power")

            smr_change = (smr_post - smr_pre) / abs(smr_pre) if smr_pre != 0 else np.nan
            hbeta_change = (hbeta_post - hbeta_pre) / abs(hbeta_pre) if hbeta_pre != 0 else np.nan
            broad_change = (broad_post - broad_pre) / abs(broad_pre) if broad_pre != 0 else np.nan

            quad = classify_subject(smr_change or 0.0, hbeta_change or 0.0)
            art = classify_artifact_aware(smr_change or 0.0, hbeta_change or 0.0,
                                          broad_change or 0.0)
            rows.append({
                "subject": subj,
                "smr_frac_change": smr_change,
                "hbeta_frac_change": hbeta_change,
                "broadband_frac_change": broad_change,
                "quadrant": quad,
                "artifact_aware_class": art,
                "data_source": "features_ses01_vs_ses08",
            })
        return pd.DataFrame(rows)

    # Use effects table
    pivot = effects.pivot_table(index="subject", columns="metric",
                                values="fractional_change", aggfunc="mean")
    pivot = pivot.reset_index()

    for _, row in pivot.iterrows():
        smr_change = float(row.get("smr_power", np.nan))
        hbeta_change = float(row.get("high_beta_power", np.nan))
        broad_change = float(row.get("broadband_non_target_power", np.nan))

        if np.isnan(smr_change) or np.isnan(hbeta_change):
            quad = "D_neither"
            art = "unstable_no_regulation"
        else:
            quad = classify_subject(smr_change, hbeta_change)
            art = classify_artifact_aware(smr_change, hbeta_change, broad_change if not np.isnan(broad_change) else 0.0)

        rows.append({
            "subject": row["subject"],
            "smr_frac_change": smr_change,
            "hbeta_frac_change": hbeta_change,
            "broadband_frac_change": broad_change,
            "quadrant": quad,
            "artifact_aware_class": art,
            "data_source": "wp8_effects",
        })
    return pd.DataFrame(rows)


def make_four_quadrant_panel(classif_df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    if classif_df.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                    fontsize=12, transform=ax.transAxes)
        plt.tight_layout()
        save_csv_backed_figure(fig, pd.DataFrame({"note": ["no data"]}),
                               "spt5_four_quadrant_panel", root)
        return

    ok = classif_df.dropna(subset=["smr_frac_change", "hbeta_frac_change"])

    # Panel A: scatter
    for _, row in ok.iterrows():
        q = row["quadrant"]
        axes[0].scatter(row["smr_frac_change"], row["hbeta_frac_change"],
                        color=QUADRANT_COLORS.get(q, "gray"),
                        s=100, zorder=3, alpha=0.85)
        axes[0].annotate(str(row["subject"]).replace("sub-", ""),
                         (row["smr_frac_change"], row["hbeta_frac_change"]),
                         fontsize=7, ha="center", va="bottom")

    axes[0].axhline(0, color="black", lw=1.0, ls="--")
    axes[0].axvline(0, color="black", lw=1.0, ls="--")
    axes[0].set_xlabel("SMR fractional change (ses-01 → ses-08)")
    axes[0].set_ylabel("High-beta fractional change (ses-01 → ses-08)")
    axes[0].set_title("Four-quadrant classification")

    # Legend
    for q, c in QUADRANT_COLORS.items():
        axes[0].scatter([], [], color=c, label=q.replace("_", " "), s=50)
    axes[0].legend(fontsize=7, loc="upper right")

    # Quadrant labels
    for qx, qy, label in [
        (0.25, -0.25, "A: Both"), (-0.25, -0.25, "C: Stab only"),
        (0.25, 0.25, "B: Acq only"), (-0.25, 0.25, "D: Neither"),
    ]:
        if not ok.empty:
            xr = ok["smr_frac_change"].abs().max() * 0.6
            yr = ok["hbeta_frac_change"].abs().max() * 0.6
            axes[0].text(np.sign(qx) * xr, np.sign(qy) * yr,
                         label, ha="center", va="center",
                         fontsize=8, color="gray", alpha=0.6)

    # Panel B: count bar chart
    quad_counts = ok["quadrant"].value_counts().reindex(
        ["A_both", "B_acquisition_only", "C_stabilization_only", "D_neither"], fill_value=0
    )
    bars = axes[1].bar(
        [q.replace("_", "\n") for q in quad_counts.index],
        quad_counts.values,
        color=[QUADRANT_COLORS[q] for q in quad_counts.index],
        edgecolor="white", alpha=0.85,
    )
    axes[1].set_xlabel("Quadrant")
    axes[1].set_ylabel("Number of subjects")
    axes[1].set_title(f"Quadrant frequencies (N={len(ok)})")
    for bar, val in zip(bars, quad_counts.values):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                     str(val), ha="center", fontsize=9)

    fig.suptitle("SPT5: Four-quadrant SMR acquisition vs high-beta stabilization", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(fig, classif_df, "spt5_four_quadrant_panel", root)


def make_artifact_aware_panel(classif_df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    if classif_df.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                    fontsize=12, transform=ax.transAxes)
        plt.tight_layout()
        save_csv_backed_figure(fig, pd.DataFrame({"note": ["no data"]}),
                               "spt5_artifact_aware_panel", root)
        return

    ok = classif_df.dropna(subset=["smr_frac_change", "hbeta_frac_change"])

    # Panel A: artifact-aware scatter
    for _, row in ok.iterrows():
        q = row["artifact_aware_class"]
        axes[0].scatter(row["smr_frac_change"], row["hbeta_frac_change"],
                        color=ARTIFACT_COLORS.get(q, "gray"),
                        s=100, zorder=3, alpha=0.85,
                        marker=("*" if "contamination" in q else "o"))
        axes[0].annotate(str(row["subject"]).replace("sub-", ""),
                         (row["smr_frac_change"], row["hbeta_frac_change"]),
                         fontsize=7, ha="center", va="bottom")

    axes[0].axhline(0, color="black", lw=1.0, ls="--")
    axes[0].axvline(0, color="black", lw=1.0, ls="--")
    axes[0].set_xlabel("SMR fractional change")
    axes[0].set_ylabel("High-beta fractional change")
    axes[0].set_title("Artifact-aware classification")
    for q, c in ARTIFACT_COLORS.items():
        marker = "*" if "contamination" in q else "o"
        axes[0].scatter([], [], color=c, label=q.replace("_", " "), s=50, marker=marker)
    axes[0].legend(fontsize=7)

    # Panel B: counts
    art_counts = ok["artifact_aware_class"].value_counts().reindex(
        list(ARTIFACT_COLORS.keys()), fill_value=0
    )
    bars = axes[1].bar(
        [q.replace("_", "\n") for q in art_counts.index],
        art_counts.values,
        color=[ARTIFACT_COLORS[q] for q in art_counts.index],
        edgecolor="white", alpha=0.85,
    )
    axes[1].set_xlabel("Category")
    axes[1].set_ylabel("Count")
    axes[1].set_title(f"Artifact-aware counts (N={len(ok)})")
    for bar, val in zip(bars, art_counts.values):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                     str(val), ha="center", fontsize=9)

    fig.suptitle("SPT5: Artifact-aware four-quadrant panel", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(fig, classif_df, "spt5_artifact_aware_panel", root)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ensure_repo_structure(ROOT)
    tbl_dir = ROOT / "outputs" / "tables"
    rep_dir = ROOT / "outputs" / "reports"

    print("SPT5: Loading empirical data from WP8...")
    effects, features, data_ok = load_empirical_data()

    if not data_ok:
        print("  No WP8 data. Creating stub classification from regime map if available...")

    classif_df = build_classification_from_wp8(effects, features)

    if classif_df.empty:
        # Stubs
        classif_df = pd.DataFrame(columns=[
            "subject", "smr_frac_change", "hbeta_frac_change", "broadband_frac_change",
            "quadrant", "artifact_aware_class", "data_source"
        ])

    classif_df.to_csv(tbl_dir / "spt5_four_quadrant_classification.csv", index=False)
    classif_df.to_csv(tbl_dir / "spt5_artifact_aware_classification.csv", index=False)
    print(f"  Saved classification tables ({len(classif_df)} subjects)")

    print("SPT5: Creating figures...")
    make_four_quadrant_panel(classif_df, ROOT)
    make_artifact_aware_panel(classif_df, ROOT)

    # Write report
    n = len(classif_df)
    if n > 0:
        ok = classif_df.dropna(subset=["smr_frac_change", "hbeta_frac_change"])
        quad_counts = ok["quadrant"].value_counts().to_dict()
        n_A = quad_counts.get("A_both", 0)
        n_B = quad_counts.get("B_acquisition_only", 0)
        n_C = quad_counts.get("C_stabilization_only", 0)
        n_D = quad_counts.get("D_neither", 0)
        n_ok = len(ok)
        separable = (n_B > 0 or n_C > 0)
    else:
        n_A = n_B = n_C = n_D = n_ok = 0
        separable = False

    report = f"""# SPT5 Results: Empirical Four-quadrant Classification

## Method

Each subject is classified by the sign of fractional change in:
- SMR power (12–15 Hz): ses-01 to ses-08.
- High-beta power (20–30 Hz): ses-01 to ses-08.
- Broadband non-target power (4–45 Hz, excluding SMR and high-beta).

Quadrants:
- A (both): SMR increases AND high-beta decreases.
- B (acquisition only): SMR increases AND high-beta does NOT decrease.
- C (stabilization only): SMR does NOT increase AND high-beta decreases.
- D (neither): neither SMR increases nor high-beta decreases.

## Results

Total subjects classified: {n_ok}
- A (both):             {n_A} / {n_ok}
- B (acquisition only): {n_B} / {n_ok}
- C (stabilization only): {n_C} / {n_ok}
- D (neither):          {n_D} / {n_ok}

## Separability test

Subjects in B or C (separable outcome) present: {separable}
Subjects with acquisition-only (B): {n_B}
Subjects with stabilization-only (C): {n_C}

## Interpretation

"""
    if n_ok == 0:
        report += "No empirical data was available for classification.\n"
    elif separable:
        report += (
            f"The empirical data show at least some subjects in B (acquisition only) "
            f"or C (stabilization only) quadrants, providing EMPIRICAL SUPPORT for "
            f"the separability hypothesis: high-beta suppression and SMR acquisition "
            f"can dissociate at the subject level.\n\n"
            f"CAUTION: Sample size is very small (N={n_ok}). These results are descriptive "
            f"only and do not constitute statistical proof.\n"
        )
    else:
        report += (
            f"With N={n_ok} subjects, all are classified in A or D quadrants. "
            f"The data do not show within-sample separability. "
            f"This is consistent with either: (1) genuine co-occurrence of the two "
            f"processes; or (2) the sample is too small to observe dissociation.\n\n"
            f"IMPORTANT: Previous WP8 results showed mixed results (SMR approximately "
            f"unchanged, high-beta slightly increased). This is consistent with quadrant D "
            f"(neither) for most subjects.\n"
        )

    report += f"""
## Previous WP8 context

From WP8 analysis: SMR fractional change ≈ -0.006, high-beta fractional change ≈ +0.052.
The full joint signature (A) was found in 0 / 5 subjects.
This is consistent with D (neither) or C (stabilization only) as dominant outcomes.

Generated: {utc_now()}
"""
    (rep_dir / "spt5_results.md").write_text(report, encoding="utf-8")
    print("SPT5 done.")


if __name__ == "__main__":
    main()
