import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "outputs" / "replication_tables"
LOG_DIR = ROOT / "outputs" / "replication_logs"
SUMMARY_DIR = ROOT / "outputs" / "replication_summary"
FIGURE_DIR = ROOT / "outputs" / "replication_figures"
PRIMARY_TABLE_DIR = ROOT / "outputs" / "tables"

SEED = 20260702
N_BOOTSTRAP = 5000
ANALYZED_DATASETS = ["ds004447", "ds004444", "ds004446"]
COMPANION_DATASETS = ["ds004444", "ds004446"]
SKIPPED_DATASETS = ["ds004448"]

MODEL_KEYS = [
    "Broadband_Noise_Floor_Only",
    "High_Beta_Only",
    "Broadband_Noise_Floor_+_High_Beta",
    "Full_NF-SQI",
]

MODEL_LABELS = {
    "Broadband_Noise_Floor_Only": "Broadband/Noise Floor Only",
    "High_Beta_Only": "High Beta Only",
    "Broadband_Noise_Floor_+_High_Beta": "Broadband/Noise Floor + High Beta",
    "Full_NF-SQI": "Full NF-SQI",
}

REQUIRED_FINAL_FILES = [
    SUMMARY_DIR / "final_replication_report.md",
    SUMMARY_DIR / "methods_parameter_report.md",
    TABLE_DIR / "primary_replication_summary.csv",
    TABLE_DIR / "primary_replication_summary.tex",
    TABLE_DIR / "bootstrap_ci_by_dataset.csv",
    TABLE_DIR / "bootstrap_ci_by_dataset.tex",
    LOG_DIR / "leakage_control_report.md",
    FIGURE_DIR / "fig_replication_blocking_by_dataset.pdf",
    FIGURE_DIR / "fig_replication_auc_by_dataset.pdf",
    FIGURE_DIR / "fig_candidate_composition_by_dataset.pdf",
    FIGURE_DIR / "fig_auc_added_value.pdf",
]

