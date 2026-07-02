from __future__ import annotations

import json
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
from scipy import signal

import mne

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style
from utils.signal_metrics import bandpower_from_psd, burst_metrics


STOP_TEXT = "Empirical validation was not run because no suitable local dataset was available."
DATASET_ID = "ds004446"
RAW_ROOT = ROOT / "data" / "raw" / "openneuro" / DATASET_ID
SENSORIMOTOR_CHANNELS = ["E36", "E104", "E128"]
PRIMARY_CONDITION = "rest"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def no_data_outputs(reason: str) -> None:
    feature_cols = [
        "dataset_id",
        "subject",
        "session",
        "condition",
        "file_path",
        "sensorimotor_channels_used",
        "sampling_rate",
        "duration_s_analyzed",
        "smr_power",
        "high_beta_power",
        "broadband_non_target_power",
        "beta_burst_rate",
        "beta_burst_duration",
        "beta_burst_occupancy",
        "smr_high_beta_coupling",
        "baseline_beta_burstiness",
        "baseline_smr_high_beta_separability",
        "status",
    ]
    effect_cols = ["dataset_id", "subject", "condition", "contrast", "metric", "pre_value", "post_value", "absolute_change", "fractional_change", "log2_ratio", "status"]
    regime_cols = [
        "dataset_id",
        "subject",
        "baseline_coupling_abs",
        "baseline_beta_burst_rate",
        "baseline_beta_burst_occupancy",
        "baseline_separability_log10",
        "inside_model_validity_regime",
        "classification_basis",
        "high_beta_change_frac",
        "burst_rate_change_frac",
        "smr_change_frac",
        "broadband_change_frac",
        "signature_supported",
        "status",
    ]
    pd.DataFrame(columns=feature_cols).to_csv(ROOT / "outputs" / "tables" / "wp8_empirical_features.csv", index=False)
    pd.DataFrame(columns=effect_cols).to_csv(ROOT / "outputs" / "tables" / "wp8_prepost_or_sessionwise_effects.csv", index=False)
    pd.DataFrame(columns=regime_cols).to_csv(ROOT / "outputs" / "tables" / "wp8_regime_classification.csv", index=False)
    report = f"""# WP8 Empirical Analysis

{STOP_TEXT}

Reason: {reason}

No simulated or placeholder empirical results were generated.
"""
    (ROOT / "outputs" / "reports" / "wp8_results.md").write_text(report, encoding="utf-8")
    (ROOT / "outputs" / "logs" / "wp8_empirical_processing.log").write_text(
        f"{utc_now()} WP8 stopped. {STOP_TEXT} Reason: {reason}\n", encoding="utf-8"
    )


def inventory_suitable() -> tuple[bool, str]:
    path = ROOT / "outputs" / "tables" / "wp7_dataset_inventory.csv"
    if not path.exists():
        return False, "WP7 inventory table was not found."
    inv = pd.read_csv(path)
    if inv.empty:
        return False, "WP7 inventory table was empty."
    row = inv.iloc[0]
    if str(row.get("suitable_for_smr_high_beta_analysis", "")).lower() != "yes":
        return False, "WP7 inventory did not mark the local subset as suitable."
    if not RAW_ROOT.exists():
        return False, f"Raw dataset directory not found: {RAW_ROOT}"
    return True, "suitable"


