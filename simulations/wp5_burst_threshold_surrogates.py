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

from models.stuart_landau import SLParams, simulate_two_mode, with_updates
from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style
from utils.signal_metrics import band_envelope, bandpower, burst_metrics, phase_randomize


def build_grid(grid: str):
    if grid == "smoke":
        return [1], 8.0, 0.25
    if grid == "reduced":
        return [1, 2, 3, 4, 5], 30.0, 0.30
    return list(range(1, 11)), 60.0, 0.30


def threshold_definitions(env_base: np.ndarray, env_feedback: np.ndarray) -> dict[str, tuple[float, float, str]]:
    med = float(np.median(env_base))
    mad = float(np.median(np.abs(env_base - med)))
    base80 = float(np.percentile(env_base, 80))
    feedback80 = float(np.percentile(env_feedback, 80))
    return {
        "baseline_percentile_75": (float(np.percentile(env_base, 75)), float(np.percentile(env_base, 75)), "baseline_fixed"),
        "baseline_percentile_80": (base80, base80, "baseline_fixed"),
        "baseline_percentile_90": (float(np.percentile(env_base, 90)), float(np.percentile(env_base, 90)), "baseline_fixed"),
        "baseline_percentile_95": (float(np.percentile(env_base, 95)), float(np.percentile(env_base, 95)), "baseline_fixed"),
        "fixed_absolute_0p65": (0.65, 0.65, "fixed_absolute"),
        "zscore_1p0": (float(np.mean(env_base) + np.std(env_base)), float(np.mean(env_base) + np.std(env_base)), "baseline_zscore"),
        "mad_1p4826": (float(med + 1.4826 * mad), float(med + 1.4826 * mad), "baseline_mad"),
        "post_feedback_percentile_80": (base80, feedback80, "post_feedback_negative_control"),
    }


def run(grid: str = "reduced") -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_repo_structure(ROOT)
    seeds, duration, gain = build_grid(grid)
    rows = []
    surrogate_rows = []
    base_params = SLParams(duration_s=duration, fs=128.0, burn_s=2.0, linear_sf=0.04, linear_fs=0.04)
    for seed in seeds:
        sim_base = simulate_two_mode(with_updates(base_params, seed=seed, feedback_gain=0.0))
        sim_feedback = simulate_two_mode(with_updates(base_params, seed=seed, feedback_gain=gain))
        fs = float(sim_base["fs"])
        x_base = np.asarray(sim_base["x"])
        x_feedback = np.asarray(sim_feedback["x"])
        env_base = band_envelope(x_base, fs, (20.0, 30.0))
        env_feedback = band_envelope(x_feedback, fs, (20.0, 30.0))
        thresholds = threshold_definitions(env_base, env_feedback)
        for method, (baseline_threshold, feedback_threshold, family) in thresholds.items():
            base_metrics = burst_metrics(env_base, baseline_threshold, fs)
            feedback_metrics = burst_metrics(env_feedback, feedback_threshold, fs)
            for condition, metrics, threshold in [
                ("baseline", base_metrics, baseline_threshold),
                ("feedback", feedback_metrics, feedback_threshold),
            ]:
                rows.append(
                    {
                        "wp": "WP5",
                        "grid": grid,
                        "seed": seed,
                        "condition": condition,
                        "feedback_gain": 0.0 if condition == "baseline" else gain,
                        "threshold_method": method,
                        "threshold_family": family,
                        "threshold_value": threshold,
                        **metrics,
                    }
                )

        baseline_threshold = thresholds["baseline_percentile_80"][0]
        baseline_metrics = burst_metrics(env_base, baseline_threshold, fs)
        feedback_metrics = burst_metrics(env_feedback, baseline_threshold, fs)
        beta_base = bandpower(x_base, fs, (20.0, 30.0))
        beta_feedback = bandpower(x_feedback, fs, (20.0, 30.0))
        scale = float(np.sqrt(beta_feedback / beta_base)) if beta_base > 0 and beta_feedback > 0 else 1.0
        controls = {
            "original_feedback": x_feedback,
            "phase_randomized_feedback": phase_randomize(x_feedback, seed=seed + 1000),
            "matched_power_baseline_scaled": x_base * scale,
        }
        for control_name, signal in controls.items():
            env = band_envelope(signal, fs, (20.0, 30.0))
            metrics = burst_metrics(env, baseline_threshold, fs)
            surrogate_rows.append(
                {
                    "wp": "WP5",
                    "grid": grid,
                    "seed": seed,
                    "control": control_name,
                    "baseline_threshold": baseline_threshold,
                    "beta_power": bandpower(signal, fs, (20.0, 30.0)),
                    "beta_power_baseline": beta_base,
                    "beta_power_feedback": beta_feedback,
                    "scale_to_match_power": scale,
                    "baseline_burst_rate_per_min": baseline_metrics["burst_rate_per_min"],
                    "feedback_burst_rate_per_min": feedback_metrics["burst_rate_per_min"],
                    **metrics,
                }
            )
    thresh = pd.DataFrame(rows)
    baseline = thresh[thresh["condition"] == "baseline"][
        ["seed", "threshold_method", "burst_rate_per_min", "burst_duration_s", "burst_occupancy"]
    ].rename(
        columns={
            "burst_rate_per_min": "baseline_burst_rate_per_min",
            "burst_duration_s": "baseline_burst_duration_s",
            "burst_occupancy": "baseline_burst_occupancy",
        }
    )
    thresh = thresh.merge(baseline, on=["seed", "threshold_method"], how="left")
    thresh["burst_rate_change_frac"] = (thresh["burst_rate_per_min"] - thresh["baseline_burst_rate_per_min"]) / thresh[
        "baseline_burst_rate_per_min"
    ].replace(0, np.nan)
    thresh["burst_duration_change_frac"] = (thresh["burst_duration_s"] - thresh["baseline_burst_duration_s"]) / thresh[
        "baseline_burst_duration_s"
    ].replace(0, np.nan)
    thresh.to_csv(ROOT / "outputs" / "tables" / "wp5_threshold_sensitivity.csv", index=False)

    sur = pd.DataFrame(surrogate_rows)
    sur["burst_rate_change_frac_vs_baseline"] = (sur["burst_rate_per_min"] - sur["baseline_burst_rate_per_min"]) / sur[
        "baseline_burst_rate_per_min"
    ].replace(0, np.nan)
    sur["beta_power_change_frac_vs_baseline"] = (sur["beta_power"] - sur["beta_power_baseline"]) / sur["beta_power_baseline"].replace(0, np.nan)
    sur.to_csv(ROOT / "outputs" / "tables" / "wp5_surrogate_burst_controls.csv", index=False)
    make_figures(thresh, sur)
    write_report(thresh, sur, grid)
    return thresh, sur


