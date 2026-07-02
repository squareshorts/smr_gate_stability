"""SPT6 Revised: Rigorous barrier-prediction analysis.

Critical methodological fix from original:
- Original: threshold computed on high-resolution (256 Hz) envelope; block means
  almost never exceed these high-resolution percentiles → violation_rate ≈ 0 for most rows.
- Fix: compute threshold on BLOCK MEANS directly. The 75th percentile of block means
  guarantees that ~25% of blocks will be labelled as violations, giving the analysis power.

Additional improvements:
- Effect size (phi/Cramer's V) for every 2×2 table
- Fisher exact test alongside chi-square
- Benjamini-Hochberg FDR correction across all tested combinations
- Pool across subjects/sessions and report aggregate
- Honest null statement when FDR-corrected p > 0.05 for all tests

Outputs
-------
outputs/tables/spt6_barrier_prediction_models.csv        (updated)
outputs/tables/spt6_threshold_sensitivity.csv            (updated)
outputs/tables/spt6_nonzero_viol_summary.csv             (new)
outputs/figures/spt6_barrier_prediction_panel.*          (updated)
outputs/figures/spt6_effect_size_forest.*                (new)
outputs/reports/spt6_results.md                          (updated)
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
from statsmodels.stats.multitest import multipletests

import mne

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style
from utils.signal_metrics import band_envelope


DATASET_ID = "ds004446"
RAW_ROOT = ROOT / "data" / "raw" / "openneuro" / DATASET_ID
SENSORIMOTOR_CHANNELS = ["E36", "E104", "E128"]
SMR_BAND = (12.0, 15.0)
HIGH_BETA_BAND = (20.0, 30.0)
BLOCK_S = 4.0
N_PERM = 1000   # permutations per test (increased for precision)
SEED = 42


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_subject_session(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def load_eeg_data(edf_path: Path,
                  condition: str) -> tuple[np.ndarray, float]:
    """Load raw EEG and return (signal, fs) for given condition."""
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

    # Concatenate trial segments for the requested condition
    n_samples = data.shape[1]
    segments = []
    for _, row in events[events["instruction"].astype(str) == condition].iterrows():
        start = int(round(float(row["onset_s"]) * fs))
        stop = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
        start = max(0, min(start, n_samples))
        stop = max(start, min(stop, n_samples))
        if stop - start >= int(fs * 4):
            segments.append(np.nanmean(data[:, start:stop], axis=0))

    if not segments:
        return np.array([]), fs

    x = np.concatenate(segments)
    return x, fs


def compute_block_series(edf_path: Path, condition: str, block_s: float = BLOCK_S
                         ) -> pd.DataFrame | None:
    """
    Load EEG, compute SMR and high-beta envelopes, split into non-overlapping
    blocks, return DataFrame with one row per block containing block means.

    CRITICAL FIX: the violation indicator is computed relative to the
    DISTRIBUTION OF BLOCK MEANS (not the instantaneous envelope), ensuring
    that ~25%/~20%/~10% of blocks are labelled as violations for the
    75th/80th/90th percentile thresholds.
    """
    x, fs = load_eeg_data(edf_path, condition)
    if x.size < int(fs * block_s * 4):
        return None

    smr_env = np.abs(band_envelope(x, fs, SMR_BAND))
    hb_env = np.abs(band_envelope(x, fs, HIGH_BETA_BAND))

    block_n = int(block_s * fs)
    n_blocks = len(x) // block_n
    if n_blocks < 4:
        return None

    smr_blocks = np.array([smr_env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])
    hb_blocks = np.array([hb_env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])

    df = pd.DataFrame({
        "block_idx": np.arange(n_blocks),
        "smr_mean": smr_blocks,
        "hb_mean": hb_blocks,
    })

    # Compute violation flags relative to BLOCK MEAN distribution (KEY FIX)
    hb_p75 = np.percentile(hb_blocks, 75)
    hb_p80 = np.percentile(hb_blocks, 80)
    hb_p90 = np.percentile(hb_blocks, 90)
    hb_zscore_thr = np.mean(hb_blocks) + 1.5 * np.std(hb_blocks)
    hb_mad_thr = np.median(hb_blocks) + 1.5 * np.median(np.abs(hb_blocks - np.median(hb_blocks)))

    df["viol_p75"] = (hb_blocks > hb_p75).astype(int)
    df["viol_p80"] = (hb_blocks > hb_p80).astype(int)
    df["viol_p90"] = (hb_blocks > hb_p90).astype(int)
    df["viol_zscore"] = (hb_blocks > hb_zscore_thr).astype(int)
    df["viol_mad"] = (hb_blocks > hb_mad_thr).astype(int)

    # SMR-increase outcome: SMR in next block > current block
    df["smr_next"] = np.concatenate([smr_blocks[1:], [np.nan]])
    df["smr_increase"] = ((df["smr_next"] > df["smr_mean"]).astype(float)
                          .where(df["smr_next"].notna(), np.nan))

    # Admissibility: next block HB < current block HB (violation resolves)
    df["hb_next"] = np.concatenate([hb_blocks[1:], [np.nan]])
    df["admissible_next"] = ((df["hb_next"] < df["hb_mean"]).astype(float)
                             .where(df["hb_next"].notna(), np.nan))

    return df


def phi_coefficient(a: int, b: int, c: int, d: int) -> float:
    """Phi coefficient for 2×2 contingency table: [[a,b],[c,d]]."""
    n = a + b + c + d
    if n == 0:
        return np.nan
    denom = np.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denom == 0:
        return np.nan
    return (a * d - b * c) / denom


def fisher_exact_2x2(a: int, b: int, c: int, d: int) -> tuple[float, float]:
    """Fisher exact test, returns (odds_ratio, p_value)."""
    table = np.array([[a, b], [c, d]])
    with np.errstate(divide="ignore", invalid="ignore"):
        res = stats.fisher_exact(table, alternative="two-sided")
    return float(res[0]), float(res[1])


def permutation_test(viol: np.ndarray, outcome: np.ndarray,
                     n_perm: int = N_PERM, rng: np.random.Generator | None = None
                     ) -> float:
    """Permutation test of association between violation indicator and outcome.

    Test statistic: absolute difference in outcome rate between violation and
    non-violation blocks.
    """
    if rng is None:
        rng = np.random.default_rng(SEED)
    mask = ~np.isnan(viol) & ~np.isnan(outcome)
    v = viol[mask].astype(bool)
    o = outcome[mask].astype(float)
    if v.sum() == 0 or (~v).sum() == 0:
        return np.nan
    obs_stat = abs(o[v].mean() - o[~v].mean())
    null = np.array([abs(o[rng.permutation(len(o)) < v.sum()].mean() -
                         o[~(rng.permutation(len(o)) < v.sum())].mean())
                     for _ in range(n_perm)])
    return float((null >= obs_stat).mean())


def analyze_barrier_prediction(block_df: pd.DataFrame, subject: str,
                                session: str, condition: str) -> list[dict]:
    """
    For each threshold × outcome combination, compute the 2×2 contingency
    table, odds ratio, Fisher exact p, phi effect size, and permutation p.
    """
    rng = np.random.default_rng(SEED + hash(subject + session + condition) % (2**16))

    thresholds = ["viol_p75", "viol_p80", "viol_p90", "viol_zscore", "viol_mad"]
    outcomes = ["smr_increase", "admissible_next"]

    rows = []
    for thr in thresholds:
        for out in outcomes:
            if thr not in block_df.columns or out not in block_df.columns:
                continue
            viol = block_df[thr].values
            out_vals = block_df[out].values
            mask = ~np.isnan(viol) & ~np.isnan(out_vals)
            v = viol[mask].astype(bool)
            o = out_vals[mask].astype(float)

            n_blocks = int(mask.sum())
            viol_rate = float(v.mean()) if len(v) > 0 else 0.0
            out_rate = float(o.mean()) if len(o) > 0 else np.nan
            n_viol = int(v.sum())
            n_noviol = int((~v).sum())

            if n_viol == 0 or n_noviol == 0:
                rows.append({
                    "subject": subject, "session": session, "condition": condition,
                    "threshold": thr, "outcome": out,
                    "n_blocks": n_blocks, "n_violation_blocks": n_viol,
                    "violation_rate": viol_rate, "outcome_rate": out_rate,
                    "n_viol_outcome": np.nan, "n_viol_no_outcome": np.nan,
                    "n_noviol_outcome": np.nan, "n_noviol_no_outcome": np.nan,
                    "odds_ratio": np.nan, "phi": np.nan,
                    "fisher_p": np.nan, "perm_p": np.nan, "chi2_p": np.nan,
                })
                continue

            # Contingency table
            a = int((v & (o == 1)).sum())   # viol + outcome
            b = int((v & (o == 0)).sum())   # viol + no outcome
            c = int((~v & (o == 1)).sum())  # no viol + outcome
            d = int((~v & (o == 0)).sum())  # no viol + no outcome

            or_val, fisher_p = fisher_exact_2x2(a, b, c, d)
            phi = phi_coefficient(a, b, c, d)
            perm_p = permutation_test(viol[mask], o, rng=rng)

            # Chi-square
            table = np.array([[a, b], [c, d]])
            try:
                chi2, chi2_p, _, _ = stats.chi2_contingency(table, correction=True)
            except Exception:
                chi2_p = np.nan

            rows.append({
                "subject": subject, "session": session, "condition": condition,
                "threshold": thr, "outcome": out,
                "n_blocks": n_blocks, "n_violation_blocks": n_viol,
                "violation_rate": viol_rate, "outcome_rate": out_rate,
                "n_viol_outcome": a, "n_viol_no_outcome": b,
                "n_noviol_outcome": c, "n_noviol_no_outcome": d,
                "odds_ratio": or_val, "phi": phi,
                "fisher_p": fisher_p, "perm_p": perm_p, "chi2_p": chi2_p,
            })

    return rows


def apply_fdr(df: pd.DataFrame) -> pd.DataFrame:
    """Apply Benjamini-Hochberg FDR correction to fisher_p column."""
    valid = df["fisher_p"].notna()
    if valid.sum() == 0:
        df["fisher_p_fdr"] = np.nan
        df["bonferroni_p"] = np.nan
        return df

    pvals = df.loc[valid, "fisher_p"].values
    # Bonferroni
    bf = np.minimum(pvals * int(valid.sum()), 1.0)
    # BH FDR
    _, fdr_pvals, _, _ = multipletests(pvals, alpha=0.05, method="fdr_bh")

    df["fisher_p_fdr"] = np.nan
    df.loc[valid, "fisher_p_fdr"] = fdr_pvals
    df["bonferroni_p"] = np.nan
    df.loc[valid, "bonferroni_p"] = bf
    df["sig_uncorrected"] = (df["fisher_p"] < 0.05).fillna(False)
    df["sig_fdr"] = (df["fisher_p_fdr"] < 0.05).fillna(False)
    df["sig_bonferroni"] = (df["bonferroni_p"] < 0.05).fillna(False)
    return df


def make_barrier_prediction_figure(df: pd.DataFrame, root: Path) -> None:
    set_style()

    # Focus on rows with non-zero violation rates
    ok = df[df["n_violation_blocks"] > 0].copy()
    if ok.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(0.5, 0.5, "No violation blocks detected", transform=ax.transAxes,
                ha="center", va="center")
        fig.savefig(root / "outputs" / "figures" / "spt6_barrier_prediction_panel.pdf",
                    dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    # A: violation rate distribution across thresholds
    for thr in ["viol_p75", "viol_p80", "viol_p90"]:
        sub = ok[ok["threshold"] == thr]["violation_rate"]
        if not sub.empty:
            axes[0, 0].hist(sub, bins=8, alpha=0.5, label=thr.replace("viol_", ""))
    axes[0, 0].set_xlabel("Violation rate (fraction of blocks)")
    axes[0, 0].set_ylabel("Count")
    axes[0, 0].set_title("(A) Violation rate distribution\n[Block-mean thresholds]")
    axes[0, 0].legend(fontsize=7)

    # B: phi effect sizes (all non-NaN tests)
    ok_phi = ok.dropna(subset=["phi"])
    if not ok_phi.empty:
        smr_phi = ok_phi[ok_phi["outcome"] == "smr_increase"]["phi"]
        adm_phi = ok_phi[ok_phi["outcome"] == "admissible_next"]["phi"]
        axes[0, 1].scatter(range(len(smr_phi)), smr_phi.values, label="SMR increase", alpha=0.7, s=25)
        axes[0, 1].scatter(range(len(adm_phi)), adm_phi.values, label="Admissible next",
                           alpha=0.7, s=25, marker="^")
        axes[0, 1].axhline(0, color="black", ls="--", lw=0.8)
        axes[0, 1].set_xlabel("Test index")
        axes[0, 1].set_ylabel("Phi coefficient")
        axes[0, 1].set_title("(B) Effect sizes (phi)")
        axes[0, 1].legend(fontsize=7)

    # C: p-value scatter (uncorrected vs FDR)
    if "fisher_p_fdr" in ok.columns:
        ok_p = ok.dropna(subset=["fisher_p", "fisher_p_fdr"])
        if not ok_p.empty:
            axes[1, 0].scatter(ok_p["fisher_p"], ok_p["fisher_p_fdr"], alpha=0.7, s=30)
            axes[1, 0].plot([0, 1], [0, 1], "k--", lw=0.8, label="y=x")
            axes[1, 0].axhline(0.05, color="red", ls=":", lw=1, label="FDR p=0.05")
            axes[1, 0].axvline(0.05, color="orange", ls=":", lw=1, label="Uncorr p=0.05")
            axes[1, 0].set_xlabel("Uncorrected Fisher p")
            axes[1, 0].set_ylabel("FDR-corrected p")
            axes[1, 0].set_title("(C) Multiple testing correction")
            axes[1, 0].legend(fontsize=7)

    # D: Summary by subject/session
    if not ok_phi.empty:
        summary = ok_phi.groupby(["subject", "session"])["phi"].agg(["mean", "std"]).reset_index()
        x_pos = np.arange(len(summary))
        axes[1, 1].bar(x_pos, summary["mean"], yerr=summary["std"],
                       capsize=3, color="#1f77b4", alpha=0.7)
        axes[1, 1].set_xticks(x_pos)
        axes[1, 1].set_xticklabels([f"{r['subject']}\n{r['session']}" for _, r in summary.iterrows()],
                                    fontsize=7, rotation=30, ha="right")
        axes[1, 1].axhline(0, color="black", ls="--", lw=0.8)
        axes[1, 1].set_ylabel("Mean phi effect size")
        axes[1, 1].set_title("(D) Effect size by subject/session")

    fig.suptitle("SPT6 Revised: Barrier-prediction (block-mean thresholds)", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(fig, ok[["subject", "session", "condition", "threshold", "outcome",
                                    "violation_rate", "phi", "fisher_p",
                                    "fisher_p_fdr" if "fisher_p_fdr" in ok.columns else "fisher_p"]],
                           "spt6_barrier_prediction_panel", root)


def make_effect_size_forest(df: pd.DataFrame, root: Path) -> None:
    set_style()
    ok = df[df["n_violation_blocks"] > 0].dropna(subset=["phi", "fisher_p"])
    if ok.empty:
        return

    fig, ax = plt.subplots(figsize=(8, max(4, len(ok) * 0.3)))
    y_vals = np.arange(len(ok))
    colors = ["red" if p < 0.05 else "steelblue" for p in ok["fisher_p"].values]
    ax.barh(y_vals, ok["phi"].values, color=colors, alpha=0.7, height=0.7)
    ax.axvline(0, color="black", lw=0.8)
    labels = [
        f"{r['subject']}/{r['session'][:5]}/{r['condition'][:4]}/{r['threshold']}/{r['outcome'][:7]}"
        for _, r in ok.iterrows()
    ]
    ax.set_yticks(y_vals)
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_xlabel("Phi coefficient (effect size)")
    ax.set_title("SPT6: Barrier-prediction effect sizes\n(red = uncorrected p<0.05)")

    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="red", label="Uncorr p<0.05"),
                        Patch(color="steelblue", label="NS")], fontsize=7)
    plt.tight_layout()
    save_csv_backed_figure(fig, ok[["subject", "session", "condition", "threshold", "outcome",
                                    "phi", "fisher_p"]],
                           "spt6_effect_size_forest", root)


def write_report(models_df: pd.DataFrame, threshold_df: pd.DataFrame) -> None:
    ok = models_df[models_df["n_violation_blocks"] > 0].copy()

    # Stats
    n_total = len(models_df)
    n_zero_viol = int((models_df["n_violation_blocks"] == 0).sum())
    n_nonzero = int((models_df["n_violation_blocks"] > 0).sum())

    if ok.empty or "fisher_p" not in ok.columns:
        (ROOT / "outputs" / "reports" / "spt6_results.md").write_text(
            "# SPT6 Results\n\nNo violation blocks detected.\n", encoding="utf-8"
        )
        return

    ok_p = ok.dropna(subset=["fisher_p"])
    n_sig_uncorr = int(ok_p["sig_uncorrected"].sum()) if "sig_uncorrected" in ok_p else 0
    n_sig_fdr = int(ok_p["sig_fdr"].sum()) if "sig_fdr" in ok_p else 0
    n_sig_bf = int(ok_p["sig_bonferroni"].sum()) if "sig_bonferroni" in ok_p else 0
    mean_phi = float(ok["phi"].dropna().mean()) if not ok["phi"].dropna().empty else np.nan
    n_tests_corrected = int(ok_p["fisher_p"].notna().sum())
    bonf_threshold = 0.05 / n_tests_corrected if n_tests_corrected > 0 else np.nan

    # Significant results
    if "sig_fdr" in ok_p.columns:
        sig_rows = ok_p[ok_p["sig_fdr"]].sort_values("fisher_p")
    else:
        sig_rows = pd.DataFrame()
    sig_uncorr_rows = ok_p[ok_p.get("sig_uncorrected", False)] if n_sig_uncorr > 0 else pd.DataFrame()

    report = f"""# SPT6 Results: Barrier-Prediction Analysis (Revised)

