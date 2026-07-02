"""SPT4 Revised: Rigorous empirical time-scale analysis.

Addresses bandwidth confound by:
1. Computing tau on decimated (1-Hz) envelopes (regulation time scale, not filter time scale)
2. Adding bandwidth-matched control (SMR 12-15 Hz 3-Hz BW vs HB 20-23 Hz 3-Hz BW)
3. Computing tau at multiple temporal resolutions
4. Reporting and flagging the bandwidth confound explicitly

Outputs
-------
outputs/tables/spt4_empirical_timescale_features.csv   (updated)
outputs/tables/spt4_empirical_tau_ratios.csv            (updated)
outputs/tables/spt4_tau_bandwidth_control.csv           (new)
outputs/figures/spt4_empirical_timescale_panel.*        (updated)
outputs/figures/spt4_tau_beta_vs_tau_smr.*              (updated)
outputs/figures/spt4_bandwidth_control.*                (new)
outputs/reports/spt4_results.md                         (updated)
outputs/logs/spt4_empirical_processing.log              (updated)
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal as scipy_signal
from scipy import stats

import mne

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style
from utils.signal_metrics import bandpower_from_psd, band_envelope


DATASET_ID = "ds004446"
RAW_ROOT = ROOT / "data" / "raw" / "openneuro" / DATASET_ID
SENSORIMOTOR_CHANNELS = ["E36", "E104", "E128"]

# Primary bands
SMR_BAND = (12.0, 15.0)        # 3 Hz bandwidth
HIGH_BETA_BAND = (20.0, 30.0)  # 10 Hz bandwidth

# Bandwidth-matched control: same 3 Hz bandwidth for both
SMR_BW_MATCHED = (12.0, 15.0)  # 3 Hz
HB_BW_MATCHED = (20.0, 23.0)   # 3 Hz (matched to SMR bandwidth)

DECIMATE_HZ = 1.0   # Regulation time scale: 1-Hz decimated envelope
BLOCK_S = 4.0       # Block duration for block-mean tau


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_subject_session(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def load_eeg_segment(edf_path: Path, condition: str) -> tuple[np.ndarray, float, list]:
    subject, session = parse_subject_session(edf_path)
    events_path = edf_path.parent / f"{subject}_{session}_task-smrbmi_events.tsv"
    if not events_path.exists():
        return np.array([]), 0.0, []

    raw = mne.io.read_raw_edf(edf_path, preload=False,
                               include=SENSORIMOTOR_CHANNELS, verbose="ERROR")
    available = [ch for ch in SENSORIMOTOR_CHANNELS if ch in raw.ch_names]
    if not available:
        raw.close()
        return np.array([]), 0.0, []

    raw.pick(available)
    raw.load_data(verbose="ERROR")
    data = raw.get_data(picks=available)
    fs = float(raw.info["sfreq"])
    raw.close()

    events = pd.read_csv(events_path, sep="\t")
    events["onset_s"] = events["onset"].astype(float) / 1000.0
    events["duration_s"] = events["duration"].astype(float)

    segments = []
    n_samples = data.shape[1]
    for _, row in events[events["instruction"].astype(str) == condition].iterrows():
        start = int(round(float(row["onset_s"]) * fs))
        stop = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
        start = max(0, min(start, n_samples))
        stop = max(start, min(stop, n_samples))
        if stop - start >= int(fs * 2):
            segments.append(np.nanmean(data[:, start:stop], axis=0))

    if not segments:
        return np.array([]), fs, available

    x = np.concatenate(segments)
    return scipy_signal.detrend(x), fs, available


def ar1_tau(env: np.ndarray, fs: float) -> float:
    """AR1 time constant of a signal at its native sample rate."""
    e = env - np.nanmean(env)
    if len(e) < 4 or np.nanstd(e) == 0:
        return np.nan
    x0, x1 = e[:-1], e[1:]
    denom = float(np.dot(x0, x0))
    phi = float(np.dot(x0, x1) / denom) if denom > 0 else np.nan
    if np.isnan(phi) or phi <= 0 or phi >= 1:
        return np.nan
    return -1.0 / (fs * np.log(phi))


def block_mean_tau(env: np.ndarray, fs: float, block_s: float = 4.0) -> float:
    """AR1 time constant computed on non-overlapping block means.

    This separates the regulation time scale from the filter bandwidth effect.
    Each block mean represents the average power in a block_s-second window.
    The AR1 of block means estimates how fast power regulation changes,
    not how fast the filter envelope fluctuates.
    """
    block_n = int(block_s * fs)
    n_blocks = len(env) // block_n
    if n_blocks < 8:
        return np.nan
    block_means = np.array([env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])
    # Effective sample rate for block means
    fs_block = 1.0 / block_s
    return ar1_tau(block_means, fs_block)


def decimated_env_tau(env: np.ndarray, fs: float,
                      target_hz: float = 1.0) -> float:
    """AR1 tau on anti-alias decimated envelope.

    Decimates the envelope to target_hz (default 1 Hz) using a low-pass filter
    before downsampling. This represents the slowly-varying envelope dynamics.
    """
    decimate_factor = int(round(fs / target_hz))
    if decimate_factor < 2:
        return ar1_tau(env, fs)
    # Anti-alias filter
    try:
        env_d = scipy_signal.decimate(env, decimate_factor, ftype="fir", zero_phase=True)
    except Exception:
        n_blk = len(env) // decimate_factor
        env_d = np.array([env[i * decimate_factor:(i + 1) * decimate_factor].mean()
                          for i in range(n_blk)])
    return ar1_tau(env_d, target_hz)


def bandwidth_expected_tau(bandwidth_hz: float, fs: float) -> float:
    """Theoretical tau_AR1 from bandwidth alone (Gaussian envelope approximation).

    For a stationary narrow-band process with bandwidth Δf:
    phi ≈ exp(-π² Δf² / fs²)
    tau = -1/(fs * log(phi)) ≈ fs / (π² Δf²)
    """
    return float(fs / (np.pi ** 2 * bandwidth_hz ** 2))


def compute_timescale_features(x: np.ndarray, fs: float,
                                subject: str, session: str,
                                condition: str) -> dict:
    if len(x) < int(fs * 8):
        return {"subject": subject, "session": session, "condition": condition,
                "status": "insufficient_data"}

    # Primary envelopes
    smr_env = band_envelope(x, fs, SMR_BAND)
    hb_env = band_envelope(x, fs, HIGH_BETA_BAND)

    # Bandwidth-matched envelopes (same 3 Hz bandwidth)
    smr_env_bw = band_envelope(x, fs, SMR_BW_MATCHED)
    hb_env_bw = band_envelope(x, fs, HB_BW_MATCHED)

    # AR1 at native fs
    smr_tau_ar1 = ar1_tau(smr_env, fs)
    hb_tau_ar1 = ar1_tau(hb_env, fs)

    # AR1 on block means (4-s blocks)
    smr_tau_block = block_mean_tau(smr_env, fs, BLOCK_S)
    hb_tau_block = block_mean_tau(hb_env, fs, BLOCK_S)

    # AR1 on 1-Hz decimated envelope
    smr_tau_dec = decimated_env_tau(smr_env, fs, DECIMATE_HZ)
    hb_tau_dec = decimated_env_tau(hb_env, fs, DECIMATE_HZ)

    # Bandwidth-matched AR1 at native fs
    smr_tau_bw = ar1_tau(smr_env_bw, fs)
    hb_tau_bw = ar1_tau(hb_env_bw, fs)

    # Theoretical tau from bandwidth alone
    smr_tau_theory = bandwidth_expected_tau(SMR_BAND[1] - SMR_BAND[0], fs)        # 3 Hz BW
    hb_tau_theory = bandwidth_expected_tau(HIGH_BETA_BAND[1] - HIGH_BETA_BAND[0], fs)  # 10 Hz BW
    hb_tau_theory_bw = bandwidth_expected_tau(HB_BW_MATCHED[1] - HB_BW_MATCHED[0], fs)  # 3 Hz BW

    # Tau ratios
    def safe_ratio(a, b):
        if np.isnan(a) or np.isnan(b) or b == 0:
            return np.nan
        return a / b

    return {
        "subject": subject,
        "session": session,
        "condition": condition,
        "n_samples": len(x),
        "fs": fs,
        "duration_s": len(x) / fs,

        # Primary (confounded by bandwidth)
        "smr_tau_ar1_s": smr_tau_ar1,
        "hb_tau_ar1_s": hb_tau_ar1,
        "tau_ratio_ar1": safe_ratio(hb_tau_ar1, smr_tau_ar1),
        "tau_ratio_ar1_expected_from_bw": safe_ratio(hb_tau_theory, smr_tau_theory),

        # Block-mean (regulation time scale, partially deconfounded)
        "smr_tau_block_s": smr_tau_block,
        "hb_tau_block_s": hb_tau_block,
        "tau_ratio_block": safe_ratio(hb_tau_block, smr_tau_block),

        # Decimated (regulation time scale)
        "smr_tau_dec_s": smr_tau_dec,
        "hb_tau_dec_s": hb_tau_dec,
        "tau_ratio_dec": safe_ratio(hb_tau_dec, smr_tau_dec),

        # Bandwidth-matched (true confound control)
        "smr_tau_bw_matched_s": smr_tau_bw,
        "hb_tau_bw_matched_s": hb_tau_bw,
        "tau_ratio_bw_matched": safe_ratio(hb_tau_bw, smr_tau_bw),

        # Theory predictions
        "smr_tau_theory_from_bw_s": smr_tau_theory,
        "hb_tau_theory_from_bw_s": hb_tau_theory,
        "hb_tau_theory_bw_matched_s": hb_tau_theory_bw,

        # Excess tau beyond bandwidth prediction (signal of regulation dynamics)
        "smr_tau_excess_s": (smr_tau_ar1 - smr_tau_theory) if not np.isnan(smr_tau_ar1) else np.nan,
        "hb_tau_excess_s": (hb_tau_ar1 - hb_tau_theory) if not np.isnan(hb_tau_ar1) else np.nan,

        "status": "ok",
    }


def make_tau_figures(feat_df: pd.DataFrame, root: Path) -> None:
    set_style()
    ok = feat_df[feat_df["status"] == "ok"].copy()
    if ok.empty:
        return

    # Figure: primary tau panel
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))

    # A: AR1 tau scatter (primary)
    axes[0, 0].scatter(ok["smr_tau_ar1_s"], ok["hb_tau_ar1_s"], alpha=0.7, s=35)
    mx = max(ok["smr_tau_ar1_s"].max(), ok["hb_tau_ar1_s"].max()) * 1.1
    axes[0, 0].plot([0, mx], [0, mx], "k--", lw=0.8, label="Equal")
    axes[0, 0].plot([0, mx], [0, mx * 0.5], "g:", lw=0.8, label="tau_HB = 0.5*tau_SMR")
    axes[0, 0].set_xlabel("tau_SMR AR1 (s)")
    axes[0, 0].set_ylabel("tau_HB AR1 (s)")
    axes[0, 0].set_title("(A) AR1 – primary\n[CONFOUNDED by bandwidth]")
    axes[0, 0].legend(fontsize=7)

    # B: Block-mean tau scatter (deconfounded)
    ok_b = ok.dropna(subset=["tau_ratio_block"])
    if not ok_b.empty:
        axes[0, 1].scatter(ok_b["smr_tau_block_s"], ok_b["hb_tau_block_s"], alpha=0.7, s=35,
                           color="#ff7f0e")
        mx2 = max(ok_b["smr_tau_block_s"].max(), ok_b["hb_tau_block_s"].max()) * 1.1
        axes[0, 1].plot([0, mx2], [0, mx2], "k--", lw=0.8)
        axes[0, 1].plot([0, mx2], [0, mx2 * 0.5], "g:", lw=0.8)
    axes[0, 1].set_xlabel("tau_SMR block-mean (s)")
    axes[0, 1].set_ylabel("tau_HB block-mean (s)")
    axes[0, 1].set_title(f"(B) Block-mean ({int(BLOCK_S)}s blocks)\n[Regulation time scale]")

    # C: Bandwidth-matched tau scatter
    ok_bw = ok.dropna(subset=["tau_ratio_bw_matched"])
    if not ok_bw.empty:
        axes[0, 2].scatter(ok_bw["smr_tau_bw_matched_s"], ok_bw["hb_tau_bw_matched_s"],
                           alpha=0.7, s=35, color="#d62728")
        mx3 = max(ok_bw["smr_tau_bw_matched_s"].max(), ok_bw["hb_tau_bw_matched_s"].max()) * 1.1
        axes[0, 2].plot([0, mx3], [0, mx3], "k--", lw=0.8, label="Equal (same BW)")
        axes[0, 2].plot([0, mx3], [0, mx3 * 0.5], "g:", lw=0.8)
    axes[0, 2].set_xlabel("tau_SMR 12-15 Hz (s)")
    axes[0, 2].set_ylabel("tau_HB 20-23 Hz (s)")
    axes[0, 2].set_title("(C) BW-matched (both 3 Hz)\n[Confound control]")

    # D: Tau ratio distributions
    ratios = {
        "AR1 (confounded)": ok["tau_ratio_ar1"].dropna(),
        "Block-mean": ok.get("tau_ratio_block", pd.Series(dtype=float)).dropna(),
        "BW-matched": ok.get("tau_ratio_bw_matched", pd.Series(dtype=float)).dropna(),
    }
    colors_d = ["#1f77b4", "#ff7f0e", "#d62728"]
    for (label, vals), color in zip(ratios.items(), colors_d):
        if not vals.empty:
            axes[1, 0].hist(vals, bins=10, alpha=0.5, color=color, label=label, edgecolor="white")
    axes[1, 0].axvline(1.0, color="black", ls="--", lw=1.0, label="Equal")
    axes[1, 0].axvline(0.5, color="green", ls=":", lw=0.8)
    axes[1, 0].set_xlabel("tau_HB / tau_SMR")
    axes[1, 0].set_ylabel("Count")
    axes[1, 0].set_title("(D) Tau ratio distributions")
    axes[1, 0].legend(fontsize=6)

    # E: Excess tau (actual - bandwidth-predicted)
    axes[1, 1].scatter(ok["smr_tau_excess_s"], ok["hb_tau_excess_s"], alpha=0.7, s=35)
    axes[1, 1].axhline(0, color="gray", ls="--", lw=0.8)
    axes[1, 1].axvline(0, color="gray", ls="--", lw=0.8)
    axes[1, 1].set_xlabel("SMR excess tau (obs - BW-theory) s")
    axes[1, 1].set_ylabel("HB excess tau (obs - BW-theory) s")
    axes[1, 1].set_title("(E) Regulation excess beyond BW\n[Dynamic contribution]")

    # F: Summary by condition
    ok_r = ok[ok["condition"] == "rest"]
    measures = ["smr_tau_ar1_s", "hb_tau_ar1_s", "smr_tau_block_s", "hb_tau_block_s"]
    labels_f = ["SMR AR1", "HB AR1", "SMR block", "HB block"]
    colors_f = ["#2ca02c", "#d62728", "#2ca02c", "#d62728"]
    styles_f = ["solid", "solid", "dashed", "dashed"]
    for m, lbl, col, ls in zip(measures, labels_f, colors_f, styles_f):
        if m in ok_r.columns and not ok_r[m].dropna().empty:
            vals = ok_r[m].dropna()
            axes[1, 2].scatter(np.ones(len(vals)) * measures.index(m) + 0.1 * np.random.default_rng(0).uniform(-1, 1, len(vals)),
                               vals, color=col, alpha=0.7, s=25)
            axes[1, 2].scatter(measures.index(m), vals.median(), color=col, s=80, marker="_",
                               linewidths=2, zorder=5)
    axes[1, 2].set_xticks(range(len(measures)))
    axes[1, 2].set_xticklabels(labels_f, rotation=30, ha="right", fontsize=7)
    axes[1, 2].set_ylabel("Tau (s)")
    axes[1, 2].set_title("(F) Tau by measure type (rest)")

    fig.suptitle("SPT4 Revised: Empirical time-scale analysis with bandwidth control", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(fig, feat_df, "spt4_empirical_timescale_panel", root)


def make_bw_control_figure(feat_df: pd.DataFrame, root: Path) -> None:
    """Bandwidth confound control figure."""
    set_style()
    ok = feat_df[feat_df["status"] == "ok"].copy()
    if ok.empty:
        return

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    # Panel A: observed vs theory tau ratio
    theory_ratio = ok["tau_ratio_ar1_expected_from_bw"].dropna().mean()
    obs_ratios = ok["tau_ratio_ar1"].dropna()
    bw_ratios = ok["tau_ratio_bw_matched"].dropna()

    axes[0].boxplot([obs_ratios.values, bw_ratios.values],
                    labels=["AR1\n(10 Hz vs 3 Hz BW)", "BW-matched\n(3 Hz vs 3 Hz)"],
                    patch_artist=True,
                    boxprops=dict(facecolor="lightblue"))
    axes[0].axhline(theory_ratio, color="red", ls="--", lw=1.2,
                    label=f"BW-predicted ratio ({theory_ratio:.2f})")
    axes[0].axhline(1.0, color="black", ls=":", lw=0.8, label="Equal time scales")
    axes[0].set_ylabel("tau_HB / tau_SMR")
    axes[0].set_title("(A) Bandwidth confound check")
    axes[0].legend(fontsize=7)

    # Panel B: excess tau scatter (beyond BW prediction)
    excess_smr = ok["smr_tau_excess_s"].dropna()
    excess_hb = ok["hb_tau_excess_s"].dropna()
    n = min(len(excess_smr), len(excess_hb))
    axes[1].scatter(excess_smr.values[:n], excess_hb.values[:n], alpha=0.7, s=35)
    axes[1].axhline(0, color="gray", ls="--", lw=0.8)
    axes[1].axvline(0, color="gray", ls="--", lw=0.8)
    axes[1].plot([0, max(excess_smr.max(), excess_hb.max())],
                 [0, max(excess_smr.max(), excess_hb.max())], "k--", lw=0.8)
    axes[1].set_xlabel("SMR excess tau beyond BW (s)")
    axes[1].set_ylabel("HB excess tau beyond BW (s)")
    axes[1].set_title("(B) Regulation excess tau\n(bandwidth effect removed)")

    # Panel C: block-mean tau (4 s) ratio
    block_ratios = ok["tau_ratio_block"].dropna()
    dec_ratios = ok["tau_ratio_dec"].dropna()
    data_c = []
    labels_c = []
    if not block_ratios.empty:
        data_c.append(block_ratios.values)
        labels_c.append(f"4-s block\nmean")
    if not dec_ratios.empty:
        data_c.append(dec_ratios.values)
        labels_c.append(f"1-Hz\ndecimated")
    if data_c:
        axes[2].boxplot(data_c, labels=labels_c, patch_artist=True,
                        boxprops=dict(facecolor="lightgreen"))
    axes[2].axhline(1.0, color="black", ls=":", lw=0.8, label="Equal")
    axes[2].axhline(0.5, color="green", ls="--", lw=0.8, label="2x separation")
    axes[2].set_ylabel("tau_HB / tau_SMR")
    axes[2].set_title("(C) Deconfounded tau ratios\n(regulation time scale)")
    axes[2].legend(fontsize=7)

    fig.suptitle("SPT4: Bandwidth confound control analysis", fontsize=10)
    plt.tight_layout()

    src = ok[[c for c in ok.columns if "tau" in c or "subject" in c or "condition" in c]].copy()
    save_csv_backed_figure(fig, src, "spt4_bandwidth_control", root)


def make_tau_ratio_figure(feat_df: pd.DataFrame, root: Path) -> None:
    set_style()
    ok = feat_df[feat_df["status"] == "ok"].dropna(subset=["tau_ratio_ar1"])
    if ok.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    axes[0].scatter(ok["smr_tau_ar1_s"], ok["hb_tau_ar1_s"], s=40, alpha=0.8)
    mx = max(ok["smr_tau_ar1_s"].max(), ok["hb_tau_ar1_s"].max()) * 1.1
    axes[0].plot([0, mx], [0, mx], "k--", lw=1, label="Equal")
    axes[0].plot([0, mx], [0, mx / 2], "g:", lw=1, label="2x separation")
    axes[0].set_xlabel("tau_SMR AR1 (s)")
    axes[0].set_ylabel("tau_HB AR1 (s)")
    axes[0].set_title("Empirical tau_HB vs tau_SMR")
    axes[0].legend(fontsize=7)

    axes[1].hist(ok["tau_ratio_ar1"], bins=min(len(ok), 15), color="#1f77b4",
                 edgecolor="white", alpha=0.8, label="AR1 (primary)")
    if "tau_ratio_bw_matched" in ok.columns:
        ok_bw = ok.dropna(subset=["tau_ratio_bw_matched"])
        if not ok_bw.empty:
            axes[1].hist(ok_bw["tau_ratio_bw_matched"], bins=min(len(ok_bw), 15),
                         color="#ff7f0e", edgecolor="white", alpha=0.5,
                         label="BW-matched (control)")
    axes[1].axvline(1.0, color="red", ls="--", lw=1.5, label="Equal time scales")
    axes[1].axvline(0.5, color="orange", ls=":", lw=1.2, label="2x separation")
    n_below = int((ok["tau_ratio_ar1"] < 0.5).sum())
    axes[1].text(0.97, 0.97, f"AR1 ratio < 0.5: {n_below}/{len(ok)}",
                 transform=axes[1].transAxes, ha="right", va="top", fontsize=8)
    axes[1].set_xlabel("tau_HB / tau_SMR")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Tau ratio distributions")
    axes[1].legend(fontsize=7)

    fig.suptitle("SPT4: tau_HB vs tau_SMR (primary and control)", fontsize=10)
    plt.tight_layout()
    tau_out = ok[["subject", "session", "condition", "tau_ratio_ar1", "tau_ratio_bw_matched",
                  "tau_ratio_block", "tau_ratio_dec", "smr_tau_ar1_s", "hb_tau_ar1_s",
                  "tau_separation_supported_ar1" if "tau_separation_supported_ar1" in ok.columns
                  else "smr_tau_ar1_s"]].copy()
    save_csv_backed_figure(fig, tau_out, "spt4_tau_beta_vs_tau_smr", root)


def write_report(feat_df: pd.DataFrame, log_path: Path) -> None:
    ok = feat_df[feat_df["status"] == "ok"] if not feat_df.empty else pd.DataFrame()

    if ok.empty:
        (ROOT / "outputs" / "reports" / "spt4_results.md").write_text(
            "# SPT4 Results\n\nNo data available.\n", encoding="utf-8"
        )
        return

    # Tau statistics
    def m(col):
        v = ok[col].dropna()
        return float(v.mean()), float(v.median()), float(v.std()), len(v)

    smr_ar1_mean, smr_ar1_med, smr_ar1_std, _ = m("smr_tau_ar1_s")
    hb_ar1_mean, hb_ar1_med, hb_ar1_std, _ = m("hb_tau_ar1_s")
    ratio_ar1_mean, ratio_ar1_med, _, n_ratio = m("tau_ratio_ar1")
    n_below_05 = int((ok["tau_ratio_ar1"].dropna() < 0.5).sum())

    # BW theory prediction
    bw_ratio_theory = bandwidth_expected_tau(HIGH_BETA_BAND[1] - HIGH_BETA_BAND[0], 256.0) / \
                      bandwidth_expected_tau(SMR_BAND[1] - SMR_BAND[0], 256.0)

    ratio_bw_mean = float(ok["tau_ratio_bw_matched"].dropna().mean()) \
        if "tau_ratio_bw_matched" in ok.columns else np.nan
    ratio_block_mean = float(ok["tau_ratio_block"].dropna().mean()) \
        if "tau_ratio_block" in ok.columns else np.nan
    ratio_dec_mean = float(ok["tau_ratio_dec"].dropna().mean()) \
        if "tau_ratio_dec" in ok.columns else np.nan

    # One-sample t-test: is tau_ratio_ar1 < 1.0?
    tval, pval = stats.ttest_1samp(ok["tau_ratio_ar1"].dropna(), 1.0)

    report = f"""# SPT4 Results: Rigorous Empirical Time-scale Analysis

