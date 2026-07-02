"""SPT4: Reanalysis of real EEG time scales (ds004446 subset).

Estimates empirical time scales for SMR, high-beta, beta-burst,
and broadband power envelopes in real EEG data.

Outputs
-------
outputs/tables/spt4_empirical_timescale_features.csv
outputs/tables/spt4_empirical_tau_ratios.csv
outputs/figures/spt4_empirical_timescale_panel.*
outputs/figures/spt4_tau_beta_vs_tau_smr.*
outputs/reports/spt4_results.md
outputs/logs/spt4_empirical_processing.log
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

import mne

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style
from utils.signal_metrics import (
    bandpower_from_psd, band_envelope, burst_metrics, envelope_timescale
)


DATASET_ID = "ds004446"
RAW_ROOT = ROOT / "data" / "raw" / "openneuro" / DATASET_ID
SENSORIMOTOR_CHANNELS = ["E36", "E104", "E128"]
SMR_BAND = (12.0, 15.0)
HIGH_BETA_BAND = (20.0, 30.0)
BROADBAND = (4.0, 45.0)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_subject_session(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def load_eeg_segment(edf_path: Path, condition: str = "rest") -> tuple[np.ndarray, float, list]:
    """Load EEG and extract condition segments, average across channels."""
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
            segments.append(data[:, start:stop])

    if not segments:
        return np.array([]), fs, available

    cat = np.concatenate(segments, axis=1)
    x = np.nanmean(cat, axis=0)
    x = scipy_signal.detrend(x)
    return x, fs, available


def compute_timescale_features(x: np.ndarray, fs: float,
                                subject: str, session: str, condition: str) -> dict:
    """Extract time-scale features from a single EEG segment."""
    result = {
        "subject": subject, "session": session, "condition": condition,
        "n_samples": len(x), "fs": fs, "duration_s": len(x) / fs,
    }
    if len(x) < int(fs * 4):
        for k in ["smr_tau_ar1_s", "smr_tau_acf_s", "hbeta_tau_ar1_s", "hbeta_tau_acf_s",
                  "burst_duration_s", "burst_return_time_s", "tau_ratio_ar1", "tau_ratio_acf",
                  "tau_separation_supported_ar1", "tau_separation_supported_acf",
                  "smr_power", "hbeta_power"]:
            result[k] = np.nan
        result["status"] = "insufficient_data"
        return result

    # Band envelopes
    smr_env = band_envelope(x, fs, SMR_BAND)
    hbeta_env = band_envelope(x, fs, HIGH_BETA_BAND)

    # Timescales
    smr_ts = envelope_timescale(smr_env, fs)
    hbeta_ts = envelope_timescale(hbeta_env, fs)

    result["smr_tau_ar1_s"] = smr_ts["ar1_tau_s"]
    result["smr_tau_acf_s"] = smr_ts["acf_efold_s"]
    result["hbeta_tau_ar1_s"] = hbeta_ts["ar1_tau_s"]
    result["hbeta_tau_acf_s"] = hbeta_ts["acf_efold_s"]

    # Burst metrics for high-beta
    threshold = float(np.percentile(hbeta_env, 75))
    bm = burst_metrics(hbeta_env, threshold, fs)
    result["burst_rate_per_min"] = bm["burst_rate_per_min"]
    result["burst_duration_s"] = bm["burst_duration_s"]
    result["burst_occupancy"] = bm["burst_occupancy"]
    result["n_bursts"] = bm["n_bursts"]

    # Burst return time (inter-burst interval)
    above = hbeta_env > threshold
    edges = np.diff(np.r_[False, above, False].astype(int))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    if len(starts) > 1:
        durations = (ends - starts) / fs
        keep = durations >= 0.04
        ends_k = ends[keep]
        starts_k = starts[keep][1:] if len(starts[keep]) > 1 else np.array([])
        if len(ends_k) > 1 and len(starts_k) > 0:
            n_intervals = min(len(ends_k) - 1, len(starts_k))
            ibi = (starts_k[:n_intervals] - ends_k[:n_intervals]) / fs
            result["burst_return_time_s"] = float(np.mean(ibi[ibi > 0])) if np.any(ibi > 0) else np.nan
        else:
            result["burst_return_time_s"] = np.nan
    else:
        result["burst_return_time_s"] = np.nan

    # Band power
    nperseg = min(len(x), int(fs * 4))
    freqs, psd = scipy_signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2)
    result["smr_power"] = bandpower_from_psd(freqs, psd, SMR_BAND)
    result["hbeta_power"] = bandpower_from_psd(freqs, psd, HIGH_BETA_BAND)

    # Tau ratios
    tau_ratio_ar1 = (hbeta_ts["ar1_tau_s"] / smr_ts["ar1_tau_s"]
                     if smr_ts["ar1_tau_s"] > 0 else np.nan)
    tau_ratio_acf = (hbeta_ts["acf_efold_s"] / smr_ts["acf_efold_s"]
                     if smr_ts["acf_efold_s"] > 0 else np.nan)

    result["tau_ratio_ar1"] = tau_ratio_ar1
    result["tau_ratio_acf"] = tau_ratio_acf
    result["tau_separation_supported_ar1"] = (
        1 if (not np.isnan(tau_ratio_ar1) and tau_ratio_ar1 < 0.5) else 0
    )
    result["tau_separation_supported_acf"] = (
        1 if (not np.isnan(tau_ratio_acf) and tau_ratio_acf < 0.5) else 0
    )
    result["status"] = "ok"
    return result


def no_data_outputs(reason: str) -> None:
    cols = [
        "subject", "session", "condition", "n_samples", "fs", "duration_s",
        "smr_tau_ar1_s", "smr_tau_acf_s", "hbeta_tau_ar1_s", "hbeta_tau_acf_s",
        "burst_duration_s", "burst_return_time_s", "tau_ratio_ar1", "tau_ratio_acf",
        "tau_separation_supported_ar1", "tau_separation_supported_acf",
        "smr_power", "hbeta_power", "status",
    ]
    pd.DataFrame(columns=cols).to_csv(
        ROOT / "outputs" / "tables" / "spt4_empirical_timescale_features.csv", index=False)
    pd.DataFrame(columns=["subject", "session", "tau_ratio_ar1", "tau_ratio_acf",
                           "smr_tau_ar1_s", "hbeta_tau_ar1_s",
                           "tau_sep_supported"]).to_csv(
        ROOT / "outputs" / "tables" / "spt4_empirical_tau_ratios.csv", index=False)
    (ROOT / "outputs" / "reports" / "spt4_results.md").write_text(
        f"# SPT4 Results\n\nNo data available. Reason: {reason}\n", encoding="utf-8"
    )


def make_timescale_panel(feat_df: pd.DataFrame, root: Path) -> None:
    set_style()
    conditions = feat_df["condition"].unique()
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))

    # Panel A: SMR vs high-beta AR1 tau by subject
    ok = feat_df[feat_df["status"] == "ok"].copy()
    if ok.empty:
        plt.close(fig)
        return

    colors = plt.cm.tab10(np.linspace(0, 0.9, len(ok["subject"].unique())))
    subj_colors = {s: c for s, c in zip(sorted(ok["subject"].unique()), colors)}

    for _, row in ok.iterrows():
        c = subj_colors.get(row["subject"], "gray")
        axes[0, 0].scatter(row["smr_tau_ar1_s"], row["hbeta_tau_ar1_s"],
                           color=c, s=30, alpha=0.7)
    lim = max(ok["smr_tau_ar1_s"].max(), ok["hbeta_tau_ar1_s"].max()) * 1.1
    axes[0, 0].plot([0, lim], [0, lim], "k--", lw=0.8, label="tau_beta = tau_SMR")
    axes[0, 0].plot([0, lim], [0, lim / 2], "g:", lw=0.8, label="tau_beta = 0.5*tau_SMR")
    axes[0, 0].set_xlabel("tau_SMR AR1 (s)")
    axes[0, 0].set_ylabel("tau_high-beta AR1 (s)")
    axes[0, 0].set_title("Tau comparison (AR1 method)")
    axes[0, 0].legend(fontsize=7)

    # Panel B: tau_ratio distribution
    ok_r = ok.dropna(subset=["tau_ratio_ar1"])
    if not ok_r.empty:
        axes[0, 1].hist(ok_r["tau_ratio_ar1"], bins=15, color="#1f77b4",
                        edgecolor="white", alpha=0.8)
        axes[0, 1].axvline(1.0, color="red", ls="--", lw=1.2, label="ratio=1 (equal)")
        axes[0, 1].axvline(0.5, color="green", ls=":", lw=1.0, label="ratio=0.5")
        axes[0, 1].set_xlabel("tau_beta / tau_SMR (AR1)")
        axes[0, 1].set_ylabel("Count")
        axes[0, 1].set_title("Tau ratio distribution")
        axes[0, 1].legend(fontsize=7)

    # Panel C: tau by condition
    cond_order = ["rest", "task", "interval"]
    for cond in cond_order:
        cdf = ok[ok["condition"] == cond]
        if cdf.empty:
            continue
        x_pos = cond_order.index(cond)
        axes[1, 0].scatter(
            np.full(len(cdf), x_pos) + np.random.default_rng(0).uniform(-0.15, 0.15, len(cdf)),
            cdf["smr_tau_ar1_s"], color="#2ca02c", s=25, alpha=0.7, label="SMR" if x_pos == 0 else "_")
        axes[1, 0].scatter(
            np.full(len(cdf), x_pos) + np.random.default_rng(1).uniform(-0.15, 0.15, len(cdf)),
            cdf["hbeta_tau_ar1_s"], color="#d62728", s=25, alpha=0.7,
            marker="^", label="High-beta" if x_pos == 0 else "_")
    axes[1, 0].set_xticks(range(len(cond_order)))
    axes[1, 0].set_xticklabels(cond_order)
    axes[1, 0].set_ylabel("AR1 tau (s)")
    axes[1, 0].set_title("Tau by condition")
    axes[1, 0].legend(fontsize=7)

    # Panel D: ACF tau ratio
    ok_acf = ok.dropna(subset=["tau_ratio_acf"])
    if not ok_acf.empty:
        axes[1, 1].scatter(ok_acf["smr_tau_acf_s"], ok_acf["hbeta_tau_acf_s"],
                           alpha=0.7, s=30)
        lim2 = max(ok_acf["smr_tau_acf_s"].max(), ok_acf["hbeta_tau_acf_s"].max()) * 1.1
        axes[1, 1].plot([0, lim2], [0, lim2], "k--", lw=0.8)
        axes[1, 1].plot([0, lim2], [0, lim2 / 2], "g:", lw=0.8)
        axes[1, 1].set_xlabel("tau_SMR ACF e-fold (s)")
        axes[1, 1].set_ylabel("tau_high-beta ACF e-fold (s)")
        axes[1, 1].set_title("ACF e-fold tau comparison")

    fig.suptitle("SPT4: Empirical time-scale analysis", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(fig, feat_df, "spt4_empirical_timescale_panel", root)


def make_tau_ratio_figure(tau_df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    ok = tau_df.dropna(subset=["tau_ratio_ar1"])
    if ok.empty:
        plt.close(fig)
        pd.DataFrame().to_csv(ROOT / "outputs" / "tables" / "spt4_empirical_tau_ratios.csv", index=False)
        return

    # Panel A: scatter per subject/session
    axes[0].scatter(ok["smr_tau_ar1_s"], ok["hbeta_tau_ar1_s"], s=40,
                    alpha=0.8, color="#1f77b4")
    mx = max(ok["smr_tau_ar1_s"].max(), ok["hbeta_tau_ar1_s"].max()) * 1.1
    axes[0].plot([0, mx], [0, mx], "k--", lw=1, label="Equal")
    axes[0].plot([0, mx], [0, mx / 2], "g:", lw=1, label="tau_beta=0.5*tau_SMR")
    axes[0].set_xlabel("tau_SMR AR1 (s)")
    axes[0].set_ylabel("tau_high-beta AR1 (s)")
    axes[0].set_title("Empirical tau_beta vs tau_SMR")
    axes[0].legend(fontsize=7)

    # Panel B: tau_ratio distribution with reference lines
    axes[1].hist(ok["tau_ratio_ar1"], bins=min(len(ok), 15),
                 color="#1f77b4", edgecolor="white", alpha=0.8)
    axes[1].axvline(1.0, color="red", ls="--", lw=1.5, label="Equal time scales")
    axes[1].axvline(0.5, color="orange", ls=":", lw=1.2, label="2x separation")
    axes[1].axvline(0.1, color="green", ls="-.", lw=1.0, label="10x separation (strong SPT)")
    n_below_half = int((ok["tau_ratio_ar1"] < 0.5).sum())
    n_total = len(ok)
    axes[1].text(0.97, 0.97,
                 f"tau_ratio < 0.5: {n_below_half}/{n_total}",
                 transform=axes[1].transAxes, ha="right", va="top", fontsize=8)
    axes[1].set_xlabel("tau_high-beta / tau_SMR (AR1)")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Tau ratio distribution")
    axes[1].legend(fontsize=7)

    fig.suptitle("SPT4: Empirical tau_beta vs tau_SMR", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(fig, tau_df, "spt4_tau_beta_vs_tau_smr", root)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ensure_repo_structure(ROOT)
    tbl_dir = ROOT / "outputs" / "tables"
    rep_dir = ROOT / "outputs" / "reports"
    log_dir = ROOT / "outputs" / "logs"

    log_lines = [f"{utc_now()} SPT4 started."]

    if not RAW_ROOT.exists():
        reason = f"Raw dataset directory not found: {RAW_ROOT}"
        log_lines.append(reason)
        no_data_outputs(reason)
        (log_dir / "spt4_empirical_processing.log").write_text("\n".join(log_lines), encoding="utf-8")
        print("SPT4: No data available, stubs written.")
        return

    edf_files = sorted(RAW_ROOT.glob("sub-*/ses-*/eeg/*_eeg.edf"))
    if not edf_files:
        reason = "No EDF files found in RAW_ROOT."
        log_lines.append(reason)
        no_data_outputs(reason)
        (log_dir / "spt4_empirical_processing.log").write_text("\n".join(log_lines), encoding="utf-8")
        print("SPT4: No EDF files found, stubs written.")
        return

    print(f"SPT4: Found {len(edf_files)} EDF files.")
    conditions = ["rest", "task", "interval"]
    feat_rows = []

    for edf_path in edf_files:
        subject, session = parse_subject_session(edf_path)
        log_lines.append(f"{utc_now()} processing {edf_path.name}")
        for cond in conditions:
            x, fs, chans = load_eeg_segment(edf_path, cond)
            if x.size < int(fs * 4 if fs > 0 else 1000):
                log_lines.append(f"  {subject}/{session}/{cond}: skipped (too short or no data)")
                continue
            feats = compute_timescale_features(x, fs, subject, session, cond)
            feats["channels_used"] = ";".join(chans)
            feat_rows.append(feats)
            log_lines.append(
                f"  {subject}/{session}/{cond}: tau_SMR={feats.get('smr_tau_ar1_s', 'N/A'):.3f}s "
                f"tau_beta={feats.get('hbeta_tau_ar1_s', 'N/A'):.3f}s "
                f"ratio={feats.get('tau_ratio_ar1', 'N/A')}"
            )

    feat_df = pd.DataFrame(feat_rows) if feat_rows else pd.DataFrame()
    feat_df.to_csv(tbl_dir / "spt4_empirical_timescale_features.csv", index=False)
    log_lines.append(f"{utc_now()} Saved spt4_empirical_timescale_features.csv ({len(feat_df)} rows)")

    # Tau ratio table (per subject/session, rest condition)
    if not feat_df.empty:
        ok = feat_df[feat_df["status"] == "ok"].copy()
        tau_df = ok[["subject", "session", "condition", "tau_ratio_ar1", "tau_ratio_acf",
                     "smr_tau_ar1_s", "hbeta_tau_ar1_s",
                     "tau_separation_supported_ar1", "tau_separation_supported_acf"]].copy()
        tau_df["tau_sep_supported"] = tau_df["tau_separation_supported_ar1"]
    else:
        tau_df = pd.DataFrame()

    tau_df.to_csv(tbl_dir / "spt4_empirical_tau_ratios.csv", index=False)

    print("SPT4: Creating figures...")
    if not feat_df.empty:
        make_timescale_panel(feat_df, ROOT)
        make_tau_ratio_figure(tau_df, ROOT)
    else:
        # Create empty placeholder figures
        for stem in ["spt4_empirical_timescale_panel", "spt4_tau_beta_vs_tau_smr"]:
            set_style()
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.text(0.5, 0.5, "No data available", ha="center", va="center",
                    fontsize=14, transform=ax.transAxes)
            ax.set_title(stem)
            save_csv_backed_figure(fig, pd.DataFrame({"note": ["no data"]}), stem, ROOT)

    # Write report
    if feat_df.empty or tau_df.empty:
        report = f"""# SPT4 Results: Empirical Time-scale Analysis