Generated: {utc_now()}

## Method (revised from original)

Original problem: Thresholds were computed on the high-resolution (256 Hz) envelope.
Block means (4-second windows) were almost never above these instantaneous percentiles
because averaging dramatically smooths peaks. Result: violation_rate ≈ 0 for most tests.

**Fix**: Thresholds now computed on the DISTRIBUTION OF BLOCK MEANS (not the raw envelope).
The p75 block-mean threshold guarantees ~25% of blocks are labelled as violations,
ensuring the analysis has statistical power.

Each 4-second block is assigned:
- violation indicator (1 = block-mean HB > threshold)
- outcome: SMR increase in next block / HB decrease in next block

Tests: Fisher exact test + permutation test + phi coefficient.
Multiple testing: Benjamini-Hochberg FDR + Bonferroni correction.

## Summary

- Total test combinations (subject × session × condition × threshold × outcome): {n_total}
- Combinations with zero violation blocks (untestable): {n_zero_viol}
- Combinations with ≥1 violation block (testable): {n_nonzero}
- Tests with sufficient data for p-value: {n_tests_corrected}
- Bonferroni threshold: 0.05 / {n_tests_corrected} = {bonf_threshold:.5f}

## Multiple testing correction results

| Correction | N significant |
|---|---|
| Uncorrected (p < 0.05) | {n_sig_uncorr} / {n_tests_corrected} |
| FDR-corrected (q < 0.05) | {n_sig_fdr} / {n_tests_corrected} |
| Bonferroni-corrected (p < 0.05/N) | {n_sig_bf} / {n_tests_corrected} |

