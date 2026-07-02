"""NCTRL8: Figure set for active-damping/noise-control hypothesis.

Assembles 7 manuscript-candidate figures from CSV source tables.

Figures:
  1. Active-damping model schematic
  2. Separability simulation (noise damp without SMR / SMR without damp)
  3. Noise-control metrics (damping vs noise floor, diffusion, SNR)
  4. Empirical PSD/noise-floor panel
  5. Empirical burst/diffusion panel
  6. Four-quadrant noise-control classification
  7. Framework comparison panel

All figures saved as PDF, SVG, PNG with matching CSV sources.
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
import matplotlib.gridspec as gridspec

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style, FIGURE_EXTENSIONS

TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_load(name: str) -> pd.DataFrame:
    p = TBL / name
    if p.exists():
        return pd.read_csv(p)
    print(f"  WARNING: {name} not found, skipping.")
    return pd.DataFrame()


def save_fig(fig: plt.Figure, stem: str, source_df: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in FIGURE_EXTENSIONS:
        fig.savefig(FIG / f"{stem}.{ext}", dpi=220, bbox_inches="tight")
    csv_p = TBL / f"{stem}_source.csv"
    source_df.to_csv(csv_p, index=False)
    plt.close(fig)


QUAD_COLORS = {
    "A_both": "#1ABC9C",
    "B_acq_only": "#3498DB",
    "C_damp_only": "#E74C3C",
    "D_neither": "#95A5A6",
}


# ─────────────────────────────────────────────────────────
# Figure 1: Active-damping model schematic (annotated block diagram)
# ─────────────────────────────────────────────────────────
def fig1_model(sim_summary: pd.DataFrame) -> None:
    set_style()
    fig = plt.figure(figsize=(11, 6))
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.4)

    # Left: block diagram
    ax_diag = fig.add_subplot(gs[:, 0])
    ax_diag.set_xlim(0, 4)
    ax_diag.set_ylim(0, 8)
    ax_diag.axis("off")

    def box(ax, x, y, w, h, fc, label, fs=8):
        r = mpatches.FancyBboxPatch((x - w/2, y - h/2), w, h,
                                     boxstyle="round,pad=0.1",
                                     facecolor=fc, edgecolor="#333", lw=1.2)
        ax.add_patch(r)
        ax.text(x, y, label, ha="center", va="center", fontsize=fs, fontweight="bold")

    def arr(ax, x1, y1, x2, y2, lab="", col="black", lw=1.5):
        ax.annotate("", (x2, y2), (x1, y1),
                    arrowprops=dict(arrowstyle="->", color=col, lw=lw))
        if lab:
            ax.text((x1+x2)/2+0.05, (y1+y2)/2+0.08, lab, fontsize=7, color=col)

    box(ax_diag, 2, 6.8, 2.2, 0.9, "#AED6F1", "x(t): SMR target\nregulation variable", fs=8)
    box(ax_diag, 2, 4.5, 2.2, 0.9, "#A9DFBF", "eta(t): HB noise\n(fast fluctuation)", fs=8)
    box(ax_diag, 2, 2.2, 2.2, 0.9, "#F9E79F", "z(t): Broadband\ncontamination", fs=8)
    box(ax_diag, 2, 0.8, 2.2, 0.7, "#F0B27A", "Active damper\nI(|eta|>eta_thr)", fs=7.5)

    arr(ax_diag, 2, 4.05, 2, 4.05, col="#ccc")  # dummy; real arrows below
    arr(ax_diag, 2, 5.0, 2, 6.35, "c_xeta", "#2980B9", lw=1.5)
    arr(ax_diag, 2, 2.65, 2, 3.55, "z→x (contam.)", "#7D3C98", lw=1.0)
    arr(ax_diag, 2, 1.15, 2, 4.05, "k_damp·I(|eta|>thr)", "#C0392B", lw=1.5)

    ax_diag.text(2, 7.7, "Equations:", ha="center", fontsize=7.5, fontweight="bold")
    ax_diag.text(2, 7.45, "dx = a_x(x*-x)dt + c_xη·ηdt + σ_x dW_x", ha="center", fontsize=6.8)
    ax_diag.text(2, 7.2, "dη = [-λ_η·η - k_d·I(|η|>η_thr)·η]dt + σ_η dW_η", ha="center", fontsize=6.8)
    ax_diag.text(2, 6.95, "dz = -λ_z·z dt + σ_z dW_z", ha="center", fontsize=6.8)
    ax_diag.set_title("(A) Model schematic", fontsize=9)

    # Right: regime bars
    if not sim_summary.empty:
        ax_occ = fig.add_subplot(gs[0, 1:])
        ax_snr = fig.add_subplot(gs[1, 1:])
        names = sim_summary["name"].tolist()
        x_pos = np.arange(len(names))
        colors_q = [QUAD_COLORS.get("A_both" if (r.smr_acquired and r.noise_damped)
                                    else "B_acq_only" if (r.smr_acquired and not r.noise_damped)
                                    else "C_damp_only" if (not r.smr_acquired and r.noise_damped)
                                    else "D_neither", "#95A5A6")
                    for r in sim_summary.itertuples()]

        ax_occ.bar(x_pos, sim_summary["reward_occupancy"].values, color=colors_q, alpha=0.85)
        ax_occ.set_xticks(x_pos)
        ax_occ.set_xticklabels([n[:12] for n in names], rotation=30, ha="right", fontsize=6)
        ax_occ.set_ylabel("Reward-state occupancy")
        ax_occ.set_title("(B) Six regimes: reward occupancy")
        ax_occ.set_ylim(0, 1)

        ax_snr.bar(x_pos, sim_summary["smr_snr"].values, color=colors_q, alpha=0.85)
        ax_snr.set_xticks(x_pos)
        ax_snr.set_xticklabels([n[:12] for n in names], rotation=30, ha="right", fontsize=6)
        ax_snr.set_ylabel("SMR SNR")
        ax_snr.set_title("(C) Six regimes: SMR SNR")

        patches = [mpatches.Patch(color=c, label=q) for q, c in QUAD_COLORS.items()]
        ax_occ.legend(handles=patches, fontsize=6, ncol=2)

    fig.suptitle("NCTRL8 Figure 1: Active-damping closed-loop model", fontsize=10, fontweight="bold")
    save_fig(fig, "nctrl8_figure_1_active_damping_model",
             sim_summary[["name", "smr_acquired", "noise_damped", "reward_occupancy", "smr_snr"]]
             if not sim_summary.empty else pd.DataFrame())


# ─────────────────────────────────────────────────────────
# Figure 2: Separability simulation
# ─────────────────────────────────────────────────────────
def fig2_separability(grid_df: pd.DataFrame) -> None:
    set_style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

    if grid_df.empty:
        fig.suptitle("No data")
        save_fig(fig, "nctrl8_figure_2_separability_simulation", pd.DataFrame())
        return

    # A: k_damp vs reward occupancy, colored by SMR acquired
    for acq, col, lab in [(True, "#3498DB", "SMR acq.=T"), (False, "#E74C3C", "SMR acq.=F")]:
        sg = grid_df[grid_df["smr_acquired"] == acq]
        axes[0].scatter(sg["k_damp"], sg["reward_occupancy"], color=col, label=lab,
                         s=40, alpha=0.75)
    axes[0].set_xlabel("k_damp (active damping gain)")
    axes[0].set_ylabel("Reward-state occupancy")
    axes[0].set_title("(A) Damping gain vs reward occupancy\n[damping improves quality without acq.]")
    axes[0].legend(fontsize=7)

    # B: Quadrant scatter — separability
    quad_counts = grid_df["quadrant"].value_counts()
    for q, grp in grid_df.groupby("quadrant"):
        axes[1].scatter(grp["a_x"], grp["k_damp"], c=QUAD_COLORS.get(q, "gray"),
                         label=f"{q} (n={len(grp)})", s=50, alpha=0.8,
                         edgecolors="white", linewidths=0.3)
    axes[1].set_xlabel("a_x (SMR drive)")
    axes[1].set_ylabel("k_damp (damping gain)")
    axes[1].set_title("(B) Four-quadrant separability\n[A=both, B=acq only, C=damp only, D=neither]")
    axes[1].legend(fontsize=6)

    # C: c_xeta effect — noise coupling degrades SMR SNR
    for damp, col, lab in [(0.0, "#E74C3C", "k_damp=0 (no damp)"),
                             (8.0, "#1ABC9C", "k_damp=8 (high damp)")]:
        sg = grid_df[grid_df["k_damp"] == damp]
        if not sg.empty:
            axes[2].scatter(sg["c_xeta"], sg["smr_snr"], color=col, label=lab, s=50, alpha=0.8)
    axes[2].set_xlabel("c_xeta (noise coupling to SMR)")
    axes[2].set_ylabel("SMR SNR")
    axes[2].set_title("(C) Noise coupling vs SMR SNR\n[damping protects from noise injection]")
    axes[2].legend(fontsize=7)

    fig.suptitle("NCTRL8 Figure 2: Separability simulation", fontsize=10, fontweight="bold")
    plt.tight_layout()
    save_fig(fig, "nctrl8_figure_2_separability_simulation",
             grid_df[["k_damp", "a_x", "sigma_eta", "c_xeta",
                       "quadrant", "smr_acquired", "noise_damped",
                       "reward_occupancy", "smr_snr", "hf_noise_floor"]])


# ─────────────────────────────────────────────────────────
# Figure 3: Noise-control metrics panel
# ─────────────────────────────────────────────────────────
def fig3_metrics(grid_df: pd.DataFrame) -> None:
    set_style()
    fig, axes = plt.subplots(2, 3, figsize=(13, 9))

    if grid_df.empty:
        save_fig(fig, "nctrl8_figure_3_noise_control_metrics", pd.DataFrame())
        return

    cmap = plt.cm.viridis

    def scatter_cmap(ax, x, y, c, xlabel, ylabel, title, cbar_label):
        sc = ax.scatter(x, y, c=c, cmap=cmap, s=40, alpha=0.75)
        plt.colorbar(sc, ax=ax, label=cbar_label)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)

    scatter_cmap(axes[0, 0], grid_df["k_damp"], grid_df["hb_variance"],
                  grid_df["sigma_eta"], "k_damp", "HB variance (var of eta)",
                  "(A) Damping vs HB variance", "sigma_eta")
    scatter_cmap(axes[0, 1], grid_df["k_damp"], grid_df["hb_burst_occupancy"],
                  grid_df["sigma_eta"], "k_damp", "HB burst occupancy",
                  "(B) Damping vs burst occupancy", "sigma_eta")
    scatter_cmap(axes[0, 2], grid_df["k_damp"], grid_df["hf_noise_floor"],
                  grid_df["a_x"], "k_damp", "HF noise floor (std eta)",
                  "(C) Damping vs HF noise floor", "a_x")
    scatter_cmap(axes[1, 0], grid_df["k_damp"], grid_df["diffusion_x"],
                  grid_df["c_xeta"], "k_damp", "SMR diffusion coef.",
                  "(D) Damping vs x diffusion", "c_xeta")
    scatter_cmap(axes[1, 1], grid_df["k_damp"], grid_df["smr_snr"],
                  grid_df["a_x"], "k_damp", "SMR SNR",
                  "(E) Damping vs SMR SNR", "a_x")
    scatter_cmap(axes[1, 2], grid_df["k_damp"], grid_df["reward_occupancy"],
                  grid_df["a_x"], "k_damp", "Reward-state occupancy",
                  "(F) Damping vs reward occupancy", "a_x")

    fig.suptitle("NCTRL8 Figure 3: Noise-control metrics vs damping gain",
                  fontsize=10, fontweight="bold")
    plt.tight_layout()
    save_fig(fig, "nctrl8_figure_3_noise_control_metrics",
             grid_df[["k_damp", "a_x", "sigma_eta", "c_xeta", "hb_variance",
                       "hb_burst_occupancy", "hf_noise_floor", "diffusion_x",
                       "smr_snr", "reward_occupancy"]])


# ─────────────────────────────────────────────────────────
# Figure 4: Empirical noise-floor panel
# ─────────────────────────────────────────────────────────
def fig4_noise_floor(noise_df: pd.DataFrame) -> None:
    set_style()
    fig, axes = plt.subplots(2, 3, figsize=(13, 9))

    if noise_df.empty:
        save_fig(fig, "nctrl8_figure_4_empirical_noise_floor", pd.DataFrame())
        return

    ch_df = noise_df[noise_df["channel"] == "mean"].copy()
    sessions = sorted(ch_df["session"].unique())
    cmap_ses = {"ses-01": "#1f77b4", "ses-08": "#ff7f0e"}

    def plot_by_ses(ax, col, ylabel, title, log=False):
        for ses in sessions:
            sdf = ch_df[ch_df["session"] == ses].dropna(subset=[col])
            y = np.log10(sdf[col].values + 1e-30) if log else sdf[col].values
            ax.scatter(range(len(sdf)), y, color=cmap_ses[ses], label=ses, s=45, alpha=0.8)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=7)

    plot_by_ses(axes[0, 0], "p_smr", "P_SMR (abs)", "(A) SMR power", log=True)
    plot_by_ses(axes[0, 1], "p_hb", "P_HB (abs)", "(B) High-beta power", log=True)
    plot_by_ses(axes[0, 2], "smr_snr_abs", "SMR SNR", "(C) SMR SNR", log=True)
    plot_by_ses(axes[1, 0], "aperiodic_slope", "1/f slope", "(D) Aperiodic 1/f slope")
    plot_by_ses(axes[1, 1], "hb_residual_above_1f", "HB residual", "(E) HB residual above 1/f\n[>0 = band-specific HB]")
    plot_by_ses(axes[1, 2], "broad_contam_idx", "Broadband contam.", "(F) Broadband contamination index")

    for ax in axes.flatten():
        ax.axhline(0, color="gray", ls="--", lw=0.6, alpha=0.5)

    fig.suptitle("NCTRL8 Figure 4: Empirical noise-floor analysis (n=5, ds004446)",
                  fontsize=10, fontweight="bold")
    plt.tight_layout()
    save_fig(fig, "nctrl8_figure_4_empirical_noise_floor",
             ch_df[["subject", "session", "condition", "p_smr", "p_hb",
                     "smr_snr_abs", "aperiodic_slope", "hb_residual_above_1f",
                     "broad_contam_idx"]])


# ─────────────────────────────────────────────────────────
# Figure 5: Empirical burst/diffusion panel
# ─────────────────────────────────────────────────────────
def fig5_burst_diff(burst_df: pd.DataFrame) -> None:
    set_style()
    fig, axes = plt.subplots(2, 3, figsize=(13, 9))

    if burst_df.empty:
        save_fig(fig, "nctrl8_figure_5_burst_diffusion", pd.DataFrame())
        return

    sessions = sorted(burst_df["session"].unique())
    cmap_ses = {"ses-01": "#1f77b4", "ses-08": "#ff7f0e"}

    def plot_metric(ax, col, ylabel, title):
        for ses in sessions:
            sdf = burst_df[burst_df["session"] == ses].dropna(subset=[col])
            ax.scatter(range(len(sdf)), sdf[col].values, color=cmap_ses[ses],
                       label=ses, s=45, alpha=0.8)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend(fontsize=7)

    plot_metric(axes[0, 0], "hb_burst_rate_per_min", "Bursts/min", "(A) HB burst rate")
    plot_metric(axes[0, 1], "hb_burst_duration_s", "Duration (s)", "(B) HB burst duration")
    plot_metric(axes[0, 2], "hb_burst_occupancy", "Occupancy", "(C) HB burst occupancy")
    plot_metric(axes[1, 0], "hb_broad_corr", "Correlation", "(D) HB-broadband correlation\n[+ = HB tracks noise]")
    plot_metric(axes[1, 1], "smr_diffusion_coef", "Diffusion coef.", "(E) SMR state diffusion")
    plot_metric(axes[1, 2], "hb_smr_block_corr", "Correlation", "(F) HB-SMR block correlation\n[- = HB suppresses SMR]")

    for ax in axes.flatten():
        ax.axhline(0, color="gray", ls="--", lw=0.6, alpha=0.5)

    fig.suptitle("NCTRL8 Figure 5: Empirical burst/diffusion (n=5, ds004446)",
                  fontsize=10, fontweight="bold")
    plt.tight_layout()
    save_fig(fig, "nctrl8_figure_5_burst_diffusion",
             burst_df[["subject", "session", "condition", "hb_burst_rate_per_min",
                        "hb_burst_duration_s", "hb_burst_occupancy", "hb_broad_corr",
                        "smr_diffusion_coef", "hb_smr_block_corr"]])


# ─────────────────────────────────────────────────────────
# Figure 6: Four-quadrant noise-control classification
# ─────────────────────────────────────────────────────────
def fig6_quadrant(classif_df: pd.DataFrame) -> None:
    set_style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 5))

    if classif_df.empty:
        save_fig(fig, "nctrl8_figure_6_four_quadrant_noise", pd.DataFrame())
        return

    # A: primary quadrant scatter
    ax = axes[0]
    for _, row in classif_df.iterrows():
        q = row.get("quadrant_primary", "D_neither")
        ax.scatter(row.get("delta_hb_power_log", np.nan),
                    row.get("delta_smr_snr_log", np.nan),
                    color=QUAD_COLORS.get(q, "gray"), s=160,
                    edgecolors="black", linewidths=0.8, zorder=5)
        ax.annotate(str(row["subject"])[:7],
                     (row.get("delta_hb_power_log", np.nan),
                      row.get("delta_smr_snr_log", np.nan)),
                     fontsize=7, ha="center", va="bottom",
                     xytext=(0, 5), textcoords="offset points")
    ax.axhline(0, color="black", ls="--", lw=0.8)
    ax.axvline(0, color="black", ls="--", lw=0.8)
    ax.set_xlabel("Δ log(P_HB) [−=damped]")
    ax.set_ylabel("Δ log(SMR SNR) [+=improved]")
    ax.set_title("(A) Primary classification\n(SNR vs HB power)")
    patches = [mpatches.Patch(color=c, label=q) for q, c in QUAD_COLORS.items()]
    ax.legend(handles=patches, fontsize=6)

    # B: quadrant counts by definition
    quad_cols = ["quadrant_primary", "quadrant_burst", "quadrant_resid", "quadrant_diff"]
    labels = ["Primary\n(SNR/HB)", "Burst\nrate", "1/f\nresid.", "Diffusion"]
    quads = ["A_both", "B_acq_only", "C_damp_only", "D_neither"]
    bottoms = np.zeros(len(quad_cols))
    x_pos = np.arange(len(quad_cols))
    for q in quads:
        counts = np.array([classif_df.get(col, pd.Series()).value_counts().get(q, 0)
                            if col in classif_df.columns else 0 for col in quad_cols])
        axes[1].bar(x_pos, counts, bottom=bottoms, color=QUAD_COLORS[q], label=q, alpha=0.85)
        for xi, (cnt, bot) in enumerate(zip(counts, bottoms)):
            if cnt > 0:
                axes[1].text(xi, bot + cnt / 2, str(int(cnt)), ha="center", va="center",
                              fontsize=10, fontweight="bold", color="white")
        bottoms += counts.astype(float)
    axes[1].set_xticks(x_pos)
    axes[1].set_xticklabels(labels, fontsize=8)
    axes[1].set_ylabel("N subjects")
    axes[1].set_title("(B) Quadrant sensitivity\nto metric definition")
    axes[1].legend(fontsize=6)

    # C: burst rate change vs SNR change
    ax = axes[2]
    if "delta_hb_burst_rate" in classif_df.columns:
        for _, row in classif_df.iterrows():
            q = row.get("quadrant_burst", "D_neither")
            ax.scatter(row.get("delta_hb_burst_rate", np.nan),
                        row.get("delta_smr_snr_log", np.nan),
                        color=QUAD_COLORS.get(q, "gray"), s=120,
                        edgecolors="black", linewidths=0.8)
            ax.annotate(str(row["subject"])[:7],
                         (row.get("delta_hb_burst_rate", np.nan),
                          row.get("delta_smr_snr_log", np.nan)),
                         fontsize=7, ha="center", va="bottom",
                         xytext=(0, 5), textcoords="offset points")
    ax.axhline(0, color="black", ls="--", lw=0.8)
    ax.axvline(0, color="black", ls="--", lw=0.8)
    ax.set_xlabel("Δ HB burst rate [−=damped]")
    ax.set_ylabel("Δ log(SMR SNR)")
    ax.set_title("(C) Burst-rate definition\n(burst change vs SNR)")

    fig.suptitle("NCTRL8 Figure 6: Four-quadrant noise-control classification",
                  fontsize=10, fontweight="bold")
    plt.tight_layout()
    save_fig(fig, "nctrl8_figure_6_four_quadrant_noise", classif_df)


# ─────────────────────────────────────────────────────────
# Figure 7: Framework comparison
# ─────────────────────────────────────────────────────────
def fig7_framework(fw_df: pd.DataFrame) -> None:
    set_style()
    fig, ax = plt.subplots(figsize=(10, 5))

    if fw_df.empty:
        save_fig(fig, "nctrl8_figure_7_framework_comparison", pd.DataFrame())
        return

    crit_cols = [c for c in fw_df.columns if c not in
                  ["framework", "total_score", "max_score", "pct_score"]]
    score_mat = fw_df.set_index("framework")[crit_cols].values.astype(float)
    fw_labels = fw_df["framework"].tolist()
    totals = fw_df["total_score"].values
    max_score = fw_df["max_score"].values[0]

    im = ax.imshow(score_mat.T, aspect="auto", vmin=0, vmax=2,
                   cmap=plt.cm.get_cmap("RdYlGn", 3))
    ax.set_xticks(range(len(fw_labels)))
    ax.set_xticklabels(fw_labels, rotation=25, ha="right", fontsize=8)
    ax.set_yticks(range(len(crit_cols)))
    ax.set_yticklabels(crit_cols, fontsize=7.5)
    for i in range(len(fw_labels)):
        for j in range(len(crit_cols)):
            val = score_mat[i, j]
            ax.text(i, j, f"{int(val)}", ha="center", va="center", fontsize=8,
                    color="white" if val != 1 else "black", fontweight="bold")
    ax.set_title(
        f"NCTRL8 Figure 7: Framework comparison (NCTRL scores "
        f"{int(totals[-1])}/{max_score}; SL scores {int(totals[0])}/{max_score})",
        fontsize=9
    )
    plt.colorbar(im, ax=ax, ticks=[0, 1, 2], label="Score", shrink=0.7)
    plt.tight_layout()
    save_fig(fig, "nctrl8_figure_7_framework_comparison", fw_df)


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────
def write_notes() -> None:
    notes = f"""# NCTRL8 Figure Notes

