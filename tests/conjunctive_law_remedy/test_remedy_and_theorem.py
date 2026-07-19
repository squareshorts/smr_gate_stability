from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RM = ROOT / "results" / "conjunctive_law_remedy"


def test_theorem_condition_identity():
    rng = np.random.default_rng(0)
    for _ in range(5000):
        P1, P2 = rng.uniform(0.05, 0.99, 2)
        Q = rng.uniform(0, min(P1, P2)); a, b = rng.uniform(0.05, 0.99, 2); c = rng.uniform(0, min(a, b))
        den_old = P1 + P2 - Q; den_new = P1 * a + P2 * b - Q * c
        if den_old <= 1e-9 or den_new <= 1e-9:
            continue
        j_old = Q / den_old; j_new = Q * c / den_new
        cond = c * (P1 + P2) <= P1 * a + P2 * b + 1e-12
        assert cond == (j_new <= j_old + 1e-9)


def test_blinding_pass():
    txt = (RM / "validation" / "higher_order_outcome_blinding_test.txt").read_text()
    assert "PASS" in txt and "max |stored_predicted - blind_reconstructed| = 0.000e+00" in txt


def test_source_reproduction():
    rep = pd.read_csv(RM / "source_result_reproduction.csv")
    row = rep.set_index("quantity")
    assert int(row.loc["sessions", "reproduced"]) == 114
    assert int(row.loc["task_windows", "reproduced"]) == 22418
    assert str(row.loc["verdict", "reproduced"]) == "GO-LAW"


def test_scorecard_verdict_and_partial_remedy():
    s = pd.read_csv(RM / "remedy" / "remedy_full_scorecard.csv")
    assert not s.passes_all_12.any()                 # no REMEDY-GO
    r1 = s[s.method == "R1_MEAN_PERCENTILE"].iloc[0]
    assert int(r1.n_pass) == 11 and not bool(r1.C7)   # fails only C7




def test_no_figure_titles():
    for f in (ROOT / "scripts" / "conjunctive_law_remedy" / "figures_r").glob("figure*.R"):
        t = f.read_text()
        assert "ggtitle(" not in t
        assert "labs(title" not in t.replace(" ", "")


def test_remedy_checkpoints_present():
    assert len(list((RM / "checkpoints").glob("*_remedy.parquet"))) == 114


def test_protected_paths_content_clean():
    res = subprocess.run(["git", "diff", "--ignore-cr-at-eol", "--exit-code", "--", "manuscript", "results/final"], cwd=ROOT)
    assert res.returncode == 0