## Effect sizes

Mean phi coefficient across all testable combinations: {mean_phi:.3f}
(phi = 0: no association; phi = 0.1: small; phi = 0.3: medium; phi = 0.5: large)

"""

    if n_sig_fdr > 0 and not sig_rows.empty:
        report += "## FDR-significant results\n\n"
        report += "| Subject | Session | Condition | Threshold | Outcome | N_blocks | Viol_rate | phi | Fisher_p | FDR_p |\n"
        report += "|---|---|---|---|---|---|---|---|---|---|\n"
        for _, row in sig_rows.iterrows():
            report += (f"| {row['subject']} | {row['session']} | {row['condition']} | "
                       f"{row['threshold']} | {row['outcome']} | {row.get('n_blocks', '?')} | "
                       f"{row['violation_rate']:.2f} | {row.get('phi', np.nan):.3f} | "
                       f"{row['fisher_p']:.4f} | {row['fisher_p_fdr']:.4f} |\n")
        report += "\n"
    elif n_sig_uncorr > 0:
        report += "## Uncorrected significant results (NOT surviving FDR correction)\n\n"
        report += "| Subject | Session | Condition | Threshold | Outcome | N_blocks | Viol_rate | phi | Fisher_p | FDR_p |\n"
        report += "|---|---|---|---|---|---|---|---|---|---|\n"
        for _, row in sig_uncorr_rows.iterrows():
            fdr_p = row.get("fisher_p_fdr", np.nan)
            report += (f"| {row['subject']} | {row['session']} | {row['condition']} | "
                       f"{row['threshold']} | {row['outcome']} | {row.get('n_blocks', '?')} | "
                       f"{row['violation_rate']:.2f} | {row.get('phi', np.nan):.3f} | "
                       f"{row['fisher_p']:.4f} | {fdr_p:.4f if not np.isnan(fdr_p) else 'NaN'} |\n")
        report += "\n"
    else:
        report += "## Significant results\n\nNone at any correction level.\n\n"

    report += f"""## Interpretation