Generated: {utc_now()}

## Figure 1: nctrl8_figure_1_active_damping_model.*
Model schematic (block diagram) and six-regime reward occupancy / SMR SNR summary.
Source: nctrl1_simulation_summary.csv

## Figure 2: nctrl8_figure_2_separability_simulation.*
Parameter-grid separability: k_damp vs reward occupancy, four-quadrant scatter,
noise coupling (c_xeta) vs SMR SNR.
Source: nctrl1_parameter_grid.csv

## Figure 3: nctrl8_figure_3_noise_control_metrics.*
Six panels: damping gain vs HB variance, burst occupancy, noise floor,
x-diffusion, SMR SNR, reward occupancy.
Source: nctrl2_noise_control_metrics.csv

## Figure 4: nctrl8_figure_4_empirical_noise_floor.*
Empirical: SMR power, HB power, SMR SNR, 1/f slope, HB residual, broadband contamination.
Source: nctrl3_empirical_noise_features.csv

## Figure 5: nctrl8_figure_5_burst_diffusion.*
Empirical: HB burst rate/duration/occupancy, HB-broadband correlation,
SMR diffusion, HB-SMR block correlation.
Source: nctrl4_burst_instability_features.csv

## Figure 6: nctrl8_figure_6_four_quadrant_noise.*
Four-quadrant noise-control classification (primary + sensitivity to metric definition).
Source: nctrl5_four_quadrant_noise_classification.csv

