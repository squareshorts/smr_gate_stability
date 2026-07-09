from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np

from empirical.nf_sqi_common import (
    BROADBAND_RANGE,
    HIGH_BETA_BAND,
    NOISE_FLOOR_BAND,
    SMR_BAND,
    bandpower_from_psd,
    welch_psd,
)


EPS = 1e-9
CHANNEL_BANDS = ("smr", "beta", "broadband", "noise")


@dataclass(frozen=True)
class ThresholdConfig:
    """Rest-baseline percentile choices matching the batch NF-SQI analyses."""

    smr_snr_percentile: float = 75.0
    high_beta_percentile: float = 75.0
    broadband_percentile: float = 75.0
    noise_floor_percentile: float = 75.0
    transient_percentile: float = 90.0
    channel_inconsistency_percentile: float = 75.0
    nonstationarity_percentile: float | None = None
    min_valid_windows: int = 10


@dataclass(frozen=True)
class NFSQLimits:
    """Decision limits learned from a local rest baseline."""

    smr_snr_min: float
    high_beta_max: float
    broadband_max: float
    noise_floor_max: float
    transient_max: float
    channel_inconsistency_max: float
    nonstationarity_max: float | None = None

    def to_dict(self) -> dict[str, float | None]:
        return {
            "smr_snr_min": self.smr_snr_min,
            "high_beta_max": self.high_beta_max,
            "broadband_max": self.broadband_max,
            "noise_floor_max": self.noise_floor_max,
            "transient_max": self.transient_max,
            "channel_inconsistency_max": self.channel_inconsistency_max,
            "nonstationarity_max": self.nonstationarity_max,
        }

    @classmethod
    def from_dict(cls, values: dict[str, float | None]) -> "NFSQLimits":
        return cls(
            smr_snr_min=float(values["smr_snr_min"]),
            high_beta_max=float(values["high_beta_max"]),
            broadband_max=float(values["broadband_max"]),
            noise_floor_max=float(values["noise_floor_max"]),
            transient_max=float(values["transient_max"]),
            channel_inconsistency_max=float(values["channel_inconsistency_max"]),
            nonstationarity_max=(
                None if values.get("nonstationarity_max") is None else float(values["nonstationarity_max"])
            ),
        )


@dataclass(frozen=True)
class ChannelBaseline:
    """Per-channel rest statistics used for online channel-inconsistency scores."""

    means: dict[str, np.ndarray]
    stds: dict[str, np.ndarray]

    @classmethod
    def fit(cls, features: Iterable["NFSQIWindowFeatures"]) -> "ChannelBaseline":
        valid_features = [f for f in features if f.valid and f.channel_bandpowers]
        if not valid_features:
            raise ValueError("Cannot fit channel baseline without valid feature windows.")

        means: dict[str, np.ndarray] = {}
        stds: dict[str, np.ndarray] = {}
        for band in CHANNEL_BANDS:
            values = np.vstack([f.channel_bandpowers[band] for f in valid_features])
            means[band] = np.nanmean(values, axis=0)
            ddof = 1 if values.shape[0] > 1 else 0
            band_stds = np.nanstd(values, axis=0, ddof=ddof)
            stds[band] = np.where(np.isfinite(band_stds) & (band_stds > 0), band_stds, EPS)
        return cls(means=means, stds=stds)

    def score(self, features: "NFSQIWindowFeatures") -> tuple[float, float]:
        if not features.valid or not features.channel_bandpowers:
            return float("nan"), float("nan")

        sd_scores = []
        mad_scores = []
        for band in CHANNEL_BANDS:
            values = features.channel_bandpowers[band]
            mean = self.means[band]
            std = self.stds[band]
            if values.shape != mean.shape:
                raise ValueError(
                    f"Channel count mismatch for {band}: got {values.shape[0]}, "
                    f"expected {mean.shape[0]}"
                )
            standardized = (values - mean) / std
            ddof = 1 if standardized.size > 1 else 0
            sd_scores.append(float(np.nanstd(standardized, ddof=ddof)))
            center = np.nanmedian(standardized)
            mad_scores.append(float(np.nanmedian(np.abs(standardized - center))))

        return float(np.nanmean(sd_scores)), float(np.nanmean(mad_scores))

    def to_dict(self) -> dict[str, dict[str, list[float]]]:
        return {
            "means": {band: values.tolist() for band, values in self.means.items()},
            "stds": {band: values.tolist() for band, values in self.stds.items()},
        }

    @classmethod
    def from_dict(cls, values: dict[str, dict[str, list[float]]]) -> "ChannelBaseline":
        return cls(
            means={band: np.asarray(values["means"][band], dtype=float) for band in CHANNEL_BANDS},
            stds={band: np.asarray(values["stds"][band], dtype=float) for band in CHANNEL_BANDS},
        )