Generated: {utc_now()}

## Dataset and method

Dataset: {DATASET_ID}
Subjects: 5 (sub-004, sub-005, sub-012, sub-013, sub-018)
Sessions: ses-01, ses-08
Conditions: rest, task, interval
EEG segments analyzed: {len(ok)}

Methods:
- Primary: AR1 autocorrelation tau at native sampling rate.
  KNOWN LIMITATION: confounded by bandwidth difference (SMR: 3 Hz BW, HB: 10 Hz BW).
- Control 1: bandwidth-matched comparison (SMR 12-15 Hz, HB 20-23 Hz; both 3 Hz BW).
- Control 2: block-mean tau ({int(BLOCK_S)}-s blocks) — removes fast filter fluctuations.
- Control 3: 1-Hz decimated envelope — isolates regulation dynamics.
- Theory: expected tau ratio from Gaussian bandwidth prediction.

## Key results

### Primary tau (AR1 at native fs)
tau_SMR: mean = {smr_ar1_mean:.1f} s, median = {smr_ar1_med:.1f} s, SD = {smr_ar1_std:.1f} s
tau_HB:  mean = {hb_ar1_mean:.1f} s, median = {hb_ar1_med:.1f} s, SD = {hb_ar1_std:.1f} s
tau_ratio (HB/SMR): mean = {ratio_ar1_mean:.3f}, median = {ratio_ar1_med:.3f}
{n_below_05}/{n_ratio} segments: tau_HB < 0.5 * tau_SMR
One-sample t-test vs ratio=1.0: t = {tval:.2f}, p = {pval:.4f}