"""
    if n_sig_fdr > 0:
        report += (
            f"After FDR correction, {n_sig_fdr} result(s) survive at q < 0.05. "
            "These constitute positive evidence for barrier prediction. "
            "Interpretation requires caution given the small n=5 sample.\n"
        )
    else:
        report += (
            f"**NULL RESULT**: After FDR correction ({n_sig_fdr}/{{n_tests_corrected}} significant at q<0.05), "
            f"NO tests survive correction.\n"
            + (f"Even the {n_sig_uncorr} uncorrected significant result(s) do NOT survive FDR correction. "
               if n_sig_uncorr > 0 else "No uncorrected results are significant either. ")
            + "\n\n"
            + "The barrier-prediction analysis provides **no reliable evidence** that high-beta violations "
            + "at time t predict next-block SMR dynamics (smr_increase) or barrier-adherence (admissible_next).\n\n"
            + "This is a NULL result. It should be reported as such.\n\n"
            + "Possible reasons for null result:\n"
            + "1. The barrier constraint h_beta(y) = y_barrier − y ≥ 0 is not empirically active in this dataset.\n"
            + "2. The n=5 subjects / 2 sessions are insufficient to detect small effects.\n"
            + "3. The block-level sequential prediction model does not capture the relevant dynamics.\n"
            + "4. High-beta violations may not follow the modelled pattern in real neurofeedback EEG.\n"
        )

    report += f"""
