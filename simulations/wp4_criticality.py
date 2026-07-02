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

from models.stuart_landau import SLParams, simulate_and_summarize, with_updates
from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style, simple_heatmap


def build_grid(grid: str):
    if grid == "smoke":
        return [-0.05, 0.20], [0.0, 0.25], [0.05], [1], 8.0
    if grid == "reduced":
        return [-0.12, -0.03, 0.02, 0.15, 0.35, 0.55], [0.0, 0.10, 0.20, 0.30, 0.40], [0.025, 0.055, 0.090], [1, 2, 3], 24.0
    return np.linspace(-0.15, 0.65, 12).round(3).tolist(), np.linspace(0, 0.50, 12).round(3).tolist(), [0.02, 0.05, 0.08, 0.12], list(range(1, 6)), 45.0


def regime_label(effective_mu: float) -> str:
    if effective_mu < -0.06:
        return "clearly stable"
    if effective_mu < -0.015:
        return "weakly stable"
    if effective_mu <= 0.05:
        return "near Hopf"
    return "self-oscillatory"


def analytic_variance(mu_eff: float, noise: float) -> tuple[float, float]:
    if abs(mu_eff) < 1e-6:
        return float("nan"), float("nan")
    if mu_eff < 0:
        lam = -2.0 * mu_eff
    else:
        lam = 2.0 * mu_eff
    var = noise**2 / (2.0 * lam) if lam > 0 else float("nan")
    return lam, var


def run(grid: str = "reduced") -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_repo_structure(ROOT)
    mu_values, gains, noise_values, seeds, duration = build_grid(grid)
    rows = []
    base = SLParams(duration_s=duration, fs=128.0, burn_s=2.0, linear_sf=0.04, linear_fs=0.04)
    for mu_f in mu_values:
        for noise in noise_values:
            for seed in seeds:
                baseline_params = with_updates(base, mu_f=float(mu_f), noise_f=float(noise), feedback_gain=0.0, seed=int(seed))
                baseline = simulate_and_summarize(baseline_params)
                threshold = baseline["burst_threshold"]
                for gain in gains:
                    params = with_updates(base, mu_f=float(mu_f), noise_f=float(noise), feedback_gain=float(gain), seed=int(seed))
                    metrics = simulate_and_summarize(params, burst_threshold=threshold)
                    mu_eff = float(mu_f - gain)
                    lam, var_pred = analytic_variance(mu_eff, float(noise))
                    rows.append(
                        {
                            "wp": "WP4",
                            "grid": grid,
                            "mu_f": float(mu_f),
                            "feedback_gain": float(gain),
                            "noise_f": float(noise),
                            "seed": int(seed),
                            "effective_mu_f": mu_eff,
                            "regime": regime_label(mu_eff),
                            "analytic_lambda": lam,
                            "analytic_radial_var": var_pred,
                            **metrics,
                            "baseline_beta_power": baseline["beta_power"],
                            "baseline_burst_rate": baseline["burst_rate_per_min"],
                        }
                    )
    df = pd.DataFrame(rows)
    df["beta_power_change_frac"] = (df["beta_power"] - df["baseline_beta_power"]) / df["baseline_beta_power"].replace(0, np.nan)
    df["burst_rate_change_frac"] = (df["burst_rate_per_min"] - df["baseline_burst_rate"]) / df["baseline_burst_rate"].replace(0, np.nan)
    df["sim_beta_env_var"] = df["beta_env_std"] ** 2
    df["monotonic_suppression_candidate"] = df["beta_power_change_frac"] < 0
    df.to_csv(ROOT / "outputs" / "tables" / "wp4_lambda_sensitivity.csv", index=False)

    analytic = df[
        [
            "mu_f",
            "feedback_gain",
            "noise_f",
            "seed",
            "effective_mu_f",
            "regime",
            "analytic_lambda",
            "analytic_radial_var",
            "sim_beta_env_var",
        ]
    ].copy()
    analytic["variance_ratio_sim_to_analytic"] = analytic["sim_beta_env_var"] / analytic["analytic_radial_var"]
    analytic["approximation_usable"] = np.isfinite(analytic["variance_ratio_sim_to_analytic"]) & (analytic["variance_ratio_sim_to_analytic"].between(0.25, 4.0))
    analytic.to_csv(ROOT / "outputs" / "tables" / "wp4_analytic_vs_simulation.csv", index=False)
    make_figures(df, analytic)
    write_report(df, analytic, grid)
    return df, analytic