def make_figures(thresh: pd.DataFrame, sur: pd.DataFrame) -> None:
    set_style()
    feedback = thresh[thresh["condition"] == "feedback"].copy()
    summary = feedback.groupby(["threshold_method", "threshold_family"], as_index=False).agg(
        burst_rate_change=("burst_rate_change_frac", "mean"),
        burst_rate_change_sd=("burst_rate_change_frac", "std"),
    )
    summary = summary.sort_values("threshold_method")
    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    ax.bar(summary["threshold_method"], summary["burst_rate_change"], color="#3b6ea8")
    ax.axhline(0, color="0.25", lw=0.8)
    ax.set_title("Burst-rate threshold sensitivity")
    ax.set_ylabel("fractional change")
    ax.tick_params(axis="x", rotation=45)
    save_csv_backed_figure(fig, summary, "wp5_burst_rate_threshold_sensitivity")

    dur = feedback.groupby(["threshold_method", "threshold_family"], as_index=False).agg(
        burst_duration_change=("burst_duration_change_frac", "mean"),
        burst_duration_change_sd=("burst_duration_change_frac", "std"),
    )
    dur = dur.sort_values("threshold_method")
    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    ax.bar(dur["threshold_method"], dur["burst_duration_change"], color="#b45f47")
    ax.axhline(0, color="0.25", lw=0.8)
    ax.set_title("Burst-duration threshold sensitivity")
    ax.set_ylabel("fractional change")
    ax.tick_params(axis="x", rotation=45)
    save_csv_backed_figure(fig, dur, "wp5_burst_duration_threshold_sensitivity")

    sur_summary = sur.groupby("control", as_index=False).agg(
        burst_rate_change=("burst_rate_change_frac_vs_baseline", "mean"),
        beta_power_change=("beta_power_change_frac_vs_baseline", "mean"),
    )
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    for _, row in sur_summary.iterrows():
        ax.scatter(row["beta_power_change"], row["burst_rate_change"], s=90)
        ax.text(row["beta_power_change"], row["burst_rate_change"], row["control"], fontsize=8, va="bottom", ha="left")
    ax.axhline(0, color="0.25", lw=0.8)
    ax.axvline(0, color="0.25", lw=0.8)
    ax.set_title("Surrogate artifact check")
    ax.set_xlabel("beta-power fractional change")
    ax.set_ylabel("burst-rate fractional change")
    save_csv_backed_figure(fig, sur_summary, "wp5_surrogate_artifact_check")


def write_report(thresh: pd.DataFrame, sur: pd.DataFrame, grid: str) -> None:
    feedback = thresh[thresh["condition"] == "feedback"]
    fixed = feedback[feedback["threshold_family"] != "post_feedback_negative_control"]
    neg = feedback[feedback["threshold_family"] == "post_feedback_negative_control"]
    fixed_rate = fixed["burst_rate_change_frac"].mean()
    neg_rate = neg["burst_rate_change_frac"].mean()
    original = sur[sur["control"] == "original_feedback"]["burst_rate_change_frac_vs_baseline"].mean()
    phase = sur[sur["control"] == "phase_randomized_feedback"]["burst_rate_change_frac_vs_baseline"].mean()
    text = f"""# WP5 Results: Burst-Threshold and Surrogate Robustness

Grid: `{grid}`.

Coarse-grid outcomes:

- Mean burst-rate change under baseline-fixed or absolute thresholds: {fixed_rate:.3f}.
- Mean burst-rate change under the post-feedback percentile negative control: {neg_rate:.3f}.
- Original feedback burst-rate change in surrogate table: {original:.3f}.
- Phase-randomized feedback burst-rate change: {phase:.3f}.

Interpretation:

Baseline-fixed percentile, z-score, MAD, and absolute thresholds generally preserve the burst-reduction signature. The post-feedback percentile threshold is expected to attenuate this signature because it redefines bursts relative to the suppressed distribution. Surrogate controls show how much of the burst effect can be explained by power scaling alone.
"""
    (ROOT / "outputs" / "reports" / "wp5_results.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", choices=["smoke", "reduced", "extended"], default="reduced")
    args = parser.parse_args()
    run(args.grid)


if __name__ == "__main__":
    main()
