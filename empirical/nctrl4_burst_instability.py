"""NCTRL4: Empirical burst/noise-instability analysis.

For each subject / session / condition:
  - High-beta burst rate, duration, amplitude, clustering
  - Inter-burst interval variability
  - State-space diffusion coefficient (SMR and HB envelopes)
  - EEG state instability index
  - Test: do burst metrics track noise floor and broadband contamination?

Outputs:
  outputs/tables/nctrl4_burst_instability_features.csv
  outputs/tables/nctrl4_diffusion_features.csv
  outputs/figures/nctrl4_burst_noise_relationship.*
  outputs/figures/nctrl4_state_diffusion_panel.*
  outputs/reports/nctrl4_results.md
  outputs/logs/nctrl4_empirical_processing.log
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal as scipy_signal
from scipy import stats
import mne

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style
from utils.signal_metrics import band_envelope, burst_metrics

DATASET_ID = "ds004446"
RAW_ROOT = ROOT / "data" / "raw" / "openneuro" / DATASET_ID
CHANNELS = ["E36", "E104", "E128"]
CONDITIONS = ["rest", "task"]
SMR_BAND = (12.0, 15.0)
HB_BAND = (20.0, 30.0)
BROAD_BAND = (30.0, 45.0)
BLOCK_S = 4.0       # for diffusion computation
BURST_MIN_DUR = 0.1  # minimum burst duration (s)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_sub_ses(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    return (m.group(1), m.group(2)) if m else ("", "")


def load_mean_segment(edf_path: Path, condition: str) -> tuple[np.ndarray, float]:
    sub, ses = parse_sub_ses(edf_path)
    ev_path = edf_path.parent / f"{sub}_{ses}_task-smrbmi_events.tsv"
    if not ev_path.exists():
        return np.array([]), 0.0

    raw = mne.io.read_raw_edf(edf_path, preload=False, include=CHANNELS, verbose="ERROR")
    avail = [ch for ch in CHANNELS if ch in raw.ch_names]
    if not avail:
        raw.close()
        return np.array([]), 0.0
    raw.pick(avail)
    raw.load_data(verbose="ERROR")
    data = raw.get_data(picks=avail)
    fs = float(raw.info["sfreq"])
    raw.close()

    events = pd.read_csv(ev_path, sep="\t")
    events["onset_s"] = events["onset"].astype(float) / 1000.0
    events["duration_s"] = events["duration"].astype(float)

    segs = []
    n_s = data.shape[1]
    for _, row in events[events["instruction"].astype(str) == condition].iterrows():
        t0 = int(round(float(row["onset_s"]) * fs))
        t1 = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
        t0 = max(0, min(t0, n_s))
        t1 = max(t0, min(t1, n_s))
        if t1 - t0 >= int(fs * 4):
            segs.append(np.mean(data[:, t0:t1], axis=0))

    if not segs:
        return np.array([]), fs
    return np.concatenate(segs), fs


def compute_inter_burst_variability(envelope: np.ndarray, threshold: float,
                                     fs: float, min_dur: float) -> tuple[float, float]:
    """Compute inter-burst interval statistics: (mean_IBI_s, cv_IBI)."""
    above = envelope > threshold
    edges = np.diff(np.r_[False, above, False].astype(int))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    durations = (ends - starts) / fs
    keep = durations >= min_dur
    starts = starts[keep]

    if len(starts) < 2:
        return np.nan, np.nan

    ibis = np.diff(starts) / fs
    return float(np.mean(ibis)), float(np.std(ibis) / (np.mean(ibis) + 1e-12))


def compute_diffusion(env: np.ndarray, fs: float, block_s: float) -> dict[str, float]:
    """Diffusion coefficient from short-lag increments of block means."""
    block_n = int(block_s * fs)
    n_blocks = len(env) // block_n
    if n_blocks < 4:
        return {"diffusion_coef": np.nan, "mean_env": np.nan,
                "var_increments": np.nan, "instability_idx": np.nan}

    blocks = np.array([env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])
    increments = np.diff(blocks)
    diffusion_coef = float(np.var(increments) / block_s)
    instability_idx = float(np.mean(np.abs(increments)) / (np.mean(blocks) + 1e-12))
    return {
        "diffusion_coef": diffusion_coef,
        "mean_env": float(np.mean(blocks)),
        "var_increments": float(np.var(increments)),
        "instability_idx": instability_idx,
    }


def extract_burst_features(edf_path: Path, condition: str) -> dict | None:
    sub, ses = parse_sub_ses(edf_path)
    x, fs = load_mean_segment(edf_path, condition)
    if x.size < int(fs * 10):
        return None

    x = x - np.mean(x)

    # Envelopes
    smr_env = band_envelope(x, fs, SMR_BAND)
    hb_env = band_envelope(x, fs, HB_BAND)
    broad_env = band_envelope(x, fs, BROAD_BAND)

    # Burst thresholds: 75th percentile of respective envelopes
    smr_thr = float(np.percentile(smr_env, 75))
    hb_thr = float(np.percentile(hb_env, 75))
    broad_thr = float(np.percentile(broad_env, 75))

    # HB burst metrics
    hb_burst = burst_metrics(hb_env, hb_thr, fs, min_duration_s=BURST_MIN_DUR)
    smr_burst = burst_metrics(smr_env, smr_thr, fs, min_duration_s=BURST_MIN_DUR)
    broad_burst = burst_metrics(broad_env, broad_thr, fs, min_duration_s=BURST_MIN_DUR)

    # HB amplitude
    hb_burst_amp = float(np.mean(hb_env[hb_env > hb_thr])) if (hb_env > hb_thr).any() else np.nan

    # Inter-burst interval variability
    mean_ibi, cv_ibi = compute_inter_burst_variability(hb_env, hb_thr, fs, BURST_MIN_DUR)

    # Diffusion coefficients
    smr_diff = compute_diffusion(smr_env, fs, BLOCK_S)
    hb_diff = compute_diffusion(hb_env, fs, BLOCK_S)

    # Correlation between HB env and broad env (time series)
    min_n = min(len(hb_env), len(broad_env))
    hb_broad_corr = float(np.corrcoef(hb_env[:min_n], broad_env[:min_n])[0, 1])

    # Correlation between HB bursts and SMR blocks (do HB bursts suppress SMR?)
    block_n = int(BLOCK_S * fs)
    n_blocks = min(len(hb_env), len(smr_env)) // block_n
    if n_blocks >= 4:
        hb_blocks = np.array([hb_env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])
        smr_blocks = np.array([smr_env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])
        hb_smr_block_corr = float(np.corrcoef(hb_blocks, smr_blocks)[0, 1])
        hb_broad_block_corr_local = float(np.corrcoef(
            hb_blocks, np.array([broad_env[b * block_n:(b + 1) * block_n].mean()
                                  for b in range(n_blocks)]))[0, 1])
    else:
        hb_smr_block_corr = np.nan
        hb_broad_block_corr_local = np.nan

    return {
        "subject": sub, "session": ses, "condition": condition,
        "n_samples": len(x), "fs": fs, "duration_s": len(x) / fs,
        # HB burst metrics
        "hb_burst_rate_per_min": hb_burst["burst_rate_per_min"],
        "hb_burst_duration_s": hb_burst["burst_duration_s"],
        "hb_burst_occupancy": hb_burst["burst_occupancy"],
        "hb_burst_amplitude": hb_burst_amp,
        "hb_n_bursts": hb_burst["n_bursts"],
        "hb_mean_ibi_s": mean_ibi,
        "hb_cv_ibi": cv_ibi,
        # SMR burst metrics
        "smr_burst_rate_per_min": smr_burst["burst_rate_per_min"],
        "smr_burst_occupancy": smr_burst["burst_occupancy"],
        # Broadband burst metrics
        "broad_burst_rate_per_min": broad_burst["burst_rate_per_min"],
        "broad_burst_occupancy": broad_burst["burst_occupancy"],
        # Correlations
        "hb_broad_corr": hb_broad_corr,
        "hb_smr_block_corr": hb_smr_block_corr,
        "hb_broad_block_corr": hb_broad_block_corr_local,
        # Diffusion
        "smr_diffusion_coef": smr_diff["diffusion_coef"],
        "smr_instability_idx": smr_diff["instability_idx"],
        "hb_diffusion_coef": hb_diff["diffusion_coef"],
        "hb_instability_idx": hb_diff["instability_idx"],
        "smr_mean_env": smr_diff["mean_env"],
        "hb_mean_env": hb_diff["mean_env"],
    }


def make_burst_noise_figure(df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))

    cmap_ses = {"ses-01": "#1f77b4", "ses-08": "#ff7f0e"}

    # A: HB burst rate by subject/session
    ax = axes[0, 0]
    for ses, grp in df.groupby("session"):
        for cond, m in zip(CONDITIONS, ["o", "s"]):
            sg = grp[grp["condition"] == cond]
            ax.scatter(range(len(sg)), sg["hb_burst_rate_per_min"].values,
                       color=cmap_ses[ses], marker=m, s=45, alpha=0.8, label=f"{ses}/{cond}")
    ax.set_title("(A) HB burst rate (per min)")
    ax.set_ylabel("Bursts/min")
    ax.legend(fontsize=6, ncol=2)

    # B: HB burst corr with broadband
    ax = axes[0, 1]
    for ses, grp in df.groupby("session"):
        ax.scatter(grp["hb_broad_corr"], grp["hb_burst_rate_per_min"],
                   color=cmap_ses[ses], label=ses, s=45, alpha=0.8)
    ax.axvline(0, color="black", ls="--", lw=0.8)
    ax.set_xlabel("HB-broadband envelope correlation")
    ax.set_ylabel("HB burst rate")
    ax.set_title("(B) HB bursts vs broadband correlation\n[+ = HB tracks noise floor]")
    ax.legend(fontsize=7)

    # C: HB-SMR block correlation
    ax = axes[0, 2]
    for ses, grp in df.groupby("session"):
        for cond, m in zip(CONDITIONS, ["o", "s"]):
            sg = grp[grp["condition"] == cond].dropna(subset=["hb_smr_block_corr"])
            ax.scatter(sg["hb_burst_rate_per_min"], sg["hb_smr_block_corr"],
                       color=cmap_ses[ses], marker=m, s=45, alpha=0.8, label=f"{ses}/{cond}")
    ax.axhline(0, color="black", ls="--", lw=0.8)
    ax.set_xlabel("HB burst rate (per min)")
    ax.set_ylabel("HB-SMR block correlation")
    ax.set_title("(C) Do HB bursts suppress SMR?\n[negative = HB bursts ↓ SMR]")
    ax.legend(fontsize=6, ncol=2)

    # D: State diffusion (SMR)
    ax = axes[1, 0]
    for ses, grp in df.groupby("session"):
        for cond, m in zip(CONDITIONS, ["o", "s"]):
            sg = grp[grp["condition"] == cond].dropna(subset=["smr_diffusion_coef"])
            ax.scatter(range(len(sg)), sg["smr_diffusion_coef"].values,
                       color=cmap_ses[ses], marker=m, s=45, alpha=0.8, label=f"{ses}/{cond}")
    ax.set_title("(D) SMR state-space diffusion coefficient")
    ax.set_ylabel("Diffusion (var of 4-s block increments)")
    ax.legend(fontsize=6, ncol=2)

    # E: HB vs SMR diffusion
    ax = axes[1, 1]
    df_ok = df.dropna(subset=["hb_diffusion_coef", "smr_diffusion_coef"])
    for ses, grp in df_ok.groupby("session"):
        ax.scatter(grp["hb_diffusion_coef"], grp["smr_diffusion_coef"],
                   color=cmap_ses[ses], label=ses, s=45, alpha=0.8)
    ax.set_xlabel("HB diffusion coefficient")
    ax.set_ylabel("SMR diffusion coefficient")
    ax.set_title("(E) HB vs SMR diffusion\n[correlated = coupled instability]")
    ax.legend(fontsize=7)

    # F: CV of inter-burst intervals
    ax = axes[1, 2]
    for ses, grp in df.groupby("session"):
        ax.scatter(grp["hb_burst_rate_per_min"], grp["hb_cv_ibi"],
                   color=cmap_ses[ses], label=ses, s=45, alpha=0.8)
    ax.set_xlabel("HB burst rate (per min)")
    ax.set_ylabel("CV of inter-burst intervals")
    ax.set_title("(F) HB burst clustering\n[high CV = irregular/clustered bursts]")
    ax.legend(fontsize=7)

    fig.suptitle("NCTRL4: Empirical burst/noise-instability analysis (ds004446)", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(
        fig,
        df[["subject", "session", "condition", "hb_burst_rate_per_min",
             "hb_burst_duration_s", "hb_burst_occupancy", "hb_broad_corr",
             "hb_smr_block_corr", "smr_diffusion_coef", "hb_diffusion_coef", "hb_cv_ibi"]],
        "nctrl4_burst_noise_relationship", root
    )


def make_diffusion_figure(df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

    # A: ses-01 vs ses-08 SMR diffusion
    s01 = df[df["session"] == "ses-01"].set_index(["subject", "condition"])
    s08 = df[df["session"] == "ses-08"].set_index(["subject", "condition"])
    common = s01.index.intersection(s08.index)
    if not common.empty:
        axes[0].scatter(s01.loc[common, "smr_diffusion_coef"],
                         s08.loc[common, "smr_diffusion_coef"], s=55, alpha=0.8)
        mx = max(s01.loc[common, "smr_diffusion_coef"].max(),
                  s08.loc[common, "smr_diffusion_coef"].max()) * 1.1
        axes[0].plot([0, mx], [0, mx], "k--", lw=0.8)
        axes[0].set_xlabel("SMR diffusion ses-01")
        axes[0].set_ylabel("SMR diffusion ses-08")
        axes[0].set_title("(A) SMR diffusion change\nses-01 → ses-08")

    # B: HB diffusion vs SMR instability index
    df_ok = df.dropna(subset=["hb_diffusion_coef", "smr_instability_idx"])
    for ses, col in zip(["ses-01", "ses-08"], ["#1f77b4", "#ff7f0e"]):
        sdf = df_ok[df_ok["session"] == ses]
        axes[1].scatter(sdf["hb_diffusion_coef"], sdf["smr_instability_idx"],
                         color=col, label=ses, s=45, alpha=0.8)
    axes[1].set_xlabel("HB diffusion coefficient")
    axes[1].set_ylabel("SMR instability index")
    axes[1].set_title("(B) HB diffusion vs SMR instability")
    axes[1].legend(fontsize=7)

    # C: Change in HB burst rate vs change in SMR diffusion
    if not common.empty:
        d_hb_burst = s08.loc[common, "hb_burst_rate_per_min"] - s01.loc[common, "hb_burst_rate_per_min"]
        d_smr_diff = s08.loc[common, "smr_diffusion_coef"] - s01.loc[common, "smr_diffusion_coef"]
        axes[2].scatter(d_hb_burst.values, d_smr_diff.values, s=55, alpha=0.8,
                         c="steelblue", edgecolors="black", linewidths=0.5)
        axes[2].axhline(0, color="black", ls="--", lw=0.8)
        axes[2].axvline(0, color="black", ls="--", lw=0.8)
        for (sub, cond), dx, dy in zip(common, d_hb_burst.values, d_smr_diff.values):
            axes[2].annotate(f"{sub[:7]}", (dx, dy), fontsize=6, alpha=0.7)
        axes[2].set_xlabel("Δ HB burst rate (ses-01→ses-08)")
        axes[2].set_ylabel("Δ SMR diffusion (ses-01→ses-08)")
        axes[2].set_title("(C) HB burst change vs SMR diffusion change\n[-,- = damping improved stability]")

    fig.suptitle("NCTRL4: State-space diffusion panel", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(
        fig,
        df[["subject", "session", "condition", "smr_diffusion_coef",
             "hb_diffusion_coef", "smr_instability_idx", "hb_instability_idx",
             "hb_burst_rate_per_min"]],
        "nctrl4_state_diffusion_panel", root
    )


def write_report(df: pd.DataFrame, diff_df: pd.DataFrame) -> None:
    s01 = df[df["session"] == "ses-01"]
    s08 = df[df["session"] == "ses-08"]
    hb_broad_corr = df["hb_broad_corr"].dropna().mean()
    hb_smr_corr = df["hb_smr_block_corr"].dropna().mean()

    report = f"""# NCTRL4 Results: Empirical Burst/Noise-Instability Analysis