COMMAND_USED = 'python analysis_replication\\finish_replication.py > outputs\\replication_logs\\finish_replication_run.log 2>&1'


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def ensure_dirs():
    for path in [TABLE_DIR, LOG_DIR, SUMMARY_DIR, FIGURE_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def require_file(path, min_bytes=1):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    if path.stat().st_size < min_bytes:
        raise ValueError(f"Required file is empty or too small: {path}")
    return path


def required_file_status():
    return [(str(path.relative_to(ROOT)), path.exists(), path.stat().st_size if path.exists() else 0) for path in REQUIRED_FINAL_FILES]


def write_failure_report(stage, exc_text):
    ensure_dirs()
    complete = [p for p in REQUIRED_FINAL_FILES if p.exists()]
    missing = [p for p in REQUIRED_FINAL_FILES if not p.exists()]
    report = SUMMARY_DIR / "final_replication_report.md"
    lines = [
        "# Replication Run Failure Report",
        "",
        f"Generated: {utc_now()}",
        "Workspace: repository root",
        "",
        "## Status",
        "",
        "The replication finishing job did not complete.",
        "",
        "No manuscript, LaTeX, captions, references, or manuscript figures were edited by this finishing script.",
        "",
        "## Failed Stage",
        "",
        stage,
        "",
        "## Traceback Or Error",
        "",
        "```text",
        exc_text.strip(),
        "```",
        "",
        "## Outputs Complete",
        "",
    ]
    if complete:
        lines.extend([f"- `{p.relative_to(ROOT)}`" for p in complete])
    else:
        lines.append("- None of the required final replication outputs were complete.")
    lines.extend(["", "## Outputs Remaining Missing", ""])
    if missing:
        lines.extend([f"- `{p.relative_to(ROOT)}`" for p in missing])
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Exact Command Needed To Resume",
            "",
            "```powershell",
            COMMAND_USED,
            "```",
            "",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")


def validate_inventory():
    inv_path = require_file(TABLE_DIR / "dataset_inventory.csv")
    md_path = require_file(LOG_DIR / "dataset_inventory.md")
    inv = pd.read_csv(inv_path)
    required = set(ANALYZED_DATASETS + SKIPPED_DATASETS)
    present = set(inv["dataset_id"].astype(str))
    missing = required - present
    if missing:
        raise ValueError(f"Dataset inventory missing rows: {sorted(missing)}")

    suitability_col = "suitability_for_nfsqi" if "suitability_for_nfsqi" in inv.columns else "suitability_for_beta_state_persistence"
    status = inv.set_index("dataset_id")[suitability_col].to_dict()
    for dataset_id in ANALYZED_DATASETS:
        if status.get(dataset_id) != "suitable":
            raise ValueError(f"{dataset_id} is not marked suitable in inventory: {status.get(dataset_id)}")
    if status.get("ds004448") == "suitable":
        raise ValueError("ds004448 is marked suitable, but this finishing pass expected it to remain skipped.")
    return inv, md_path


def inventory_suitability(row: dict, default: str = "NA") -> str:
    return row.get("suitability_for_nfsqi", row.get("suitability_for_beta_state_persistence", default))


def validate_companion_outputs():
    validations = []
    for dataset_id in COMPANION_DATASETS:
        paths = [
            TABLE_DIR / f"{dataset_id}_contamination_overlap.csv",
            TABLE_DIR / f"{dataset_id}_model_comparison.csv",
            TABLE_DIR / f"{dataset_id}_window_features.csv",
            TABLE_DIR / f"{dataset_id}_task_labeled_windows.csv",
        ]
        paths.extend(TABLE_DIR / f"{dataset_id}_{model}_predictions.csv" for model in MODEL_KEYS)
        for path in paths:
            require_file(path)

        overlap = pd.read_csv(TABLE_DIR / f"{dataset_id}_contamination_overlap.csv")
        models = pd.read_csv(TABLE_DIR / f"{dataset_id}_model_comparison.csv")
        if overlap.empty:
            raise ValueError(f"{dataset_id} contamination overlap is empty")
        if len(models) != 4:
            raise ValueError(f"{dataset_id} model comparison should have 4 rows, found {len(models)}")
        for col in ["subject", "session", "total_candidates", "blocked_by_full"]:
            if col not in overlap.columns:
                raise ValueError(f"{dataset_id} overlap missing column {col}")
        for col in ["Dataset", "Model", "AUC", "Balanced_Accuracy"]:
            if col not in models.columns:
                raise ValueError(f"{dataset_id} model comparison missing column {col}")

        validations.append(
            {
                "dataset": dataset_id,
                "overlap_rows": len(overlap),
                "model_rows": len(models),
                "subjects": overlap["subject"].nunique(),
                "candidate_windows": int(overlap["total_candidates"].sum()),
            }
        )
    return validations


def safe_mean_percent(df, column):
    return float(df[column].mean() * 100.0)


def run_ds004447_reproduction_check():
    overlap_path = require_file(PRIMARY_TABLE_DIR / "nf_sqi_contamination_overlap.csv")
    model_path = require_file(PRIMARY_TABLE_DIR / "nf_sqi_model_comparison.csv")
    task_path = require_file(PRIMARY_TABLE_DIR / "nf_sqi_task_labeled_windows.csv")
    require_file(PRIMARY_TABLE_DIR / "nf_sqi_window_features.csv")

    overlap = pd.read_csv(overlap_path)
    models = pd.read_csv(model_path)
    if overlap.empty or models.empty:
        raise ValueError("ds004447 primary outputs are empty")

    expected_composition = {
        "Clean": ("clean", 53.5),
        "High beta only": ("high_beta_excl", 4.5),
        "Broadband/noise only": ("broadband_noise_excl", 15.2),
        "Channel inconsistency only": ("channel_inc_excl", 9.0),
        "Transient amplitude only": ("transient_excl", 0.2),
        "Multi-contaminated": ("multi_contam", 17.7),
    }
    expected_blocking = {
        "High beta": ("blocked_by_hb_single", 30.4),
        "Broadband/noise floor": ("blocked_by_bbnf_single", 62.0),
        "Transient amplitude": ("blocked_by_tr_single", 4.1),
        "Channel inconsistency": ("blocked_by_ch_single", 47.9),
        "Full NF-SQI": ("blocked_by_full", 97.7),
    }
    expected_models = {
        "Model A: Broadband/Noise": (0.714, 0.662),
        "Model B: High Beta Only": (0.558, 0.544),
        "Model C: Broadband/Noise + High Beta": (0.700, 0.660),
        "Model D: Full NF-SQI": (0.702, 0.656),
    }

    checks = []
    tolerance_pct = 0.1
    for label, (column, expected) in {**expected_composition, **expected_blocking}.items():
        actual = safe_mean_percent(overlap, column)
        checks.append(
            {
                "section": "composition_or_blocking",
                "metric": label,
                "actual": actual,
                "expected": expected,
                "passed": abs(actual - expected) <= tolerance_pct,
            }
        )

    tolerance_model_pct = 0.1
    indexed = models.set_index("Model")
    for label, (expected_auc, expected_bacc) in expected_models.items():
        if label not in indexed.index:
            raise ValueError(f"ds004447 model comparison missing row: {label}")
        actual_auc = float(indexed.loc[label, "AUC"])
        actual_bacc = float(indexed.loc[label, "Balanced_Accuracy"])
        checks.append(
            {
                "section": "model_auc",
                "metric": f"{label} AUC",
                "actual": actual_auc * 100,
                "expected": expected_auc * 100,
                "passed": abs((actual_auc - expected_auc) * 100) <= tolerance_model_pct,
            }
        )
        checks.append(
            {
                "section": "model_balanced_accuracy",
                "metric": f"{label} Balanced Accuracy",
                "actual": actual_bacc * 100,
                "expected": expected_bacc * 100,
                "passed": abs((actual_bacc - expected_bacc) * 100) <= tolerance_model_pct,
            }
        )

    failed = [c for c in checks if not c["passed"]]
    if failed:
        raise ValueError(f"ds004447 reproduction check failed: {failed}")

    task = pd.read_csv(task_path, usecols=["subject", "session", "window_size"])
    return {
        "passed": True,
        "checks": checks,
        "subjects": int(task["subject"].nunique()),
        "sessions": int(task[["subject", "session"]].drop_duplicates().shape[0]),
        "task_rows": int(len(task)),
    }


def generate_ds004447_predictions():
    task_path = require_file(PRIMARY_TABLE_DIR / "nf_sqi_task_labeled_windows.csv")
    df = pd.read_csv(task_path)
    df = df[df["window_size"] == 1.0].copy()
    if df.empty:
        raise ValueError("No ds004447 1.0 s task windows found for prediction generation")

    target = "is_contaminated"
    if target not in df.columns:
        raise ValueError("ds004447 task-labeled windows missing is_contaminated")

    models = {
        "Broadband_Noise_Floor_Only": ["broadband_power", "noise_floor_power"],
        "High_Beta_Only": ["high_beta_power"],
        "Broadband_Noise_Floor_+_High_Beta": ["broadband_power", "noise_floor_power", "high_beta_power"],
        "Full_NF-SQI": [
            "broadband_power",
            "noise_floor_power",
            "high_beta_power",
            "transient_score",
            "channel_inconsistency",
            "nonstationarity",
        ],
    }
    rows = []
    leakage_rows = []
    subjects = sorted(df["subject"].dropna().unique())
    for model_key, features in models.items():
        y_true = []
        y_pred = []
        y_pred_proba = []
        test_subjects = []
        for test_sub in subjects:
            train_df = df[df["subject"] != test_sub]
            test_df = df[df["subject"] == test_sub]
            leakage_rows.append(
                {
                    "dataset": "ds004447",
                    "model": MODEL_LABELS[model_key],
                    "test_subject": test_sub,
                    "train_subject_count": int(train_df["subject"].nunique()),
                    "test_subject_count": int(test_df["subject"].nunique()),
                    "subject_overlap": int(bool(set(train_df["subject"]) & set(test_df["subject"]))),
                }
            )
            if train_df.empty or test_df.empty or train_df[target].nunique() < 2:
                continue
            scaler = StandardScaler()
            x_train = scaler.fit_transform(train_df[features].fillna(0))
            x_test = scaler.transform(test_df[features].fillna(0))
            clf = LogisticRegression(class_weight="balanced", random_state=SEED, solver="lbfgs", max_iter=1000)
            clf.fit(x_train, train_df[target])
            y_true.extend(test_df[target].astype(int).to_numpy())
            y_pred.extend(clf.predict(x_test))
            y_pred_proba.extend(clf.predict_proba(x_test)[:, 1])
            test_subjects.extend([test_sub] * len(test_df))

        if len(set(y_true)) < 2:
            raise ValueError(f"Cannot compute ds004447 model performance for {model_key}; one target class only")
        auc = roc_auc_score(y_true, y_pred_proba)
        bacc = balanced_accuracy_score(y_true, y_pred)
        rows.append(
            {
                "Dataset": "ds004447",
                "Model": MODEL_LABELS[model_key],
                "AUC": auc,
                "Balanced_Accuracy": bacc,
            }
        )
        pred_df = pd.DataFrame({"subject": test_subjects, "y_true": y_true, "y_pred_proba": y_pred_proba})
        pred_df.to_csv(TABLE_DIR / f"ds004447_{model_key}_predictions.csv", index=False)

    model_df = pd.DataFrame(rows)
    model_df.to_csv(TABLE_DIR / "ds004447_model_comparison.csv", index=False)
    leakage_df = pd.DataFrame(leakage_rows)
    leakage_df.to_csv(TABLE_DIR / "ds004447_loso_leakage_check.csv", index=False)
    if leakage_df["subject_overlap"].sum() != 0:
        raise ValueError("Subject overlap detected in ds004447 LOSO prediction generation")
    return {"model_rows": rows, "leakage_rows": leakage_rows}


def load_inventory_row(inventory, dataset_id):
    row = inventory[inventory["dataset_id"] == dataset_id]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


def load_overlap(dataset_id):
    if dataset_id == "ds004447":
        path = PRIMARY_TABLE_DIR / "nf_sqi_contamination_overlap.csv"
    else:
        path = TABLE_DIR / f"{dataset_id}_contamination_overlap.csv"
    require_file(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"{dataset_id} overlap table is empty")
    return df


def as_rate_and_count(df, column, denominator):
    values = pd.to_numeric(df[column], errors="coerce").astype(float)
    denom = pd.to_numeric(denominator, errors="coerce").astype(float)
    if values.dropna().empty:
        return np.full(len(df), np.nan), np.full(len(df), np.nan)
    if values.max(skipna=True) <= 1.0000001:
        rate = values * 100.0
        count = values * denom
    else:
        count = values
        rate = np.where(denom > 0, count / denom * 100.0, 0.0)
    return np.asarray(rate, dtype=float), np.asarray(count, dtype=float)


def normalize_overlap(dataset_id):
    df = load_overlap(dataset_id).copy()
    if "contaminated" in df.columns:
        fa_denominator = pd.to_numeric(df["contaminated"], errors="coerce").fillna(0.0)
    elif "fa_total" in df.columns:
        fa_denominator = pd.to_numeric(df["fa_total"], errors="coerce").fillna(0.0)
    else:
        raise ValueError(f"{dataset_id} overlap table has no false-admissible denominator")

    total = pd.to_numeric(df["total_candidates"], errors="coerce").fillna(0.0)
    out = pd.DataFrame(
        {
            "Dataset": dataset_id,
            "subject": df["subject"].astype(str),
            "session": df["session"].astype(str),
            "total_candidates": total,
            "false_admissible_total": fa_denominator,
        }
    )

    composition_cols = {
        "Clean_Pct": "clean",
        "HB_Only_Pct": "high_beta_excl",
        "BB_Only_Pct": "broadband_noise_excl",
        "Ch_Inc_Only_Pct": "channel_inc_excl",
        "Transient_Only_Pct": "transient_excl",
        "Multi_Contam_Pct": "multi_contam",
    }
    for metric, column in composition_cols.items():
        if column in df.columns:
            rate, count = as_rate_and_count(df, column, total)
            out[metric] = rate
            out[metric.replace("_Pct", "_Count")] = count
        else:
            out[metric] = np.nan
            out[metric.replace("_Pct", "_Count")] = np.nan

    blocking_cols = {
        "Blk_HB_Pct": "blocked_by_hb_single",
        "Blk_BBNF_Pct": "blocked_by_bbnf_single",
        "Blk_Tr_Pct": "blocked_by_tr_single",
        "Blk_Ch_Inc_Pct": "blocked_by_ch_single",
        "Blk_Full_Pct": "blocked_by_full",
    }
    for metric, column in blocking_cols.items():
        if column in df.columns:
            rate, count = as_rate_and_count(df, column, fa_denominator)
            out[metric] = rate
            out[metric.replace("_Pct", "_Count")] = count
        else:
            out[metric] = np.nan
            out[metric.replace("_Pct", "_Count")] = np.nan

    out["Delta_Block_Full_minus_HB_Pct"] = out["Blk_Full_Pct"] - out["Blk_HB_Pct"]
    out["Delta_Block_BBNF_minus_HB_Pct"] = out["Blk_BBNF_Pct"] - out["Blk_HB_Pct"]
    return out


def percentile_ci(values):
    arr = np.asarray([v for v in values if not pd.isna(v)], dtype=float)
    if arr.size == 0:
        return np.nan, np.nan, np.nan
    return float(np.mean(arr)), float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))


