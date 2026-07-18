from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from baseline_gate_stability.core import agreement_metrics, apply_monitor, regularize_covariance
from scripts.baseline_gate_stability.analyze_stability_transport_availability import grouped_bootstrap_summary, split_samples
from scripts.baseline_gate_stability.build_canonical_cache import checkpoint_valid

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "baseline_gate_stability"


def test_checkpoint_resume_accepts_verified_cache() -> None:
    feature = next((OUT / "checkpoints" / "features").glob("*_canonical.csv.gz"))
    key = feature.name.removesuffix("_canonical.csv.gz")
    decision = OUT / "checkpoints" / "monitor_decisions" / f"{key}_decisions.csv.gz"
    assert checkpoint_valid(feature, decision)


def test_no_complete_dataset_memory_accumulation() -> None:
    text = (ROOT / "scripts" / "baseline_gate_stability" / "build_canonical_cache.py").read_text(encoding="utf-8")
    assert "del data, raw" in text
    assert "checkpoint_valid" in text


def test_canonical_count_reproduction() -> None:
    counts = pd.read_csv(OUT / "data" / "count_reproduction.csv")
    pooled = counts.loc[counts.dataset == "pooled"].iloc[0]
    assert int(pooled.compared_windows) == 22418
    assert int(pooled.decision_differences) == 0
    assert int(pooled.reason_code_differences) == 0


def test_calibration_split_independence() -> None:
    rest = pd.DataFrame({"window_start_s": np.arange(120) * 0.5, "window_id": np.arange(120)})
    splits = split_samples(rest, "deterministic-key")
    for name in ("first_half_second_half", "odd_even_nonoverlap"):
        left, right = splits[name]
        assert set(left.window_id).isdisjoint(set(right.window_id))


def test_identical_evaluation_windows_across_variants() -> None:
    decisions = pd.read_csv(OUT / "calibration" / "decisions_by_split.csv", usecols=["dataset", "participant", "session", "monitor", "split_type", "window_id"])
    counts = decisions.groupby(["dataset", "participant", "session", "monitor", "split_type"]).window_id.nunique()
    assert counts.groupby(level=[0, 1, 2, 3]).nunique().eq(1).all()


def test_accepted_set_jaccard() -> None:
    result = agreement_metrics(np.array([1, 1, 0, 0], bool), np.array([1, 0, 1, 0], bool))
    assert result["accepted_set_jaccard"] == 1 / 3
    assert result["overall_agreement"] == 0.5


def test_cross_session_leakage_prevention() -> None:
    script = (ROOT / "scripts" / "baseline_gate_stability" / "analyze_stability_transport_availability.py").read_text(encoding="utf-8")
    assert "source_rest" in script and "target_rest" in script
    assert "monitor_fit_and_apply(task, source_rest, monitor)" in script


def test_participant_grouped_inference() -> None:
    data = pd.DataFrame({"dataset": ["d", "d"], "participant": ["p1", "p2"], "monitor": ["m", "m"], "metric": [0.5, 1.0]})
    result = grouped_bootstrap_summary(data, ["monitor"], ["metric"], draws=20)
    assert result.loc[0, "participants"] == 2
    assert result.loc[0, "median_metric"] == 0.75


def test_fail_closed_behavior() -> None:
    thresholds = {name: 1.0 for name in ("high_beta_power", "broadband_power", "noise_floor_power", "transient_score", "channel_inconsistency")}
    frame = pd.DataFrame([{"raw_feature_valid": True, "high_beta_power": np.nan, "broadband_power": 0.0, "noise_floor_power": 0.0, "transient_score": 0.0, "channel_inconsistency": 0.0, "peak_to_peak_uv": 0.0}])
    for monitor in ("M0_NO_GATE", "M1_HIGH_BETA", "M2_BROADBAND_HIGH_FREQUENCY", "M3_AMPLITUDE_150", "M4_NFSQI_FULL_QUALITY"):
        assert not apply_monitor(frame, monitor, thresholds)[0][0]


def test_covariance_regularization() -> None:
    covariance = np.array([[1.0, 0.999, 0.999], [0.999, 1.0, 0.999], [0.999, 0.999, 1.0]])
    regularized = regularize_covariance(covariance)
    assert np.linalg.eigvalsh(regularized).min() > 0


def test_external_environment_isolation() -> None:
    manifest = (OUT / "external_monitor" / "environment_manifest.txt").read_text(encoding="utf-8")
    assert "isolated .venv/Scripts/python.exe" in manifest
    assert "pyRiemann: 0.10" in manifest


def test_downstream_identical_test_sets() -> None:
    folds = pd.read_csv(ROOT / "results" / "downstream_decoder_validation" / "fold_definition.csv")
    results = pd.read_csv(OUT / "downstream" / "monitor_decoder_results.csv")
    merged = results.merge(folds[["fold_id", "test_windows"]], on="fold_id", how="left")
    assert merged.groupby("fold_id").test_windows.nunique().eq(1).all()


def test_r_figure_source_data_validation() -> None:
    for number in range(1, 8):
        source = OUT / "figure_data" / f"figure{number}_value_validation.csv"
        validation = pd.read_csv(source)
        assert validation.exact_source_values.all()


def test_no_figure_titles() -> None:
    for script in (ROOT / "scripts" / "baseline_gate_stability" / "figures_r").glob("figure*.R"):
        text = script.read_text(encoding="utf-8")
        assert "ggtitle(" not in text
        assert "labs(title" not in text.replace(" ", "")


def test_protected_manuscript_paths() -> None:
    result = subprocess.run(["git", "diff", "--exit-code", "--", "manuscript", "results/final"], cwd=ROOT)
    assert result.returncode == 0


def test_deterministic_outputs() -> None:
    rest = pd.DataFrame({"window_start_s": np.arange(120) * 0.5, "window_id": np.arange(120)})
    first = split_samples(rest, "same-key")
    second = split_samples(rest, "same-key")
    for name in first:
        assert first[name][0].equals(second[name][0])
        assert first[name][1].equals(second[name][1])
