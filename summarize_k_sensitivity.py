import pandas as pd
from pathlib import Path

LOCAL_ROOT = Path('c:/work/smr_gate_stability')
out_lines = []

out_lines.append("# Sensitivity Analysis for k")
out_lines.append("")
out_lines.append("| k | N Trained | N Control | Trained Slope (/min) | Control Slope (/min) | Diff (/min) | 95% CI | Exact p | Hedges g |")
out_lines.append("|---|---|---|---|---|---|---|---|---|")

for k in [5, 10, 20, 30]:
    inf_path = LOCAL_ROOT / "results" / "k_sensitivity" / f"k_{k}" / "tables" / "benchmark_phase_geometry_inference.csv"
    if not inf_path.exists():
        continue
    df = pd.read_csv(inf_path)
    
    primary = df[
        (df["analysis_set"] == "primary_first_15_min") & 
        (df["analysis_family"] == "phase_geometry") & 
        (df["metric"] == "gini_phase_sensitivity")
    ].iloc[0]
    
    n_trained = primary["n_trained"]
    n_control = primary["n_control"]
    trained_slope = primary["trained_mean_slope"]
    control_slope = primary["control_mean_slope"]
    diff = primary["effect_estimate"]
    ci_low = primary["ci_lower_95"]
    ci_high = primary["ci_upper_95"]
    p_exact = primary["p_exact_two_sided"]
    g = primary["standardized_effect_estimate"]
    
    out_lines.append(
        f"| {k} | {int(n_trained)} | {int(n_control)} | {trained_slope:.4g} | {control_slope:.4g} | {diff:.4g} | [{ci_low:.4g}, {ci_high:.4g}] | {p_exact:.4g} | {g:.4g} |"
    )

with open(LOCAL_ROOT / "k_sensitivity_summary.md", "w") as f:
    f.write("\n".join(out_lines))
    
print("Summary written to k_sensitivity_summary.md")