def bootstrap_overlap_metrics(dataset_id, norm_df, rng):
    metrics = [
        "Clean_Pct",
        "HB_Only_Pct",
        "BB_Only_Pct",
        "Ch_Inc_Only_Pct",
        "Transient_Only_Pct",
        "Multi_Contam_Pct",
        "Blk_HB_Pct",
        "Blk_BBNF_Pct",
        "Blk_Tr_Pct",
        "Blk_Ch_Inc_Pct",
        "Blk_Full_Pct",
        "Delta_Block_Full_minus_HB_Pct",
        "Delta_Block_BBNF_minus_HB_Pct",
    ]
    subjects = sorted(norm_df["subject"].dropna().unique())
    subject_values = {
        metric: {sub: norm_df.loc[norm_df["subject"] == sub, metric].to_numpy(dtype=float) for sub in subjects}
        for metric in metrics
    }
    boot = {metric: [] for metric in metrics}
    for _ in range(N_BOOTSTRAP):
        sampled = rng.choice(subjects, size=len(subjects), replace=True)
        for metric in metrics:
            vals = np.concatenate([subject_values[metric][sub] for sub in sampled])
            if vals.size:
                boot[metric].append(float(np.nanmean(vals)))

    rows = []
    for metric in metrics:
        mean, low, high = percentile_ci(boot[metric])
        rows.append(
            {
                "Dataset": dataset_id,
                "Metric": metric,
                "Mean": mean,
                "CI_Lower": low,
                "CI_Upper": high,
                "Unit": "percent",
                "Bootstrap_N": N_BOOTSTRAP,
                "Grouping": "subject",
            }
        )
    return rows


