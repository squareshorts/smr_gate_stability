from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style, simple_heatmap


def require_table(name: str) -> pd.DataFrame:
    path = ROOT / "outputs" / "tables" / name
    if not path.exists():
        raise FileNotFoundError(f"Required table missing: {path}")
    return pd.read_csv(path)


def figure_1() -> None:
    wp1 = require_table("wp1_constraint_validity.csv")
    source = wp1[(wp1["coupling_type"].isin(["none", "symmetric_linear"])) & (wp1["epsilon"].isin([0.0, 0.03, 0.06]))].copy()
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.5))
    for label, group in source.groupby(["coupling_type", "epsilon"]):
        name = f"{label[0]}, eps={label[1]:g}"
        group = group.sort_values("feedback_gain")
        axes[0].plot(group["feedback_gain"], group["beta_change_frac"], marker="o", lw=1.0, label=name)
        axes[1].plot(group["feedback_gain"], group["smr_change_frac"], marker="o", lw=1.0, label=name)
    axes[0].axhline(0, color="0.25", lw=0.8)
    axes[1].axhline(0, color="0.25", lw=0.8)
    axes[0].set_title("Fast-mode suppression")
    axes[0].set_xlabel("feedback gain k")
    axes[0].set_ylabel("high-beta change")
    axes[1].set_title("Slow-mode invariance")
    axes[1].set_xlabel("feedback gain k")
    axes[1].set_ylabel("SMR change")
    axes[1].legend(loc="best", fontsize=7)
    save_csv_backed_figure(fig, source, "wp9_CN_main_figure_1_model_validity")


def figure_2() -> None:
    wp1 = require_table("wp1_constraint_validity.csv")
    source = wp1.copy()
    source["valid_code"] = source["directional_valid"].astype(int)
    pivot = source.pivot_table(index="epsilon", columns="feedback_gain", values="valid_code", aggfunc="mean").fillna(0)
    set_style()
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    image = simple_heatmap(ax, pivot, "Coupling robustness and failure", "viridis", vmin=0, vmax=1)
    ax.set_xlabel("feedback gain k")
    ax.set_ylabel("coupling epsilon")
    fig.colorbar(image, ax=ax, label="validity fraction")
    save_csv_backed_figure(fig, source, "wp9_CN_main_figure_2_coupling_failure")


def figure_3() -> None:
    wp4 = require_table("wp4_lambda_sensitivity.csv")
    source = wp4.groupby(["effective_mu_f", "regime"], as_index=False).agg(
        beta_change=("beta_power_change_frac", "mean"),
        burst_rate=("burst_rate_per_min", "mean"),
        burst_duration=("burst_duration_s", "mean"),
    )
    source = source.sort_values("effective_mu_f")
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.5))
    for regime, group in source.groupby("regime"):
        axes[0].plot(group["effective_mu_f"], group["beta_change"], marker="o", label=regime)
        axes[1].plot(group["effective_mu_f"], group["burst_rate"], marker="o", label=regime)
    axes[0].axvline(0, color="0.25", lw=0.8)
    axes[0].axhline(0, color="0.25", lw=0.8)
    axes[0].set_title("Criticality sensitivity")
    axes[0].set_xlabel("effective mu_f")
    axes[0].set_ylabel("high-beta change")
    axes[1].axvline(0, color="0.25", lw=0.8)
    axes[1].set_title("Burst instability")
    axes[1].set_xlabel("effective mu_f")
    axes[1].set_ylabel("bursts/min")
    axes[1].legend(loc="best", fontsize=7)
    save_csv_backed_figure(fig, source, "wp9_CN_main_figure_3_criticality_bursts")