Generated: {utc_now()}

## Method
Dataset: ds004446, 5 subjects, ses-01 + ses-08
Conditions: {CONDITIONS}
Burst threshold: 75th percentile of HB envelope
Block duration for diffusion: {BLOCK_S} s

## Key results

### HB burst characteristics (mean across subjects)
ses-01 burst rate: {s01["hb_burst_rate_per_min"].mean():.2f} /min | ses-08: {s08["hb_burst_rate_per_min"].mean():.2f} /min
ses-01 burst occ.: {s01["hb_burst_occupancy"].mean():.3f} | ses-08: {s08["hb_burst_occupancy"].mean():.3f}
ses-01 burst dur.: {s01["hb_burst_duration_s"].mean():.3f} s | ses-08: {s08["hb_burst_duration_s"].mean():.3f} s

### HB-broadband correlation (stochastic noise interpretation)
Mean HB-broadband envelope correlation = {hb_broad_corr:.3f}
{"Positive (HB bursts co-occur with broadband fluctuations): consistent with HB as noise event." if hb_broad_corr > 0.2 else "Low/negative (HB bursts not correlated with broadband): HB may be band-specific regulation."}

### HB-SMR block correlation (suppression interpretation)
Mean HB-SMR block correlation = {hb_smr_corr:.3f}
{"Negative (HB bursts associated with lower SMR): consistent with HB bursts suppressing SMR signal." if hb_smr_corr < -0.1 else "Near zero or positive: HB bursts do not reliably suppress SMR at the block level."}

