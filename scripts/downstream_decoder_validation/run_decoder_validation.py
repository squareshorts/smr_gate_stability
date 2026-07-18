#!/usr/bin/env python3
"""Primary downstream decoder validation after the mandatory count gate passes."""
from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
from scipy.stats import median_abs_deviation
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, f1_score, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from empirical.nf_sqi_common import SENSORIMOTOR_CHANNELS, bandpower_from_psd, read_events_for_edf, welch_psd  # noqa: E402
from empirical.nf_sqi_t1_features import extract_window_features  # noqa: E402

mne.set_log_level("ERROR")
OUT = ROOT / "results" / "downstream_decoder_validation"
FIG = OUT / "figures"
DATASETS = ("ds004447", "ds004444", "ds004446")
BANDS = ((8.0, 12.0), (12.0, 15.0), (15.0, 20.0), (20.0, 30.0))
POLICIES = ("ALL", "HB", "BBHF", "NFSQI_NO_HB", "NFSQI_FULL", "AMPLITUDE_150")
SEEDS = tuple(range(20260716, 20260816))
BOOT_SEED, PERM_SEED = 20260717, 20260718
MIN_PER_CLASS = 10


def pct(series: pd.Series, value: float) -> float:
    return float(np.nanpercentile(series.to_numpy(dtype=float), value))