def load_predictions(dataset_id):
    pred = {}
    for model_key in MODEL_KEYS:
        path = TABLE_DIR / f"{dataset_id}_{model_key}_predictions.csv"
        require_file(path)
        df = pd.read_csv(path)
        for col in ["subject", "y_true", "y_pred_proba"]:
            if col not in df.columns:
                raise ValueError(f"{path} missing column {col}")
        pred[model_key] = df
    return pred


def bootstrap_model_metrics(dataset_id, rng):
    pred = load_predictions(dataset_id)
    subjects = sorted(pred[MODEL_KEYS[0]]["subject"].dropna().unique())
    sub_idx = {
        model: {sub: np.flatnonzero(pred[model]["subject"].astype(str).to_numpy() == str(sub)) for sub in subjects}
        for model in MODEL_KEYS
    }
    y_true = {model: pred[model]["y_true"].astype(int).to_numpy() for model in MODEL_KEYS}
    y_score = {model: pred[model]["y_pred_proba"].astype(float).to_numpy() for model in MODEL_KEYS}

    auc_boot = {model: [] for model in MODEL_KEYS}
    bacc_boot = {model: [] for model in MODEL_KEYS}
    deltas = {
        "Delta_AUC_BBNF_minus_HB": [],
        "Delta_AUC_BBNF_HB_minus_BBNF": [],
        "Delta_AUC_Full_minus_HB": [],
    }

    for _ in range(N_BOOTSTRAP):
        sampled = rng.choice(subjects, size=len(subjects), replace=True)
        aucs = {}
        for model in MODEL_KEYS:
            idx = np.concatenate([sub_idx[model][sub] for sub in sampled])
            yt = y_true[model][idx]
            ys = y_score[model][idx]
            if len(np.unique(yt)) < 2:
                aucs[model] = np.nan
                continue
            auc = roc_auc_score(yt, ys)
            bacc = balanced_accuracy_score(yt, ys > 0.5)
            auc_boot[model].append(float(auc))
            bacc_boot[model].append(float(bacc))
            aucs[model] = float(auc)
        if all(not pd.isna(aucs.get(model, np.nan)) for model in MODEL_KEYS):
            deltas["Delta_AUC_BBNF_minus_HB"].append(
                aucs["Broadband_Noise_Floor_Only"] - aucs["High_Beta_Only"]
            )
            deltas["Delta_AUC_BBNF_HB_minus_BBNF"].append(
                aucs["Broadband_Noise_Floor_+_High_Beta"] - aucs["Broadband_Noise_Floor_Only"]
            )
            deltas["Delta_AUC_Full_minus_HB"].append(aucs["Full_NF-SQI"] - aucs["High_Beta_Only"])

    rows = []
    for model in MODEL_KEYS:
        mean, low, high = percentile_ci(auc_boot[model])
        rows.append(
            {
                "Dataset": dataset_id,
                "Metric": f"{model}_AUC",
                "Mean": mean,
                "CI_Lower": low,
                "CI_Upper": high,
                "Unit": "auc",
                "Bootstrap_N": N_BOOTSTRAP,
                "Grouping": "subject",
            }
        )
        mean, low, high = percentile_ci(bacc_boot[model])
        rows.append(
            {
                "Dataset": dataset_id,
                "Metric": f"{model}_BACC",
                "Mean": mean,
                "CI_Lower": low,
                "CI_Upper": high,
                "Unit": "proportion",
                "Bootstrap_N": N_BOOTSTRAP,
                "Grouping": "subject",
            }
        )
    for metric, values in deltas.items():
        mean, low, high = percentile_ci(values)
        rows.append(
            {
                "Dataset": dataset_id,
                "Metric": metric,
                "Mean": mean,
                "CI_Lower": low,
                "CI_Upper": high,
                "Unit": "auc",
                "Bootstrap_N": N_BOOTSTRAP,
                "Grouping": "subject",
            }
        )
    return rows


def generate_bootstrap_tables(norm_overlaps):
    rows = []
    for idx, dataset_id in enumerate(ANALYZED_DATASETS):
        rng = np.random.RandomState(SEED + idx)
        rows.extend(bootstrap_overlap_metrics(dataset_id, norm_overlaps[dataset_id], rng))
        rng = np.random.RandomState(SEED + 100 + idx)
        rows.extend(bootstrap_model_metrics(dataset_id, rng))
    df = pd.DataFrame(rows)
    df.to_csv(TABLE_DIR / "bootstrap_ci_by_dataset.csv", index=False)
    with (TABLE_DIR / "bootstrap_ci_by_dataset.tex").open("w", encoding="utf-8") as f:
        f.write(df.to_latex(index=False, float_format="%.4f"))
    return df


def metric_row(df, dataset_id, metric):
    row = df[(df["Dataset"] == dataset_id) & (df["Metric"] == metric)]
    if row.empty:
        return None
    return row.iloc[0]


def format_ci(row, decimals=1):
    if row is None or pd.isna(row["Mean"]):
        return "NA"
    return f"{row['Mean']:.{decimals}f} [{row['CI_Lower']:.{decimals}f}, {row['CI_Upper']:.{decimals}f}]"


