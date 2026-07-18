"""Validate saved law + remedy + degradation outputs without heavy rerun."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
LAW = ROOT / "results" / "conjunctive_gate_instability"
REM = ROOT / "results" / "conjunctive_law_remedy"
DEG = ROOT / "results" / "conjunctive_gate_final" / "degradation"


def main():
    checks = {}
    emp = pd.read_csv(LAW / "subset_results_by_session.csv")
    emp = emp[emp.estimator == "empirical"]
    checks["law_spearman_0.988"] = round(float(spearmanr(emp.predicted_jaccard, emp.observed_jaccard).statistic), 3) == 0.988
    card = pd.read_csv(LAW / "cardinality_results.csv"); ce = card[card.estimator == "empirical"].set_index("cardinality")
    checks["K1_0.915"] = round(float(ce.loc[1, "median_observed_jaccard"]), 3) == 0.915
    checks["K5_0.630"] = round(float(ce.loc[5, "median_observed_jaccard"]), 3) == 0.630
    cal = pd.read_csv(REM / "author_package" / "calibration_stability_table.csv").set_index("method")
    checks["R1_splithalf_0.944"] = round(float(cal.loc["R1_MEAN_PERCENTILE", "pooled_median_splithalf_jaccard"]), 3) == 0.944
    score = pd.read_csv(REM / "remedy" / "remedy_full_scorecard.csv")
    checks["no_remedy_all12"] = not score.passes_all_12.any()
    dsc = pd.read_csv(DEG / "degradation_success_scorecard.csv")
    checks["degradation_scorecard_present"] = (dsc.condition == "VERDICT").any()
    ok = all(checks.values())
    print("validate_existing_results:", checks, "ALL_PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
