from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import pandas as pd

from models.stuart_landau import SLParams, simulate_and_summarize, with_updates
from simulations import (
    wp1_stuart_landau_validity,
    wp2_weak_coupling_checks,
    wp3_null_models,
    wp4_criticality,
    wp5_burst_threshold_surrogates,
    wp6_parameter_regime_map,
)
from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style


def run_core_smoke_check() -> None:
    params = SLParams(duration_s=8.0, fs=128.0, burn_s=1.0, seed=101)
    baseline = simulate_and_summarize(with_updates(params, feedback_gain=0.0))
    feedback = simulate_and_summarize(with_updates(params, feedback_gain=0.30), burst_threshold=baseline["burst_threshold"])
    if feedback["beta_power"] >= baseline["beta_power"]:
        raise AssertionError("Smoke check expected high-beta power to decrease under feedback.")

    source = pd.DataFrame(
        [
            {"condition": "baseline", "metric": "smr_power", "value": baseline["smr_power"]},
            {"condition": "baseline", "metric": "beta_power", "value": baseline["beta_power"]},
            {"condition": "feedback", "metric": "smr_power", "value": feedback["smr_power"]},
            {"condition": "feedback", "metric": "beta_power", "value": feedback["beta_power"]},
        ]
    )
    set_style()
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    for condition, group in source.groupby("condition"):
        ax.plot(group["metric"], group["value"], marker="o", label=condition)
    ax.set_title("Smoke gain check")
    ax.set_ylabel("band power")
    ax.legend(loc="best")
    save_csv_backed_figure(fig, source, "smoke_stuart_landau_gain_check")


def main() -> None:
    ensure_repo_structure(ROOT)
    run_core_smoke_check()
    wp1_stuart_landau_validity.run("smoke")
    wp2_weak_coupling_checks.run("smoke")
    wp3_null_models.run("smoke")
    wp4_criticality.run("smoke")
    wp5_burst_threshold_surrogates.run("smoke")
    wp6_parameter_regime_map.run("smoke")
    print("Smoke tests completed.")


if __name__ == "__main__":
    main()
