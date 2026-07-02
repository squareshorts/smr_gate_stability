from __future__ import annotations

import argparse
import itertools
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
        return {
            "mu_s": [0.45],
            "mu_f": [0.10, 0.35],
            "sat_f": [1.0],
            "noise_f": [0.055],
            "feedback_gain": [0.25],
            "coupling_epsilon": [0.0, 0.08],
            "seeds": [7],
            "duration": 8.0,
        }
    if grid == "reduced":
        return {
            "mu_s": [0.35, 0.55, 0.75],
            "mu_f": [0.05, 0.35, 0.75],
            "sat_f": [0.80, 1.00, 1.40],
            "noise_f": [0.035, 0.075],
            "feedback_gain": [0.00, 0.10, 0.30],
            "coupling_epsilon": [0.00, 0.05, 0.12, 0.20],
            "seeds": [7],
            "duration": 18.0,
        }
    return {
        "mu_s": np.linspace(0.25, 0.85, 5).round(3).tolist(),
        "mu_f": np.linspace(-0.05, 0.55, 6).round(3).tolist(),
        "sat_f": [0.70, 0.90, 1.10, 1.40],
        "noise_f": [0.025, 0.055, 0.085, 0.12],
        "feedback_gain": [0.10, 0.20, 0.30, 0.40],
        "coupling_epsilon": [0.00, 0.03, 0.06, 0.10, 0.14],
        "seeds": [7, 8, 9],
        "duration": 30.0,
    }


