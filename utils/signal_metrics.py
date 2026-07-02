from __future__ import annotations

import numpy as np
from scipy import signal


def welch_psd(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    nperseg = min(len(x), max(128, int(fs * 4)))
    freqs, psd = signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2)
    return freqs, psd


def bandpower_from_psd(freqs: np.ndarray, psd: np.ndarray, band: tuple[float, float]) -> float:
    mask = (freqs >= band[0]) & (freqs <= band[1])
    if mask.sum() < 2:
        return float("nan")
    return float(np.trapz(psd[mask], freqs[mask]))


def bandpower(x: np.ndarray, fs: float, band: tuple[float, float]) -> float:
    freqs, psd = welch_psd(x, fs)
    return bandpower_from_psd(freqs, psd, band)


def band_envelope(x: np.ndarray, fs: float, band: tuple[float, float]) -> np.ndarray:
    nyq = fs / 2.0
    low = max(0.001, band[0] / nyq)
    high = min(0.999, band[1] / nyq)
    sos = signal.butter(4, [low, high], btype="bandpass", output="sos")
    filtered = signal.sosfiltfilt(sos, x)
    return np.abs(signal.hilbert(filtered))


def burst_metrics(envelope: np.ndarray, threshold: float, fs: float, min_duration_s: float = 0.04) -> dict[str, float]:
    above = envelope > threshold
    if above.size == 0:
        return {"burst_rate_per_min": 0.0, "burst_duration_s": 0.0, "burst_occupancy": 0.0, "n_bursts": 0}
    edges = np.diff(np.r_[False, above, False].astype(int))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    durations = (ends - starts) / fs
    keep = durations >= min_duration_s
    durations = durations[keep]
    total_minutes = len(envelope) / fs / 60.0
    n_bursts = int(len(durations))
    rate = n_bursts / total_minutes if total_minutes > 0 else 0.0
    occupancy = float(np.sum(above) / len(above))
    return {
        "burst_rate_per_min": float(rate),
        "burst_duration_s": float(np.mean(durations)) if n_bursts else 0.0,
        "burst_occupancy": occupancy,
        "n_bursts": n_bursts,
    }


def envelope_timescale(envelope: np.ndarray, fs: float) -> dict[str, float]:
    env = np.asarray(envelope, dtype=float)
    env = env - np.nanmean(env)
    if len(env) < 4 or np.nanstd(env) == 0:
        return {"ar1_tau_s": float("nan"), "acf_efold_s": float("nan")}
    x0 = env[:-1]
    x1 = env[1:]
    denom = float(np.dot(x0, x0))
    phi = float(np.dot(x0, x1) / denom) if denom > 0 else float("nan")
    phi = min(max(phi, 1e-6), 0.999999)
    ar_tau = -1.0 / (fs * np.log(phi))

    max_lag = min(len(env) // 2, int(fs * 5))
    acf = signal.correlate(env, env, mode="full")
    acf = acf[len(acf) // 2 : len(acf) // 2 + max_lag]
    if acf[0] <= 0:
        efold = float("nan")
    else:
        acf = acf / acf[0]
        below = np.flatnonzero(acf <= np.exp(-1))
        efold = float(below[0] / fs) if len(below) else float(max_lag / fs)
    return {"ar1_tau_s": float(ar_tau), "acf_efold_s": efold}


def phase_randomize(x: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    spectrum = np.fft.rfft(x)
    phases = rng.uniform(0, 2 * np.pi, size=len(spectrum))
    phases[0] = 0.0
    if len(phases) > 1:
        phases[-1] = 0.0
    randomized = np.abs(spectrum) * np.exp(1j * phases)
    return np.fft.irfft(randomized, n=len(x))
