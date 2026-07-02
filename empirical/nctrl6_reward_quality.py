"""NCTRL6: Closed-loop reward-quality state analysis.

Uses proxy reward criteria (no direct feedback markers in ds004446):
  - Clean target: SMR > session-median AND HB < session-median AND broad < broad-median
  - Noisy target: SMR > session-median AND (HB > session-median OR broad > broad-median)
  - Clean non-target: SMR ≤ median AND HB < median
  - Noisy non-target: SMR ≤ median AND HB ≥ median

Computes per-block (4-s windows):
  - State occupancy fractions
  - Transition probabilities between states
  - False-reward risk (noisy-target fraction / total-reward fraction)
  - Reward-state purity (clean-target / all-reward)

Outputs:
  outputs/tables/nctrl6_reward_quality_states.csv
  outputs/tables/nctrl6_state_transition_probabilities.csv
  outputs/figures/nctrl6_reward_quality_state_space.*
  outputs/figures/nctrl6_state_transition_panel.*
  outputs/reports/nctrl6_results.md
  outputs/logs/nctrl6_empirical_processing.log
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
import mne

from utils.paths import ensure_repo_structure
from utils.plotting import save_csv_backed_figure, set_style
from utils.signal_metrics import band_envelope

DATASET_ID = "ds004446"
RAW_ROOT = ROOT / "data" / "raw" / "openneuro" / DATASET_ID
CHANNELS = ["E36", "E104", "E128"]
CONDITIONS = ["rest", "task"]
SMR_BAND = (12.0, 15.0)
HB_BAND = (20.0, 30.0)
BROAD_BAND = (30.0, 45.0)
BLOCK_S = 4.0

STATES = ["clean_target", "noisy_target", "clean_nontarget", "noisy_nontarget"]
STATE_COLORS = {
    "clean_target": "#1ABC9C",
    "noisy_target": "#F39C12",
    "clean_nontarget": "#3498DB",
    "noisy_nontarget": "#E74C3C",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_sub_ses(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    return (m.group(1), m.group(2)) if m else ("", "")


def load_segment(edf_path: Path, condition: str) -> tuple[np.ndarray, float]:
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
    n_s = data.shape[1]
    segs = []
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


def classify_blocks(smr_blocks: np.ndarray, hb_blocks: np.ndarray,
                    broad_blocks: np.ndarray) -> np.ndarray:
    """Classify each block into one of 4 states using median thresholds."""
    smr_thr = np.median(smr_blocks)
    hb_thr = np.median(hb_blocks)
    broad_thr = np.median(broad_blocks)

    smr_high = smr_blocks > smr_thr
    hb_high = hb_blocks > hb_thr
    broad_high = broad_blocks > broad_thr
    noisy = hb_high | broad_high

    state = np.full(len(smr_blocks), "noisy_nontarget", dtype=object)
    state[smr_high & ~noisy] = "clean_target"
    state[smr_high & noisy] = "noisy_target"
    state[~smr_high & ~noisy] = "clean_nontarget"
    # noisy_nontarget already set
    return state


def compute_transition_matrix(states: np.ndarray) -> pd.DataFrame:
    """Compute 4×4 transition probability matrix."""
    mat = pd.DataFrame(0, index=STATES, columns=STATES, dtype=float)
    for a, b in zip(states[:-1], states[1:]):
        if a in STATES and b in STATES:
            mat.loc[a, b] += 1.0
    row_sums = mat.sum(axis=1)
    for s in STATES:
        if row_sums[s] > 0:
            mat.loc[s] /= row_sums[s]
    return mat


def analyze_reward_quality(edf_path: Path, condition: str) -> tuple[dict, pd.DataFrame]:
    sub, ses = parse_sub_ses(edf_path)
    x, fs = load_segment(edf_path, condition)
    if x.size < int(fs * 12):
        return {}, pd.DataFrame()

    x = x - np.mean(x)
    smr_env = band_envelope(x, fs, SMR_BAND)
    hb_env = band_envelope(x, fs, HB_BAND)
    broad_env = band_envelope(x, fs, BROAD_BAND)

    block_n = int(BLOCK_S * fs)
    n_blocks = min(len(smr_env), len(hb_env), len(broad_env)) // block_n
    if n_blocks < 4:
        return {}, pd.DataFrame()

    smr_b = np.array([smr_env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])
    hb_b = np.array([hb_env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])
    broad_b = np.array([broad_env[b * block_n:(b + 1) * block_n].mean() for b in range(n_blocks)])

    states = classify_blocks(smr_b, hb_b, broad_b)
    trans = compute_transition_matrix(states)

    # Occupancies
    occ = {s: float(np.mean(states == s)) for s in STATES}
    # Reward-compatible blocks (SMR high)
    n_reward = int((states == "clean_target").sum() + (states == "noisy_target").sum())
    n_clean_target = int((states == "clean_target").sum())
    n_noisy_target = int((states == "noisy_target").sum())
    false_reward_risk = n_noisy_target / n_reward if n_reward > 0 else np.nan
    reward_purity = n_clean_target / n_reward if n_reward > 0 else np.nan

    row = {
        "subject": sub, "session": ses, "condition": condition,
        "n_blocks": n_blocks,
        "occ_clean_target": occ["clean_target"],
        "occ_noisy_target": occ["noisy_target"],
        "occ_clean_nontarget": occ["clean_nontarget"],
        "occ_noisy_nontarget": occ["noisy_nontarget"],
        "false_reward_risk": false_reward_risk,
        "reward_purity": reward_purity,
        "total_reward_frac": n_reward / n_blocks,
        # Transitions of interest
        "trans_clean_to_clean": trans.loc["clean_target", "clean_target"],
        "trans_noisy_to_clean": trans.loc["noisy_target", "clean_target"],
        "trans_clean_to_noisy": trans.loc["clean_target", "noisy_target"],
        "trans_noisy_to_noisy": trans.loc["noisy_target", "noisy_target"],
    }

    # Also return block-level data
    block_df = pd.DataFrame({
        "subject": sub, "session": ses, "condition": condition,
        "block_idx": np.arange(n_blocks),
        "smr_mean": smr_b, "hb_mean": hb_b, "broad_mean": broad_b,
        "state": states,
    })
    return row, block_df


def make_state_space_figure(state_df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))

    for ses, row_idx in zip(["ses-01", "ses-08"], [0, 1]):
        sdf_raw = state_df[state_df["session"] == ses]
        if sdf_raw.empty:
            continue
        # Aggregate across conditions per subject (mean occupancy)
        num_cols = sdf_raw.select_dtypes(include="number").columns.tolist()
        sdf = sdf_raw.groupby("subject", sort=True)[num_cols].mean().reset_index()

        # Panel 1: State occupancy breakdown
        ax = axes[row_idx, 0]
        subjects = sorted(sdf["subject"].unique())
        occ_cols = ["occ_clean_target", "occ_noisy_target", "occ_clean_nontarget", "occ_noisy_nontarget"]
        col_labels = ["clean_target", "noisy_target", "clean_nontarget", "noisy_nontarget"]
        x_pos = np.arange(len(subjects))
        bottoms = np.zeros(len(subjects))
        for col, lab in zip(occ_cols, col_labels):
            vals = sdf.set_index("subject").reindex(subjects)[col].fillna(0).values
            ax.bar(x_pos, vals, bottom=bottoms, color=STATE_COLORS.get(lab.replace("occ_", ""), "gray"),
                   label=lab, alpha=0.85)
            bottoms += vals
        ax.set_xticks(x_pos)
        ax.set_xticklabels(subjects, rotation=30, ha="right", fontsize=7)
        ax.set_ylabel("Fraction of blocks")
        ax.set_title(f"({['A','D'][row_idx]}) State occupancy {ses}")
        if row_idx == 0:
            ax.legend(fontsize=6, ncol=1)

        # Panel 2: False-reward risk
        ax = axes[row_idx, 1]
        sdf_ok = sdf.dropna(subset=["false_reward_risk"])
        ax.bar(range(len(sdf_ok)), sdf_ok["false_reward_risk"].values,
               color=["#E74C3C" if v > 0.4 else "#2ECC71" for v in sdf_ok["false_reward_risk"].values],
               alpha=0.8)
        ax.set_xticks(range(len(sdf_ok)))
        ax.set_xticklabels(sdf_ok["subject"].values, rotation=30, ha="right", fontsize=7)
        ax.axhline(0.5, color="black", ls="--", lw=0.8, label="50% risk")
        ax.set_ylabel("False-reward risk\n(noisy target / all reward)")
        ax.set_title(f"({['B','E'][row_idx]}) False-reward risk {ses}")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=7)

        # Panel 3: Reward purity
        ax = axes[row_idx, 2]
        sdf_ok2 = sdf.dropna(subset=["reward_purity"])
        ax.bar(range(len(sdf_ok2)), sdf_ok2["reward_purity"].values,
               color="steelblue", alpha=0.8)
        ax.set_xticks(range(len(sdf_ok2)))
        ax.set_xticklabels(sdf_ok2["subject"].values, rotation=30, ha="right", fontsize=7)
        ax.axhline(0.5, color="black", ls="--", lw=0.8, label="50% purity")
        ax.set_ylabel("Reward purity\n(clean target / all reward)")
        ax.set_title(f"({['C','F'][row_idx]}) Reward purity {ses}")
        ax.set_ylim(0, 1)
        ax.legend(fontsize=7)

    fig.suptitle("NCTRL6: Reward-quality state analysis (ds004446)", fontsize=10, fontweight="bold")
    plt.tight_layout()
    save_csv_backed_figure(
        fig,
        state_df[["subject", "session", "condition", "occ_clean_target", "occ_noisy_target",
                   "false_reward_risk", "reward_purity", "total_reward_frac"]],
        "nctrl6_reward_quality_state_space", root
    )


def make_transition_figure(trans_rows: list[pd.DataFrame], state_df: pd.DataFrame, root: Path) -> None:
    set_style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

    # A: Noisy-to-clean transition probability change
    num_cols = state_df.select_dtypes(include="number").columns.tolist()
    s01 = state_df[state_df["session"] == "ses-01"].groupby("subject")[num_cols].mean()
    s08 = state_df[state_df["session"] == "ses-08"].groupby("subject")[num_cols].mean()
    common = s01.index.intersection(s08.index)
    if not common.empty:
        delta_ntoc = s08.loc[common, "trans_noisy_to_clean"] - s01.loc[common, "trans_noisy_to_clean"]
        axes[0].bar(range(len(delta_ntoc)), delta_ntoc.values,
                     color=["#27AE60" if v > 0 else "#E74C3C" for v in delta_ntoc.values], alpha=0.8)
        axes[0].set_xticks(range(len(delta_ntoc)))
        axes[0].set_xticklabels(common.tolist(), rotation=30, ha="right", fontsize=7)
        axes[0].axhline(0, color="black", ls="--", lw=0.8)
        axes[0].set_ylabel("Δ P(noisy→clean)")
        axes[0].set_title("(A) Change in noisy→clean\ntransition probability")

    # B: Clean-to-clean (self-return) probability
    ax = axes[1]
    for ses, col in zip(["ses-01", "ses-08"], ["#1f77b4", "#ff7f0e"]):
        sdf = state_df[state_df["session"] == ses]
        ax.scatter(range(len(sdf)), sdf["trans_clean_to_clean"].values,
                   color=col, label=ses, s=50, alpha=0.8)
    ax.set_ylabel("P(clean→clean)")
    ax.set_title("(B) Self-stability of clean-target state")
    ax.legend(fontsize=7)
    ax.set_ylim(0, 1)

    # C: False-reward change ses-01 → ses-08
    ax = axes[2]
    if not common.empty:
        delta_fr = s08.loc[common, "false_reward_risk"] - s01.loc[common, "false_reward_risk"]
        ax.bar(range(len(delta_fr)), delta_fr.values,
                color=["#E74C3C" if v > 0 else "#27AE60" for v in delta_fr.values], alpha=0.8)
        ax.set_xticks(range(len(delta_fr)))
        ax.set_xticklabels(common.tolist(), rotation=30, ha="right", fontsize=7)
        ax.axhline(0, color="black", ls="--", lw=0.8)
        ax.set_ylabel("Δ False-reward risk")
        ax.set_title("(C) Change in false-reward risk\n[− = improved quality]")

    fig.suptitle("NCTRL6: State transition analysis", fontsize=10)
    plt.tight_layout()
    save_csv_backed_figure(
        fig,
        state_df[["subject", "session", "condition", "trans_clean_to_clean",
                   "trans_noisy_to_clean", "false_reward_risk"]],
        "nctrl6_state_transition_panel", root
    )


def write_report(state_df: pd.DataFrame) -> None:
    s01 = state_df[state_df["session"] == "ses-01"]
    s08 = state_df[state_df["session"] == "ses-08"]
    fr_s01 = s01["false_reward_risk"].dropna().mean()
    fr_s08 = s08["false_reward_risk"].dropna().mean()
    purity_s01 = s01["reward_purity"].dropna().mean()
    purity_s08 = s08["reward_purity"].dropna().mean()

    report = f"""# NCTRL6 Results: Closed-Loop Reward-Quality Analysis

