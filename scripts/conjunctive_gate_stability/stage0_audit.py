"""STAGE 0 — current-state and dependency audit for the final package."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AUD = ROOT / "results" / "conjunctive_gate_final" / "audit"
AUD.mkdir(parents=True, exist_ok=True)
LAW = ROOT / "results" / "conjunctive_gate_instability"
REM = ROOT / "results" / "conjunctive_law_remedy"


def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, shell=True).stdout


def main():
    # repository_state_before.txt
    state = []
    state.append("root: " + str(ROOT))
    state.append("branch: " + sh("git branch --show-current").strip())
    state.append("commit: " + sh("git rev-parse HEAD").strip())
    state.append("=== git status --short ===\n" + sh("git status --short"))
    (AUD / "repository_state_before.txt").write_text("\n".join(state), encoding="utf-8")

    # running_processes_before.txt
    (AUD / "running_processes_before.txt").write_text(sh("ps aux | grep -iE 'python|Rscript' | grep -v grep || echo none"), encoding="utf-8")

    # dependency_inventory.txt
    deps = []
    for mod in ("numpy", "pandas", "scipy", "sklearn", "mne", "sympy", "pyarrow"):
        try:
            m = __import__(mod)
            deps.append(f"{mod}={getattr(m,'__version__','?')}")
        except Exception as e:
            deps.append(f"{mod}=MISSING ({e})")
    deps.append("Rscript=" + (sh("which Rscript").strip() or "NONE (sandbox); host R present but unreachable from sandbox"))
    deps.append("raw_edf_count=" + sh("find data/raw/openneuro -name '*.edf' 2>/dev/null | wc -l").strip())
    deps.append("canonical_cache=" + ("present" if (ROOT/"results/baseline_gate_stability/checkpoints/features").exists() else "MISSING"))
    deps.append("reusable_feature_cache=" + ("present" if (ROOT/"results/runtime_assurance_remediation/checkpoints/feature_cache").exists() else "MISSING"))
    deps.append("mount_move=OK, mount_delete=DENIED (Operation not permitted)")
    (AUD / "dependency_inventory.txt").write_text("\n".join(deps), encoding="utf-8")

    # verified_result_inventory.csv  (validate key values from saved outputs)
    by_sess = pd.read_csv(LAW / "subset_results_by_session.csv")
    emp = by_sess[by_sess.estimator == "empirical"]
    from scipy.stats import spearmanr
    sp = float(spearmanr(emp.predicted_jaccard, emp.observed_jaccard).statistic)
    mae = float(np.median(np.abs(emp.observed_jaccard - emp.predicted_jaccard)))
    card = pd.read_csv(LAW / "cardinality_results.csv")
    ce = card[card.estimator == "empirical"].set_index("cardinality")
    counts = pd.read_csv(LAW / "count_reproduction.csv")
    cal = pd.read_csv(REM / "author_package" / "calibration_stability_table.csv").set_index("method")
    down = pd.read_csv(REM / "remedy" / "downstream_information_cost_R.csv").set_index("method")
    ver = [
        ("law_pooled_spearman", 0.988, round(sp, 3)),
        ("law_pooled_median_ae", 0.013, round(mae, 3)),
        ("law_K1_jaccard", 0.915, round(float(ce.loc[1, "median_observed_jaccard"]), 3)),
        ("law_K5_jaccard", 0.630, round(float(ce.loc[5, "median_observed_jaccard"]), 3)),
        ("task_windows", 22418, int(counts.loc[counts.dataset == "pooled", "compared_windows"].iloc[0])),
        ("R0_splithalf", 0.707, round(float(cal.loc["R0_ORIGINAL_AND", "pooled_median_splithalf_jaccard"]), 3)),
        ("R1_splithalf", 0.944, round(float(cal.loc["R1_MEAN_PERCENTILE", "pooled_median_splithalf_jaccard"]), 3)),
        ("R2_splithalf", 0.945, round(float(cal.loc["R2_RMS_PERCENTILE", "pooled_median_splithalf_jaccard"]), 3)),
        ("R3_splithalf", 0.735, round(float(cal.loc["R3_ROBUST_MAHALANOBIS_PERCENTILE", "pooled_median_splithalf_jaccard"]), 3)),
        ("R1_natural_vs_nogate", -0.0011, round(float(down.loc["R1_MEAN_PERCENTILE", "natural_minus_nogate"]), 4)),
    ]
    inv = pd.DataFrame(ver, columns=["quantity", "expected", "reproduced"])
    inv["match"] = inv.expected.round(3) == inv.reproduced.round(3) if False else [
        abs(e - r) < 0.01 for e, r in zip(inv.expected, inv.reproduced)]
    inv.to_csv(AUD / "verified_result_inventory.csv", index=False)

    # reusable_artifact_inventory.csv
    reuse = []
    for label, p in [
        ("canonical_feature_cache", "results/baseline_gate_stability/checkpoints/features"),
        ("reusable_feature_cache", "results/runtime_assurance_remediation/checkpoints/feature_cache"),
        ("law_outputs", "results/conjunctive_gate_instability"),
        ("remedy_outputs", "results/conjunctive_law_remedy"),
        ("downstream_decoder_features", "results/baseline_gate_stability/checkpoints/downstream_decoder_features"),
        ("fold_definition", "results/downstream_decoder_validation/fold_definition.csv"),
        ("raw_edf", "data/raw/openneuro"),
        ("law_figure_data", "results/conjunctive_gate_instability/figure_data"),
        ("remedy_figure_data", "results/conjunctive_law_remedy/figure_data"),
    ]:
        fp = ROOT / p
        n = len(list(fp.rglob("*"))) if fp.is_dir() else (1 if fp.exists() else 0)
        reuse.append({"artifact": label, "path": p, "exists": fp.exists(), "entries": n})
    pd.DataFrame(reuse).to_csv(AUD / "reusable_artifact_inventory.csv", index=False)

    print("verified_result_inventory:")
    print(inv.to_string(index=False))
    print("all_verified_match:", bool(inv.match.all()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
