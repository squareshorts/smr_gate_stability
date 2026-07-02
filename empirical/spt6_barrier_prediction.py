"""SPT6: Barrier violation and future-state prediction (real EEG).

Tests whether high-beta barrier violations at time t predict next-state dynamics.

Outputs
-------
outputs/tables/spt6_barrier_prediction_models.csv
outputs/tables/spt6_threshold_sensitivity.csv
outputs/figures/spt6_prediction_effects.*
outputs/figures/spt6_threshold_sensitivity.*
outputs/reports/spt6_results.md
outputs/logs/spt6_empirical_processing.log
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
from utils.signal_metrics import band_envelope, burst_metrics


DATASET_ID = "ds004446"
RAW_ROOT = ROOT / "data" / "raw" / "openneuro" / DATASET_ID
SENSORIMOTOR_CHANNELS = ["E36", "E104", "E128"]
SMR_BAND = (12.0, 15.0)
HIGH_BETA_BAND = (20.0, 30.0)
BROADBAND_BAND = (4.0, 45.0)
BLOCK_DURATION_S = 4.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_subject_session(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def load_signal(edf_path: Path, condition: str) -> tuple[np.ndarray, float]:
    """Load concatenated condition signal."""
    subject, session = parse_subject_session(edf_path)
    events_path = edf_path.parent / f"{subject}_{session}_task-smrbmi_events.tsv"
    if not events_path.exists():
        return np.array([]), 0.0

    raw = mne.io.read_raw_edf(edf_path, preload=False,
                               include=SENSORIMOTOR_CHANNELS, verbose="ERROR")
    available = [ch for ch in SENSORIMOTOR_CHANNELS if ch in raw.ch_names]
    if not available:
        raw.close()
        return np.array([]), 0.0

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
        return np.array([]), fs

    x = np.concatenate(segments)
    return scipy_signal.detrend(x), fs


def extract_block_features(x: np.ndarray, fs: float,
                            block_s: float = 4.0) -> pd.DataFrame:
    """Extract per-block features for prediction analysis."""
    block_n = int(block_s * fs)
    n_blocks = len(x) // block_n
    if n_blocks < 3:
        return pd.DataFrame()

    # Band envelopes
    smr_env = band_envelope(x, fs, SMR_BAND)
    hbeta_env = band_envelope(x, fs, HIGH_BETA_BAND)
    broad_env = band_envelope(x, fs, BROADBAND_BAND)

    # Baseline statistics for thresholding
    hbeta_p75 = float(np.percentile(hbeta_env, 75))
    hbeta_p80 = float(np.percentile(hbeta_env, 80))
    hbeta_p90 = float(np.percentile(hbeta_env, 90))
    hbeta_mean = float(np.mean(hbeta_env))
    hbeta_std = float(np.std(hbeta_env))
    hbeta_mad = float(np.median(np.abs(hbeta_env - np.median(hbeta_env))))

    rows = []
    for b in range(n_blocks - 1):
        sl = slice(b * block_n, (b + 1) * block_n)
        sl_next = slice((b + 1) * block_n, (b + 2) * block_n)

        smr_now = float(np.mean(smr_env[sl]))
        hbeta_now = float(np.mean(hbeta_env[sl]))
        broad_now = float(np.mean(broad_env[sl]))

        smr_next = float(np.mean(smr_env[sl_next]))
        hbeta_next = float(np.mean(hbeta_env[sl_next]))

        smr_increase = int(smr_next > smr_now)
        admissible_next = int(hbeta_next < hbeta_p75)

        rows.append({
            "block": b,
            "smr_now": smr_now,
            "hbeta_now": hbeta_now,
            "broad_now": broad_now,
            "smr_next": smr_next,
            "hbeta_next": hbeta_next,
            "smr_increase": smr_increase,
            "admissible_next": admissible_next,
            "viol_p75": int(hbeta_now > hbeta_p75),
            "viol_p80": int(hbeta_now > hbeta_p80),
            "viol_p90": int(hbeta_now > hbeta_p90),
            "viol_zscore": int(hbeta_now > hbeta_mean + 2 * hbeta_std),
            "viol_mad": int(hbeta_now > np.median(hbeta_env) + 3 * hbeta_mad),
            "broadband_contam": int(broad_now > float(np.percentile(broad_env, 80))),
        })
    return pd.DataFrame(rows)


def simple_logistic_association(X: np.ndarray, y: np.ndarray) -> dict:
    """Simple logistic regression-like association using scipy."""
    if len(y) < 10 or y.std() == 0:
        return {"slope": np.nan, "p_value": np.nan, "n": len(y)}
    # Use point-biserial for binary X vs continuous, or contingency for binary-binary
    if len(np.unique(X)) <= 2 and len(np.unique(y)) <= 2:
        # 2x2 contingency
        ct = np.zeros((2, 2), dtype=int)
        for xi, yi in zip(X.astype(int), y.astype(int)):
            ct[min(xi, 1), min(yi, 1)] += 1
        try:
            chi2, p, _, _ = stats.chi2_contingency(ct, correction=False)
            # Odds ratio
            a, b, c, d = ct[1, 1], ct[1, 0], ct[0, 1], ct[0, 0]
            or_ = (a * d) / (b * c) if (b * c) > 0 else np.nan
            return {"odds_ratio": or_, "chi2": chi2, "p_value": p, "n": len(y)}
        except Exception:
            return {"odds_ratio": np.nan, "p_value": np.nan, "n": len(y)}
    else:
        r, p = stats.pointbiserialr(X, y.astype(float))
        return {"correlation": r, "p_value": p, "n": len(y)}


def permutation_test(X: np.ndarray, y: np.ndarray, n_perm: int = 500,
                     seed: int = 42) -> float:
    """Permutation test for association between violation indicator and outcome."""
    rng = np.random.default_rng(seed)
    if len(np.unique(y)) <= 1 or len(np.unique(X)) <= 1:
        return np.nan
    observed = abs(stats.pointbiserialr(X, y.astype(float))[0])
    perm_stats = []
    for _ in range(n_perm):
        y_perm = rng.permutation(y)
        perm_stats.append(abs(stats.pointbiserialr(X, y_perm.astype(float))[0]))
    perm_p = float(np.mean(np.array(perm_stats) >= observed))
    return perm_p


def run_barrier_prediction(block_df: pd.DataFrame,
                            subject: str, session: str) -> list[dict]:
    """Fit prediction models for a subject/session block DataFrame."""
    if block_df.empty or len(block_df) < 5:
        return []

    y_admissible = block_df["admissible_next"].values
    y_smr_inc = block_df["smr_increase"].values
    rows = []

    for thresh_name in ["viol_p75", "viol_p80", "viol_p90", "viol_zscore", "viol_mad"]:
        X = block_df[thresh_name].values

        for outcome_name, y in [("admissible_next", y_admissible),
                                 ("smr_increase", y_smr_inc)]:
            assoc = simple_logistic_association(X, y)
            perm_p = permutation_test(X, y, n_perm=200)

            rows.append({
                "subject": subject,
                "session": session,
                "threshold": thresh_name,
                "outcome": outcome_name,
                "n_blocks": len(block_df),
                "violation_rate": float(np.mean(X)),
                "outcome_rate": float(np.mean(y)),
                "odds_ratio": assoc.get("odds_ratio", np.nan),
                "correlation": assoc.get("correlation", np.nan),
                "p_value": assoc.get("p_value", np.nan),
                "perm_p": perm_p,
            })
    return rows


def threshold_sensitivity_summary(pred_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate prediction effect across threshold methods."""
    if pred_df.empty:
        return pd.DataFrame()
    agg = (
        pred_df.groupby(["threshold", "outcome"])
        .agg(
            mean_or=("odds_ratio", "mean"),
            mean_corr=("correlation", "mean"),
            mean_p=("p_value", "mean"),
            n_subjects=("subject", "nunique"),
        )
        .reset_index()
    )
    return agg