def parse_subject_session(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def read_events(edf_path: Path) -> pd.DataFrame:
    subject, session = parse_subject_session(edf_path)
    events_path = edf_path.parent / f"{subject}_{session}_task-smrbmi_events.tsv"
    events = pd.read_csv(events_path, sep="\t")
    events["onset_s"] = events["onset"].astype(float) / 1000.0
    events["duration_s"] = events["duration"].astype(float)
    return events


def load_sensorimotor_raw(edf_path: Path):
    raw = mne.io.read_raw_edf(edf_path, preload=False, include=SENSORIMOTOR_CHANNELS, verbose="ERROR")
    available = [ch for ch in SENSORIMOTOR_CHANNELS if ch in raw.ch_names]
    if not available:
        raw.close()
        raise RuntimeError(f"No configured sensorimotor channels found in {edf_path}")
    raw.pick(available)
    raw.load_data(verbose="ERROR")
    data = raw.get_data(picks=available)
    fs = float(raw.info["sfreq"])
    raw.close()
    return data, fs, available


def concatenate_condition(data: np.ndarray, fs: float, events: pd.DataFrame, condition: str) -> np.ndarray:
    segments = []
    n_samples = data.shape[1]
    for _, row in events[events["instruction"].astype(str) == condition].iterrows():
        start = int(round(float(row["onset_s"]) * fs))
        stop = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
        start = max(0, min(start, n_samples))
        stop = max(start, min(stop, n_samples))
        if stop - start >= fs:
            segments.append(data[:, start:stop])
    if not segments:
        return np.array([])
    stacked = np.concatenate(segments, axis=1)
    avg = np.nanmean(stacked, axis=0)
    return signal.detrend(avg)


def welch_features(x: np.ndarray, fs: float) -> dict[str, float]:
    nperseg = min(len(x), int(fs * 4))
    if nperseg < int(fs):
        return {"smr_power": np.nan, "high_beta_power": np.nan, "broadband_non_target_power": np.nan}
    freqs, psd = signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2)
    smr = bandpower_from_psd(freqs, psd, (12.0, 15.0))
    beta = bandpower_from_psd(freqs, psd, (20.0, 30.0))
    broadband_mask = (freqs >= 4.0) & (freqs <= 45.0) & ~((freqs >= 12.0) & (freqs <= 15.0)) & ~((freqs >= 20.0) & (freqs <= 30.0))
    broadband = float(np.trapz(psd[broadband_mask], freqs[broadband_mask])) if broadband_mask.sum() > 2 else np.nan
    return {"smr_power": smr, "high_beta_power": beta, "broadband_non_target_power": broadband}


def band_envelope_fast(x: np.ndarray, fs: float, band: tuple[float, float]) -> np.ndarray:
    sos = signal.butter(4, [band[0] / (fs / 2.0), band[1] / (fs / 2.0)], btype="bandpass", output="sos")
    filtered = signal.sosfiltfilt(sos, x)
    return np.abs(signal.hilbert(filtered))


def coupling_and_envelopes(x: np.ndarray, fs: float) -> tuple[float, np.ndarray, np.ndarray]:
    smr_env = band_envelope_fast(x, fs, (12.0, 15.0))
    beta_env = band_envelope_fast(x, fs, (20.0, 30.0))
    step = max(1, int(round(fs / 50.0)))
    a = smr_env[::step]
    b = beta_env[::step]
    if len(a) < 5 or np.std(a) == 0 or np.std(b) == 0:
        corr = np.nan
    else:
        corr = float(np.corrcoef(a, b)[0, 1])
    return corr, smr_env, beta_env


def collect_signals(log_lines: list[str]) -> tuple[pd.DataFrame, dict[tuple[str, str, str], np.ndarray], dict[tuple[str, str, str], float]]:
    rows = []
    signals: dict[tuple[str, str, str], np.ndarray] = {}
    fs_by_key: dict[tuple[str, str, str], float] = {}
    edf_files = sorted(RAW_ROOT.glob("sub-*/ses-*/eeg/*_eeg.edf"))
    for edf_path in edf_files:
        subject, session = parse_subject_session(edf_path)
        log_lines.append(f"{utc_now()} loading {edf_path.relative_to(ROOT)}")
        data, fs, channels = load_sensorimotor_raw(edf_path)
        events = read_events(edf_path)
        for condition in sorted(events["instruction"].astype(str).unique()):
            x = concatenate_condition(data, fs, events, condition)
            if x.size == 0:
                continue
            key = (subject, session, condition)
            signals[key] = x
            fs_by_key[key] = fs
            rows.append(
                {
                    "dataset_id": DATASET_ID,
                    "subject": subject,
                    "session": session,
                    "condition": condition,
                    "file_path": str(edf_path.relative_to(ROOT)).replace("\\", "/"),
                    "sensorimotor_channels_used": ";".join(channels),
                    "sampling_rate": fs,
                    "duration_s_analyzed": len(x) / fs,
                }
            )
    return pd.DataFrame(rows), signals, fs_by_key


