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

from models.stuart_landau import SLParams, psd_table, simulate_and_summarize, simulate_two_mode, timeseries_table, with_updates
from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style, simple_heatmap


def coupling_kwargs(coupling_type: str, epsilon: float) -> dict[str, float]:
    if coupling_type == "none":
        return {}
    if coupling_type == "symmetric_linear":
        return {"linear_sf": epsilon, "linear_fs": epsilon}
    if coupling_type == "asymmetric_fast_to_smr":
        return {"linear_fs": epsilon, "linear_sf": 0.0}
    if coupling_type == "symmetric_amplitude":
        return {"amp_sf": epsilon, "amp_fs": epsilon}
    if coupling_type == "weak_phase":
        return {"phase_coupling": epsilon}
    raise ValueError(coupling_type)


def build_grid(grid: str):
    if grid == "smoke":
        gains = [0.0, 0.25]
        eps = [0.0, 0.06]
        reps = [1]
        duration = 8.0
    elif grid == "reduced":
        gains = [0.0, 0.10, 0.20, 0.30, 0.40]
        eps = [0.0, 0.03, 0.06, 0.09, 0.12]
        reps = [1, 2, 3]
        duration = 24.0
    else:
        gains = np.linspace(0, 0.45, 10).round(3).tolist()
        eps = np.linspace(0, 0.15, 8).round(3).tolist()
        reps = list(range(1, 6))
        duration = 45.0
    return gains, eps, reps, duration


def run(grid: str = "reduced") -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_repo_structure(ROOT)
    gains, eps_values, seeds, duration = build_grid(grid)
    coupling_types = ["none", "symmetric_linear", "asymmetric_fast_to_smr", "symmetric_amplitude", "weak_phase"]
    rows = []
    base = SLParams(duration_s=duration, fs=128.0, burn_s=2.0)
    for coupling_type in coupling_types:
        local_eps = [0.0] if coupling_type == "none" else eps_values
        for epsilon in local_eps:
            for gain in gains:
                for seed in seeds:
                    params = with_updates(
                        base,
                        feedback_gain=float(gain),
                        seed=int(seed),
                        **coupling_kwargs(coupling_type, float(epsilon)),
                    )
                    metrics = simulate_and_summarize(params)
                    rows.append(
                        {
                            "wp": "WP1",
                            "grid": grid,
                            "coupling_type": coupling_type,
                            "epsilon": float(epsilon),
                            "feedback_gain": float(gain),
                            "seed": int(seed),
                            **metrics,
                        }
                    )
    raw = pd.DataFrame(rows)
    raw_path = ROOT / "outputs" / "tables" / "wp1_parameter_grid.csv"
    raw.to_csv(raw_path, index=False)

    baseline = raw.loc[raw["feedback_gain"] == 0.0, ["coupling_type", "epsilon", "seed", "smr_power", "beta_power", "burst_rate_per_min"]]
    baseline = baseline.rename(
        columns={
            "smr_power": "smr_power_baseline",
            "beta_power": "beta_power_baseline",
            "burst_rate_per_min": "burst_rate_baseline",
        }
    )
    merged = raw.merge(baseline, on=["coupling_type", "epsilon", "seed"], how="left")
    for col, base_col in [
        ("smr_power", "smr_power_baseline"),
        ("beta_power", "beta_power_baseline"),
        ("burst_rate_per_min", "burst_rate_baseline"),
    ]:
        merged[f"{col}_change_frac"] = (merged[col] - merged[base_col]) / merged[base_col].replace(0, np.nan)

    agg = (
        merged.groupby(["coupling_type", "epsilon", "feedback_gain"], as_index=False)
        .agg(
            smr_change_frac=("smr_power_change_frac", "mean"),
            beta_change_frac=("beta_power_change_frac", "mean"),
            burst_rate_change_frac=("burst_rate_per_min_change_frac", "mean"),
            smr_change_sd=("smr_power_change_frac", "std"),
            beta_change_sd=("beta_power_change_frac", "std"),
            n_reps=("seed", "nunique"),
        )
        .fillna(0.0)
    )
    agg["directional_valid"] = (agg["beta_change_frac"] < -0.02) & (agg["smr_change_frac"].abs() <= 0.08)
    agg["smr_contaminated"] = agg["smr_change_frac"].abs() > 0.08
    agg["directional_failure"] = agg["beta_change_frac"] >= -0.02
    agg["failure_label"] = np.select(
        [agg["smr_contaminated"], agg["directional_failure"]],
        ["SMR contamination", "weak beta suppression"],
        default="valid",
    )
    agg_path = ROOT / "outputs" / "tables" / "wp1_constraint_validity.csv"
    agg.to_csv(agg_path, index=False)
    make_figures(agg, grid)
    write_report(agg, grid)
    return raw, agg