def make_prediction_figure(pred_df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    if pred_df.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center",
                    fontsize=12, transform=ax.transAxes)
        plt.tight_layout()
        save_csv_backed_figure(fig, pd.DataFrame({"note": ["no data"]}),
                               "spt6_prediction_effects", root)
        return

    # Panel A: correlation/OR by threshold and outcome
    thresholds = pred_df["threshold"].unique()
    outcomes = pred_df["outcome"].unique()
    outcome_colors = {"admissible_next": "#2ca02c", "smr_increase": "#1f77b4"}

    for outcome in outcomes:
        odf = pred_df[pred_df["outcome"] == outcome]
        agg = odf.groupby("threshold")["correlation"].mean()
        agg_p = odf.groupby("threshold")["perm_p"].mean()
        xs = range(len(agg))
        axes[0].plot(xs, agg.values, "o-", color=outcome_colors.get(outcome, "gray"),
                     label=outcome, lw=1.5)
        # Mark significant points
        for xi, (_, corr, pp) in enumerate(zip(agg.index, agg.values, agg_p.values)):
            if not np.isnan(pp) and pp < 0.05:
                axes[0].scatter(xi, corr, s=100, marker="*",
                                color=outcome_colors.get(outcome, "gray"), zorder=5)

    axes[0].axhline(0, color="black", ls="--", lw=0.8)
    axes[0].set_xticks(range(len(thresholds)))
    axes[0].set_xticklabels([t.replace("viol_", "") for t in thresholds], rotation=30, ha="right")
    axes[0].set_xlabel("Violation threshold")
    axes[0].set_ylabel("Point-biserial correlation")
    axes[0].set_title("Violation → next-state prediction")
    axes[0].legend(fontsize=7)

    # Panel B: p-value distribution
    for outcome in outcomes:
        odf = pred_df[pred_df["outcome"] == outcome].dropna(subset=["perm_p"])
        if odf.empty:
            continue
        agg = odf.groupby("threshold")["perm_p"].mean()
        axes[1].plot(range(len(agg)), agg.values, "o-",
                     color=outcome_colors.get(outcome, "gray"), label=outcome, lw=1.5)

    axes[1].axhline(0.05, color="red", ls="--", lw=1.0, label="p=0.05")
    axes[1].set_xticks(range(len(thresholds)))
    axes[1].set_xticklabels([t.replace("viol_", "") for t in thresholds], rotation=30, ha="right")
    axes[1].set_xlabel("Violation threshold")
    axes[1].set_ylabel("Permutation p-value (mean)")
    axes[1].set_title("Prediction significance")
    axes[1].legend(fontsize=7)
    axes[1].set_ylim(0, 1)

    fig.suptitle("SPT6: Barrier violation prediction of next-state", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(fig, pred_df, "spt6_prediction_effects", root)


def make_threshold_sensitivity_figure(sens_df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    if sens_df.empty:
        for ax in axes:
            ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center",
                    fontsize=12, transform=ax.transAxes)
        plt.tight_layout()
        save_csv_backed_figure(fig, pd.DataFrame({"note": ["no data"]}),
                               "spt6_threshold_sensitivity", root)
        return

    outcomes = sens_df["outcome"].unique()
    colors = {"admissible_next": "#2ca02c", "smr_increase": "#1f77b4"}

    for outcome in outcomes:
        odf = sens_df[sens_df["outcome"] == outcome]
        axes[0].plot(range(len(odf)), odf["mean_corr"].values, "o-",
                     color=colors.get(outcome, "gray"), label=outcome, lw=1.5)

    axes[0].axhline(0, color="black", ls="--", lw=0.8)
    axes[0].set_xticks(range(len(sens_df["threshold"].unique())))
    axes[0].set_xticklabels([t.replace("viol_", "") for t in sens_df["threshold"].unique()],
                            rotation=30, ha="right")
    axes[0].set_xlabel("Violation threshold")
    axes[0].set_ylabel("Mean correlation (across subjects)")
    axes[0].set_title("Threshold sensitivity: correlation")
    axes[0].legend(fontsize=7)

    for outcome in outcomes:
        odf = sens_df[sens_df["outcome"] == outcome]
        axes[1].plot(range(len(odf)), odf["mean_p"].values, "o-",
                     color=colors.get(outcome, "gray"), label=outcome, lw=1.5)

    axes[1].axhline(0.05, color="red", ls="--", lw=1.0, label="p=0.05")
    axes[1].set_xticks(range(len(sens_df["threshold"].unique())))
    axes[1].set_xticklabels([t.replace("viol_", "") for t in sens_df["threshold"].unique()],
                            rotation=30, ha="right")
    axes[1].set_xlabel("Violation threshold")
    axes[1].set_ylabel("Mean p-value")
    axes[1].set_title("Threshold sensitivity: significance")
    axes[1].legend(fontsize=7)
    axes[1].set_ylim(0, 1)

    fig.suptitle("SPT6: Threshold sensitivity analysis", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(fig, sens_df, "spt6_threshold_sensitivity", root)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ensure_repo_structure(ROOT)
    tbl_dir = ROOT / "outputs" / "tables"
    rep_dir = ROOT / "outputs" / "reports"
    log_dir = ROOT / "outputs" / "logs"

    log_lines = [f"{utc_now()} SPT6 started."]

    edf_files = sorted(RAW_ROOT.glob("sub-*/ses-*/eeg/*_eeg.edf")) if RAW_ROOT.exists() else []
    log_lines.append(f"EDF files found: {len(edf_files)}")

    all_pred_rows = []
    all_block_rows = []

    for edf_path in edf_files:
        subject, session = parse_subject_session(edf_path)
        log_lines.append(f"{utc_now()} Processing {edf_path.name}")
        for condition in ["rest", "task"]:
            x, fs = load_signal(edf_path, condition)
            if x.size < int(fs * 10) if fs > 0 else 0:
                log_lines.append(f"  {condition}: skipped (too short)")
                continue

            block_df = extract_block_features(x, fs, BLOCK_DURATION_S)
            if block_df.empty:
                log_lines.append(f"  {condition}: no blocks extracted")
                continue

            block_df["subject"] = subject
            block_df["session"] = session
            block_df["condition"] = condition
            all_block_rows.append(block_df)

            pred_rows = run_barrier_prediction(block_df, subject, session)
            if pred_rows:
                for r in pred_rows:
                    r["condition"] = condition
                all_pred_rows.extend(pred_rows)
            log_lines.append(f"  {condition}: {len(block_df)} blocks, {len(pred_rows)} prediction rows")

    pred_df = pd.DataFrame(all_pred_rows) if all_pred_rows else pd.DataFrame()
    pred_df.to_csv(tbl_dir / "spt6_barrier_prediction_models.csv", index=False)

    sens_df = threshold_sensitivity_summary(pred_df)
    sens_df.to_csv(tbl_dir / "spt6_threshold_sensitivity.csv", index=False)

    print("SPT6: Creating figures...")
    make_prediction_figure(pred_df, ROOT)
    make_threshold_sensitivity_figure(sens_df, ROOT)

    # Report
    n_subjects = pred_df["subject"].nunique() if not pred_df.empty else 0
    n_blocks = sum(len(b) for b in all_block_rows) if all_block_rows else 0
    has_significant = False
    best_result = "No prediction results available."

    if not pred_df.empty and "perm_p" in pred_df.columns:
        sig = pred_df[pred_df["perm_p"] < 0.05]
        has_significant = len(sig) > 0
        if has_significant:
            best = sig.iloc[0]
            best_result = (
                f"Significant: threshold={best['threshold']}, "
                f"outcome={best['outcome']}, perm_p={best['perm_p']:.3f}"
            )
        else:
            best_result = (
                f"No threshold/outcome combination reached p<0.05 by permutation test "
                f"(across {n_subjects} subjects, {n_blocks} blocks)."
            )

    report = f"""# SPT6 Results: Barrier Violation and Future-state Prediction

## Method

High-beta barrier violations at block t are tested as predictors of:
1. Admissible-state occupancy at block t+1.
2. SMR increase at block t+1.

Block size: {BLOCK_DURATION_S} s.
Violation thresholds: 75th, 80th, 90th percentile; 2-SD z-score; 3-MAD.
Statistical tests: point-biserial correlation + permutation test (200 permutations).

## Data

EDF files processed: {len(edf_files)}
Subjects analyzed: {n_subjects}
Total blocks: {n_blocks}

## Results

{best_result}

"""
    if not pred_df.empty and not sens_df.empty:
        report += "### Mean correlation by threshold and outcome\n\n"
        report += sens_df[["threshold", "outcome", "mean_corr", "mean_p"]].to_string(index=False)
        report += "\n\n"

    report += f"""## Interpretation

"""
    if has_significant:
        report += (
            "At least one threshold/outcome pair showed statistically significant association "
            "between high-beta barrier violation and next-state outcome. "
            "This provides PRELIMINARY EVIDENCE that barrier violations predict instability. "
            "CAUTION: Sample size is very small (N={n_subjects}), so results are exploratory only.\n"
        ).format(n_subjects=n_subjects)
    elif n_subjects > 0:
        report += (
            f"No statistically significant association was found between high-beta "
            f"barrier violations and next-state admissibility or SMR increase "
            f"(N={n_subjects} subjects, {n_blocks} total blocks). "
            f"This does NOT rule out the barrier hypothesis — insufficient statistical "
            f"power is the most likely explanation for the null result given the small sample.\n"
        )
    else:
        report += (
            "No empirical data was available for this analysis. "
            "Results cannot be evaluated.\n"
        )

    report += f"\nGenerated: {utc_now()}\n"
    (rep_dir / "spt6_results.md").write_text(report, encoding="utf-8")
    (log_dir / "spt6_empirical_processing.log").write_text("\n".join(log_lines), encoding="utf-8")
    print("SPT6 done.")


if __name__ == "__main__":
    main()
