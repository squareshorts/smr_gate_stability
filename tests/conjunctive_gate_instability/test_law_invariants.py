from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "conjunctive_gate_instability"


def test_frozen_subset_lattice_is_31():
    subs = pd.read_csv(OUT / "frozen_gate_subsets.csv")
    assert len(subs) == 31
    assert subs.cardinality.value_counts().to_dict() == {1: 5, 2: 10, 3: 10, 4: 5, 5: 1}


def test_input_cache_reproduction_exact():
    counts = pd.read_csv(OUT / "count_reproduction.csv")
    pooled = counts.loc[counts.dataset == "pooled"].iloc[0]
    assert int(pooled.compared_windows) == 22418
    assert int(pooled.decision_differences) == 0
    manifest = pd.read_csv(OUT / "input_cache_manifest.csv")
    assert len(manifest) == 114
    assert manifest.groupby(["dataset", "participant"]).ngroups == 57
    assert set(manifest.dataset) == {"ds004444", "ds004446", "ds004447"}


def test_all_sessions_checkpointed():
    ckpts = list((OUT / "checkpoints").glob("*.parquet"))
    assert len(ckpts) == 114
    errors = pd.read_csv(OUT / "execution_errors.csv")
    assert len(errors) == 0


def test_predicted_jaccard_formula_bounds():
    df = pd.read_csv(OUT / "subset_results_by_session.csv")
    e = df[df.estimator == "empirical"]
    assert e.observed_jaccard.between(0, 1).all()
    assert e.predicted_jaccard.between(0, 1).all()
    # singletons: predicted equals q/(p1+p2-q) exactly from stored terms
    s = e[e.cardinality == 1].iloc[0]
    denom = s.pred_accept_g1 + s.pred_accept_g2 - s.pred_joint_accept
    expected = 1.0 if denom <= 1e-12 else s.pred_joint_accept / denom
    assert abs(expected - s.predicted_jaccard) < 1e-9


def test_cardinality_monotone_drop():
    card = pd.read_csv(OUT / "cardinality_results.csv")
    e = card[card.estimator == "empirical"].set_index("cardinality")
    assert e.loc[1, "median_observed_jaccard"] - e.loc[5, "median_observed_jaccard"] >= 0.15
    # observed medians non-increasing in cardinality
    med = [e.loc[k, "median_observed_jaccard"] for k in range(1, 6)]
    assert all(med[i] >= med[i + 1] - 1e-9 for i in range(4))


def test_scorecard_has_verdict():
    score = pd.read_csv(OUT / "law_success_scorecard.csv")
    v = score.loc[score.condition == "VERDICT", "passed"].iloc[0]
    assert v in {"GO-LAW", "PARTIAL-LAW", "NO-GO-LAW"}


def test_protected_paths_content_clean():
    # CRLF-insensitive protected-path check must be clean (no content change).
    result = subprocess.run(
        ["git", "diff", "--ignore-cr-at-eol", "--exit-code", "--", "manuscript", "results/final"],
        cwd=ROOT)
    assert result.returncode == 0