### SMR state-space diffusion
ses-01: {s01["smr_diffusion_coef"].dropna().mean():.4f} | ses-08: {s08["smr_diffusion_coef"].dropna().mean():.4f}
{"SMR diffusion decreased from ses-01 to ses-08 (more stable target state)." if s08["smr_diffusion_coef"].dropna().mean() < s01["smr_diffusion_coef"].dropna().mean() else "SMR diffusion did not decrease from ses-01 to ses-08."}

## Interpretation

{"HB burst metrics are positively correlated with broadband envelope fluctuations (mean r=" + f"{hb_broad_corr:.2f}), suggesting that HB bursts in this dataset co-occur with broadband noise events rather than purely band-specific activity. This is consistent with the active-damping/noise-control hypothesis: HB inhibition may reduce a broader class of high-frequency instability events." if hb_broad_corr > 0.2 else "HB burst metrics show low correlation with broadband envelope fluctuations (mean r=" + f"{hb_broad_corr:.2f}). HB bursts may be more band-specific than noise-floor events. This partially limits the noise-control interpretation."}

The HB-SMR block correlation = {hb_smr_corr:.2f} {"suggests HB bursts are associated with reduced SMR power at the block level, compatible with the noise-control hypothesis that HB bursts degrade feedback-state quality." if hb_smr_corr < -0.1 else "does not show reliable suppression of SMR by HB bursts at the block level."}