No data was available for analysis. Dataset: {DATASET_ID}
EDF files found: {len(edf_files)}
Rows extracted: {len(feat_rows)}

Generated: {utc_now()}
"""
    else:
        ok = feat_df[feat_df["status"] == "ok"]
        n_ok = len(ok)
        n_tau_sep_ar1 = int(tau_df["tau_separation_supported_ar1"].sum()) if "tau_separation_supported_ar1" in tau_df else 0
        n_tau_sep_acf = int(tau_df["tau_separation_supported_acf"].sum()) if "tau_separation_supported_acf" in tau_df else 0
        mean_ratio = float(tau_df["tau_ratio_ar1"].dropna().mean()) if not tau_df.empty else np.nan
        median_ratio = float(tau_df["tau_ratio_ar1"].dropna().median()) if not tau_df.empty else np.nan

        report = f"""# SPT4 Results: Empirical Time-scale Analysis

## Dataset

Dataset: {DATASET_ID}
EDF files processed: {len(edf_files)}
Analyzable segments (status=ok): {n_ok}

## Time-scale results

Method: AR1 autocorrelation and ACF e-fold time for band envelopes.
SMR band: {SMR_BAND} Hz; High-beta band: {HIGH_BETA_BAND} Hz.

Mean tau_ratio (tau_beta / tau_SMR, AR1): {mean_ratio:.3f}
Median tau_ratio (AR1): {median_ratio:.3f}

