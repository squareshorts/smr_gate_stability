from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from utils.signal_metrics import band_envelope, bandpower, burst_metrics, envelope_timescale


@dataclass(frozen=True)
class NullParams:
    model: str
    duration_s: float = 20.0
    fs: float = 128.0
    burn_s: float = 2.0
    beta_hz: float = 25.0
    smr_hz: float = 13.0
    feedback_gain: float = 0.0
    noise: float = 0.08
    seed: int = 1


def _complex_ou_mode(freq_hz: float, damping: float, noise: float, n_total: int, fs: float, rng) -> np.ndarray:
    dt = 1.0 / fs
    z = np.zeros(n_total, dtype=np.complex128)
    z[0] = 0.1 + 0.1j
    rot = np.exp(1j * 2 * np.pi * freq_hz * dt)
    for t in range(1, n_total):
        z[t] = (z[t - 1] + dt * (-damping * z[t - 1]) + noise * np.sqrt(dt) * (rng.normal() + 1j * rng.normal())) * rot
    return z


def _damped_harmonic(freq_hz: float, zeta: float, noise: float, n_total: int, fs: float, rng) -> np.ndarray:
    dt = 1.0 / fs
    omega = 2 * np.pi * freq_hz
    radius = float(np.exp(-zeta * omega * dt))
    theta = omega * dt
    x = np.zeros(n_total)
    x[0] = rng.normal(scale=noise)
    x[1] = rng.normal(scale=noise)
    a1 = 2 * radius * np.cos(theta)
    a2 = -(radius**2)
    for t in range(2, n_total):
        x[t] = a1 * x[t - 1] + a2 * x[t - 2] + noise * rng.normal()
    return x


def _ar2_oscillator(freq_hz: float, radius: float, noise: float, n_total: int, fs: float, rng) -> np.ndarray:
    dt = 1.0 / fs
    theta = 2 * np.pi * freq_hz * dt
    x = np.zeros(n_total)
    x[0] = rng.normal(scale=noise)
    x[1] = rng.normal(scale=noise)
    a1 = 2 * radius * np.cos(theta)
    a2 = -(radius**2)
    for t in range(2, n_total):
        x[t] = a1 * x[t - 1] + a2 * x[t - 2] + noise * rng.normal()
    return x


def _nonlinear_saturation(freq_hz: float, mu: float, sat: float, gain: float, noise: float, n_total: int, fs: float, rng) -> np.ndarray:
    dt = 1.0 / fs
    z = np.zeros(n_total, dtype=np.complex128)
    z[0] = 0.15 + 0.05j
    rot = np.exp(1j * 2 * np.pi * freq_hz * dt)
    for t in range(1, n_total):
        r2 = float(np.abs(z[t - 1]) ** 2)
        drift = (mu - gain - sat * r2) * z[t - 1]
        z[t] = (z[t - 1] + dt * drift + noise * np.sqrt(dt) * (rng.normal() + 1j * rng.normal())) * rot
    return np.real(z)


def simulate_null_model(params: NullParams) -> dict[str, np.ndarray | float]:
    rng = np.random.default_rng(params.seed)
    fs = params.fs
    n_total = int(round((params.duration_s + params.burn_s) * fs))
    burn_n = int(round(params.burn_s * fs))

    slow = _complex_ou_mode(params.smr_hz, damping=0.04, noise=params.noise * 0.55, n_total=n_total, fs=fs, rng=rng)

    if params.model == "linear_ou":
        fast = np.real(
            _complex_ou_mode(
                params.beta_hz,
                damping=0.06 + params.feedback_gain,
                noise=params.noise,
                n_total=n_total,
                fs=fs,
                rng=rng,
            )
        )
    elif params.model == "damped_harmonic":
        fast = _damped_harmonic(
            params.beta_hz,
            zeta=0.06 + 0.25 * params.feedback_gain,
            noise=params.noise * 0.8,
            n_total=n_total,
            fs=fs,
            rng=rng,
        )
    elif params.model == "ar2":
        radius = max(0.70, 0.985 - 0.22 * params.feedback_gain)
        fast = _ar2_oscillator(params.beta_hz, radius=radius, noise=params.noise * 0.35, n_total=n_total, fs=fs, rng=rng)
    elif params.model == "stuart_landau":
        fast = _nonlinear_saturation(
            params.beta_hz,
            mu=0.45,
            sat=1.0,
            gain=params.feedback_gain,
            noise=params.noise,
            n_total=n_total,
            fs=fs,
            rng=rng,
        )
    else:
        raise ValueError(f"Unknown null model: {params.model}")

    slow = np.real(slow)
    x = slow[burn_n:] + fast[burn_n:]
    time = np.arange(len(x)) / fs
    return {"time": time, "x": x, "fs": fs}


def summarize_null_model(sim: dict[str, np.ndarray | float], burst_threshold: float | None = None) -> dict[str, float]:
    x = np.asarray(sim["x"])
    fs = float(sim["fs"])
    env = band_envelope(x, fs, (20.0, 30.0))
    threshold = float(np.percentile(env, 80.0)) if burst_threshold is None else float(burst_threshold)
    return {
        "smr_power": bandpower(x, fs, (12.0, 15.0)),
        "beta_power": bandpower(x, fs, (20.0, 30.0)),
        "high_freq_35_55_power": bandpower(x, fs, (35.0, 55.0)),
        "beta_env_mean": float(np.mean(env)),
        "beta_env_std": float(np.std(env)),
        "burst_threshold": threshold,
        **burst_metrics(env, threshold, fs),
        **envelope_timescale(env, fs),
    }
