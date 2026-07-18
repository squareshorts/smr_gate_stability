"""Controlled-degradation primitives: raw-window loading, faithful feature re-extraction
(reusing the canonical nf_sqi extractor), and frozen D0-D9 signal transforms."""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for c in (ROOT, ROOT / "src"):
    if str(c) not in sys.path:
        sys.path.insert(0, str(c))

import mne  # noqa: E402
mne.set_log_level("ERROR")
from src.empirical.nf_sqi_common import SENSORIMOTOR_CHANNELS  # noqa: E402
from src.empirical.nf_sqi_t1_features import extract_window_features  # noqa: E402
from src.empirical.nf_sqi_common import read_events_for_edf  # noqa: E402

CACHE = ROOT / "results" / "baseline_gate_stability" / "checkpoints" / "features"
BAND_MAP = {"smr": "smr", "beta": "beta", "broadband": "broadband", "noise": "noise"}
SEVERITY = [1, 2, 3, 4]
FAMILIES = ["D0_unchanged", "D1_single_channel_broadband", "D2_common_mode_broadband",
            "D3_narrowband_35_45", "D4_narrowband_20_30", "D5_transient_impulse",
            "D6_clipping", "D7_partial_channel_freeze", "D8_full_channel_variance_collapse",
            "D9_missing_channel"]
CONTINUOUS = FAMILIES[1:9]  # D1..D8


def load_canonical(key):
    with gzip.open(CACHE / f"{key}_canonical.csv.gz", "rt") as fh:
        return pd.read_csv(fh)


def edf_path(dataset, subject, session):
    return ROOT / "data" / "raw" / "openneuro" / dataset / subject / session / "eeg" / f"{subject}_{session}_task-smrbmi_eeg.edf"


def load_raw_task_windows(dataset, subject, session, with_rest_sigma=False):
    """Return (fs, {round(time_s,3): (3,N) volts}) for task windows only.
    If with_rest_sigma, also return per-channel robust sigma over all rest samples."""
    raw = mne.io.read_raw_edf(edf_path(dataset, subject, session), preload=True, verbose=False)
    chans = [c for c in SENSORIMOTOR_CHANNELS if c in raw.ch_names]
    if chans != SENSORIMOTOR_CHANNELS:
        raise ValueError("montage")
    raw.pick_channels(chans)
    raw = raw.reorder_channels(SENSORIMOTOR_CHANNELS)
    fs = float(raw.info["sfreq"])
    events = read_events_for_edf(edf_path(dataset, subject, session), raw.times[-1])
    state = np.full(raw.n_times, -1, np.int8)
    for _, ev in events.loc[events["instruction"].astype(str).isin(["rest", "task"])].iterrows():
        code = 0 if str(ev["instruction"]) == "rest" else 1
        s = max(0, min(raw.n_times, int(round(float(ev["onset_s"]) * fs))))
        e = max(s, min(raw.n_times, int(round((float(ev["onset_s"]) + float(ev["duration_s"])) * fs))))
        state[s:e] = code
    data = raw.get_data()
    win, hop = int(fs), int(fs * 0.5)
    out = {}
    for start in np.arange(0, data.shape[1] - win, hop):
        start = int(start); stop = start + win
        if float(np.mean(state[start:stop] == 1)) >= 0.95:
            out[round(start / fs, 3)] = data[:, start:stop].copy()
    if with_rest_sigma:
        rest_samples = data[:, state == 0]
        if rest_samples.shape[1] > 0:
            med = np.median(rest_samples, axis=1, keepdims=True)
            mad = np.median(np.abs(rest_samples - med), axis=1)
            rest_sigma = 1.4826 * mad
        else:
            rest_sigma = None
        return fs, out, rest_sigma
    return fs, out


def features_from_window(w, fs):
    """Re-extract canonical features from a (3,N) volts window; map to cache column names."""
    if not np.isfinite(w).all():
        return {"raw_feature_valid": False}
    res = extract_window_features(w, fs)
    if not res.get("valid", False):
        return {"raw_feature_valid": False}
    row = {
        "high_beta_power": res["high_beta_power"], "broadband_power": res["broadband_power"],
        "noise_floor_power": res["noise_floor_power"], "transient_score": res["transient_score"],
        "smr_snr": res["smr_snr"], "raw_feature_valid": True,
        "peak_to_peak_uv": float(np.max(np.ptp(w, axis=1)) * 1e6),
    }
    for i in range(3):
        for band in ("smr", "beta", "broadband", "noise"):
            row[f"channel_{band}_{i}"] = res[f"ch_{i}_{band}"]
    return row


def robust_sigma(w):
    med = np.median(w, axis=1, keepdims=True)
    mad = np.median(np.abs(w - med), axis=1)
    return 1.4826 * mad  # per channel


# ---- frozen transforms; return degraded copy ----
def degrade(w, fs, family, level, ch, gindex, sigma_override=None):
    w = w.copy()
    sig = robust_sigma(w) if sigma_override is None else np.asarray(sigma_override, float)
    sig_mean = float(np.mean(sig))
    N = w.shape[1]
    rng = np.random.default_rng(1000 * gindex + 100 * FAMILIES.index(family) + level)
    if family == "D0_unchanged":
        return w
    if family == "D1_single_channel_broadband":
        amp = [0.5, 1.0, 1.5, 2.0][level - 1] * sig[ch]
        w[ch] += rng.normal(0, amp, N)
    elif family == "D2_common_mode_broadband":
        amp = [0.5, 1.0, 1.5, 2.0][level - 1] * sig_mean
        n = rng.normal(0, amp, N); w += n
    elif family == "D3_narrowband_35_45":
        amp = [0.5, 1.0, 1.5, 2.0][level - 1] * sig_mean
        t = np.arange(N) / fs; w += amp * np.sin(2 * np.pi * 40.0 * t)
    elif family == "D4_narrowband_20_30":
        amp = [0.5, 1.0, 1.5, 2.0][level - 1] * sig_mean
        t = np.arange(N) / fs; w += amp * np.sin(2 * np.pi * 25.0 * t)
    elif family == "D5_transient_impulse":
        amp = [2.0, 4.0, 8.0, 16.0][level - 1] * sig[ch]
        c = N // 2; w[ch, c - 2:c + 3] += amp
    elif family == "D6_clipping":
        frac = [0.6, 0.45, 0.30, 0.15][level - 1]
        lim = frac * float(np.max(np.abs(w)))
        w = np.clip(w, -lim, lim)
    elif family == "D7_partial_channel_freeze":
        frac = [0.25, 0.50, 0.75, 0.90][level - 1]
        k = max(1, int((1 - frac) * N)); w[ch, k:] = w[ch, k - 1]
    elif family == "D8_full_channel_variance_collapse":
        fac = [0.50, 0.25, 0.10, 0.00][level - 1]
        m = float(np.mean(w[ch])); w[ch] = m + np.sqrt(fac) * (w[ch] - m)
    elif family == "D9_missing_channel":
        w[ch] = np.nan
    return w