## Figure 7: nctrl8_figure_7_framework_comparison.*
Framework comparison heatmap: 4 frameworks × 8 criteria.
Source: nctrl7_framework_comparison.csv

Generated: {utc_now()}
"""
    (ROOT / "outputs" / "reports" / "nctrl8_figure_notes.md").write_text(notes, encoding="utf-8")


def main() -> None:
    ensure_repo_structure(ROOT)

    print("NCTRL8: Loading tables...")
    sim_summary = safe_load("nctrl1_simulation_summary.csv")
    grid_df = safe_load("nctrl1_parameter_grid.csv")
    noise_df = safe_load("nctrl3_empirical_noise_features.csv")
    burst_df = safe_load("nctrl4_burst_instability_features.csv")
    classif_df = safe_load("nctrl5_four_quadrant_noise_classification.csv")
    fw_df = safe_load("nctrl7_framework_comparison.csv")

    print("NCTRL8: Generating figures...")
    fig1_model(sim_summary)
    fig2_separability(grid_df)
    fig3_metrics(grid_df)
    fig4_noise_floor(noise_df)
    fig5_burst_diff(burst_df)
    fig6_quadrant(classif_df)
    fig7_framework(fw_df)

    write_notes()
    print("NCTRL8 done.")


if __name__ == "__main__":
    main()
