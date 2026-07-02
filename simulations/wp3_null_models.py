from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from models.null_models import NullParams, simulate_null_model, summarize_null_model
from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style


def build_grid(grid: str):
    if grid == "smoke":
        return [0.0, 0.25], [1], 8.0
    if grid == "reduced":
        return [0.0, 0.10, 0.20, 0.30, 0.40], [1, 2, 3], 24.0
    return np.linspace(0, 0.45, 10).round(3).tolist(), list(range(1, 6)), 45.0


def run(grid: str = "reduced") -> pd.DataFrame:
    ensure_repo_structure(ROOT)
    gains, seeds, duration = build_grid(grid)
    models = ["stuart_landau", "linear_ou", "damped_harmonic", "ar2"]
    rows = []
    for model_name in models:
        for seed in seeds:
            baseline_params = NullParams(model=model_name, duration_s=duration, seed=seed, feedback_gain=0.0)
            baseline_sim = simulate_null_model(baseline_params)
            baseline_metrics = summarize_null_model(baseline_sim)
            threshold = baseline_metrics["burst_threshold"]
            for gain in gains:
                params = NullParams(model=model_name, duration_s=duration, seed=seed, feedback_gain=float(gain))
                metrics = summarize_null_model(simulate_null_model(params), burst_threshold=threshold)
                rows.append(
                    {
                        "wp": "WP3",
                        "grid": grid,
                        "model": model_name,
                        "seed": int(seed),
                        "feedback_gain": float(gain),
                        **metrics,
                        "smr_power_baseline": baseline_metrics["smr_power"],
                        "beta_power_baseline": baseline_metrics["beta_power"],
                        "burst_rate_baseline": baseline_metrics["burst_rate_per_min"],
                        "burst_duration_baseline": baseline_metrics["burst_duration_s"],
                        "high_freq_baseline": baseline_metrics["high_freq_35_55_power"],
                    }
                )
    df = pd.DataFrame(rows)
    for col, base_col in [
        ("smr_power", "smr_power_baseline"),
        ("beta_power", "beta_power_baseline"),
        ("burst_rate_per_min", "burst_rate_baseline"),
        ("burst_duration_s", "burst_duration_baseline"),
        ("high_freq_35_55_power", "high_freq_baseline"),
    ]:
        df[f"{col}_change_frac"] = (df[col] - df[base_col]) / df[base_col].replace(0, np.nan)
    df["burst_change_per_beta_change"] = df["burst_rate_per_min_change_frac"] / df["beta_power_change_frac"].replace(0, np.nan)
    df.to_csv(ROOT / "outputs" / "tables" / "wp3_model_comparison.csv", index=False)
    make_figures(df)
    write_report(df, grid)
    return df


def make_figures(df: pd.DataFrame) -> None:
    set_style()
    summary = (
        df.groupby(["model", "feedback_gain"], as_index=False)
        .agg(
            beta_change=("beta_power_change_frac", "mean"),
            smr_change=("smr_power_change_frac", "mean"),
            burst_rate_change=("burst_rate_per_min_change_frac", "mean"),
            high_freq_change=("high_freq_35_55_power_change_frac", "mean"),
        )
    )
    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.2))
    for model_name, group in summary.groupby("model"):
        axes[0].plot(group["feedback_gain"], group["beta_change"], marker="o", label=model_name)
        axes[1].plot(group["feedback_gain"], group["smr_change"], marker="o", label=model_name)
        axes[2].plot(group["feedback_gain"], group["burst_rate_change"], marker="o", label=model_name)
    axes[0].set_title("High-beta suppression")
    axes[0].set_xlabel("feedback gain k")
    axes[0].set_ylabel("fractional change")
    axes[1].set_title("SMR collateral change")
    axes[1].set_xlabel("feedback gain k")
    axes[2].set_title("Burst-rate change")
    axes[2].set_xlabel("feedback gain k")
    axes[2].legend(loc="best", fontsize=7)
    save_csv_backed_figure(fig, summary, "wp3_feedback_model_comparison")

    target_gain = df["feedback_gain"].max()
    target = (
        df[df["feedback_gain"] == target_gain]
        .groupby("model", as_index=False)
        .agg(
            beta_change=("beta_power_change_frac", "mean"),
            burst_rate_change=("burst_rate_per_min_change_frac", "mean"),
            high_freq_change=("high_freq_35_55_power_change_frac", "mean"),
            ar_tau=("ar1_tau_s", "mean"),
        )
    )
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    for _, row in target.iterrows():
        ax.scatter(row["beta_change"], row["burst_rate_change"], s=80)
        ax.text(row["beta_change"], row["burst_rate_change"], row["model"], fontsize=8, ha="left", va="bottom")
    ax.axhline(0, color="0.3", lw=0.8)
    ax.axvline(0, color="0.3", lw=0.8)
    ax.set_title(f"Burst change beyond matched feedback at k={target_gain:g}")
    ax.set_xlabel("high-beta fractional change")
    ax.set_ylabel("burst-rate fractional change")
    save_csv_backed_figure(fig, target, "wp3_nonlinear_added_value_panel")


def write_report(df: pd.DataFrame, grid: str) -> None:
    summary = df[df["feedback_gain"] == df["feedback_gain"].max()].groupby("model").agg(
        beta_change=("beta_power_change_frac", "mean"),
        burst_change=("burst_rate_per_min_change_frac", "mean"),
        smr_abs=("smr_power_change_frac", lambda x: float(np.mean(np.abs(x)))),
        hf_abs=("high_freq_35_55_power_change_frac", lambda x: float(np.mean(np.abs(x)))),
    )
    lines = ["# WP3 Results: Generic-Feedback Null Models", "", f"Grid: `{grid}`.", ""]
    lines.append("At the highest tested gain, aggregate model behavior was:")
    lines.append("")
    for model_name, row in summary.iterrows():
        lines.append(
            f"- `{model_name}`: beta change {row['beta_change']:.3f}, burst-rate change {row['burst_change']:.3f}, mean abs SMR collateral {row['smr_abs']:.3f}, mean abs high-frequency collateral {row['hf_abs']:.3f}."
        )
    lines.append("")
    lines.append(
        "Interpretation: selective feedback in generic linear oscillators can suppress high-beta power, so stationary suppression alone is not specific. The nonlinear Stuart-Landau model is most informative when evaluated jointly with burst occupancy, saturation, non-target power, and validity-boundary behavior."
    )
    (ROOT / "outputs" / "reports" / "wp3_results.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", choices=["smoke", "reduced", "extended"], default="reduced")
    args = parser.parse_args()
    run(args.grid)


if __name__ == "__main__":
    main()
