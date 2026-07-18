"""Comparative engineering analysis of baseline-calibrated EEG quality gates."""

from .core import agreement_metrics, apply_monitor, fit_quality_thresholds, temporal_metrics

__all__ = ["agreement_metrics", "apply_monitor", "fit_quality_thresholds", "temporal_metrics"]