@dataclass(frozen=True)
class NFSQICalibration:
    """Portable calibration artifact for deployment-time loading."""

    fs: float
    limits: NFSQLimits
    channel_baseline: ChannelBaseline
    window_s: float = 1.0
    step_s: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return {
            "fs": self.fs,
            "window_s": self.window_s,
            "step_s": self.step_s,
            "limits": self.limits.to_dict(),
            "channel_baseline": self.channel_baseline.to_dict(),
        }

    @classmethod
    def from_dict(cls, values: dict[str, object]) -> "NFSQICalibration":
        return cls(
            fs=float(values["fs"]),
            window_s=float(values.get("window_s", 1.0)),
            step_s=float(values.get("step_s", 0.5)),
            limits=NFSQLimits.from_dict(values["limits"]),  # type: ignore[arg-type]
            channel_baseline=ChannelBaseline.from_dict(values["channel_baseline"]),  # type: ignore[arg-type]
        )

    def save_json(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "NFSQICalibration":
        values = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(values)


@dataclass
class NFSQIWindowFeatures:
    valid: bool
    smr_power: float = float("nan")
    smr_snr: float = float("nan")
    high_beta_power: float = float("nan")
    noise_floor_power: float = float("nan")
    broadband_power: float = float("nan")
    spectral_slope: float = float("nan")
    transient_score: float = float("nan")
    channel_inconsistency: float = float("nan")
    channel_inconsistency_mad: float = float("nan")
    nonstationarity: float = 0.0
    channel_bandpowers: dict[str, np.ndarray] = field(default_factory=dict, repr=False)

    def to_dict(self, include_channel_bandpowers: bool = False) -> dict[str, float | bool | list[float]]:
        values: dict[str, float | bool | list[float]] = {
            "valid": self.valid,
            "smr_power": self.smr_power,
            "smr_snr": self.smr_snr,
            "high_beta_power": self.high_beta_power,
            "noise_floor_power": self.noise_floor_power,
            "broadband_power": self.broadband_power,
            "spectral_slope": self.spectral_slope,
            "transient_score": self.transient_score,
            "channel_inconsistency": self.channel_inconsistency,
            "channel_inconsistency_mad": self.channel_inconsistency_mad,
            "nonstationarity": self.nonstationarity,
        }
        if include_channel_bandpowers:
            for band, band_values in self.channel_bandpowers.items():
                values[f"channel_{band}_power"] = band_values.tolist()
        return values


@dataclass(frozen=True)
class NFSQIResult:
    timestamp_s: float | None
    features: NFSQIWindowFeatures
    gate_A: bool
    gate_B: bool
    gate_C: bool
    contamination_flags: tuple[str, ...]
    rejection_flags: tuple[str, ...]

    @property
    def admissible(self) -> bool:
        return self.gate_C

    @property
    def false_admissible_A(self) -> bool:
        return self.gate_A and bool(self.contamination_flags)

    @property
    def false_admissible_B(self) -> bool:
        return self.gate_B and bool(self.contamination_flags)

    def to_dict(self) -> dict[str, object]:
        values = self.features.to_dict()
        values.update(
            {
                "timestamp_s": self.timestamp_s,
                "gate_A": self.gate_A,
                "gate_B": self.gate_B,
                "gate_C": self.gate_C,
                "admissible": self.admissible,
                "false_admissible_A": self.false_admissible_A,
                "false_admissible_B": self.false_admissible_B,
                "contamination_flags": ";".join(self.contamination_flags),
                "rejection_flags": ";".join(self.rejection_flags),
            }
        )
        return values


def _as_channel_matrix(x_channels: np.ndarray) -> np.ndarray:
    data = np.asarray(x_channels, dtype=float)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.ndim != 2:
        raise ValueError("Expected data with shape (n_channels, n_samples).")
    if data.shape[1] == 0:
        raise ValueError("Expected at least one sample.")
    return data


def _percentile(values: Iterable[float], percentile: float) -> float:
    finite = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if finite.size == 0:
        return float("nan")
    return float(np.percentile(finite, percentile))


def _bandpower_map(x_channels: np.ndarray, fs: float) -> dict[str, np.ndarray]:
    powers: dict[str, list[float]] = {band: [] for band in CHANNEL_BANDS}
    for channel in x_channels:
        freqs, psd = welch_psd(channel, fs)
        powers["smr"].append(bandpower_from_psd(freqs, psd, SMR_BAND))
        powers["beta"].append(bandpower_from_psd(freqs, psd, HIGH_BETA_BAND))
        powers["broadband"].append(bandpower_from_psd(freqs, psd, BROADBAND_RANGE))
        powers["noise"].append(bandpower_from_psd(freqs, psd, NOISE_FLOOR_BAND))
    return {band: np.asarray(values, dtype=float) for band, values in powers.items()}


def extract_realtime_features(
    x_channels: np.ndarray,
    fs: float,
    channel_baseline: ChannelBaseline | None = None,
    previous_smr_power: float | None = None,
) -> NFSQIWindowFeatures:
    """Extract NF-SQI features from one deployment-time EEG window.

    Input samples should be shaped as ``(n_channels, n_samples)`` and use the
    same units as the calibration windows. The amplitude-based transient score
    is unit-dependent, so calibration and evaluation should not mix volts and
    microvolts.
    """

    data = _as_channel_matrix(x_channels)
    transient_score = float(np.nanmax(np.abs(data)))
    averaged = np.nanmean(data, axis=0)
    freqs, psd = welch_psd(averaged, fs)
    if freqs.size == 0:
        return NFSQIWindowFeatures(valid=False, transient_score=transient_score)

    smr_power = bandpower_from_psd(freqs, psd, SMR_BAND)
    beta_power = bandpower_from_psd(freqs, psd, HIGH_BETA_BAND)
    noise_power = bandpower_from_psd(freqs, psd, NOISE_FLOOR_BAND)

    broadband_mask = (
        (freqs >= BROADBAND_RANGE[0])
        & (freqs <= BROADBAND_RANGE[1])
        & ~((freqs >= SMR_BAND[0]) & (freqs <= SMR_BAND[1]))
        & ~((freqs >= HIGH_BETA_BAND[0]) & (freqs <= HIGH_BETA_BAND[1]))
    )
    broadband_power = (
        float(np.trapz(psd[broadband_mask], freqs[broadband_mask]))
        if broadband_mask.sum() >= 2
        else float("nan")
    )
    smr_snr = float(smr_power / (broadband_power + EPS))

    slope_mask = broadband_mask & (psd > 0) & (freqs > 0)
    spectral_slope = float("nan")
    if slope_mask.sum() >= 5:
        xx = np.log10(freqs[slope_mask])
        yy = np.log10(psd[slope_mask])
        spectral_slope = float(np.polyfit(xx, yy, deg=1)[0])

    nonstationarity = 0.0
    if previous_smr_power is not None and np.isfinite(previous_smr_power):
        nonstationarity = float(abs(smr_power - previous_smr_power))

    features = NFSQIWindowFeatures(
        valid=True,
        smr_power=smr_power,
        smr_snr=smr_snr,
        high_beta_power=beta_power,
        noise_floor_power=noise_power,
        broadband_power=broadband_power,
        spectral_slope=spectral_slope,
        transient_score=transient_score,
        nonstationarity=nonstationarity,
        channel_bandpowers=_bandpower_map(data, fs),
    )

    if channel_baseline is not None:
        channel_inc, channel_inc_mad = channel_baseline.score(features)
        features.channel_inconsistency = channel_inc
        features.channel_inconsistency_mad = channel_inc_mad

    return features


def calibrate_nf_sqi(
    rest_windows: Iterable[np.ndarray],
    fs: float,
    config: ThresholdConfig | None = None,
) -> tuple[NFSQLimits, ChannelBaseline, list[NFSQIWindowFeatures]]:
    """Learn deployable NF-SQI limits from rest-baseline windows."""

    config = config or ThresholdConfig()
    features: list[NFSQIWindowFeatures] = []
    previous_smr: float | None = None

    for window in rest_windows:
        feats = extract_realtime_features(window, fs, previous_smr_power=previous_smr)
        if feats.valid:
            previous_smr = feats.smr_power
            features.append(feats)

    if len(features) < config.min_valid_windows:
        raise ValueError(
            f"Need at least {config.min_valid_windows} valid rest windows; got {len(features)}."
        )

    channel_baseline = ChannelBaseline.fit(features)
    for feats in features:
        feats.channel_inconsistency, feats.channel_inconsistency_mad = channel_baseline.score(feats)

    limits = NFSQLimits(
        smr_snr_min=_percentile((f.smr_snr for f in features), config.smr_snr_percentile),
        high_beta_max=_percentile((f.high_beta_power for f in features), config.high_beta_percentile),
        broadband_max=_percentile((f.broadband_power for f in features), config.broadband_percentile),
        noise_floor_max=_percentile((f.noise_floor_power for f in features), config.noise_floor_percentile),
        transient_max=_percentile((f.transient_score for f in features), config.transient_percentile),
        channel_inconsistency_max=_percentile(
            (f.channel_inconsistency for f in features),
            config.channel_inconsistency_percentile,
        ),
        nonstationarity_max=(
            _percentile((f.nonstationarity for f in features), config.nonstationarity_percentile)
            if config.nonstationarity_percentile is not None
            else None
        ),
    )
    return limits, channel_baseline, features


def calibrate_nf_sqi_bundle(
    rest_windows: Iterable[np.ndarray],
    fs: float,
    window_s: float = 1.0,
    step_s: float = 0.5,
    config: ThresholdConfig | None = None,
) -> tuple[NFSQICalibration, list[NFSQIWindowFeatures]]:
    """Calibrate NF-SQI and return a JSON-serializable deployment artifact."""

    limits, channel_baseline, features = calibrate_nf_sqi(rest_windows, fs, config=config)
    return (
        NFSQICalibration(
            fs=float(fs),
            limits=limits,
            channel_baseline=channel_baseline,
            window_s=window_s,
            step_s=step_s,
        ),
        features,
    )


def evaluate_nf_sqi_window(
    x_channels: np.ndarray,
    fs: float,
    limits: NFSQLimits,
    channel_baseline: ChannelBaseline,
    previous_smr_power: float | None = None,
    timestamp_s: float | None = None,
) -> NFSQIResult:
    """Evaluate one EEG window using calibrated NF-SQI limits."""

    features = extract_realtime_features(
        x_channels,
        fs,
        channel_baseline=channel_baseline,
        previous_smr_power=previous_smr_power,
    )
    if not features.valid:
        return NFSQIResult(
            timestamp_s=timestamp_s,
            features=features,
            gate_A=False,
            gate_B=False,
            gate_C=False,
            contamination_flags=("invalid_window",),
            rejection_flags=("invalid_window",),
        )

    rejection_flags = []
    contamination_flags = []

    if not features.smr_snr > limits.smr_snr_min:
        rejection_flags.append("low_smr_snr")
    if not features.high_beta_power < limits.high_beta_max:
        rejection_flags.append("high_beta")
    if not features.broadband_power < limits.broadband_max:
        contamination_flags.append("broadband")
    if not features.noise_floor_power < limits.noise_floor_max:
        contamination_flags.append("noise_floor")
    if not features.transient_score < limits.transient_max:
        contamination_flags.append("transient")
    if not features.channel_inconsistency < limits.channel_inconsistency_max:
        contamination_flags.append("channel_inconsistency")
    if limits.nonstationarity_max is not None and not features.nonstationarity < limits.nonstationarity_max:
        contamination_flags.append("nonstationarity")

    rejection_flags.extend(contamination_flags)
    gate_A = "low_smr_snr" not in rejection_flags
    gate_B = gate_A and "high_beta" not in rejection_flags
    gate_C = gate_B and not contamination_flags

    return NFSQIResult(
        timestamp_s=timestamp_s,
        features=features,
        gate_A=gate_A,
        gate_B=gate_B,
        gate_C=gate_C,
        contamination_flags=tuple(contamination_flags),
        rejection_flags=tuple(rejection_flags),
    )


class NFSQIRealtime:
    """Small rolling-window helper for online NF-SQI evaluation."""

    def __init__(
        self,
        fs: float,
        limits: NFSQLimits,
        channel_baseline: ChannelBaseline,
        window_s: float = 1.0,
        step_s: float = 0.5,
    ) -> None:
        if fs <= 0:
            raise ValueError("Sampling frequency must be positive.")
        if window_s <= 0 or step_s <= 0:
            raise ValueError("Window and step durations must be positive.")

        self.fs = float(fs)
        self.limits = limits
        self.channel_baseline = channel_baseline
        self.window_samples = int(round(window_s * fs))
        self.step_samples = int(round(step_s * fs))
        if self.window_samples < 1 or self.step_samples < 1:
            raise ValueError("Window and step durations must include at least one sample.")

        self._buffer: np.ndarray | None = None
        self._buffer_start_sample = 0
        self._previous_smr_power: float | None = None

    @classmethod
    def from_calibration(cls, calibration: NFSQICalibration) -> "NFSQIRealtime":
        return cls(
            fs=calibration.fs,
            limits=calibration.limits,
            channel_baseline=calibration.channel_baseline,
            window_s=calibration.window_s,
            step_s=calibration.step_s,
        )

    @classmethod
    def from_rest_windows(
        cls,
        rest_windows: Iterable[np.ndarray],
        fs: float,
        window_s: float = 1.0,
        step_s: float = 0.5,
        config: ThresholdConfig | None = None,
    ) -> "NFSQIRealtime":
        calibration, _ = calibrate_nf_sqi_bundle(
            rest_windows,
            fs,
            window_s=window_s,
            step_s=step_s,
            config=config,
        )
        return cls.from_calibration(calibration)

    def reset_state(self) -> None:
        self._buffer = None
        self._buffer_start_sample = 0
        self._previous_smr_power = None

    def evaluate_window(self, x_channels: np.ndarray, timestamp_s: float | None = None) -> NFSQIResult:
        result = evaluate_nf_sqi_window(
            x_channels,
            fs=self.fs,
            limits=self.limits,
            channel_baseline=self.channel_baseline,
            previous_smr_power=self._previous_smr_power,
            timestamp_s=timestamp_s,
        )
        if result.features.valid:
            self._previous_smr_power = result.features.smr_power
        return result

    def push(self, samples: np.ndarray) -> list[NFSQIResult]:
        """Append new samples and return each completed rolling-window result."""

        chunk = _as_channel_matrix(samples)
        if self._buffer is None:
            self._buffer = chunk
        else:
            if chunk.shape[0] != self._buffer.shape[0]:
                raise ValueError(
                    f"Channel count mismatch: got {chunk.shape[0]}, expected {self._buffer.shape[0]}"
                )
            self._buffer = np.concatenate([self._buffer, chunk], axis=1)

        results: list[NFSQIResult] = []
        while self._buffer.shape[1] >= self.window_samples:
            timestamp_s = self._buffer_start_sample / self.fs
            window = self._buffer[:, : self.window_samples]
            results.append(self.evaluate_window(window, timestamp_s=timestamp_s))
            self._buffer = self._buffer[:, self.step_samples :]
            self._buffer_start_sample += self.step_samples

        return results


__all__ = [
    "ChannelBaseline",
    "NFSQICalibration",
    "NFSQLimits",
    "NFSQIRealtime",
    "NFSQIResult",
    "NFSQIWindowFeatures",
    "ThresholdConfig",
    "calibrate_nf_sqi_bundle",
    "calibrate_nf_sqi",
    "evaluate_nf_sqi_window",
    "extract_realtime_features",
]