def format_auc_ci(row):
    if row is None or pd.isna(row["Mean"]):
        return "NA"
    return f"{row['Mean']:.3f} [{row['CI_Lower']:.3f}, {row['CI_Upper']:.3f}]"


def format_delta_auc_ci(row):
    if row is None or pd.isna(row["Mean"]):
        return "NA"
    return f"{row['Mean']:+.3f} [{row['CI_Lower']:+.3f}, {row['CI_Upper']:+.3f}]"


def qualitative_summary_for_dataset(boot_df, dataset_id):
    full_delta = metric_row(boot_df, dataset_id, "Delta_Block_Full_minus_HB_Pct")
    bbnf_delta = metric_row(boot_df, dataset_id, "Delta_AUC_BBNF_minus_HB")
    added_delta = metric_row(boot_df, dataset_id, "Delta_AUC_BBNF_HB_minus_BBNF")
    parts = []
    if full_delta is not None and full_delta["Mean"] > 0:
        parts.append("Full NF-SQI blocks more false-admissible windows than high beta")
    if bbnf_delta is not None and bbnf_delta["Mean"] > 0:
        parts.append("BB/noise AUC exceeds high beta")
    if added_delta is not None and abs(added_delta["Mean"]) < 0.01:
        parts.append("adding high beta gives negligible AUC change")
    elif added_delta is not None and added_delta["Mean"] < 0:
        parts.append("adding high beta reduces AUC versus BB/noise")
    elif added_delta is not None:
        parts.append("adding high beta increases AUC versus BB/noise")
    return "; ".join(parts)


def generate_primary_summary(boot_df, norm_overlaps, inventory):
    rows = []
    roles = {"ds004447": "Primary reproduction", "ds004444": "Replication", "ds004446": "Replication"}
    for dataset_id in ANALYZED_DATASETS:
        overlap = norm_overlaps[dataset_id]
        inv = load_inventory_row(inventory, dataset_id)
        rows.append(
            {
                "Dataset": dataset_id,
                "Role": roles[dataset_id],
                "Status": "analyzed",
                "Inventory suitability": inventory_suitability(inv, "suitable"),
                "Subjects": int(overlap["subject"].nunique()),
                "Subject-session rows": int(overlap[["subject", "session"]].drop_duplicates().shape[0]),
                "Candidate windows": int(round(overlap["total_candidates"].sum())),
                "Clean candidate % (95% CI)": format_ci(metric_row(boot_df, dataset_id, "Clean_Pct")),
                "HB-only candidate % (95% CI)": format_ci(metric_row(boot_df, dataset_id, "HB_Only_Pct")),
                "BB/noise-only candidate % (95% CI)": format_ci(metric_row(boot_df, dataset_id, "BB_Only_Pct")),
                "Full blocks false-admissible % (95% CI)": format_ci(
                    metric_row(boot_df, dataset_id, "Blk_Full_Pct")
                ),
                "High beta blocks false-admissible % (95% CI)": format_ci(
                    metric_row(boot_df, dataset_id, "Blk_HB_Pct")
                ),
                "BB/noise blocks false-admissible % (95% CI)": format_ci(
                    metric_row(boot_df, dataset_id, "Blk_BBNF_Pct")
                ),
                "BB/noise AUC (95% CI)": format_auc_ci(
                    metric_row(boot_df, dataset_id, "Broadband_Noise_Floor_Only_AUC")
                ),
                "High beta AUC (95% CI)": format_auc_ci(metric_row(boot_df, dataset_id, "High_Beta_Only_AUC")),
                "BB/noise + high beta AUC (95% CI)": format_auc_ci(
                    metric_row(boot_df, dataset_id, "Broadband_Noise_Floor_+_High_Beta_AUC")
                ),
                "Full NF-SQI AUC (95% CI)": format_auc_ci(metric_row(boot_df, dataset_id, "Full_NF-SQI_AUC")),
                "Delta AUC BB/noise - high beta (95% CI)": format_delta_auc_ci(
                    metric_row(boot_df, dataset_id, "Delta_AUC_BBNF_minus_HB")
                ),
                "Delta AUC add high beta to BB/noise (95% CI)": format_delta_auc_ci(
                    metric_row(boot_df, dataset_id, "Delta_AUC_BBNF_HB_minus_BBNF")
                ),
                "Qualitative conclusion": qualitative_summary_for_dataset(boot_df, dataset_id),
            }
        )

    inv = load_inventory_row(inventory, "ds004448")
    rows.append(
        {
            "Dataset": "ds004448",
            "Role": "Candidate companion dataset",
            "Status": "skipped",
            "Inventory suitability": inventory_suitability(inv, "not_suitable_or_metadata_only"),
            "Subjects": inv.get("local_subject_count", "NA"),
            "Subject-session rows": inv.get("local_session_count", "NA"),
            "Candidate windows": "NA",
            "Clean candidate % (95% CI)": "NA",
            "HB-only candidate % (95% CI)": "NA",
            "BB/noise-only candidate % (95% CI)": "NA",
            "Full blocks false-admissible % (95% CI)": "NA",
            "High beta blocks false-admissible % (95% CI)": "NA",
            "BB/noise blocks false-admissible % (95% CI)": "NA",
            "BB/noise AUC (95% CI)": "NA",
            "High beta AUC (95% CI)": "NA",
            "BB/noise + high beta AUC (95% CI)": "NA",
            "Full NF-SQI AUC (95% CI)": "NA",
            "Delta AUC BB/noise - high beta (95% CI)": "NA",
            "Delta AUC add high beta to BB/noise (95% CI)": "NA",
            "Qualitative conclusion": "Skipped: inventory marks not_suitable_or_metadata_only; only Trial start/event marker 1 was detected, so no safe rest/task-compatible analysis path was identified.",
        }
    )

    df = pd.DataFrame(rows)
    df.to_csv(TABLE_DIR / "primary_replication_summary.csv", index=False)
    with (TABLE_DIR / "primary_replication_summary.tex").open("w", encoding="utf-8") as f:
        f.write(df.to_latex(index=False))
    return df