def figure_4() -> None:
    wp3 = require_table("wp3_model_comparison.csv")
    source = wp3.groupby(["model", "feedback_gain"], as_index=False).agg(
        beta_change=("beta_power_change_frac", "mean"),
        smr_change=("smr_power_change_frac", "mean"),
        burst_change=("burst_rate_per_min_change_frac", "mean"),
    )
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.4))
    for model_name, group in source.groupby("model"):
        axes[0].plot(group["feedback_gain"], group["beta_change"], marker="o", label=model_name)
        axes[1].plot(group["feedback_gain"], group["burst_change"], marker="o", label=model_name)
    axes[0].set_title("Generic feedback")
    axes[0].set_xlabel("feedback gain k")
    axes[0].set_ylabel("high-beta change")
    axes[1].set_title("Burst response")
    axes[1].set_xlabel("feedback gain k")
    axes[1].set_ylabel("burst-rate change")
    axes[1].legend(loc="best", fontsize=7)
    save_csv_backed_figure(fig, source, "wp9_CN_main_figure_4_null_models")


def figure_5() -> None:
    thresh = require_table("wp5_threshold_sensitivity.csv")
    sur = require_table("wp5_surrogate_burst_controls.csv")
    source_a = thresh[thresh["condition"] == "feedback"].groupby("threshold_method", as_index=False).agg(
        burst_rate_change=("burst_rate_change_frac", "mean"),
        burst_duration_change=("burst_duration_change_frac", "mean"),
    )
    source_b = sur.groupby("control", as_index=False).agg(
        beta_power_change=("beta_power_change_frac_vs_baseline", "mean"),
        burst_rate_change=("burst_rate_change_frac_vs_baseline", "mean"),
    )
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    axes[0].bar(source_a["threshold_method"], source_a["burst_rate_change"], color="#3b6ea8")
    axes[0].axhline(0, color="0.25", lw=0.8)
    axes[0].set_title("Threshold robustness")
    axes[0].set_ylabel("burst-rate change")
    axes[0].tick_params(axis="x", rotation=45)
    for _, row in source_b.iterrows():
        axes[1].scatter(row["beta_power_change"], row["burst_rate_change"], s=80)
        axes[1].text(row["beta_power_change"], row["burst_rate_change"], row["control"], fontsize=8, va="bottom", ha="left")
    axes[1].axhline(0, color="0.25", lw=0.8)
    axes[1].axvline(0, color="0.25", lw=0.8)
    axes[1].set_title("Surrogate controls")
    axes[1].set_xlabel("beta-power change")
    axes[1].set_ylabel("burst-rate change")
    save_csv_backed_figure(fig, source_a, "wp9_CN_main_figure_5_threshold_surrogates", extra_sources=[("surrogate", source_b)])


def maybe_empirical_figures() -> list[str]:
    features = ROOT / "outputs" / "tables" / "wp8_empirical_features.csv"
    effects = ROOT / "outputs" / "tables" / "wp8_prepost_or_sessionwise_effects.csv"
    if not features.exists() or not effects.exists():
        return ["Empirical main figures 6 and 7 were not generated because WP8 did not produce real EEG-derived tables."]
    feat = pd.read_csv(features)
    eff = pd.read_csv(effects)
    if feat.empty or eff.empty:
        return ["Empirical main figures 6 and 7 were not generated because WP8 tables were empty."]
    return ["Empirical tables exist, but this first-pass assembler requires a finalized WP8 schema before plotting."]


def write_notes(notes: list[str]) -> None:
    text = """# WP9 Figure Notes for Cognitive Neurodynamics

Generated main-figure candidates:

- Figure 1: model validity condition from WP1.
- Figure 2: coupling robustness and failure regimes from WP1.
- Figure 3: criticality, variance sensitivity, and burst instability from WP4.
- Figure 4: null-model comparison from WP3.
- Figure 5: burst-threshold and surrogate robustness from WP5.

Empirical figure status:

""" + "\n".join(f"- {note}" for note in notes) + """

Each generated figure has a matching source CSV in `outputs/tables`.
"""
    (ROOT / "outputs" / "reports" / "wp9_figure_notes_for_Cognitive_Neurodynamics.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_repo_structure(ROOT)
    figure_1()
    figure_2()
    figure_3()
    figure_4()
    figure_5()
    notes = maybe_empirical_figures()
    write_notes(notes)


if __name__ == "__main__":
    main()
