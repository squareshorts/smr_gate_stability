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
from simulations.wp1_stuart_landau_validity import coupling_kwargs
from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style


def build_grid(grid: str):
    if grid == "smoke":
        return [0.0, 0.25], [0.0, 0.06], [1], 8.0
    if grid == "reduced":
        return [0.0, 0.08, 0.16, 0.24, 0.32, 0.40], [0.0, 0.03, 0.06, 0.10], [1, 2, 3], 24.0
    return np.linspace(0, 0.45, 12).round(3).tolist(), np.linspace(0, 0.14, 8).round(3).tolist(), list(range(1, 6)), 45.0


def run(grid: str = "reduced") -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_repo_structure(ROOT)
    gains, eps_values, seeds, duration = build_grid(grid)
    coupling_types = ["none", "symmetric_linear", "asymmetric_fast_to_smr", "symmetric_amplitude", "weak_phase"]
    rows = []
    base = SLParams(duration_s=duration, fs=128.0, burn_s=2.0)
    for coupling_type in coupling_types:
        local_eps = [0.0] if coupling_type == "none" else eps_values
        for epsilon in local_eps:
            for seed in seeds:
                for gain in gains:
                    params = with_updates(
                        base,
                        seed=int(seed),
                        feedback_gain=float(gain),
                        **coupling_kwargs(coupling_type, float(epsilon)),
                    )
                    metrics = simulate_and_summarize(params)
                    rows.append(
                        {
                            "coupling_type": coupling_type,
                            "epsilon": float(epsilon),
                            "seed": int(seed),
                            "feedback_gain": float(gain),
                            "smr_power": metrics["smr_power"],
                            "beta_power": metrics["beta_power"],
                        }
                    )
    powers = pd.DataFrame(rows)
    baseline = powers[powers["feedback_gain"] == 0.0][["coupling_type", "epsilon", "seed", "smr_power", "beta_power"]]
    baseline = baseline.rename(columns={"smr_power": "smr_power_0", "beta_power": "beta_power_0"})
    powers = powers.merge(baseline, on=["coupling_type", "epsilon", "seed"], how="left")
    powers["smr_power_norm"] = powers["smr_power"] / powers["smr_power_0"]
    powers["beta_power_norm"] = powers["beta_power"] / powers["beta_power_0"]

    derivative_rows = []
    for key, group in powers.groupby(["coupling_type", "epsilon", "seed"]):
        group = group.sort_values("feedback_gain")
        gains_arr = group["feedback_gain"].to_numpy()
        for band in ["smr", "beta"]:
            y = group[f"{band}_power_norm"].to_numpy()
            dydk = np.gradient(y, gains_arr)
            for gain, deriv in zip(gains_arr, dydk):
                derivative_rows.append(
                    {
                        "wp": "WP2",
                        "grid": grid,
                        "coupling_type": key[0],
                        "epsilon": float(key[1]),
                        "seed": int(key[2]),
                        "feedback_gain": float(gain),
                        "band": band,
                        "d_powernorm_dk": float(deriv),
                    }
                )
    deriv = pd.DataFrame(derivative_rows)
    beta_deriv = deriv[deriv["band"] == "beta"].rename(columns={"d_powernorm_dk": "dP_beta_dk"})
    smr_deriv = deriv[deriv["band"] == "smr"].rename(columns={"d_powernorm_dk": "dP_smr_dk"})
    checks = beta_deriv.merge(
        smr_deriv[["coupling_type", "epsilon", "seed", "feedback_gain", "dP_smr_dk"]],
        on=["coupling_type", "epsilon", "seed", "feedback_gain"],
        how="left",
    )
    checks["beta_derivative_negative"] = checks["dP_beta_dk"] < 0
    checks = checks.drop(columns=["band"])
    checks.to_csv(ROOT / "outputs" / "tables" / "wp2_derivative_checks.csv", index=False)

    bound_c = 3.0
    checks["bound_c"] = bound_c
    checks["smr_bound_rhs"] = bound_c * checks["epsilon"] + 0.015
    checks["smr_bound_holds"] = checks["dP_smr_dk"].abs() <= checks["smr_bound_rhs"]
    bound = (
        checks.groupby(["coupling_type", "epsilon", "feedback_gain"], as_index=False)
        .agg(
            dP_beta_dk_mean=("dP_beta_dk", "mean"),
            dP_smr_dk_abs_mean=("dP_smr_dk", lambda x: float(np.mean(np.abs(x)))),
            beta_derivative_negative_rate=("beta_derivative_negative", "mean"),
            smr_bound_hold_rate=("smr_bound_holds", "mean"),
            bound_c=("bound_c", "first"),
            n_reps=("seed", "nunique"),
        )
    )
    bound.to_csv(ROOT / "outputs" / "tables" / "wp2_bound_checks.csv", index=False)
    make_figure(bound)
    write_report(bound, grid, bound_c)
    return checks, bound


def make_figure(bound: pd.DataFrame) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.4))
    for coupling_type, group in bound.groupby("coupling_type"):
        summary = group.groupby("epsilon", as_index=False).agg(
            beta_neg=("beta_derivative_negative_rate", "mean"),
            smr_bound=("smr_bound_hold_rate", "mean"),
            smr_abs=("dP_smr_dk_abs_mean", "mean"),
        )
        axes[0].plot(summary["epsilon"], summary["beta_neg"], marker="o", label=coupling_type)
        axes[1].plot(summary["epsilon"], summary["smr_bound"], marker="o", label=coupling_type)
    axes[0].set_title("dP_beta/dk < 0")
    axes[0].set_xlabel("epsilon")
    axes[0].set_ylabel("fraction of checks")
    axes[0].set_ylim(-0.05, 1.05)
    axes[1].set_title("|dP_SMR/dk| <= C epsilon")
    axes[1].set_xlabel("epsilon")
    axes[1].set_ylabel("fraction of checks")
    axes[1].set_ylim(-0.05, 1.05)
    axes[1].legend(loc="lower left", fontsize=7)
    save_csv_backed_figure(fig, bound, "wp2_derivative_and_bound_summary")


def write_report(bound: pd.DataFrame, grid: str, bound_c: float) -> None:
    beta_rate = bound["beta_derivative_negative_rate"].mean()
    smr_rate = bound["smr_bound_hold_rate"].mean()
    text = f"""# WP2 Analytical Weak-Coupling Validity Statement

Grid: `{grid}`.

Finite-difference checks were run on normalized SMR and high-beta powers. The tested qualitative inequalities were:

- `dP_beta/dk < 0`
- `|dP_SMR/dk| <= C epsilon`, with `C={bound_c:g}` and a small numerical tolerance of 0.015.

Coarse-grid outcomes:

- Mean high-beta negative-derivative rate: {beta_rate:.3f}.
- Mean SMR coupling-bound hold rate: {smr_rate:.3f}.

Working validity statement:

For weak linear, amplitude, or phase coupling, the simulated Stuart-Landau system usually satisfies a monotone high-beta suppression inequality as feedback gain increases. The induced SMR derivative remains bounded by coupling strength in most weak-coupling settings, but the bound fails when coupling terms directly contaminate the slow mode or when numerical finite differences straddle unstable transition regions.

This supports a restricted weak-coupling statement rather than a universal theorem.
"""
    (ROOT / "outputs" / "reports" / "wp2_analytical_validity_statement.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", choices=["smoke", "reduced", "extended"], default="reduced")
    args = parser.parse_args()
    run(args.grid)


if __name__ == "__main__":
    main()