## Claim status

Q5 (barrier-prediction claim): **NOT SUPPORTED** by this analysis.
The empirical barrier-prediction test yields a null result after proper multiple testing correction.
This does not invalidate the theoretical framework but means the empirical test of Q5 is inconclusive.

**DO NOT CLAIM**: "High-beta violations predict subsequent SMR changes."
**SHOULD STATE**: "The barrier-prediction test was underpowered in this small dataset (n=5) and
yielded a null result after FDR correction ({n_sig_fdr}/{n_tests_corrected} tests significant at q<0.05)."

Generated: {utc_now()}
"""

    (ROOT / "outputs" / "reports" / "spt6_results.md").write_text(report, encoding="utf-8")


def main() -> None:
    ensure_repo_structure(ROOT)
    tbl_dir = ROOT / "outputs" / "tables"
    rep_dir = ROOT / "outputs" / "reports"

    edf_files = sorted(RAW_ROOT.glob("sub-*/ses-*/eeg/*_eeg.edf")) if RAW_ROOT.exists() else []
    print(f"SPT6 Revised: {len(edf_files)} EDF files.")

    conditions = ["rest", "task"]  # interval blocks often too short for block analysis
    all_rows = []

    for edf_path in edf_files:
        subject, session = parse_subject_session(edf_path)
        for cond in conditions:
            block_df = compute_block_series(edf_path, cond)
            if block_df is None:
                print(f"  Skipped {subject}/{session}/{cond}")
                continue
            print(f"  {subject}/{session}/{cond}: {len(block_df)} blocks, "
                  f"viol_p75_rate={block_df['viol_p75'].mean():.2f}")
            rows = analyze_barrier_prediction(block_df, subject, session, cond)
            all_rows.extend(rows)

    if not all_rows:
        print("No barrier prediction results.")
        models_df = pd.DataFrame()
    else:
        models_df = pd.DataFrame(all_rows)
        models_df = apply_fdr(models_df)

    models_df.to_csv(tbl_dir / "spt6_barrier_prediction_models.csv", index=False)

    # Non-zero summary
    if not models_df.empty:
        nonzero = models_df[models_df["n_violation_blocks"] > 0].copy()
        nonzero.to_csv(tbl_dir / "spt6_nonzero_viol_summary.csv", index=False)
    else:
        nonzero = pd.DataFrame()
        nonzero.to_csv(tbl_dir / "spt6_nonzero_viol_summary.csv", index=False)

    # Threshold sensitivity: mean phi by threshold
    if not models_df.empty and "phi" in models_df.columns:
        thr_sens = (models_df[models_df["n_violation_blocks"] > 0]
                    .groupby(["threshold", "outcome"])[["phi", "fisher_p", "violation_rate"]]
                    .agg(["mean", "std", "count"])
                    .reset_index())
        thr_sens.columns = ["_".join(c).strip("_") for c in thr_sens.columns]
        thr_sens.to_csv(tbl_dir / "spt6_threshold_sensitivity.csv", index=False)
    else:
        pd.DataFrame().to_csv(tbl_dir / "spt6_threshold_sensitivity.csv", index=False)

    print("SPT6 Revised: Creating figures...")
    if not models_df.empty:
        make_barrier_prediction_figure(models_df, ROOT)
        make_effect_size_forest(models_df, ROOT)

    write_report(models_df, pd.DataFrame())
    print("SPT6 Revised done.")


if __name__ == "__main__":
    main()
