"""Quality-only training masks for downstream decoder validation.

These functions deliberately contain no SMR-target or Gate A logic.  They are
kept separate from the deployment gate because decoder-training selection must
not use the signal the decoder is intended to learn.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


QUALITY_FEATURES = (
    "high_beta_power",
    "broadband_power",
    "noise_floor_power",
    "transient_score",
    "channel_inconsistency",
)

POLICY_NAMES = (
    "ALL",
    "HB",
    "BBHF",
    "NFSQI_NO_HB",
    "NFSQI_FULL",
    "AMPLITUDE_150",
)


def build_quality_only_masks(
    windows: pd.DataFrame,
    thresholds: Mapping[str, float],
    *,
    finite_labelled_column: str = "finite_labelled",
    peak_to_peak_uv_column: str = "peak_to_peak_uv",
) -> dict[str, pd.Series]:
    """Return quality-only masks for one training session.

    ``thresholds`` must have the released rest-baseline-calibrated upper
    limits for every value in :data:`QUALITY_FEATURES`.  ``ALL`` requires only
    finite correctly labelled training windows.  Every other policy is a
    subset of that same base mask and applies identically to both classes.
    """
    required = set(QUALITY_FEATURES) | {finite_labelled_column, peak_to_peak_uv_column}
    missing = sorted(required - set(windows.columns))
    if missing:
        raise ValueError(f"Missing required downstream-mask columns: {missing}")
    missing_limits = sorted(set(QUALITY_FEATURES) - set(thresholds))
    if missing_limits:
        raise ValueError(f"Missing released rest-baseline thresholds: {missing_limits}")

    base = windows[finite_labelled_column].astype(bool).copy()
    values = {name: pd.to_numeric(windows[name], errors="coerce") for name in QUALITY_FEATURES}
    for value in values.values():
        base &= np.isfinite(value)

    hb = values["high_beta_power"] < float(thresholds["high_beta_power"])
    bb = values["broadband_power"] < float(thresholds["broadband_power"])
    hf = values["noise_floor_power"] < float(thresholds["noise_floor_power"])
    transient = values["transient_score"] < float(thresholds["transient_score"])
    channel = values["channel_inconsistency"] < float(thresholds["channel_inconsistency"])
    p2p = pd.to_numeric(windows[peak_to_peak_uv_column], errors="coerce")

    return {
        "ALL": base,
        "HB": base & hb,
        "BBHF": base & bb & hf,
        "NFSQI_NO_HB": base & bb & hf & transient & channel,
        "NFSQI_FULL": base & hb & bb & hf & transient & channel,
        "AMPLITUDE_150": base & np.isfinite(p2p) & (p2p < 150.0),
    }
