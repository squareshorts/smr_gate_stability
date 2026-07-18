"""STAGE 0 — audit and reproduce the verified GO-LAW outputs from saved files.

Does NOT rerun the 31-subset analysis. Reads saved outputs and recomputes the
headline statistics to confirm exact reproducibility.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "results" / "conjunctive_gate_instability"
OUT = ROOT / "results" / "conjunctive_law_remedy"
OUT.mkdir(parents=True, exist_ok=True)

EXPECT = {
    "sessions": 114, "pairs": 57, "task_windows": 22418, "subsets": 31,
    "pooled_spearman": 0.988, "pooled_median_ae": 0.013, "k1": 0.915, "k5": 0.630,
}


def main() -> int:
    manifest = pd.read_csv(SRC / "input_cache_manifest.csv")
    counts = pd.read_csv(SRC / "count_reproduction.csv")
    by_sess = pd.read_csv(SRC / "subset_results_by_session.csv")
    card = pd.read_csv(SRC / "cardinality_results.csv")
    hd = pd.read_csv(SRC / "harrell_davis_sensitivity.csv")
    score = pd.read_csv(SRC / "law_success_scorecard.csv")

    emp = by_sess[by_sess.estimator == "empirical"]
    pooled_spear = float(spearmanr(emp.predicted_jaccard, emp.observed_jaccard).statistic)
    pooled_mae = float(np.median(np.abs(emp.observed_jaccard - emp.predicted_jaccard)))
    cemp = card[card.estimator == "empirical"].set_index("cardinality")
    k1 = float(cemp.loc[1, "median_observed_jaccard"])
    k5 = float(cemp.loc[5, "median_observed_jaccard"])
    pooled_windows = int(counts.loc[counts.dataset == "pooled", "compared_windows"].iloc[0])
    pooled_diffs = int(counts.loc[counts.dataset == "pooled", "decision_differences"].iloc[0])
    n_subsets = emp.subset_id.nunique()
    cond_rows = score[score.condition.str.startswith("C")]
    nine_pass = bool(cond_rows.passed.astype(str).str.lower().isin(["true", "1", "1.0"]).all())
    verdict = score.loc[score.condition == "VERDICT", "passed"].iloc[0]

    checks = {
        "sessions_114": len(manifest) == 114,
        "pairs_57": manifest.groupby(["dataset", "participant"]).ngroups == 57,
        "task_windows_22418": pooled_windows == 22418,
        "subsets_31": n_subsets == 31,
        "zero_decision_mismatch": pooled_diffs == 0,
        "pooled_spearman_0.988": round(pooled_spear, 3) == 0.988,
        "pooled_median_ae_0.013": round(pooled_mae, 3) == 0.013,
        "k1_0.915": round(k1, 3) == 0.915,
        "k5_0.630": round(k5, 3) == 0.630,
        "emp_hd_qualitative_agreement": bool((hd.pooled_spearman > 0).all()
                                             and (hd[hd.estimator == "empirical"].median_jaccard_K1.iloc[0]
                                                  - hd[hd.estimator == "empirical"].median_jaccard_K5.iloc[0] > 0.15)
                                             and (hd[hd.estimator == "hd"].median_jaccard_K1.iloc[0]
                                                  - hd[hd.estimator == "hd"].median_jaccard_K5.iloc[0] > 0.15)),
        "nine_conditions_pass": nine_pass,
        "verdict_go_law": verdict == "GO-LAW",
    }

    repro = pd.DataFrame([
        {"quantity": "sessions", "expected": 114, "reproduced": len(manifest)},
        {"quantity": "dataset_participant_pairs", "expected": 57, "reproduced": manifest.groupby(["dataset", "participant"]).ngroups},
        {"quantity": "task_windows", "expected": 22418, "reproduced": pooled_windows},
        {"quantity": "subsets", "expected": 31, "reproduced": n_subsets},
        {"quantity": "decision_mismatches", "expected": 0, "reproduced": pooled_diffs},
        {"quantity": "pooled_spearman", "expected": 0.988, "reproduced": round(pooled_spear, 4)},
        {"quantity": "pooled_median_abs_error", "expected": 0.013, "reproduced": round(pooled_mae, 4)},
        {"quantity": "K1_median_jaccard", "expected": 0.915, "reproduced": round(k1, 4)},
        {"quantity": "K5_median_jaccard", "expected": 0.630, "reproduced": round(k5, 4)},
        {"quantity": "verdict", "expected": "GO-LAW", "reproduced": verdict},
    ])
    repro.to_csv(OUT / "source_result_reproduction.csv", index=False)

    all_pass = all(checks.values())
    lines = ["# Stage 0 — source result audit", ""]
    lines.append(f"Reproduced from saved outputs in `{SRC.name}/` without rerunning the 31-subset analysis.")
    lines.append("")
    for k, v in checks.items():
        lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    lines.append("")
    lines.append(f"Pooled Spearman = {pooled_spear:.4f}; pooled median |error| = {pooled_mae:.4f}; "
                 f"K1 = {k1:.4f}; K5 = {k5:.4f}; verdict = {verdict}.")
    lines.append("")
    lines.append(f"## VERDICT: {'ALL SOURCE CHECKS REPRODUCE — proceed' if all_pass else 'BLOCKER — source results do not reproduce'}")
    (OUT / "source_result_audit.md").write_text("\n".join(lines), encoding="utf-8")

    print("checks:", checks)
    print(f"spearman={pooled_spear:.4f} mae={pooled_mae:.4f} k1={k1:.4f} k5={k5:.4f} verdict={verdict}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