Generated: {utc_now()}
"""
    (ROOT / "outputs" / "reports" / "nctrl4_results.md").write_text(report, encoding="utf-8")


def main() -> None:
    ensure_repo_structure(ROOT)
    tbl = ROOT / "outputs" / "tables"
    log_lines = [f"{utc_now()} NCTRL4 started."]

    edfs = sorted(RAW_ROOT.glob("sub-*/ses-*/eeg/*_eeg.edf")) if RAW_ROOT.exists() else []
    print(f"NCTRL4: {len(edfs)} EDF files.")

    all_rows = []
    for edf in edfs:
        sub, ses = parse_sub_ses(edf)
        for cond in CONDITIONS:
            row = extract_burst_features(edf, cond)
            if row is not None:
                all_rows.append(row)
            log_lines.append(f"  {sub}/{ses}/{cond}: {'ok' if row else 'skip'}")

    df = pd.DataFrame(all_rows) if all_rows else pd.DataFrame()
    df.to_csv(tbl / "nctrl4_burst_instability_features.csv", index=False)

    # Diffusion features subset
    diff_df = df[["subject", "session", "condition", "smr_diffusion_coef",
                   "hb_diffusion_coef", "smr_instability_idx", "hb_instability_idx"]].copy() \
        if not df.empty else pd.DataFrame()
    diff_df.to_csv(tbl / "nctrl4_diffusion_features.csv", index=False)

    print("NCTRL4: Creating figures...")
    if not df.empty:
        make_burst_noise_figure(df, ROOT)
        make_diffusion_figure(df, ROOT)

    write_report(df, diff_df)
    (ROOT / "outputs" / "logs" / "nctrl4_empirical_processing.log").write_text(
        "\n".join(log_lines), encoding="utf-8")
    print("NCTRL4 done.")


if __name__ == "__main__":
    main()