def make_figures(agg: pd.DataFrame, grid: str) -> None:
    set_style()
    sym = agg[agg["coupling_type"] == "symmetric_linear"].copy()
    pivot = sym.pivot(index="epsilon", columns="feedback_gain", values="beta_change_frac")
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    image = simple_heatmap(ax, pivot, "High-beta change under symmetric coupling", cmap="viridis_r", vmin=-0.8, vmax=0.1)
    ax.set_xlabel("feedback gain k")
    ax.set_ylabel("linear coupling epsilon")
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("fractional beta-power change")
    save_csv_backed_figure(fig, sym, "wp1_coupling_robustness_map")

    max_gain = agg["feedback_gain"].max()
    failure = agg[agg["feedback_gain"] == max_gain].copy()
    failure["failure_code"] = failure["failure_label"].map({"valid": 0, "weak beta suppression": 1, "SMR contamination": 2}).astype(int)
    fail_pivot = failure.pivot_table(index="coupling_type", columns="epsilon", values="failure_code", aggfunc="mean").fillna(0)
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    image = simple_heatmap(ax, fail_pivot, f"Failure regimes at k={max_gain:g}", cmap="magma", vmin=0, vmax=2)
    ax.set_xlabel("coupling epsilon")
    ax.set_ylabel("coupling form")
    cbar = fig.colorbar(image, ax=ax, ticks=[0, 1, 2])
    cbar.ax.set_yticklabels(["valid", "weak beta", "SMR contaminated"])
    save_csv_backed_figure(fig, failure, "wp1_failure_regime_map")

    params_base = SLParams(duration_s=20.0 if grid != "smoke" else 8.0, fs=128.0, burn_s=2.0, seed=11, linear_sf=0.06, linear_fs=0.06)
    sim0 = simulate_two_mode(with_updates(params_base, feedback_gain=0.0))
    sim1 = simulate_two_mode(with_updates(params_base, feedback_gain=0.30))
    source = pd.DataFrame(
        timeseries_table(sim0, "baseline") + timeseries_table(sim1, "feedback")
        + psd_table(sim0, "baseline")
        + psd_table(sim1, "feedback")
    )
    fig, axes = plt.subplots(2, 2, figsize=(8.0, 5.2))
    ts = source.dropna(subset=["time_s"]) if "time_s" in source.columns else pd.DataFrame()
    for condition, group in ts.groupby("condition"):
        axes[0, 0].plot(group["time_s"], group["signal"], lw=0.7, label=condition)
        axes[1, 0].plot(group["time_s"], group["beta_amplitude"], lw=0.9, label=condition)
    psd = source.dropna(subset=["frequency_hz"]) if "frequency_hz" in source.columns else pd.DataFrame()
    for condition, group in psd.groupby("condition"):
        axes[0, 1].plot(group["frequency_hz"], group["psd"], lw=1.0, label=condition)
        axes[1, 1].plot(group["frequency_hz"], group["psd"], lw=1.0, label=condition)
    axes[0, 0].set_title("Sensor signal")
    axes[0, 0].set_xlabel("time (s)")
    axes[0, 0].set_ylabel("amplitude")
    axes[1, 0].set_title("Latent high-beta amplitude")
    axes[1, 0].set_xlabel("time (s)")
    axes[1, 0].set_ylabel("|z_f|")
    axes[0, 1].set_title("Power spectrum")
    axes[0, 1].set_xlabel("frequency (Hz)")
    axes[0, 1].set_ylabel("PSD")
    axes[0, 1].set_xlim(4, 45)
    axes[1, 1].set_title("Target bands")
    axes[1, 1].set_xlabel("frequency (Hz)")
    axes[1, 1].set_ylabel("PSD")
    axes[1, 1].set_xlim(10, 32)
    for ax in axes.ravel():
        ax.legend(loc="best")
    save_csv_backed_figure(fig, source, "wp1_example_timeseries_spectra")


def write_report(agg: pd.DataFrame, grid: str) -> None:
    report = ROOT / "outputs" / "reports" / "wp1_results.md"
    tested = len(agg)
    valid = int(agg["directional_valid"].sum())
    max_gain = agg["feedback_gain"].max()
    high_gain = agg[agg["feedback_gain"] == max_gain]
    text = f"""# WP1 Results: Coupled Stuart-Landau Validity Simulations

Grid: `{grid}`.

This reduced run tested {tested} aggregate gain/coupling conditions after replicate averaging. Directional validity was defined as high-beta power reduction below -2% with absolute SMR change not exceeding 8%.

Summary:

- Valid aggregate conditions: {valid} / {tested}.
- At the highest gain (`k={max_gain:g}`), mean high-beta change was {high_gain['beta_change_frac'].mean():.3f}.
- At the highest gain, mean absolute SMR change was {high_gain['smr_change_frac'].abs().mean():.3f}.
- Failures are retained in `outputs/tables/wp1_constraint_validity.csv` and visualized in `wp1_failure_regime_map.*`.

Interpretation:

The coarse validity-domain map supports the restricted claim that selective fast-mode stabilization can suppress high-beta activity while leaving SMR approximately unchanged in weakly coupled regimes. It also identifies coupling forms and strengths where the directional constraint begins to fail through SMR contamination or insufficient beta suppression.
"""
    report.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", choices=["smoke", "reduced", "extended"], default="reduced")
    args = parser.parse_args()
    run(args.grid)


if __name__ == "__main__":
    main()