Generated: {utc_now()}

## Method

Proxy reward states (no direct feedback markers in ds004446):
- Clean target: SMR > session-median AND HB < session-median AND broad < broad-median
- Noisy target: SMR > session-median AND (HB or broad above median)
- Clean non-target: SMR ≤ median AND HB < median
- Noisy non-target: SMR ≤ median AND HB or broad above median

Block size: {BLOCK_S} s. State transitions computed as empirical probabilities.

## Key results

### Mean state occupancies (rest condition)
ses-01: clean_target={s01["occ_clean_target"].mean():.3f}, noisy_target={s01["occ_noisy_target"].mean():.3f}
ses-08: clean_target={s08["occ_clean_target"].mean():.3f}, noisy_target={s08["occ_noisy_target"].mean():.3f}

### Reward-state quality
False-reward risk: ses-01 = {fr_s01:.3f} | ses-08 = {fr_s08:.3f}
Change: {fr_s08 - fr_s01:+.3f} {"(risk decreased = improved quality)" if fr_s08 < fr_s01 else "(risk increased or unchanged)"}

Reward purity: ses-01 = {purity_s01:.3f} | ses-08 = {purity_s08:.3f}
Change: {purity_s08 - purity_s01:+.3f} {"(purity increased = improved quality)" if purity_s08 > purity_s01 else "(purity decreased or unchanged)"}