def compute_features(base_rows: pd.DataFrame, signals: dict[tuple[str, str, str], np.ndarray], fs_by_key: dict[tuple[str, str, str], float]) -> pd.DataFrame:
    baseline_thresholds = {}
    for key, x in signals.items():
        subject, session, condition = key
        if session == "ses-01" and condition == PRIMARY_CONDITION:
            fs = fs_by_key[key]
            _, _, beta_env = coupling_and_envelopes(x, fs)
            baseline_thresholds[subject] = float(np.percentile(beta_env, 80.0))
    rows = []
    for _, base in base_rows.iterrows():
        key = (base["subject"], base["session"], base["condition"])
        x = signals[key]
        fs = fs_by_key[key]
        powers = welch_features(x, fs)
        corr, _, beta_env = coupling_and_envelopes(x, fs)
        threshold = baseline_thresholds.get(base["subject"], float(np.percentile(beta_env, 80.0)))
        bursts = burst_metrics(beta_env, threshold, fs)
        rows.append(
            {
                **base.to_dict(),
                **powers,
                "beta_burst_rate": bursts["burst_rate_per_min"],
                "beta_burst_duration": bursts["burst_duration_s"],
                "beta_burst_occupancy": bursts["burst_occupancy"],
                "smr_high_beta_coupling": corr,
                "baseline_burst_threshold": threshold,
                "status": "real_eeg_analyzed",
            }
        )
    features = pd.DataFrame(rows)
    baseline = features[(features["session"] == "ses-01") & (features["condition"] == PRIMARY_CONDITION)][
        ["subject", "beta_burst_rate", "beta_burst_occupancy", "smr_high_beta_coupling", "smr_power", "high_beta_power"]
    ].copy()
    baseline["baseline_beta_burstiness"] = baseline["beta_burst_occupancy"]
    baseline["baseline_smr_high_beta_separability"] = np.abs(np.log10((baseline["smr_power"] + 1e-30) / (baseline["high_beta_power"] + 1e-30)))
    baseline = baseline[["subject", "baseline_beta_burstiness", "baseline_smr_high_beta_separability"]]
    features = features.merge(baseline, on="subject", how="left")
    return features


def fractional_change(pre: float, post: float) -> tuple[float, float, float]:
    abs_change = post - pre
    frac = abs_change / pre if np.isfinite(pre) and pre != 0 else np.nan
    log2 = np.log2((post + 1e-30) / (pre + 1e-30)) if np.isfinite(pre) and np.isfinite(post) else np.nan
    return float(abs_change), float(frac), float(log2)


def compute_effects(features: pd.DataFrame) -> pd.DataFrame:
    metrics = {
        "smr_power": "SMR power",
        "high_beta_power": "high-beta power",
        "broadband_non_target_power": "broadband non-target power",
        "beta_burst_rate": "beta-burst rate",
        "beta_burst_duration": "beta-burst duration",
        "smr_high_beta_coupling": "SMR/high-beta coupling",
    }
    rows = []
    for (subject, condition), group in features.groupby(["subject", "condition"]):
        pre = group[group["session"] == "ses-01"]
        post = group[group["session"] == "ses-08"]
        if pre.empty or post.empty:
            continue
        pre = pre.iloc[0]
        post = post.iloc[0]
        for col, label in metrics.items():
            abs_change, frac, log2 = fractional_change(float(pre[col]), float(post[col]))
            rows.append(
                {
                    "dataset_id": DATASET_ID,
                    "subject": subject,
                    "condition": condition,
                    "contrast": "ses-08_minus_ses-01",
                    "metric": col,
                    "metric_label": label,
                    "pre_value": float(pre[col]),
                    "post_value": float(post[col]),
                    "absolute_change": abs_change,
                    "fractional_change": frac,
                    "log2_ratio": log2,
                    "status": "real_eeg_prepost",
                }
            )
    return pd.DataFrame(rows)


