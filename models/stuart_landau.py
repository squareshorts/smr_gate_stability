from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from utils.signal_metrics import band_envelope, bandpower, burst_metrics, envelope_timescale, welch_psd


@dataclass(frozen=True)
class SLParams:
    duration_s: float = 20.0
    fs: float = 128.0
    burn_s: float = 2.0
    smr_hz: float = 13.0
    beta_hz: float = 25.0
    mu_s: float = 0.55
    mu_f: float = 0.45
    sat_s: float = 1.0
    sat_f: float = 1.0
    noise_s: float = 0.045
    noise_f: float = 0.055
    feedback_gain: float = 0.0
    linear_sf: float = 0.0
    linear_fs: float = 0.0
    amp_sf: float = 0.0
    amp_fs: float = 0.0
    phase_coupling: float = 0.0
    seed: int = 1


def with_updates(params: SLParams, **kwargs) -> SLParams:
    return replace(params, **kwargs)


def simulate_two_mode(params: SLParams) -> dict[str, np.ndarray | float]:
    rng = np.random.default_rng(params.seed)
    fs = float(params.fs)
    dt = 1.0 / fs
    n_total = int(round((params.duration_s + params.burn_s) * fs))
    burn_n = int(round(params.burn_s * fs))

    z_s = np.zeros(n_total, dtype=np.complex128)
    z_f = np.zeros(n_total, dtype=np.complex128)
    z_s[0] = 0.2 + 0.1j
    z_f[0] = 0.15 - 0.08j
    rot_s = np.exp(1j * 2.0 * np.pi * params.smr_hz * dt)
    rot_f = np.exp(1j * 2.0 * np.pi * params.beta_hz * dt)
    sqrt_dt = np.sqrt(dt)

    for t in range(1, n_total):
        zs = z_s[t - 1]
        zf = z_f[t - 1]
        rs2 = float(np.abs(zs) ** 2)
        rf2 = float(np.abs(zf) ** 2)

        # Real-valued phase coupling is kept weak and optional.
        phase_push_s = np.exp(1j * params.phase_coupling * np.imag(zf * np.conj(zs)) * dt)
        phase_push_f = np.exp(1j * params.phase_coupling * np.imag(zs * np.conj(zf)) * dt)

        drift_s = (
            (params.mu_s - params.sat_s * rs2 + params.amp_fs * rf2) * zs
            + params.linear_fs * zf
        )
        drift_f = (
            (params.mu_f - params.feedback_gain - params.sat_f * rf2 + params.amp_sf * rs2) * zf
            + params.linear_sf * zs
        )
        noise_s = params.noise_s * sqrt_dt * (rng.normal() + 1j * rng.normal())
        noise_f = params.noise_f * sqrt_dt * (rng.normal() + 1j * rng.normal())
        z_s[t] = (zs + dt * drift_s + noise_s) * rot_s * phase_push_s
        z_f[t] = (zf + dt * drift_f + noise_f) * rot_f * phase_push_f

    z_s = z_s[burn_n:]
    z_f = z_f[burn_n:]
    time = np.arange(len(z_s)) / fs
    x = np.real(z_s + z_f)
    return {"time": time, "z_s": z_s, "z_f": z_f, "x": x, "fs": fs}


def summarize_simulation(sim: dict[str, np.ndarray | float], burst_threshold: float | None = None) -> dict[str, float]:
    x = np.asarray(sim["x"])
    fs = float(sim["fs"])
    freqs, psd = welch_psd(x, fs)
    env_beta = band_envelope(x, fs, (20.0, 30.0))
    env_smr = band_envelope(x, fs, (12.0, 15.0))
    threshold = float(np.percentile(env_beta, 80.0)) if burst_threshold is None else float(burst_threshold)
    bursts = burst_metrics(env_beta, threshold, fs)
    timescale = envelope_timescale(env_beta, fs)
    return {
        "smr_power": bandpower(x, fs, (12.0, 15.0)),
        "beta_power": bandpower(x, fs, (20.0, 30.0)),
        "broadband_4_45_power": bandpower(x, fs, (4.0, 45.0)),
        "high_freq_35_55_power": bandpower(x, fs, (35.0, 55.0)),
        "smr_env_mean": float(np.mean(env_smr)),
        "beta_env_mean": float(np.mean(env_beta)),
        "beta_env_std": float(np.std(env_beta)),
        "burst_threshold": threshold,
        **bursts,
        **timescale,
    }


def simulate_and_summarize(params: SLParams, burst_threshold: float | None = None) -> dict[str, float]:
    sim = simulate_two_mode(params)
    return summarize_simulation(sim, burst_threshold=burst_threshold)


def psd_table(sim: dict[str, np.ndarray | float], label: str) -> list[dict[str, float | str]]:
    freqs, psd = welch_psd(np.asarray(sim["x"]), float(sim["fs"]))
    return [{"condition": label, "frequency_hz": float(f), "psd": float(p)} for f, p in zip(freqs, psd)]


def timeseries_table(sim: dict[str, np.ndarray | float], label: str, max_points: int = 800) -> list[dict[str, float | str]]:
    time = np.asarray(sim["time"])
    x = np.asarray(sim["x"])
    z_s = np.asarray(sim["z_s"])
    z_f = np.asarray(sim["z_f"])
    step = max(1, int(np.ceil(len(time) / max_points)))
    rows = []
    for idx in range(0, len(time), step):
        rows.append(
            {
                "condition": label,
                "time_s": float(time[idx]),
                "signal": float(x[idx]),
                "smr_amplitude": float(np.abs(z_s[idx])),
                "beta_amplitude": float(np.abs(z_f[idx])),
            }
        )
    return rows