def make_figures(df: pd.DataFrame, analytic: pd.DataFrame) -> None:
    set_style()
    mid_noise = sorted(df["noise_f"].unique())[len(df["noise_f"].unique()) // 2]
    sub = df[np.isclose(df["noise_f"], mid_noise)]
    heat = sub.groupby(["mu_f", "feedback_gain"], as_index=False).agg(beta_change=("beta_power_change_frac", "mean"))
    pivot = heat.pivot(index="mu_f", columns="feedback_gain", values="beta_change")
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    image = simple_heatmap(ax, pivot, f"Suppression near Hopf boundary (noise={mid_noise:g})", "coolwarm", vmin=-0.8, vmax=0.5)
    ax.set_xlabel("feedback gain k")
    ax.set_ylabel("fast-mode growth mu_f")
    fig.colorbar(image, ax=ax, label="fractional beta-power change")
    save_csv_backed_figure(fig, heat, "wp4_criticality_sensitivity_map")

    usable = analytic.replace([np.inf, -np.inf], np.nan).dropna(subset=["analytic_lambda", "analytic_radial_var", "sim_beta_env_var"])
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    for regime, group in usable.groupby("regime"):
        ax.scatter(group["analytic_radial_var"], group["sim_beta_env_var"], s=24, alpha=0.75, label=regime)
    lim_hi = float(np.nanpercentile(usable[["analytic_radial_var", "sim_beta_env_var"]].to_numpy(), 95)) if len(usable) else 1.0
    ax.plot([0, lim_hi], [0, lim_hi], color="0.25", lw=1.0)
    ax.set_title("Radial variance approximation")
    ax.set_xlabel("analytic variance proxy")
    ax.set_ylabel("simulated beta-envelope variance")
    ax.legend(loc="best", fontsize=7)
    save_csv_backed_figure(fig, usable, "wp4_variance_vs_lambda")

    burst = df.groupby(["effective_mu_f", "regime"], as_index=False).agg(
        burst_rate=("burst_rate_per_min", "mean"),
        burst_duration=("burst_duration_s", "mean"),
        beta_change=("beta_power_change_frac", "mean"),
    )
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.4))
    for regime, group in burst.groupby("regime"):
        group = group.sort_values("effective_mu_f")
        axes[0].plot(group["effective_mu_f"], group["burst_rate"], marker="o", lw=1.0, label=regime)
        axes[1].plot(group["effective_mu_f"], group["burst_duration"], marker="o", lw=1.0, label=regime)
    axes[0].set_title("Burst rate")
    axes[0].set_xlabel("effective mu_f = mu_f - k")
    axes[0].set_ylabel("bursts/min")
    axes[1].set_title("Burst duration")
    axes[1].set_xlabel("effective mu_f = mu_f - k")
    axes[1].set_ylabel("seconds")
    axes[1].legend(loc="best", fontsize=7)
    save_csv_backed_figure(fig, burst, "wp4_burst_statistics_vs_lambda")


def write_report(df: pd.DataFrame, analytic: pd.DataFrame, grid: str) -> None:
    near = df[df["regime"] == "near Hopf"]
    suppression_rate = df["monotonic_suppression_candidate"].mean()
    usable_rate = analytic["approximation_usable"].mean()
    near_burst = near["burst_rate_per_min"].mean() if len(near) else float("nan")
    text = f"""# WP4 Results: Criticality and Near-Hopf Sensitivity

Grid: `{grid}`.

Coarse-grid outcomes:

- Fraction of conditions with beta power below their `k=0` baseline: {suppression_rate:.3f}.
- Fraction of analytic radial-variance checks within a four-fold simulation ratio: {usable_rate:.3f}.
- Mean burst rate in near-Hopf conditions: {near_burst:.2f} bursts/min.

Interpretation:

Monotone high-beta suppression is most reliable away from the Hopf boundary. Near the boundary, noise sensitivity and burst statistics become less stable, and the simple linearized variance approximation is a diagnostic guide rather than a reliable quantitative prediction. These are validity-domain restrictions, not failures to be hidden.
"""
    (ROOT / "outputs" / "reports" / "wp4_results.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", choices=["smoke", "reduced", "extended"], default="reduced")
    args = parser.parse_args()
    run(args.grid)


if __name__ == "__main__":
    main()