### Bandwidth confound assessment
Gaussian bandwidth theory predicts tau ratio = {bw_ratio_theory:.3f}
(from BW_SMR=3 Hz, BW_HB=10 Hz at fs=256 Hz)

Observed tau_ratio (primary) = {ratio_ar1_mean:.3f}
Expected from BW alone       = {bw_ratio_theory:.3f}

{'>> IMPORTANT: The observed tau_ratio ({:.3f}) is close to the bandwidth-predicted ratio ({:.3f}).'.format(ratio_ar1_mean, bw_ratio_theory)}
{'A significant fraction of the observed time-scale separation may reflect the 3 Hz vs 10 Hz bandwidth difference, not genuine regulation dynamics.'}

### Bandwidth-matched control (3 Hz BW for both)
Mean tau_ratio (BW-matched): {ratio_bw_mean:.3f}
{'This tests separation when bandwidth is equalized. A ratio < 1.0 would indicate separation beyond the bandwidth artifact.' if not np.isnan(ratio_bw_mean) else ''}

### Block-mean tau ({int(BLOCK_S)}-s blocks, regulation scale)
Mean tau_ratio (block): {ratio_block_mean:.3f}
{'Ratios close to 1.0 or variable here indicate that the separation may be driven primarily by bandwidth, not regulation.' if not np.isnan(ratio_block_mean) else ''}