def classify_regime(features: pd.DataFrame, effects: pd.DataFrame) -> pd.DataFrame:
    baseline = features[(features["session"] == "ses-01") & (features["condition"] == PRIMARY_CONDITION)].copy()
    if baseline.empty:
        return pd.DataFrame()
    burst_median = float(baseline["beta_burst_occupancy"].median())
    rows = []
    for _, row in baseline.iterrows():
        subject = row["subject"]
        subj_eff = effects[(effects["subject"] == subject) & (effects["condition"] == PRIMARY_CONDITION)]
        def eff(metric: str) -> float:
            vals = subj_eff.loc[subj_eff["metric"] == metric, "fractional_change"]
            return float(vals.iloc[0]) if len(vals) else np.nan
        coupling_abs = abs(float(row["smr_high_beta_coupling"]))
        separability = float(np.abs(np.log10((row["smr_power"] + 1e-30) / (row["high_beta_power"] + 1e-30))))
        inside = bool(coupling_abs <= 0.30 and float(row["beta_burst_occupancy"]) >= burst_median and separability >= 0.05)
        hb = eff("high_beta_power")
        br = eff("beta_burst_rate")
        smr = eff("smr_power")
        broad = eff("broadband_non_target_power")
        signature = bool(np.isfinite(hb) and np.isfinite(br) and np.isfinite(smr) and hb < 0 and br < 0 and abs(smr) <= 0.25)
        rows.append(
            {
                "dataset_id": DATASET_ID,
                "subject": subject,
                "baseline_coupling_abs": coupling_abs,
                "baseline_beta_burst_rate": float(row["beta_burst_rate"]),
                "baseline_beta_burst_occupancy": float(row["beta_burst_occupancy"]),
                "baseline_separability_log10": separability,
                "inside_model_validity_regime": inside,
                "classification_basis": "abs baseline rest coupling <= 0.30; burst occupancy >= subset median; SMR/high-beta separability >= 0.05",
                "high_beta_change_frac": hb,
                "burst_rate_change_frac": br,
                "smr_change_frac": smr,
                "broadband_change_frac": broad,
                "signature_supported": signature,
                "status": "descriptive_real_eeg_subset",
            }
        )
    return pd.DataFrame(rows)


def make_figures(features: pd.DataFrame, effects: pd.DataFrame, regimes: pd.DataFrame) -> None:
    set_style()
    primary = effects[effects["condition"] == PRIMARY_CONDITION].copy()
    keep = ["smr_power", "high_beta_power", "broadband_non_target_power", "beta_burst_rate", "beta_burst_duration"]
    source = primary[primary["metric"].isin(keep)].copy()
    summary = source.groupby("metric", as_index=False).agg(mean_log2_ratio=("log2_ratio", "mean"), sem_log2_ratio=("log2_ratio", lambda x: float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else 0.0))
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.6))
    ordered = [m for m in keep if m in summary["metric"].tolist()]
    y = [float(summary.loc[summary["metric"] == m, "mean_log2_ratio"].iloc[0]) for m in ordered]
    axes[0].bar(ordered, y, color="#4d7f72")
    axes[0].axhline(0, color="0.25", lw=0.8)
    axes[0].set_title("Pre/post rest signature")
    axes[0].set_ylabel("mean log2(post/pre)")
    axes[0].tick_params(axis="x", rotation=35)
    for metric in ["high_beta_power", "beta_burst_rate", "smr_power"]:
        g = primary[primary["metric"] == metric].sort_values("subject")
        axes[1].plot(g["subject"], g["fractional_change"], marker="o", lw=1.0, label=metric)
    axes[1].axhline(0, color="0.25", lw=0.8)
    axes[1].set_title("Subject-level fractional changes")
    axes[1].set_ylabel("fractional change")
    axes[1].tick_params(axis="x", rotation=35)
    axes[1].legend(fontsize=7, loc="best")
    save_csv_backed_figure(fig, source, "wp8_empirical_signature_panel")

    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6))
    if regimes.empty:
        regimes = pd.DataFrame({"baseline_coupling_abs": [], "baseline_beta_burst_occupancy": [], "high_beta_change_frac": [], "inside_model_validity_regime": []})
    colors = regimes["inside_model_validity_regime"].map({True: "#3b6ea8", False: "#b45f47"}) if "inside_model_validity_regime" in regimes else []
    axes[0].scatter(regimes.get("baseline_coupling_abs", []), regimes.get("high_beta_change_frac", []), c=colors)
    axes[0].axhline(0, color="0.25", lw=0.8)
    axes[0].axvline(0.30, color="0.4", lw=0.8, ls="--")
    axes[0].set_title("Baseline coupling vs beta change")
    axes[0].set_xlabel("|SMR/high-beta coupling|")
    axes[0].set_ylabel("high-beta fractional change")
    axes[1].scatter(regimes.get("baseline_beta_burst_occupancy", []), regimes.get("burst_rate_change_frac", []), c=colors)
    axes[1].axhline(0, color="0.25", lw=0.8)
    axes[1].set_title("Baseline burstiness vs burst change")
    axes[1].set_xlabel("baseline beta-burst occupancy")
    axes[1].set_ylabel("burst-rate fractional change")
    save_csv_backed_figure(fig, regimes, "wp8_regime_prediction_panel")