def run(grid: str = "reduced") -> pd.DataFrame:
    ensure_repo_structure(ROOT)
    cfg = build_grid(grid)
    rows = []
    base = SLParams(duration_s=cfg["duration"], fs=128.0, burn_s=2.0)
    combo_keys = ["mu_s", "mu_f", "sat_f", "noise_f", "feedback_gain", "coupling_epsilon", "seeds"]
    for mu_s, mu_f, sat_f, noise_f, gain, epsilon, seed in itertools.product(*(cfg[key] for key in combo_keys)):
        common = dict(
            mu_s=float(mu_s),
            mu_f=float(mu_f),
            sat_f=float(sat_f),
            noise_f=float(noise_f),
            linear_sf=float(epsilon),
            linear_fs=float(epsilon),
            seed=int(seed),
        )
        baseline = simulate_and_summarize(with_updates(base, feedback_gain=0.0, **common))
        feedback = simulate_and_summarize(with_updates(base, feedback_gain=float(gain), **common), burst_threshold=baseline["burst_threshold"])
        smr_change = (feedback["smr_power"] - baseline["smr_power"]) / baseline["smr_power"] if baseline["smr_power"] else np.nan
        beta_change = (feedback["beta_power"] - baseline["beta_power"]) / baseline["beta_power"] if baseline["beta_power"] else np.nan
        burst_change = (feedback["burst_rate_per_min"] - baseline["burst_rate_per_min"]) / baseline["burst_rate_per_min"] if baseline["burst_rate_per_min"] else np.nan
        valid = bool((beta_change < -0.05) and (abs(smr_change) <= 0.08))
        if abs(smr_change) > 0.08:
            failure = "SMR contamination"
        elif beta_change >= -0.05:
            failure = "weak beta suppression"
        else:
            failure = "valid"
        rows.append(
            {
                "wp": "WP6",
                "grid": grid,
                "mu_s": float(mu_s),
                "mu_f": float(mu_f),
                "sat_f": float(sat_f),
                "noise_f": float(noise_f),
                "feedback_gain": float(gain),
                "coupling_epsilon": float(epsilon),
                "seed": int(seed),
                "baseline_smr_power": baseline["smr_power"],
                "baseline_beta_power": baseline["beta_power"],
                "feedback_smr_power": feedback["smr_power"],
                "feedback_beta_power": feedback["beta_power"],
                "smr_change_frac": smr_change,
                "beta_change_frac": beta_change,
                "burst_rate_change_frac": burst_change,
                "directional_valid": valid,
                "failure_label": failure,
                "baseline_burst_rate_per_min": baseline["burst_rate_per_min"],
                "feedback_burst_rate_per_min": feedback["burst_rate_per_min"],
                "feedback_time_constant_s": "not_modeled",
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "outputs" / "tables" / "wp6_parameter_sensitivity.csv", index=False)
    make_figures(df)
    write_report(df, grid)
    return df


def parameter_importance(df: pd.DataFrame) -> pd.DataFrame:
    params = ["mu_s", "mu_f", "sat_f", "noise_f", "feedback_gain", "coupling_epsilon"]
    rows = []
    for param in params:
        grouped = df.groupby(param).agg(
            validity_rate=("directional_valid", "mean"),
            beta_change=("beta_change_frac", "mean"),
            smr_abs_change=("smr_change_frac", lambda x: float(np.mean(np.abs(x)))),
        )
        rows.append(
            {
                "parameter": param,
                "validity_rate_range": float(grouped["validity_rate"].max() - grouped["validity_rate"].min()),
                "beta_change_range": float(grouped["beta_change"].max() - grouped["beta_change"].min()),
                "smr_abs_change_range": float(grouped["smr_abs_change"].max() - grouped["smr_abs_change"].min()),
            }
        )
    return pd.DataFrame(rows).sort_values("validity_rate_range", ascending=False)


def make_figures(df: pd.DataFrame) -> None:
    set_style()
    validity = df.groupby(["mu_f", "coupling_epsilon"], as_index=False).agg(validity_rate=("directional_valid", "mean"))
    pivot = validity.pivot(index="mu_f", columns="coupling_epsilon", values="validity_rate")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    image = simple_heatmap(ax, pivot, "Directional-validity region", "viridis", vmin=0, vmax=1)
    ax.set_xlabel("coupling epsilon")
    ax.set_ylabel("fast growth mu_f")
    fig.colorbar(image, ax=ax, label="validity rate")
    save_csv_backed_figure(fig, validity, "wp6_validity_map")

    fail = df.copy()
    fail["failure_code"] = fail["failure_label"].map({"valid": 0, "weak beta suppression": 1, "SMR contamination": 2})
    failure = fail.groupby(["coupling_epsilon", "feedback_gain"], as_index=False).agg(mean_failure_code=("failure_code", "mean"))
    pivot_fail = failure.pivot(index="coupling_epsilon", columns="feedback_gain", values="mean_failure_code")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    image = simple_heatmap(ax, pivot_fail, "Failure regime by gain and coupling", "magma", vmin=0, vmax=2)
    ax.set_xlabel("feedback gain k")
    ax.set_ylabel("coupling epsilon")
    fig.colorbar(image, ax=ax, label="failure code mean")
    save_csv_backed_figure(fig, failure, "wp6_failure_regime_map")

    importance = parameter_importance(df)
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    ax.bar(importance["parameter"], importance["validity_rate_range"], color="#4d7f72")
    ax.set_title("Coarse parameter importance")
    ax.set_ylabel("range in validity rate")
    ax.tick_params(axis="x", rotation=35)
    save_csv_backed_figure(fig, importance, "wp6_parameter_importance")


def write_report(df: pd.DataFrame, grid: str) -> None:
    validity = df["directional_valid"].mean()
    failures = df["failure_label"].value_counts(normalize=True).to_dict()
    importance = parameter_importance(df).head(3)
    lines = ["# WP6 Results: Parameter-Regime Validity Map", "", f"Grid: `{grid}`.", ""]
    lines.append(f"Overall directional-validity rate: {validity:.3f}.")
    lines.append("")
    lines.append("Failure composition:")
    for label, frac in failures.items():
        lines.append(f"- {label}: {frac:.3f}")
    lines.append("")
    lines.append("Most influential coarse parameters by validity-rate range:")
    for _, row in importance.iterrows():
        lines.append(f"- `{row['parameter']}`: range {row['validity_rate_range']:.3f}")
    lines.append("")
    lines.append(
        "Interpretation: the validity regime is broadest when feedback gain is sufficient for beta suppression, coupling is weak, and fast-mode growth is not so high that beta dynamics remain self-sustained after feedback. Conditions outside this domain should be excluded from the central claim."
    )
    (ROOT / "outputs" / "reports" / "wp6_results.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", choices=["smoke", "reduced", "extended"], default="reduced")
    args = parser.parse_args()
    run(args.grid)


if __name__ == "__main__":
    main()