## Interpretation

{"The false-reward risk decreased from ses-01 to ses-08 (mean Δ=" + f"{fr_s08-fr_s01:+.3f}), suggesting that high-beta inhibition improved reward-state purity — more reward signals accompanied by low HB/broadband noise." if fr_s08 < fr_s01 else "The false-reward risk did not consistently decrease from ses-01 to ses-08. Reward-state quality was not reliably improved by the training session."}

Note: These classifications use proxy criteria (median-based thresholds). Without direct
reward/inhibit timing markers from the neurofeedback software, true reward-state analysis
cannot be performed. Results should be interpreted as proxy estimates only.

Generated: {utc_now()}
"""
    (ROOT / "outputs" / "reports" / "nctrl6_results.md").write_text(report, encoding="utf-8")


def main() -> None:
    ensure_repo_structure(ROOT)
    tbl = ROOT / "outputs" / "tables"
    log_lines = [f"{utc_now()} NCTRL6 started."]

    edfs = sorted(RAW_ROOT.glob("sub-*/ses-*/eeg/*_eeg.edf")) if RAW_ROOT.exists() else []
    print(f"NCTRL6: {len(edfs)} EDF files.")

    state_rows = []
    block_rows = []
    trans_rows = []

    for edf in edfs:
        sub, ses = parse_sub_ses(edf)
        for cond in CONDITIONS:
            row, block_df = analyze_reward_quality(edf, cond)
            if row:
                state_rows.append(row)
                block_rows.append(block_df)
                log_lines.append(f"  {sub}/{ses}/{cond}: {row['n_blocks']} blocks")
            else:
                log_lines.append(f"  {sub}/{ses}/{cond}: skip")

    state_df = pd.DataFrame(state_rows)
    state_df.to_csv(tbl / "nctrl6_reward_quality_states.csv", index=False)

    # Aggregate transitions
    if block_rows:
        all_blocks = pd.concat(block_rows, ignore_index=True)
        # Compute transition probabilities per subject/session/condition
        trans_out = []
        for (sub, ses, cond), grp in all_blocks.groupby(["subject", "session", "condition"]):
            tmat = compute_transition_matrix(grp["state"].values)
            for src in STATES:
                for dst in STATES:
                    trans_out.append({
                        "subject": sub, "session": ses, "condition": cond,
                        "from_state": src, "to_state": dst,
                        "probability": float(tmat.loc[src, dst]),
                    })
        trans_df = pd.DataFrame(trans_out)
        trans_df.to_csv(tbl / "nctrl6_state_transition_probabilities.csv", index=False)
    else:
        pd.DataFrame().to_csv(tbl / "nctrl6_state_transition_probabilities.csv", index=False)

    print("NCTRL6: Creating figures...")
    if not state_df.empty:
        make_state_space_figure(state_df, ROOT)
        make_transition_figure([], state_df, ROOT)

    write_report(state_df)
    (ROOT / "outputs" / "logs" / "nctrl6_empirical_processing.log").write_text(
        "\n".join(log_lines), encoding="utf-8")
    print("NCTRL6 done.")


if __name__ == "__main__":
    main()