### 1-Hz decimated tau
Mean tau_ratio (decimated): {ratio_dec_mean:.3f}

## Interpretation

"""

    # Determine interpretation
    bw_confound_severe = abs(ratio_ar1_mean - bw_ratio_theory) < 0.05
    if bw_confound_severe:
        report += f"""**BANDWIDTH CONFOUND WARNING**: The observed tau_ratio ({ratio_ar1_mean:.3f}) is
within 0.05 of the bandwidth-predicted ratio ({bw_ratio_theory:.3f}). The primary tau analysis
CANNOT reliably distinguish filter bandwidth effects from genuine time-scale separation.
The high tau_ratio of {ratio_ar1_mean:.3f} may be almost entirely explained by the fact that
the SMR band (3 Hz) is narrower than the high-beta band (10 Hz).

"""
    else:
        excess = ratio_ar1_mean - bw_ratio_theory
        report += f"""The observed tau_ratio ({ratio_ar1_mean:.3f}) exceeds the bandwidth prediction
({bw_ratio_theory:.3f}) by {excess:.3f}. This suggests that some time-scale separation
exists BEYOND the bandwidth artifact, but the magnitude of the genuine separation
is reduced compared to the primary analysis.

"""

    # BW-matched control assessment
    if not np.isnan(ratio_bw_mean):
        if ratio_bw_mean < 0.8:
            report += (
                f"The bandwidth-matched control shows tau_ratio = {ratio_bw_mean:.3f} < 1.0, "
                f"suggesting residual time-scale separation even after equating bandwidths. "
                f"This is mild evidence that the separation is not entirely artifactual.\n"
            )
        elif ratio_bw_mean >= 0.8:
            report += (
                f"The bandwidth-matched control shows tau_ratio = {ratio_bw_mean:.3f} ≈ 1.0, "
                f"indicating that most or all of the observed time-scale separation disappears "
                f"when bandwidths are matched. This strongly implicates the bandwidth difference "
                f"as the primary driver of the observed tau_ratio.\n"
            )

    report += f"""