def extract_session(edf: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    raw = mne.io.read_raw_edf(edf, preload=True, verbose=False)
    channels = [name for name in SENSORIMOTOR_CHANNELS if name in raw.ch_names]
    if channels != SENSORIMOTOR_CHANNELS:
        raise ValueError(f"Canonical channel set unavailable: {edf}")
    raw.pick_channels(channels)
    fs = float(raw.info["sfreq"])
    events = read_events_for_edf(edf, raw.times[-1])
    state = np.full(raw.n_times, -1, dtype=np.int8)
    segments = np.full(raw.n_times, -1, dtype=np.int32)
    valid_events = events.loc[events["instruction"].astype(str).isin(["rest", "task"])].copy()
    for event_index, (_, event) in enumerate(valid_events.iterrows()):
        code = 0 if str(event["instruction"]) == "rest" else 1
        start = max(0, min(raw.n_times, int(round(float(event["onset_s"]) * fs))))
        stop = max(start, min(raw.n_times, int(round((float(event["onset_s"]) + float(event["duration_s"])) * fs))))
        state[start:stop] = code
        segments[start:stop] = event_index
    data = raw.get_data()
    subject, session = edf.parts[-4], edf.parts[-3]
    rows: list[dict[str, object]] = []
    counts = {"rest": 0, "task": 0, "transition": 0, "ambiguous": 0}
    previous_smr = np.nan
    win, hop = int(fs), int(fs * 0.5)
    for start in np.arange(0, data.shape[1] - win, hop):
        start, stop = int(start), int(start + win)
        samples = state[start:stop]
        task_fraction = float(np.mean(samples == 1))
        rest_fraction = float(np.mean(samples == 0))
        if task_fraction >= 0.95:
            label, y = "task", 1
        elif rest_fraction >= 0.95:
            label, y = "rest", 0
        else:
            counts["transition" if task_fraction > 0 or rest_fraction > 0 else "ambiguous"] += 1
            continue
        seg_values = segments[start:stop]
        segment = int(pd.Series(seg_values[seg_values >= 0]).mode().iloc[0])
        quality = extract_window_features(data[:, start:stop], fs)
        if not quality["valid"]:
            counts["ambiguous"] += 1
            continue
        del quality["valid"]
        decoder: dict[str, float] = {}
        for channel_index, signal in enumerate(data[:, start:stop]):
            freqs, power = welch_psd(signal, fs)
            for band_index, band in enumerate(BANDS):
                decoder[f"decoder_ch{channel_index}_band{band_index}"] = float(np.log10(bandpower_from_psd(freqs, power, band) + 1e-20))
        smr = float(quality["smr_power"])
        quality.update(decoder)
        quality.update(
            dataset=edf.parts[-5], subject=subject, session=session, time_s=start / fs,
            segment_id=f"{subject}_{session}_{label}_{segment}", event_label=label, y=y,
            task_overlap=task_fraction, rest_overlap=rest_fraction,
            peak_to_peak_uv=float(np.max(np.ptp(data[:, start:stop], axis=1)) * 1e6),
            nonstationarity=float(abs(smr - previous_smr)) if np.isfinite(previous_smr) else 0.0,
        )
        previous_smr = smr
        rows.append(quality)
        counts[label] += 1
    frame = pd.DataFrame(rows)
    rest = frame.event_label == "rest"
    for band in ("smr", "beta", "broadband", "noise"):
        cols = [f"ch_{index}_{band}" for index in range(3)]
        standardized = (frame[cols] - frame.loc[rest, cols].mean()) / frame.loc[rest, cols].std().replace(0, 1e-9)
        frame[f"ch_inc_{band}_sd"] = standardized.std(axis=1)
        frame[f"ch_inc_{band}_mad"] = standardized.apply(lambda row: median_abs_deviation(row.dropna()), axis=1)
    frame["channel_inconsistency"] = frame[[f"ch_inc_{band}_sd" for band in ("smr", "beta", "broadband", "noise")]].mean(axis=1)
    frame = frame.drop(columns=[col for col in frame if col.startswith("ch_") and not col.startswith("ch_inc")])
    trial_count = int(valid_events["trial"].nunique()) if "trial" in valid_events else int(len(valid_events))
    audit = {
        "dataset": edf.parts[-5], "subject": subject, "session": session,
        "event_label": "rest/task", "number_of_trials_or_segments": trial_count,
        "usable_windows": len(frame), "excluded_transition_windows": counts["transition"],
        "ambiguous_windows": counts["ambiguous"], "final_rest_windows": counts["rest"], "final_task_windows": counts["task"],
        "overlap_rule": "at least 95% of the 1 s window overlaps an explicit rest or task event",
    }
    return frame, audit


def load_windows() -> tuple[pd.DataFrame, pd.DataFrame]:
    frames, audits = [], []
    for dataset in DATASETS:
        for edf in sorted((ROOT / "data" / "raw" / "openneuro" / dataset).rglob("sub-*/ses-*/eeg/*_task-smrbmi_eeg.edf")):
            frame, audit = extract_session(edf)
            frames.append(frame)
            audits.append(audit)
            print(f"features {dataset} {audit['subject']} {audit['session']}: {len(frame)}", flush=True)
    return pd.concat(frames, ignore_index=True), pd.DataFrame(audits)


def session_thresholds(train: pd.DataFrame) -> dict[str, float]:
    rest = train.loc[train.event_label == "rest"]
    return {
        "high_beta_power": pct(rest.high_beta_power, 75), "broadband_power": pct(rest.broadband_power, 75),
        "noise_floor_power": pct(rest.noise_floor_power, 75), "transient_score": pct(rest.transient_score, 90),
        "channel_inconsistency": pct(rest.channel_inconsistency, 75),
    }


def masks(train: pd.DataFrame, thresholds: dict[str, float], decoder_cols: list[str]) -> dict[str, pd.Series]:
    finite = np.isfinite(train[list(thresholds) + decoder_cols + ["peak_to_peak_uv"]]).all(axis=1)
    hb = train.high_beta_power < thresholds["high_beta_power"]
    bb = train.broadband_power < thresholds["broadband_power"]
    hf = train.noise_floor_power < thresholds["noise_floor_power"]
    tr = train.transient_score < thresholds["transient_score"]
    ci = train.channel_inconsistency < thresholds["channel_inconsistency"]
    return {"ALL": finite, "HB": finite & hb, "BBHF": finite & bb & hf,
            "NFSQI_NO_HB": finite & bb & hf & tr & ci,
            "NFSQI_FULL": finite & hb & bb & hf & tr & ci,
            "AMPLITUDE_150": finite & (train.peak_to_peak_uv < 150.0)}


def metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    prediction = (probability >= 0.5).astype(int)
    sensitivity = float(np.mean(prediction[y == 1] == 1))
    specificity = float(np.mean(prediction[y == 0] == 0))
    return {"balanced_accuracy": float(balanced_accuracy_score(y, prediction)), "roc_auc": float(roc_auc_score(y, probability)),
            "accuracy": float(accuracy_score(y, prediction)), "macro_f1": float(f1_score(y, prediction, average="macro")),
            "sensitivity": sensitivity, "specificity": specificity, "log_loss": float(log_loss(y, probability, labels=[0, 1])),
            "brier_score": float(brier_score_loss(y, probability))}


def fit_score(train: pd.DataFrame, test: pd.DataFrame, decoder_cols: list[str]) -> tuple[dict[str, float], np.ndarray]:
    scaler = StandardScaler().fit(train[decoder_cols])
    model = LogisticRegression(class_weight="balanced", random_state=20260715, solver="lbfgs", max_iter=1000)
    model.fit(scaler.transform(train[decoder_cols]), train.y.astype(int))
    probability = model.predict_proba(scaler.transform(test[decoder_cols]))[:, 1]
    return metrics(test.y.to_numpy(dtype=int), probability), probability


def valid_selection(selection: pd.DataFrame) -> bool:
    return len(selection) >= 2 * MIN_PER_CLASS and all((selection.y == label).sum() >= MIN_PER_CLASS for label in (0, 1))


def summarize_subjects(results: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [c for c in ("balanced_accuracy", "roc_auc", "accuracy", "macro_f1", "sensitivity", "specificity", "log_loss", "brier_score", "trial_balanced_accuracy") if c in results]
    return results.loc[results.status == "valid"].groupby(["dataset", "subject", "policy", "analysis"], as_index=False)[metric_cols].mean()


def contrasts(subjects: pd.DataFrame) -> pd.DataFrame:
    rows = []
    rng_boot, rng_perm = np.random.default_rng(BOOT_SEED), np.random.default_rng(PERM_SEED)
    for analysis in subjects.analysis.unique():
        for dataset in (*DATASETS, "pooled"):
            data = subjects.loc[subjects.analysis == analysis]
            if dataset != "pooled":
                data = data.loc[data.dataset == dataset]
            wide = data.pivot_table(index=["dataset", "subject"], columns="policy", values="balanced_accuracy", aggfunc="mean")
            if not {"NFSQI_FULL", "HB"}.issubset(wide):
                continue
            diff = (wide.NFSQI_FULL - wide.HB).dropna().to_numpy()
            if not len(diff):
                continue
            boot = np.array([rng_boot.choice(diff, len(diff), replace=True).mean() for _ in range(5000)])
            perm = np.array([np.mean(diff * rng_perm.choice([-1, 1], len(diff))) for _ in range(5000)])
            rows.append({"dataset": dataset, "contrast": "NFSQI_FULL minus HB", "analysis": analysis,
                         "mean_paired_difference": float(diff.mean()), "median_paired_difference": float(np.median(diff)),
                         "bootstrap_ci_low": float(np.quantile(boot, .025)), "bootstrap_ci_high": float(np.quantile(boot, .975)),
                         "p_value": float((np.sum(np.abs(perm) >= abs(diff.mean())) + 1) / 5001), "n_participants": len(diff), "status": "valid"})
    return pd.DataFrame(rows)


def make_figures(subjects: pd.DataFrame, retention: pd.DataFrame, primary: pd.DataFrame) -> None:
    FIG.mkdir(exist_ok=True)
    def save(name: str) -> None:
        plt.tight_layout(); plt.savefig(FIG / f"{name}.pdf"); plt.savefig(FIG / f"{name}.png", dpi=600); plt.close()
    natural = subjects.loc[subjects.analysis == "natural"]
    for name, data, ylabel in (("training_retention", retention, "Training retention"), ("heldout_balanced_accuracy", natural, "Held-out balanced accuracy")):
        plt.figure(figsize=(9, 4));
        for i, dataset in enumerate(DATASETS):
            subset = data.loc[data.dataset == dataset]
            column = "retention_proportion" if name == "training_retention" else "balanced_accuracy"
            if not subset.empty:
                plt.scatter(np.full(len(subset), i), subset[column], s=12, alpha=.5, label=dataset)
        plt.xticks(range(len(DATASETS)), DATASETS); plt.ylabel(ylabel); save(name)
    wide = natural.pivot_table(index=["dataset", "subject"], columns="policy", values="balanced_accuracy")
    if {"NFSQI_FULL", "HB"}.issubset(wide):
        diff = (wide.NFSQI_FULL - wide.HB).dropna(); plt.figure(figsize=(7, 4)); plt.axhline(0, color="black", lw=.7); plt.scatter(range(len(diff)), diff.values); plt.ylabel("NFSQI_FULL minus HB balanced accuracy"); save("paired_full_minus_hb")
    merged = subjects.pivot_table(index=["dataset", "subject", "policy"], columns="analysis", values="balanced_accuracy")
    if {"natural", "count_matched"}.issubset(merged):
        plt.figure(figsize=(6, 4)); plt.scatter(merged.natural, merged.count_matched, s=12); lim=(min(merged.natural.min(), merged.count_matched.min()), max(merged.natural.max(), merged.count_matched.max())); plt.plot(lim, lim, color="black", lw=.7); plt.xlabel("Natural"); plt.ylabel("Count matched"); save("natural_vs_count_matched")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(exist_ok=True)
    all_windows, audit = load_windows(); audit.to_csv(OUT / "event_label_audit.csv", index=False)
    decoder_cols = [col for col in all_windows if col.startswith("decoder_")]
    fold_rows: list[dict[str, object]] = []; retention_rows: list[dict[str, object]] = []; result_rows: list[dict[str, object]] = []; match_rows: list[dict[str, object]] = []; nonviable: list[dict[str, object]] = []
    for (dataset, subject), subject_frame in all_windows.groupby(["dataset", "subject"], sort=True):
        sessions = sorted(subject_frame.session.unique(), key=lambda x: int(x.split("-")[1]))
        if len(sessions) != 2:
            continue
        for train_session, test_session in ((sessions[0], sessions[1]), (sessions[1], sessions[0])):
            train = subject_frame.loc[subject_frame.session == train_session].reset_index(drop=True); test = subject_frame.loc[subject_frame.session == test_session].reset_index(drop=True)
            fold_id = f"{dataset}_{subject}_{train_session}_to_{test_session}"
            fold_rows.append({"fold_id": fold_id, "dataset": dataset, "subject": subject, "train_session": train_session, "test_session": test_session, "direction": "reverse" if train_session > test_session else "forward", "test_windows": len(test), "test_rest": int((test.y == 0).sum()), "test_task": int((test.y == 1).sum()), "status": "valid"})
            threshold = session_thresholds(train); policy_masks = masks(train, threshold, decoder_cols)
            target_counts = {label: int(((train.y == label) & policy_masks["NFSQI_FULL"]).sum()) for label in (0, 1)}
            for policy, mask in policy_masks.items():
                selected = train.loc[mask].copy()
                for label, label_name in ((0, "rest"), (1, "task")):
                    available = int((train.y == label).sum()); kept = int((selected.y == label).sum())
                    retention_rows.append({"fold_id": fold_id, "dataset": dataset, "subject": subject, "train_session": train_session, "test_session": test_session, "policy": policy, "class": label_name, "retained_windows": kept, "available_windows": available, "retention_proportion": kept / available if available else np.nan})
                if not valid_selection(selected):
                    nonviable.append({"fold_id": fold_id, "dataset": dataset, "subject": subject, "train_session": train_session, "test_session": test_session, "policy": policy, "analysis": "natural", "reason": "fewer than 10 retained windows in at least one class", "status": "nonviable"}); continue
                started = time.perf_counter(); score, probability = fit_score(selected, test, decoder_cols); elapsed = time.perf_counter() - started
                trial = pd.DataFrame({"segment": test.segment_id, "y": test.y, "p": probability}).groupby("segment", as_index=False).agg(y=("y", "first"), p=("p", "mean"))
                score["trial_balanced_accuracy"] = float(balanced_accuracy_score(trial.y, trial.p >= .5)); score["runtime_seconds"] = elapsed
                result_rows.append({"fold_id": fold_id, "dataset": dataset, "subject": subject, "train_session": train_session, "test_session": test_session, "policy": policy, "analysis": "natural", "seed": np.nan, "status": "valid", **score})
                for seed in SEEDS:
                    rng = np.random.default_rng(seed)
                    chosen = []
                    for label in (0, 1):
                        pool = selected.index[selected.y == label].to_numpy(); target = target_counts[label]
                        if target < MIN_PER_CLASS or len(pool) < target:
                            chosen = []; break
                        chosen.extend(rng.choice(pool, target, replace=False).tolist())
                    if not chosen:
                        nonviable.append({"fold_id": fold_id, "dataset": dataset, "subject": subject, "train_session": train_session, "test_session": test_session, "policy": policy, "analysis": "count_matched", "reason": "NFSQI_FULL target or policy pool lacks 10 windows per class", "status": "nonviable"}); break
                    matched = selected.loc[chosen]
                    started = time.perf_counter(); cm_score, _ = fit_score(matched, test, decoder_cols); cm_score["runtime_seconds"] = time.perf_counter() - started
                    match_rows.append({"fold_id": fold_id, "dataset": dataset, "subject": subject, "train_session": train_session, "test_session": test_session, "policy": policy, "seed": seed, "n_rest": target_counts[0], "n_task": target_counts[1], "status": "valid", **cm_score})
    fold_df, retention_df, natural_df, count_df = pd.DataFrame(fold_rows), pd.DataFrame(retention_rows), pd.DataFrame(result_rows), pd.DataFrame(match_rows)
    count_summary = count_df.groupby(["fold_id", "dataset", "subject", "train_session", "test_session", "policy", "status"], as_index=False)[["balanced_accuracy", "roc_auc", "accuracy", "macro_f1", "sensitivity", "specificity", "log_loss", "brier_score", "runtime_seconds"]].mean() if not count_df.empty else pd.DataFrame()
    if not count_summary.empty: count_summary["analysis"] = "count_matched"; count_summary["seed"] = np.nan; count_summary["trial_balanced_accuracy"] = np.nan
    combined = pd.concat([natural_df, count_summary], ignore_index=True, sort=False)
    retention_df.to_csv(OUT / "retention_by_fold.csv", index=False); fold_df.to_csv(OUT / "fold_definition.csv", index=False); combined.to_csv(OUT / "decoder_results_all_folds.csv", index=False); count_df.to_csv(OUT / "count_matched_results.csv", index=False); pd.DataFrame(nonviable).to_csv(OUT / "nonviable_folds.csv", index=False)
    subject_df = summarize_subjects(combined); subject_df.to_csv(OUT / "decoder_results_by_subject.csv", index=False)
    retention_subject = retention_df.groupby(["dataset", "subject", "policy", "class"], as_index=False)[["retained_windows", "available_windows"]].sum(); retention_subject["retention_proportion"] = retention_subject.retained_windows / retention_subject.available_windows; retention_subject.to_csv(OUT / "retention_by_subject.csv", index=False)
    primary = contrasts(subject_df); primary.to_csv(OUT / "primary_contrasts.csv", index=False)
    loo_rows = []
    pooled = subject_df.loc[subject_df.analysis == "natural"].pivot_table(index=["dataset", "subject"], columns="policy", values="balanced_accuracy")
    if {"NFSQI_FULL", "HB"}.issubset(pooled):
        for index in pooled.index:
            diff = (pooled.drop(index).NFSQI_FULL - pooled.drop(index).HB).dropna(); loo_rows.append({"omitted_subject": f"{index[0]}:{index[1]}", "contrast": "NFSQI_FULL minus HB", "mean_paired_difference": diff.mean(), "n_participants": len(diff), "status": "valid"})
    pd.DataFrame(loo_rows).to_csv(OUT / "leave_one_subject_out_sensitivity.csv", index=False)
    ldo = []
    for omitted in DATASETS:
        diff = (pooled.loc[[idx for idx in pooled.index if idx[0] != omitted]].NFSQI_FULL - pooled.loc[[idx for idx in pooled.index if idx[0] != omitted]].HB).dropna(); ldo.append({"omitted_dataset": omitted, "contrast": "NFSQI_FULL minus HB", "mean_paired_difference": diff.mean(), "n_participants": len(diff), "status": "valid"})
    pd.DataFrame(ldo).to_csv(OUT / "leave_one_dataset_out_sensitivity.csv", index=False)
    pd.DataFrame(columns=combined.columns).to_csv(OUT / "expanded_roi_results.csv", index=False)
    (OUT / "rpf_implementation_report.md").write_text("# RPF implementation report\n\nStatus: not attempted. The required Priority 1 primary analysis was completed first; a faithful Riemannian Potato/Field implementation is not bundled in the frozen dependency set.\n", encoding="utf-8")
    make_figures(subject_df, retention_subject, primary)
    main_contrast = primary.loc[(primary.dataset == "pooled") & (primary.analysis == "natural") & (primary.contrast == "NFSQI_FULL minus HB")]
    conclusion = "No pooled contrast available."
    if not main_contrast.empty:
        row = main_contrast.iloc[0]; conclusion = f"Pooled natural-retention NFSQI_FULL minus HB balanced accuracy: {row.mean_paired_difference:.4f} (95% bootstrap CI {row.bootstrap_ci_low:.4f}, {row.bootstrap_ci_high:.4f}; n={int(row.n_participants)})."
    (OUT / "analysis_report.md").write_text("# Downstream decoder validation report\n\n" + conclusion + "\n\nThe outcome uses explicit rest/task event labels, never NF-SQI labels; participant-level paired inference; session-held-out folds; and the same unfiltered test set across policies. See the CSV outputs for dataset-specific and count-matched results.\n", encoding="utf-8")
    (OUT / "environment.txt").write_text(f"Python: {sys.version}\nOS: {platform.platform()}\nCPU: {platform.processor()}\nSeeds: model=20260715, count_matching=20260716..20260815, bootstrap={BOOT_SEED}, permutation={PERM_SEED}\n", encoding="utf-8")
    print(conclusion)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