Segments where tau_beta < 0.5 * tau_SMR (AR1): {n_tau_sep_ar1}/{n_ok}
Segments where tau_beta < 0.5 * tau_SMR (ACF): {n_tau_sep_acf}/{n_ok}

## Descriptive statistics by condition

"""
        if not ok.empty:
            for cond in ok["condition"].unique():
                cdf = ok[ok["condition"] == cond]
                report += (
                    f"### {cond} (n={len(cdf)} segments)\n"
                    f"- Mean SMR tau (AR1): {cdf['smr_tau_ar1_s'].mean():.3f} s\n"
                    f"- Mean High-beta tau (AR1): {cdf['hbeta_tau_ar1_s'].mean():.3f} s\n"
                    f"- Mean tau_ratio: {cdf['tau_ratio_ar1'].mean():.3f}\n\n"
                )

        report += f"""
## Interpretation

"""
        if mean_ratio < 0.5 and n_ok > 0:
            report += (
                f"Empirical evidence PARTIALLY SUPPORTS time-scale separation: "
                f"high-beta envelope time scale (tau_beta) is on average shorter than "
                f"SMR envelope time scale (tau_SMR) with mean ratio {mean_ratio:.3f}. "
                f"However, variability is high and sample size is small (n={n_ok} segments). "
                f"This is consistent with the singular perturbation hypothesis but "
                f"does not constitute strong empirical proof.\n"
            )
        elif mean_ratio < 1.0 and n_ok > 0:
            report += (
                f"Empirical evidence is WEAKLY CONSISTENT with time-scale separation: "
                f"tau_ratio = {mean_ratio:.3f} (< 1 but not strongly < 0.5). "
                f"The time scales are not clearly separated in this small dataset.\n"
            )
        else:
            report += (
                f"Empirical evidence does NOT support clear time-scale separation: "
                f"tau_ratio = {mean_ratio:.3f} is near 1.0 or above. "
                f"The fast–slow assumption may not hold in this dataset.\n"
            )

        report += f"\nGenerated: {utc_now()}\n"

    (rep_dir / "spt4_results.md").write_text(report, encoding="utf-8")
    log_lines.append(f"{utc_now()} SPT4 report written.")
    (log_dir / "spt4_empirical_processing.log").write_text("\n".join(log_lines), encoding="utf-8")
    print("SPT4 done.")


if __name__ == "__main__":
    main()