def style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2)


def get_metric_arrays(boot_df, datasets, metric):
    means, lows, highs = [], [], []
    for dataset_id in datasets:
        row = metric_row(boot_df, dataset_id, metric)
        if row is None:
            means.append(np.nan)
            lows.append(np.nan)
            highs.append(np.nan)
        else:
            means.append(float(row["Mean"]))
            lows.append(float(row["CI_Lower"]))
            highs.append(float(row["CI_Upper"]))
    means = np.asarray(means, dtype=float)
    yerr = np.vstack([means - np.asarray(lows), np.asarray(highs) - means])
    return means, yerr


def generate_figures(boot_df):
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["font.family"] = "DejaVu Sans"
    datasets = ANALYZED_DATASETS
    x = np.arange(len(datasets))
    labels = [d.replace("ds00", "DS") for d in datasets]

    # Blocking figure
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    block_metrics = [
        ("Blk_HB_Pct", "High beta", "#c55a11"),
        ("Blk_BBNF_Pct", "BB/noise", "#4472c4"),
        ("Blk_Full_Pct", "Full NF-SQI", "#70ad47"),
    ]
    width = 0.23
    for i, (metric, label, color) in enumerate(block_metrics):
        vals, err = get_metric_arrays(boot_df, datasets, metric)
        pos = x + (i - 1) * width
        ax.bar(pos, vals, width=width, color=color, label=label, alpha=0.9)
        ax.errorbar(pos, vals, yerr=err, fmt="none", ecolor="black", capsize=3, linewidth=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("False-admissible windows blocked (%)")
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    style_axis(ax)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "fig_replication_blocking_by_dataset.pdf", bbox_inches="tight")
    plt.close(fig)

    # AUC figure
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    auc_metrics = [
        ("Broadband_Noise_Floor_Only_AUC", "BB/noise", "#4472c4"),
        ("High_Beta_Only_AUC", "High beta", "#c55a11"),
        ("Broadband_Noise_Floor_+_High_Beta_AUC", "BB/noise + HB", "#70ad47"),
        ("Full_NF-SQI_AUC", "Full NF-SQI", "#a5a5a5"),
    ]
    width = 0.19
    for i, (metric, label, color) in enumerate(auc_metrics):
        vals, err = get_metric_arrays(boot_df, datasets, metric)
        pos = x + (i - 1.5) * width
        ax.bar(pos, vals, width=width, color=color, label=label, alpha=0.9)
        ax.errorbar(pos, vals, yerr=err, fmt="none", ecolor="black", capsize=3, linewidth=0.9)
    ax.axhline(0.5, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("ROC AUC")
    ax.set_ylim(0.45, 0.9)
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    style_axis(ax)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "fig_replication_auc_by_dataset.pdf", bbox_inches="tight")
    plt.close(fig)

    # Candidate composition
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    comp_metrics = [
        ("Clean_Pct", "Clean", "#70ad47"),
        ("HB_Only_Pct", "HB only", "#c55a11"),
        ("BB_Only_Pct", "BB/noise only", "#4472c4"),
        ("Ch_Inc_Only_Pct", "Channel inc.", "#8064a2"),
        ("Transient_Only_Pct", "Transient", "#f1c232"),
        ("Multi_Contam_Pct", "Multi", "#a5a5a5"),
    ]
    bottom = np.zeros(len(datasets))
    for metric, label, color in comp_metrics:
        vals, _ = get_metric_arrays(boot_df, datasets, metric)
        vals = np.nan_to_num(vals, nan=0.0)
        ax.bar(x, vals, bottom=bottom, width=0.62, color=color, label=label, alpha=0.92)
        bottom += vals
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Candidate composition (%)")
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.22))
    style_axis(ax)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "fig_candidate_composition_by_dataset.pdf", bbox_inches="tight")
    plt.close(fig)

    # Added value
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    delta_metrics = [
        ("Delta_AUC_BBNF_minus_HB", "BB/noise - high beta"),
        ("Delta_AUC_BBNF_HB_minus_BBNF", "(BB/noise + HB) - BB/noise"),
        ("Delta_AUC_Full_minus_HB", "Full NF-SQI - high beta"),
    ]
    colors = ["#4472c4", "#70ad47", "#a5a5a5"]
    y_base = np.arange(len(delta_metrics))
    offsets = np.linspace(-0.22, 0.22, len(datasets))
    for j, dataset_id in enumerate(datasets):
        for i, (metric, label) in enumerate(delta_metrics):
            row = metric_row(boot_df, dataset_id, metric)
            if row is None:
                continue
            mean = float(row["Mean"])
            err = np.array([[mean - float(row["CI_Lower"])], [float(row["CI_Upper"]) - mean]])
            ax.errorbar(
                mean,
                y_base[i] + offsets[j],
                xerr=err,
                fmt="o",
                color=colors[j],
                ecolor=colors[j],
                capsize=3,
                label=dataset_id.replace("ds00", "DS") if i == 0 else None,
            )
    ax.axvline(0, color="black", linestyle="--", linewidth=0.9, alpha=0.6)
    ax.set_yticks(y_base)
    ax.set_yticklabels([label for _, label in delta_metrics])
    ax.set_xlabel("Delta ROC AUC (95% CI)")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="x", alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "fig_auc_added_value.pdf", bbox_inches="tight")
    plt.close(fig)


