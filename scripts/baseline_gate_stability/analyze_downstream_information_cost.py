#!/usr/bin/env python3
"""Reuse verified decoder outputs and add the completed M5 quality mask."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from scripts.downstream_decoder_validation.run_decoder_validation import (  # noqa: E402
    BOOT_SEED,
    DATASETS,
    MIN_PER_CLASS,
    PERM_SEED,
    SEEDS,
    extract_session,
    fit_score,
    valid_selection,
)

OUT = ROOT / "results" / "baseline_gate_stability"
DOWN = OUT / "downstream"
EXT_DECISIONS = OUT / "external_monitor" / "decisions_by_window.csv"
SOURCE = ROOT / "results" / "downstream_decoder_validation"
CKPT = OUT / "checkpoints" / "downstream_decoder_features"
FOLD_CKPT = OUT / "checkpoints" / "downstream_decoder_folds"
POLICY_MAP = {
    "ALL": "M0_NO_GATE",
    "HB": "M1_HIGH_BETA",
    "BBHF": "M2_BROADBAND_HIGH_FREQUENCY",
    "AMPLITUDE_150": "M3_AMPLITUDE_150",
    "NFSQI_FULL": "M4_NFSQI_FULL_QUALITY",
}
M5 = "M5_RIEMANNIAN_POTATO"


def atomic_csv(frame: pd.DataFrame, path: Path, compression: str | None = None) -> None:
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=False, compression=compression)
    temporary.replace(path)


def locate_edf(dataset: str, subject: str, session: str) -> Path:
    matches = list((ROOT / "data" / "raw" / "openneuro" / dataset).glob(
        f"{subject}/{session}/eeg/*_task-smrbmi_eeg.edf"
    ))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one EDF for {dataset}/{subject}/{session}; found {len(matches)}")
    return matches[0]


def build_decoder_cache(folds: pd.DataFrame, decisions: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    sessions = folds[["dataset", "subject", "train_session"]].rename(columns={"train_session": "session"})
    sessions = pd.concat([
        sessions,
        folds[["dataset", "subject", "test_session"]].rename(columns={"test_session": "session"}),
    ]).drop_duplicates().sort_values(["dataset", "subject", "session"])
    for sequence, row in enumerate(sessions.itertuples(index=False), 1):
        checkpoint = CKPT / f"{row.dataset}_{row.subject}_{row.session}_decoder.csv.gz"
        if checkpoint.exists() and checkpoint.stat().st_size > 100:
            frame = pd.read_csv(checkpoint)
            status = "reused"
        else:
            frame, _audit = extract_session(locate_edf(row.dataset, row.subject, row.session))
            mask = decisions.loc[
                (decisions.dataset == row.dataset)
                & (decisions.participant == row.subject)
                & (decisions.session == row.session),
                ["condition", "window_id", "decision", "z_score", "reason_codes"],
            ].copy()
            canonical = pd.read_csv(
                OUT / "checkpoints" / "features" / f"{row.dataset}_{row.subject}_{row.session}_canonical.csv.gz",
                usecols=["condition", "window_start_s", "window_id"],
            )
            key = canonical.merge(mask, on=["condition", "window_id"], how="left", validate="one_to_one")
            frame = frame.merge(
                key,
                left_on=["event_label", "time_s"],
                right_on=["condition", "window_start_s"],
                how="left",
                validate="one_to_one",
            )
            if frame.decision.isna().any():
                raise RuntimeError(f"M5 decision alignment failed for {row.dataset}/{row.subject}/{row.session}")
            frame["decision"] = frame.decision.astype(bool)
            atomic_csv(frame, checkpoint, "gzip")
            status = "created"
        frames.append(frame)
        print(f"[decoder features {sequence}/{len(sessions)}] {row.dataset}_{row.subject}_{row.session} {status}", flush=True)
    return pd.concat(frames, ignore_index=True)


def run_m5_folds(windows: pd.DataFrame, folds: pd.DataFrame, source_retention: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    natural_rows: list[dict[str, object]] = []
    count_rows: list[dict[str, object]] = []
    retention_rows: list[dict[str, object]] = []
    nonviable_rows: list[dict[str, object]] = []
    decoder_cols = [column for column in windows if column.startswith("decoder_")]
    for sequence, fold in enumerate(folds.itertuples(index=False), 1):
        checkpoint = FOLD_CKPT / f"{fold.fold_id}_m5.npz"
        train = windows.loc[
            (windows.dataset == fold.dataset) & (windows.subject == fold.subject)
            & (windows.session == fold.train_session)
        ].reset_index(drop=True)
        test = windows.loc[
            (windows.dataset == fold.dataset) & (windows.subject == fold.subject)
            & (windows.session == fold.test_session)
        ].reset_index(drop=True)
        finite = np.isfinite(train[decoder_cols]).all(axis=1)
        selected = train.loc[finite & train.decision].copy()
        for label, label_name in ((0, "rest"), (1, "task")):
            available = int((train.y == label).sum())
            kept = int((selected.y == label).sum())
            retention_rows.append({
                "fold_id": fold.fold_id, "dataset": fold.dataset, "subject": fold.subject,
                "train_session": fold.train_session, "test_session": fold.test_session,
                "monitor": M5, "class": label_name, "retained_windows": kept,
                "available_windows": available,
                "retention_proportion": kept / available if available else np.nan,
            })
        if not valid_selection(selected):
            nonviable_rows.append({
                "fold_id": fold.fold_id, "dataset": fold.dataset, "subject": fold.subject,
                "train_session": fold.train_session, "test_session": fold.test_session,
                "monitor": M5, "analysis": "natural",
                "reason": "fewer than 10 retained windows in at least one class", "status": "nonviable",
            })
            continue
        started = time.perf_counter()
        score, _ = fit_score(selected, test, decoder_cols)
        natural_rows.append({
            "fold_id": fold.fold_id, "dataset": fold.dataset, "subject": fold.subject,
            "train_session": fold.train_session, "test_session": fold.test_session,
            "monitor": M5, "analysis": "natural", "seed": np.nan, "status": "valid",
            "runtime_seconds": time.perf_counter() - started, **score,
        })
        targets = source_retention.loc[
            (source_retention.fold_id == fold.fold_id) & (source_retention.policy == "NFSQI_FULL")
        ].set_index("class").retained_windows.to_dict()
        failed = False
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            chosen: list[int] = []
            for label, label_name in ((0, "rest"), (1, "task")):
                pool = selected.index[selected.y == label].to_numpy()
                target = int(targets.get(label_name, 0))
                if target < MIN_PER_CLASS or len(pool) < target:
                    failed = True
                    break
                chosen.extend(rng.choice(pool, target, replace=False).tolist())
            if failed:
                nonviable_rows.append({
                    "fold_id": fold.fold_id, "dataset": fold.dataset, "subject": fold.subject,
                    "train_session": fold.train_session, "test_session": fold.test_session,
                    "monitor": M5, "analysis": "count_matched",
                    "reason": "M4 target or M5 pool lacks 10 windows per class", "status": "nonviable",
                })
                break
            score, _ = fit_score(selected.loc[chosen], test, decoder_cols)
            count_rows.append({
                "fold_id": fold.fold_id, "dataset": fold.dataset, "subject": fold.subject,
                "train_session": fold.train_session, "test_session": fold.test_session,
                "monitor": M5, "seed": seed, "n_rest": int(targets["rest"]),
                "n_task": int(targets["task"]), "status": "valid", **score,
            })
        np.savez_compressed(checkpoint, natural=len(natural_rows), count=len(count_rows), failed=failed)
        print(f"[M5 decoder {sequence}/{len(folds)}] {fold.fold_id}", flush=True)
    return tuple(pd.DataFrame(rows) for rows in (natural_rows, count_rows, retention_rows, nonviable_rows))


def participant_results(fold_results: pd.DataFrame) -> pd.DataFrame:
    metrics = [column for column in ("balanced_accuracy", "roc_auc", "accuracy", "macro_f1", "sensitivity", "specificity", "log_loss", "brier_score") if column in fold_results]
    return fold_results.loc[fold_results.status == "valid"].groupby(
        ["dataset", "subject", "monitor", "analysis"], as_index=False
    )[metrics].mean()


def make_contrasts(subjects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rng_boot = np.random.default_rng(BOOT_SEED)
    rng_perm = np.random.default_rng(PERM_SEED)
    for analysis in sorted(subjects.analysis.unique()):
        data = subjects.loc[subjects.analysis == analysis]
        wide = data.pivot_table(index=["dataset", "subject"], columns="monitor", values="balanced_accuracy")
        for monitor in [column for column in wide if column != "M0_NO_GATE"]:
            diff = (wide[monitor] - wide["M0_NO_GATE"]).dropna().to_numpy()
            if not len(diff):
                continue
            boot = np.array([rng_boot.choice(diff, len(diff), replace=True).mean() for _ in range(5000)])
            perm = np.array([np.mean(diff * rng_perm.choice((-1, 1), len(diff))) for _ in range(5000)])
            rows.append({
                "dataset": "pooled", "analysis": analysis, "contrast": f"{monitor} minus M0_NO_GATE",
                "mean_paired_difference": float(diff.mean()), "median_paired_difference": float(np.median(diff)),
                "bootstrap_ci_low": float(np.quantile(boot, 0.025)), "bootstrap_ci_high": float(np.quantile(boot, 0.975)),
                "p_value": float((np.sum(np.abs(perm) >= abs(diff.mean())) + 1) / 5001),
                "n_participants": len(diff), "status": "valid",
            })
    return pd.DataFrame(rows)


def main() -> int:
    for directory in (DOWN, CKPT, FOLD_CKPT):
        directory.mkdir(parents=True, exist_ok=True)
    decisions = pd.read_csv(EXT_DECISIONS)
    folds = pd.read_csv(SOURCE / "fold_definition.csv")
    source_natural = pd.read_csv(SOURCE / "decoder_results_all_folds.csv")
    source_count = pd.read_csv(SOURCE / "count_matched_results.csv")
    source_retention = pd.read_csv(SOURCE / "retention_by_fold.csv")
    source_nonviable = pd.read_csv(SOURCE / "nonviable_folds.csv")

    base = source_natural.loc[source_natural.policy.isin(POLICY_MAP)].copy()
    base["monitor"] = base.policy.map(POLICY_MAP)
    base = base.drop(columns="policy")
    base_count = source_count.loc[source_count.policy.isin(POLICY_MAP)].copy()
    base_count["monitor"] = base_count.policy.map(POLICY_MAP)
    base_count = base_count.drop(columns="policy")
    base_retention = source_retention.loc[source_retention.policy.isin(POLICY_MAP)].copy()
    base_retention["monitor"] = base_retention.policy.map(POLICY_MAP)
    base_retention = base_retention.drop(columns="policy")
    base_nonviable = source_nonviable.loc[source_nonviable.policy.isin(POLICY_MAP)].copy()
    base_nonviable["monitor"] = base_nonviable.policy.map(POLICY_MAP)
    base_nonviable = base_nonviable.drop(columns="policy")

    windows = build_decoder_cache(folds, decisions)
    m5_natural, m5_count, m5_retention, m5_nonviable = run_m5_folds(windows, folds, source_retention)
    if not m5_count.empty:
        m5_summary = m5_count.groupby(
            ["fold_id", "dataset", "subject", "train_session", "test_session", "monitor", "status"], as_index=False
        )[["balanced_accuracy", "roc_auc", "accuracy", "macro_f1", "sensitivity", "specificity", "log_loss", "brier_score"]].mean()
        m5_summary["analysis"] = "count_matched"
        m5_summary["seed"] = np.nan
        m5_results = pd.concat([m5_natural, m5_summary], ignore_index=True, sort=False)
    else:
        m5_results = m5_natural
    monitor_results = pd.concat([base, m5_results], ignore_index=True, sort=False)
    count_comparison = pd.concat([base_count, m5_count], ignore_index=True, sort=False)
    retention = pd.concat([base_retention, m5_retention], ignore_index=True, sort=False)
    nonviable = pd.concat([base_nonviable, m5_nonviable], ignore_index=True, sort=False)
    monitor_results.to_csv(DOWN / "monitor_decoder_results.csv", index=False)
    count_comparison.to_csv(DOWN / "count_matched_results.csv", index=False)
    retention.to_csv(DOWN / "retention_results.csv", index=False)
    nonviable.to_csv(DOWN / "nonviable_folds.csv", index=False)
    subjects = participant_results(monitor_results)
    contrasts = make_contrasts(subjects)
    contrasts.to_csv(DOWN / "monitor_decoder_contrasts.csv", index=False)
    natural = contrasts.loc[contrasts.analysis == "natural"]
    lines = [
        "# Downstream information-cost report", "",
        "M0-M4 reuse the verified event labels, session-held-out folds, decoder features, models, and seeds. "
        "M5 is added as a completed training-only quality mask; every test session remains unfiltered.", "",
        "Count matching uses the frozen M4 class-specific retained counts, matching the verified comparator analysis.", "",
    ]
    for row in natural.itertuples(index=False):
        lines.append(
            f"- {row.contrast}: {row.mean_paired_difference:+.4f} balanced accuracy "
            f"(95% bootstrap CI {row.bootstrap_ci_low:+.4f} to {row.bootstrap_ci_high:+.4f}; p={row.p_value:.4f}; n={row.n_participants})."
        )
    lines.extend(["", f"Nonviable fold-monitor-analysis records: {len(nonviable)}."])
    (DOWN / "downstream_information_cost_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[done] {len(monitor_results)} monitor-fold summaries; {len(count_comparison)} seeded count-matched fits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