def write_report(features: pd.DataFrame, effects: pd.DataFrame, regimes: pd.DataFrame) -> None:
    primary = effects[effects["condition"] == PRIMARY_CONDITION]
    def mean_change(metric: str) -> float:
        vals = primary.loc[primary["metric"] == metric, "fractional_change"]
        return float(vals.mean()) if len(vals) else np.nan
    inside = regimes[regimes["inside_model_validity_regime"] == True] if not regimes.empty else pd.DataFrame()
    outside = regimes[regimes["inside_model_validity_regime"] == False] if not regimes.empty else pd.DataFrame()
    hb = mean_change("high_beta_power")
    br = mean_change("beta_burst_rate")
    smr = mean_change("smr_power")
    supported = int(regimes["signature_supported"].sum()) if not regimes.empty else 0
    if supported == len(regimes) and len(regimes) > 0:
        support_label = "support"
    elif supported > 0:
        support_label = "partial support"
    else:
        support_label = "non-support for the full joint signature"
    text = f"""# WP8 Results: Empirical Anchoring in Real SMR-BCI EEG

Dataset analyzed: `{DATASET_ID}` OpenNeuro high-density SMR-BCI subset.

Scope:

- Real EDF files were downloaded, inventoried, loaded, and analyzed.
- Subset: {features['subject'].nunique()} subjects, sessions `{';'.join(sorted(features['session'].unique()))}`, condition labels `{';'.join(sorted(features['condition'].unique()))}`.
- Sensorimotor channels: `{';'.join(SENSORIMOTOR_CHANNELS)}` based on the official helper code identifying `[36,104,128]` as C3/C4/Cz.
- Results are descriptive empirical anchoring, not proof of mechanism.

Primary rest-condition pre/post changes:

- SMR power fractional change: {smr:.3f}.
- High-beta power fractional change: {hb:.3f}.
- Broadband non-target power fractional change: {mean_change('broadband_non_target_power'):.3f}.
- Beta-burst rate fractional change: {br:.3f}.
- Beta-burst duration fractional change: {mean_change('beta_burst_duration'):.3f}.

Regime classification:

- Inside validity-regime count: {len(inside)}.
- Outside validity-regime count: {len(outside)}.
- Signature-supported subjects: {supported} / {len(regimes)}.
- Empirical interpretation label: {support_label}.

Interpretation:

This subset provides a proof-of-pipeline empirical anchor. It does not provide strong empirical support for the predicted joint signature because mean high-beta power did not decrease, although beta-burst rate decreased and SMR power was approximately unchanged. No universal or mechanistic claim is made from this five-subject subset.
"""
    (ROOT / "outputs" / "reports" / "wp8_results.md").write_text(text, encoding="utf-8")


def run() -> None:
    ensure_repo_structure(ROOT)
    log_lines = [f"{utc_now()} WP8 empirical analysis started."]
    ok, reason = inventory_suitable()
    if not ok:
        no_data_outputs(reason)
        return
    try:
        base_rows, signals, fs_by_key = collect_signals(log_lines)
        if base_rows.empty:
            no_data_outputs("No EDF condition segments could be loaded.")
            return
        features = compute_features(base_rows, signals, fs_by_key)
        effects = compute_effects(features)
        regimes = classify_regime(features, effects)
        features.to_csv(ROOT / "outputs" / "tables" / "wp8_empirical_features.csv", index=False)
        effects.to_csv(ROOT / "outputs" / "tables" / "wp8_prepost_or_sessionwise_effects.csv", index=False)
        regimes.to_csv(ROOT / "outputs" / "tables" / "wp8_regime_classification.csv", index=False)
        make_figures(features, effects, regimes)
        write_report(features, effects, regimes)
        log_lines.append(f"{utc_now()} WP8 completed successfully with {len(features)} feature rows.")
        (ROOT / "outputs" / "logs" / "wp8_empirical_processing.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    except Exception as exc:
        no_data_outputs(f"WP8 failed while loading or analyzing real EEG: {type(exc).__name__}: {exc}")
        with (ROOT / "outputs" / "logs" / "wp8_empirical_processing.log").open("a", encoding="utf-8") as handle:
            handle.write("\n".join(log_lines) + "\n")
            handle.write(f"{utc_now()} ERROR {type(exc).__name__}: {exc}\n")
        raise


def main() -> None:
    run()


if __name__ == "__main__":
    main()