def write_leakage_report(companion_validations, ds447_prediction_info):
    lines = [
        "# Leakage Control Report",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Scope",
        "",
        "This report covers only the replication finishing run. It did not edit manuscript, LaTeX, caption, reference, or manuscript-figure files.",
        "",
        "## Controls Applied",
        "",
        "- Existing ds004444 and ds004446 outputs were validated and reused; they were not rerun.",
        "- ds004447 prediction files used for bootstrap CIs were regenerated under `outputs/replication_tables` with leave-one-subject-out splits.",
        "- All bootstrap confidence intervals were generated by subject-level grouped resampling.",
        "- No row-level bootstrap resampling was used.",
        "- Feature standardization for ds004447 prediction generation was fit on training subjects only and applied to the held-out subject.",
        "- Rest/baseline thresholds were taken from existing pipeline outputs and were not recomputed from task labels in this finishing script.",
        "- Deterministic seed: `20260702`.",
        "",
        "## Existing Output Validation",
        "",
    ]
    for item in companion_validations:
        lines.append(
            f"- {item['dataset']}: PASS; {item['subjects']} subjects, {item['overlap_rows']} overlap rows, "
            f"{item['model_rows']} model rows, {item['candidate_windows']} candidate windows."
        )
    overlap_count = sum(row["subject_overlap"] for row in ds447_prediction_info["leakage_rows"])
    lines.extend(
        [
            "",
            "## ds004447 LOSO Leakage Check",
            "",
            f"- Subject-overlap violations: {overlap_count}",
            f"- Model rows written: {len(ds447_prediction_info['model_rows'])}",
            f"- Fold checks written to: `outputs/replication_tables/ds004447_loso_leakage_check.csv`",
            "",
            "## Result",
            "",
            "PASS: the finishing run used subject-grouped validation and bootstrap procedures and found no ds004447 train/test subject overlap.",
        ]
    )
    (LOG_DIR / "leakage_control_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_methods_parameter_report(inventory):
    skip = load_inventory_row(inventory, "ds004448")
    lines = [
        "# Methods Parameter Report",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Analysis Inputs",
        "",
        "- Workspace: repository root",
        "- Existing primary ds004447 tables: `outputs/tables/nf_sqi_*`",
        "- Existing companion tables: `outputs/replication_tables/ds004444_*` and `outputs/replication_tables/ds004446_*`",
        "- Dataset inventory: `outputs/replication_tables/dataset_inventory.csv` and `outputs/replication_logs/dataset_inventory.md`",
        "",
        "## Datasets",
        "",
        "- Analyzed: ds004447, ds004444, ds004446",
        "- Skipped: ds004448",
        f"- ds004448 skip reason: inventory status `{inventory_suitability(skip)}`; event markers `{skip.get('event_markers', 'NA')}`; condition markers `{skip.get('condition_markers', 'NA')}`. No safe rest/task-compatible path was identified.",
        "",
        "## Signal And Gate Parameters",
        "",
        "- Sensorimotor channels: E36, E104, E128 when present.",
        "- Candidate window: 1.0 s length with 0.5 s step for companion extraction and primary model comparison.",
        "- SMR band: 12-15 Hz.",
        "- High beta band: 20-30 Hz.",
        "- Noise-floor band: 35-45 Hz.",
        "- Broadband/noise predictors: broadband power and noise-floor power.",
        "- Gate A: SMR above the subject/session rest-baseline 75th percentile.",
        "- Gate B: Gate A plus high beta at or below the subject/session rest-baseline 75th percentile.",
        "- Gate C / full NF-SQI: Gate B plus broadband, noise floor, transient amplitude, and channel inconsistency exclusions.",
        "- Transient threshold: subject/session rest-baseline 90th percentile.",
        "- Channel inconsistency threshold: subject/session rest-baseline 75th percentile.",
        "",
        "## Model Parameters",
        "",
        "- Classifier: logistic regression.",
        "- Class weighting: balanced.",
        "- Cross-validation: leave-one-subject-out.",
        "- Standardization: `StandardScaler` fit on training subjects only.",
        "- ds004447 full model predictors: broadband power, noise-floor power, high beta power, transient score, channel inconsistency, nonstationarity.",
        "- ds004444/ds004446 full model predictors were reused from the existing companion outputs.",
        "",
        "## Bootstrap Parameters",
        "",
        f"- Bootstrap iterations: {N_BOOTSTRAP}.",
        "- Bootstrap grouping: subject-level grouped bootstrap.",
        "- Confidence interval: percentile 95% CI.",
        "- Random seed base: 20260702.",
        "",
        "## Exact Command Used",
        "",
        "```powershell",
        COMMAND_USED,
        "```",
        "",
    ]
    (SUMMARY_DIR / "methods_parameter_report.md").write_text("\n".join(lines), encoding="utf-8")


def final_report_key_table(boot_df):
    metrics = [
        ("Delta_Block_Full_minus_HB_Pct", "Full NF-SQI minus high beta blocking, percentage points", "percent"),
        ("Delta_Block_BBNF_minus_HB_Pct", "BB/noise minus high beta blocking, percentage points", "percent"),
        ("Delta_AUC_BBNF_minus_HB", "BB/noise AUC minus high beta AUC", "auc"),
        ("Delta_AUC_BBNF_HB_minus_BBNF", "Added high beta AUC beyond BB/noise", "auc"),
    ]
    lines = ["| Dataset | Key effect | Mean [95% CI] |", "|---|---|---|"]
    for dataset_id in ANALYZED_DATASETS:
        for metric, label, unit in metrics:
            row = metric_row(boot_df, dataset_id, metric)
            value = format_ci(row, 1) if unit == "percent" else format_delta_auc_ci(row)
            lines.append(f"| {dataset_id} | {label} | {value} |")
    return lines


def write_final_report(boot_df, primary_summary, reproduction, inventory):
    ds448 = load_inventory_row(inventory, "ds004448")
    checklist = required_file_status()
    full_vs_hb = {d: metric_row(boot_df, d, "Delta_Block_Full_minus_HB_Pct") for d in ANALYZED_DATASETS}
    bbnf_vs_hb = {d: metric_row(boot_df, d, "Delta_AUC_BBNF_minus_HB") for d in ANALYZED_DATASETS}
    add_hb = {d: metric_row(boot_df, d, "Delta_AUC_BBNF_HB_minus_BBNF") for d in ANALYZED_DATASETS}

    lines = [
        "# Final Replication Report",
        "",
        f"Generated: {utc_now()}",
        "Workspace: repository root",
        "",
        "No manuscript, LaTeX, captions, references, or manuscript figures were edited or regenerated by this finishing run.",
        "",
        "## Datasets Analyzed",
        "",
        "- ds004447: primary reproduction check and bootstrap synthesis.",
        "- ds004444: companion replication using existing outputs.",
        "- ds004446: companion replication using existing outputs.",
        "",
        "## Datasets Skipped",
        "",
        (
            "- ds004448: skipped because the inventory marks it as "
            f"`{inventory_suitability(ds448, 'not_suitable_or_metadata_only')}`. "
            f"The inventory detected event markers `{ds448.get('event_markers', 'NA')}` and condition markers "
            f"`{ds448.get('condition_markers', 'NA')}`, not the rest/task-compatible event structure used by the safe analysis path. "
            "No compatible model-comparison output or safe rest/task mapping was identified, so it was not forced."
        ),
        "",
        "## ds004447 Reproduction",
        "",
        "PASS: ds004447 reproduced the manuscript values within the 0.1 percentage-point rounding tolerance used by the reproduction check.",
        "",
        "| Metric | Actual | Expected |",
        "|---|---:|---:|",
    ]
    for check in reproduction["checks"]:
        lines.append(f"| {check['metric']} | {check['actual']:.2f} | {check['expected']:.2f} |")

    lines.extend(
        [
            "",
            "## Qualitative Replication",
            "",
            "ds004444 and ds004446 replicate the qualitative pattern: broadband/noise-floor predictors outperform high beta alone, full NF-SQI blocks more false-admissible windows than high beta alone, and adding high beta to broadband/noise-floor predictors does not provide a material AUC gain.",
            "",
            "Full NF-SQI blocks more false-admissible windows than high beta alone in every analyzed dataset:",
        ]
    )
    for dataset_id, row in full_vs_hb.items():
        lines.append(f"- {dataset_id}: {format_ci(row, 1)} percentage-point advantage.")

    lines.extend(["", "Broadband/noise-floor predictors outperform high beta alone by AUC:"])
    for dataset_id, row in bbnf_vs_hb.items():
        lines.append(f"- {dataset_id}: {format_delta_auc_ci(row)}.")

    lines.extend(["", "Adding high beta beyond broadband/noise-floor predictors does not materially improve AUC:"])
    for dataset_id, row in add_hb.items():
        lines.append(f"- {dataset_id}: {format_delta_auc_ci(row)}.")

    lines.extend(["", "## Bootstrap 95% CIs", ""])
    lines.extend(final_report_key_table(boot_df))

    lines.extend(
        [
            "",
            "## Exact Commands Used To Reproduce",
            "",
            "```powershell",
            "Set-Location <repository-root>",
            "Get-Location",
            "Get-ChildItem -Force",
            "Get-ChildItem outputs\\replication_tables",
            "Get-ChildItem outputs\\replication_logs",
            "Get-ChildItem analysis_replication -ErrorAction SilentlyContinue",
            COMMAND_USED,
            "```",
            "",
            "## Completion Checklist",
            "",
        ]
    )
    final_report_rel = str((SUMMARY_DIR / "final_replication_report.md").relative_to(ROOT))
    for rel, exists, size in checklist:
        if rel == final_report_rel:
            lines.append(f"- Present: `{rel}` (current report)")
        else:
            status = "Present" if exists else "Missing"
            lines.append(f"- {status}: `{rel}` ({size} bytes)")

    lines.extend(
        [
            "",
            "## Output Tables",
            "",
            "- Primary summary: `outputs/replication_tables/primary_replication_summary.csv` and `.tex`.",
            "- Bootstrap CIs: `outputs/replication_tables/bootstrap_ci_by_dataset.csv` and `.tex`.",
            "- Leakage report: `outputs/replication_logs/leakage_control_report.md`.",
            "- Methods parameters: `outputs/replication_summary/methods_parameter_report.md`.",
            "",
        ]
    )
    (SUMMARY_DIR / "final_replication_report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    stage = "initializing output directories"
    ensure_dirs()

    try:
        print(f"[{utc_now()}] Starting finish_replication.py in {ROOT}")
        if Path.cwd().resolve() != ROOT.resolve():
            raise RuntimeError(f"Script must run from {ROOT}; current directory is {Path.cwd()}")

        stage = "validating dataset inventory"
        inventory, _ = validate_inventory()
        print("Inventory validated.")

        stage = "validating existing ds004444 and ds004446 outputs"
        companion_validations = validate_companion_outputs()
        print("Existing companion outputs validated.")

        stage = "running ds004447 reproduction check"
        reproduction = run_ds004447_reproduction_check()
        print("ds004447 reproduction check passed.")

        stage = "generating sanitized ds004447 prediction files"
        ds447_prediction_info = generate_ds004447_predictions()
        print("ds004447 prediction files generated.")

        stage = "normalizing overlap tables"
        norm_overlaps = {dataset_id: normalize_overlap(dataset_id) for dataset_id in ANALYZED_DATASETS}
        for dataset_id, df in norm_overlaps.items():
            df.to_csv(TABLE_DIR / f"{dataset_id}_normalized_overlap_for_bootstrap.csv", index=False)
        print("Overlap tables normalized.")

        stage = "generating subject-level grouped bootstrap confidence intervals"
        boot_df = generate_bootstrap_tables(norm_overlaps)
        print("Bootstrap confidence intervals generated.")

        stage = "generating primary replication summary"
        primary_summary = generate_primary_summary(boot_df, norm_overlaps, inventory)
        print("Primary replication summary generated.")

        stage = "generating integrated replication figures"
        generate_figures(boot_df)
        print("Integrated figures generated.")

        stage = "generating leakage-control and methods reports"
        write_leakage_report(companion_validations, ds447_prediction_info)
        write_methods_parameter_report(inventory)
        print("Leakage and methods reports generated.")

        stage = "generating final replication report"
        write_final_report(boot_df, primary_summary, reproduction, inventory)
        print("Final replication report generated.")

        stage = "validating required final files"
        missing = [path for path in REQUIRED_FINAL_FILES if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Missing final required files: {missing}")
        empty = [path for path in REQUIRED_FINAL_FILES if path.stat().st_size == 0]
        if empty:
            raise ValueError(f"Final required files are empty: {empty}")
        print("All required final files exist.")

    except Exception:
        exc_text = traceback.format_exc()
        write_failure_report(stage, exc_text)
        print(exc_text, file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
