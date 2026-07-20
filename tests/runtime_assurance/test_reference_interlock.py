from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts.runtime_assurance.reference_interlock import SPECIFICATION_VERSION, evaluate

FEATURES = {"smr_snr": 2.0, "high_beta_power": 1.0, "broadband_power": 1.0, "noise_floor_power": 1.0, "transient_score": 1.0, "channel_inconsistency": 1.0}
LIMITS = {"smr_snr_min": 1.0, "high_beta_max": 2.0, "broadband_max": 2.0, "noise_floor_max": 2.0, "transient_max": 2.0, "channel_inconsistency_max": 2.0}

def test_gate_a_is_separate_from_quality_conditions():
    base = evaluate(FEATURES, LIMITS)
    poor_quality = evaluate(dict(FEATURES, broadband_power=3.0), LIMITS)
    assert base.gate_a_requested and poor_quality.gate_a_requested
    assert not poor_quality.gate_c_allowed

def test_equality_is_fail_closed_and_deterministic():
    boundary = dict(FEATURES, high_beta_power=2.0)
    first, second = evaluate(boundary, LIMITS), evaluate(boundary, LIMITS)
    assert first == second
    assert not first.gate_c_allowed and "high_beta" in first.reason_codes
    assert not evaluate(dict(FEATURES, smr_snr=1.0), LIMITS).gate_a_requested

def test_nonfinite_and_missing_features_fail_closed():
    for value in (np.nan, np.inf, -np.inf):
        result = evaluate(dict(FEATURES, smr_snr=value), LIMITS)
        assert result.withhold and result.invalid_input
    assert evaluate({}, LIMITS).withhold

def test_configuration_version_and_isolated_output_paths():
    assert SPECIFICATION_VERSION == "1.0.0-runtime-assurance"
    root = Path(__file__).resolve().parents[2]
    assert (root / "scripts" / "runtime_assurance" / "reference_interlock.py").is_file()
    assert not any((root / "manuscript").glob("*.runtime_assurance*"))
