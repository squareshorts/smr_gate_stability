from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "downstream_decoder_validation" / "quality_policies.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("downstream_quality_policies", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _windows() -> pd.DataFrame:
    return pd.DataFrame({
        "finite_labelled": [True, True, True, False],
        "high_beta_power": [1.0, 4.0, 1.0, 1.0],
        "broadband_power": [1.0, 1.0, 4.0, 1.0],
        "noise_floor_power": [1.0, 1.0, 1.0, 1.0],
        "transient_score": [1.0, 1.0, 1.0, 1.0],
        "channel_inconsistency": [1.0, 1.0, 1.0, 1.0],
        "peak_to_peak_uv": [100.0, 100.0, 200.0, 100.0],
    })


def test_quality_masks_have_required_policies_and_quality_only_logic() -> None:
    module = _load_module()
    source = MODULE.read_text(encoding="utf-8").lower()
    assert "gate_a" not in source
    assert "smr_snr" not in source
    thresholds = {name: 2.0 for name in module.QUALITY_FEATURES}
    masks = module.build_quality_only_masks(_windows(), thresholds)
    assert tuple(masks) == module.POLICY_NAMES
    assert masks["ALL"].tolist() == [True, True, True, False]
    assert masks["HB"].tolist() == [True, False, True, False]
    assert masks["NFSQI_FULL"].tolist() == [True, False, False, False]
    assert masks["AMPLITUDE_150"].tolist() == [True, True, False, False]


def test_policy_masks_are_nested_as_required() -> None:
    module = _load_module()
    thresholds = {name: 2.0 for name in module.QUALITY_FEATURES}
    masks = module.build_quality_only_masks(_windows(), thresholds)
    assert (masks["NFSQI_FULL"] <= masks["HB"]).all()
    assert (masks["NFSQI_FULL"] <= masks["NFSQI_NO_HB"]).all()
    assert (masks["NFSQI_FULL"] <= masks["BBHF"]).all()
