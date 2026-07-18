from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FINAL = ROOT / "results" / "conjunctive_gate_final"
DEG = FINAL / "degradation"


def test_source_feature_reproduction_exact():
    rep = pd.read_csv(DEG / "source_feature_reproduction.csv")
    assert rep.max_rel_feature_diff.max() < 1e-6


def test_unchanged_copy_identity_and_false_withhold():
    d0 = pd.read_csv(DEG / "unchanged_control_results.csv").set_index("method")
    assert float(d0.loc["R1", "false_withhold_rate"]) <= 0.01
    assert float(d0.loc["R1", "decision_reproduction"]) >= 0.99


def test_fail_closed_missing_channel():
    fc = pd.read_csv(DEG / "fail_closed_results.csv").set_index("method")
    assert float(fc.loc["R1", "fail_closed_rate"]) >= 1.0 - 1e-9
    assert float(fc.loc["R0", "fail_closed_rate"]) >= 1.0 - 1e-9


def test_degradation_deterministic_replay():
    from scripts.conjunctive_gate_stability.degradation_common import degrade
    w = np.random.default_rng(0).normal(0, 1e-5, (3, 1000))
    a = degrade(w, 1000.0, "D1_single_channel_broadband", 3, 1, 42)
    b = degrade(w, 1000.0, "D1_single_channel_broadband", 3, 1, 42)
    assert np.allclose(a, b)


def test_severity_monotone_recorded():
    curves = pd.read_csv(DEG / "severity_response_curves.csv")
    # at least some continuous families are nondecreasing (recorded in scorecard)
    sc = pd.read_csv(DEG / "degradation_success_scorecard.csv").set_index("condition")
    assert int(sc.loc["n_monotonic_families", "passed"]) >= 6


def test_degradation_scorecard_verdict():
    sc = pd.read_csv(DEG / "degradation_success_scorecard.csv").set_index("condition")
    assert str(sc.loc["VERDICT", "passed"]) in {"DEGRADATION-PASS", "DEGRADATION-FAIL"}


def test_figure_sources_have_no_titles():
    for f in (ROOT / "scripts" / "conjunctive_gate_stability" / "figures_r").glob("figure*.R"):
        t = f.read_text()
        assert "ggtitle(" not in t and "labs(title" not in t.replace(" ", "")


FINAL_FIG_STEMS = [
    "figure1_composition_theorem", "figure2_composition_validation", "figure3_cardinality_lattice",
    "figure4_stability_transport", "figure5_operational_behavior", "figure6_downstream_information",
    "figure7_controlled_degradation", "figureS1_evidence_scorecard",
]


def test_figure_source_map_is_revised_set():
    smap = pd.read_csv(FINAL / "figure_source_map.csv")
    assert list(smap.figure) == FINAL_FIG_STEMS
    for s in FINAL_FIG_STEMS:
        assert (ROOT / "scripts" / "conjunctive_gate_stability" / "figures_r" / f"{s}.R").exists(), s


def test_figure_value_validation_all_ok():
    vv = pd.read_csv(FINAL / "figure_value_validation.csv")
    assert bool(vv.ok.all())
    assert float(vv.max_abs_discrepancy.max()) < 1e-3


def test_no_forbidden_figure_tokens():
    import re
    forbidden = [r"ggtitle\(", r"labs\(\s*title", r"plot_annotation\(\s*title", r"main="]
    for f in (ROOT / "scripts" / "conjunctive_gate_stability" / "figures_r").glob("*.R"):
        t = f.read_text()
        for pat in forbidden:
            assert not re.search(pat, t), f"{f.name}: {pat}"


FIG_DIR = ROOT / "scripts" / "conjunctive_gate_stability" / "figures_r"
MANIFEST = ROOT / "configs" / "conjunctive_gate_stability" / "final_figures.csv"


def _manifest_stems():
    return list(pd.read_csv(MANIFEST).figure)


def test_manifest_exists_and_lists_S1():
    assert MANIFEST.exists()
    stems = _manifest_stems()
    assert "figureS1_evidence_scorecard" in stems
    assert stems == FINAL_FIG_STEMS


def test_no_final_figure_script_has_bare_source_common():
    for stem in _manifest_stems():
        t = (FIG_DIR / f"{stem}.R").read_text()
        assert 'source("common.R")' not in t, stem
        # must use the injected script dir + guarded loader
        assert "CGS_FIGURE_SCRIPT_DIR" in t, stem


def test_every_manifest_script_exists_and_every_final_script_listed():
    stems = set(_manifest_stems())
    for stem in stems:
        assert (FIG_DIR / f"{stem}.R").exists(), stem
    # any non-superseded figure*_.R that renders must be in the manifest
    for f in FIG_DIR.glob("figure*.R"):
        txt = f.read_text()
        if "superseded" in txt:
            continue
        assert f.stem in stems, f"{f.stem} not in manifest"