## Conclusion on time-scale separation

The primary AR1 tau analysis shows tau_HB ≈ {hb_ar1_mean:.1f} s and tau_SMR ≈ {smr_ar1_mean:.1f} s
(ratio ≈ {ratio_ar1_mean:.2f}). However, the Gaussian bandwidth prediction gives a ratio of
{bw_ratio_theory:.3f} from filter properties alone. This means the observed time-scale separation
is at least partly (and possibly largely) a filter artifact.

The block-mean tau ratio = {ratio_block_mean:.3f} and decimated tau ratio = {ratio_dec_mean:.3f}
provide a more regulation-focused estimate.

**Claim status**: The claim of "empirical time-scale separation" from AR1 analysis at native fs
is **NOT RELIABLE** without bandwidth matching. The block-mean and BW-matched analyses are more
defensible. Results should be reported with the bandwidth caveat.

Generated: {utc_now()}
"""
    (ROOT / "outputs" / "reports" / "spt4_results.md").write_text(report, encoding="utf-8")
    log_path.write_text(f"{utc_now()} SPT4 revised completed. {len(ok)} segments analyzed.\n",
                        encoding="utf-8")


def main() -> None:
    ensure_repo_structure(ROOT)
    tbl_dir = ROOT / "outputs" / "tables"
    rep_dir = ROOT / "outputs" / "reports"
    log_dir = ROOT / "outputs" / "logs"

    log_lines = [f"{utc_now()} SPT4 revised started."]

    edf_files = sorted(RAW_ROOT.glob("sub-*/ses-*/eeg/*_eeg.edf")) if RAW_ROOT.exists() else []
    log_lines.append(f"EDF files: {len(edf_files)}")
    print(f"SPT4 Revised: {len(edf_files)} EDF files.")

    conditions = ["rest", "task", "interval"]
    feat_rows = []

    for edf_path in edf_files:
        subject, session = parse_subject_session(edf_path)
        log_lines.append(f"  {edf_path.name}")
        for cond in conditions:
            x, fs, chans = load_eeg_segment(edf_path, cond)
            if x.size < int(fs * 8 if fs > 0 else 2048):
                continue
            feats = compute_timescale_features(x, fs, subject, session, cond)
            feats["channels"] = ";".join(chans)
            feat_rows.append(feats)

    feat_df = pd.DataFrame(feat_rows) if feat_rows else pd.DataFrame()
    feat_df.to_csv(tbl_dir / "spt4_empirical_timescale_features.csv", index=False)

    # tau ratio table
    if not feat_df.empty and "tau_ratio_ar1" in feat_df.columns:
        ok = feat_df[feat_df["status"] == "ok"].copy()
        ok["tau_separation_supported_ar1"] = (ok["tau_ratio_ar1"] < 0.5).astype(int)
        ok["tau_separation_supported_bw_matched"] = (
            ok["tau_ratio_bw_matched"].fillna(1.0) < 0.8).astype(int)
        tau_df = ok[[
            "subject", "session", "condition",
            "tau_ratio_ar1", "tau_ratio_bw_matched", "tau_ratio_block", "tau_ratio_dec",
            "smr_tau_ar1_s", "hb_tau_ar1_s",
            "smr_tau_block_s", "hb_tau_block_s",
            "tau_ratio_ar1_expected_from_bw",
            "tau_separation_supported_ar1", "tau_separation_supported_bw_matched",
        ]].copy()
        tau_df["tau_sep_supported"] = ok["tau_separation_supported_ar1"]
        tau_df.to_csv(tbl_dir / "spt4_empirical_tau_ratios.csv", index=False)
    else:
        tau_df = pd.DataFrame()
        tau_df.to_csv(tbl_dir / "spt4_empirical_tau_ratios.csv", index=False)

    # BW control table
    if not feat_df.empty:
        bw_control = feat_df[feat_df["status"] == "ok"][[
            "subject", "session", "condition",
            "tau_ratio_ar1", "tau_ratio_ar1_expected_from_bw", "tau_ratio_bw_matched",
            "smr_tau_theory_from_bw_s", "hb_tau_theory_from_bw_s", "hb_tau_theory_bw_matched_s",
            "smr_tau_excess_s", "hb_tau_excess_s",
        ]].copy() if "tau_ratio_bw_matched" in feat_df.columns else pd.DataFrame()
        bw_control.to_csv(tbl_dir / "spt4_tau_bandwidth_control.csv", index=False)

    print("SPT4 Revised: Creating figures...")
    if not feat_df.empty and "tau_ratio_ar1" in feat_df.columns:
        make_tau_figures(feat_df, ROOT)
        make_bw_control_figure(feat_df, ROOT)
        make_tau_ratio_figure(feat_df, ROOT)

    log_path = log_dir / "spt4_empirical_processing.log"
    write_report(feat_df, log_path)
    print("SPT4 Revised done.")


if __name__ == "__main__":
    main()