def test_render_entrypoint_injects_options_and_reads_manifest():
    r = (ROOT / "scripts" / "conjunctive_gate_stability" / "render_all_figures.R").read_text()
    assert "CGS_PROJECT_ROOT" in r and "CGS_FIGURE_SCRIPT_DIR" in r
    assert "final_figures.csv" in r
    assert "chdir = TRUE" in r and "new.env(parent = globalenv())" in r


def test_no_zero_byte_rendered_figures():
    # Any manifest-stem figure that has been rendered must be non-zero.
    figdir = FINAL / "figures"
    for s in _manifest_stems():
        for ext in ("pdf", "png"):
            p = figdir / f"{s}.{ext}"
            if p.exists():
                assert p.stat().st_size > 0, f"zero-byte {p.name}"


def test_all_manifest_figures_rendered_complete():
    # Enforced once the host render has produced the full set; skips until then.
    figdir = FINAL / "figures"
    stems = _manifest_stems()
    complete = all((figdir / f"{s}.pdf").exists() and (figdir / f"{s}.png").exists() for s in stems)
    if not complete:
        import pytest
        rendered = sorted(s for s in stems if (figdir / f"{s}.pdf").exists())
        pytest.skip(f"Host render incomplete ({len(rendered)}/8). Rendered: {rendered}")
    for s in stems:
        for ext in ("pdf", "png"):
            p = figdir / f"{s}.{ext}"
            assert p.exists() and p.stat().st_size > 0, p.name


def test_author_package_complete():
    ap = FINAL / "author_package"
    required = ["executive_numerical_summary.md", "theorem_statement.md", "theorem_evidence_table.csv",
                "composition_validation_table.csv", "cardinality_results_table.csv", "lattice_edge_results_table.csv",
                "remedy_primary_results_table.csv", "remedy_sensitivity_results_table.csv", "transport_results_table.csv",
                "operational_results_table.csv", "downstream_results_table.csv", "degradation_results_table.csv",
                "runtime_results_table.csv", "final_claim_evidence_matrix.csv", "limitations_inventory.md",
                "manuscript_blueprint.md", "figure_map.md", "table_map.md", "abstract_numbers_only.md",
                "title_options.txt", "contribution_inventory.md", "prohibited_claims.md", "submission_readiness_report.md"]
    missing = [f for f in required if not (ap / f).exists()]
    assert not missing, missing


def test_no_raw_data_tracked():
    out = subprocess.run(["git", "ls-files", "data/raw"], cwd=ROOT, capture_output=True, text=True).stdout
    assert out.strip() == ""


def test_protected_paths_content_clean():
    res = subprocess.run(["git", "diff", "--ignore-cr-at-eol", "--exit-code", "--", "manuscript", "results/final"], cwd=ROOT)
    assert res.returncode == 0


def test_prohibited_claims_documented():
    txt = (FINAL / "author_package" / "prohibited_claims.md").read_text().lower()
    for term in ["clinical", "efficacy", "universal biological law", "regulatory", "artifact"]:
        assert term in txt


def test_paired_contrasts_present_and_significant():
    p = pd.read_csv(DEG / "degradation_paired_contrasts.csv")
    top = p[(p.severity == 4) & (p.family.str.startswith("D") & ~p.family.str.contains("D9"))]
    assert len(top) == 8
    # all top-severity paired R1-R0 contrasts are negative (R1 responds less) and BH-significant
    assert (top.R1_minus_R0 < 0).all()
    assert (top.bh_adj_p_top_severity < 0.05).all()


def test_baseline_scale_sensitivity_persistent_blindspots():
    s = pd.read_csv(DEG / "degradation_scale_sensitivity.csv")
    top = s[s.severity == 4].set_index("family")
    for fam in ["D6_clipping", "D7_partial_channel_freeze", "D8_full_channel_variance_collapse"]:
        assert top.loc[fam, "R1_perwindow"] < 0.6 and top.loc[fam, "R1_baseline"] < 0.6


def test_revised_figure_data_present():
    fd = FINAL / "figure_data"
    for f in ["f1_theorem.csv", "f2a_pooled.csv", "f2b_by_dataset.csv", "f3a_cardinality.csv",
              "f3b_lattice_points.csv", "f3b_lattice_summary.csv", "f4a_stability_sessions.csv",
              "f4b_transport_summary.csv", "f5_operational_points.csv", "f6a_natural.csv",
              "f6b_countmatched.csv", "f7a_severity.csv", "f7b_paired_top.csv", "f7c_controls.csv",
              "fS1_scorecard.csv"]:
        assert (fd / f).exists(), f


def test_windows_render_entrypoint_exists():
    assert (ROOT / "scripts" / "conjunctive_gate_stability" / "render_figures_windows.ps1").exists()
    r = (ROOT / "scripts" / "conjunctive_gate_stability" / "render_all_figures.R").read_text()
    assert "commandArgs" in r and "--file=" in r


def test_scripts_init_restored_and_nfsqi_import():
    assert (ROOT / "scripts" / "__init__.py").exists()
    # extract_window_features remains importable despite deprecated standalone main
    import importlib
    m = importlib.import_module("src.empirical.nf_sqi_t1_features")
    assert hasattr(m, "extract_window_features")
