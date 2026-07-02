from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mne
import numpy as np
import pandas as pd
import requests
from scipy import signal, stats

from utils.manifest import write_manifest
from utils.paths import ensure_repo_structure


OPENNEURO_DATASETS = {
    "ds004444": "1.0.1",
    "ds004446": "1.0.1",
    "ds004447": "1.0.1",
    "ds004448": "1.0.2",
}
SELECTED_DATASET = "ds004447"
SELECTED_TAG = "1.0.1"
PILOT_DATASET = "ds004446"
TASK_NAME = "task-smrbmi"
SENSORIMOTOR_CHANNELS = ["E36", "E104", "E128"]
PRIMARY_CONDITION = "task"
SMR_BAND = (12.0, 15.0)
HIGH_BETA_BAND = (20.0, 30.0)
BROADBAND_RANGE = (4.0, 45.0)
NOISE_FLOOR_BAND = (35.0, 45.0)
STATE_FS = 20.0
MIN_EPISODE_S = 0.10
THRESHOLD_DEFS = ["p75", "p80", "p90", "z1", "mad1"]
PRIMARY_THRESHOLD = "p75"
USER_AGENT = "smr-cn-revision-beta-escape/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_gb(value: int | float | None) -> float:
    if value is None:
        return float("nan")
    return round(float(value) / 1_000_000_000.0, 3)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_table(df: pd.DataFrame, name: str) -> Path:
    path = ROOT / "outputs" / "tables" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def write_report(text: str, name: str) -> Path:
    path = ROOT / "outputs" / "reports" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now()} {message}\n")


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "legend.fontsize": 7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "figure.dpi": 130,
            "savefig.dpi": 240,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.20,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save_figure(fig: plt.Figure, source: pd.DataFrame, stem: str) -> None:
    table_path = ROOT / "outputs" / "tables" / f"{stem}_source.csv"
    fig_dir = ROOT / "outputs" / "figures"
    table_path.parent.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    source.to_csv(table_path, index=False)
    for ext in ["pdf", "svg", "png"]:
        fig.savefig(fig_dir / f"{stem}.{ext}", bbox_inches="tight")
    plt.close(fig)


def load_openneuro_index(dataset_id: str) -> dict[str, Any]:
    tag = OPENNEURO_DATASETS[dataset_id]
    path = ROOT / "data" / "manifests" / f"openneuro_{dataset_id}_{tag}_file_index.json"
    if not path.exists():
        raise FileNotFoundError(f"OpenNeuro index missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def index_file_rows(dataset_id: str) -> pd.DataFrame:
    tag = OPENNEURO_DATASETS[dataset_id]
    path = ROOT / "data" / "manifests" / f"openneuro_{dataset_id}_{tag}_file_index.csv"
    if not path.exists():
        raise FileNotFoundError(f"OpenNeuro CSV index missing: {path}")
    return pd.read_csv(path)


def dataset_summary_from_index(dataset_id: str) -> dict[str, Any]:
    index = load_openneuro_index(dataset_id)
    desc = index.get("snapshot", {}).get("description") or {}
    files = [f for f in index["snapshot"]["files"] if not f.get("directory")]
    edf_files = [f for f in files if f["filename"].lower().endswith(".edf")]
    subjects = sorted({m.group(1) for f in edf_files if (m := re.search(r"(sub-\d+)", f["filename"]))})
    sessions = sorted({m.group(1) for f in edf_files if (m := re.search(r"(ses-\d+)", f["filename"]))}, key=session_sort_key)
    return {
        "dataset_id": dataset_id,
        "dataset_name": desc.get("Name") or index.get("dataset", {}).get("name", ""),
        "snapshot_tag": index["snapshot"]["tag"],
        "source_url": f"https://openneuro.org/datasets/{dataset_id}/versions/{index['snapshot']['tag']}",
        "dataset_doi": desc.get("DatasetDOI", ""),
        "license": desc.get("License", ""),
        "public": bool(index.get("dataset", {}).get("public")),
        "file_count": len(files),
        "edf_file_count": len(edf_files),
        "full_size_bytes": int(sum(int(f.get("size") or 0) for f in files)),
        "full_size_gb": bytes_gb(sum(int(f.get("size") or 0) for f in files)),
        "subject_count_from_index": len(subjects),
        "session_count_from_index": len(sessions),
        "subjects_from_index": ";".join(subjects),
        "sessions_from_index": ";".join(sessions),
    }


def session_sort_key(session: str) -> int:
    try:
        return int(session.split("-")[1])
    except Exception:
        return 0


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def scan_local_inventory(stage: str) -> pd.DataFrame:
    rows = []
    raw_openneuro = ROOT / "data" / "raw" / "openneuro"
    for dataset_id in OPENNEURO_DATASETS:
        raw_root = raw_openneuro / dataset_id
        index_summary = dataset_summary_from_index(dataset_id)
        files = sorted(raw_root.rglob("*")) if raw_root.exists() else []
        files = [p for p in files if p.is_file()]
        edfs = [p for p in files if p.suffix.lower() == ".edf"]
        subjects = sorted({m.group(1) for p in edfs if (m := re.search(r"(sub-\d+)", str(p)))})
        sessions = sorted({m.group(1) for p in edfs if (m := re.search(r"(ses-\d+)", str(p)))}, key=session_sort_key)
        channel_names: list[str] = []
        sampling_rates: set[str] = set()
        event_values: set[str] = set()
        instructions: set[str] = set()
        reward_like: set[str] = set()
        for channels_path in sorted(raw_root.glob("sub-*/ses-*/eeg/*_channels.tsv"))[:1]:
            try:
                ch = read_tsv(channels_path)
                if "name" in ch:
                    channel_names = ch["name"].astype(str).tolist()
            except Exception:
                pass
        for eeg_json in sorted(raw_root.glob("sub-*/ses-*/eeg/*_eeg.json"))[:10]:
            try:
                meta = read_json(eeg_json)
                if "SamplingFrequency" in meta:
                    sampling_rates.add(str(meta["SamplingFrequency"]))
            except Exception:
                pass
        for events_path in sorted(raw_root.glob("sub-*/ses-*/eeg/*_events.tsv"))[:20]:
            try:
                ev = read_tsv(events_path)
                if "value" in ev:
                    event_values.update(ev["value"].astype(str).unique().tolist())
                if "instruction" in ev:
                    instructions.update(ev["instruction"].astype(str).unique().tolist())
                for col in ev.columns:
                    if re.search(r"reward|feedback|score|success", col, re.I):
                        reward_like.add(col)
                    vals = ev[col].astype(str).str.lower()
                    if vals.str.contains("reward|feedback|score|success", regex=True).any():
                        reward_like.add(col)
            except Exception:
                pass
        sensorimotor = [ch for ch in SENSORIMOTOR_CHANNELS if ch in channel_names]
        has_primary = PRIMARY_CONDITION in instructions
        suitable = bool(edfs and len(subjects) >= 1 and sensorimotor and sampling_rates and has_primary)
        rows.append(
            {
                "inventory_stage": stage,
                "dataset_id": dataset_id,
                "raw_dataset_present": raw_root.exists(),
                "local_file_count": len(files),
                "local_eeg_file_count": len(edfs),
                "local_size_bytes": int(sum(p.stat().st_size for p in files)),
                "local_size_gb": bytes_gb(sum(p.stat().st_size for p in files)),
                "local_subject_count": len(subjects),
                "local_subjects": ";".join(subjects),
                "local_session_count": len(sessions),
                "local_sessions": ";".join(sessions),
                "index_subject_count": index_summary["subject_count_from_index"],
                "index_session_count": index_summary["session_count_from_index"],
                "channels": ";".join(channel_names),
                "sensorimotor_channels_found": ";".join(sensorimotor),
                "sampling_rates": ";".join(sorted(sampling_rates)),
                "event_markers": ";".join(sorted(event_values)),
                "condition_markers": ";".join(sorted(instructions)),
                "feedback_reward_markers": ";".join(sorted(reward_like)) if reward_like else "none_detected",
                "suitability_for_beta_state_persistence": "suitable" if suitable else "not_suitable_or_metadata_only",
                "suitability_notes": (
                    "Raw EDFs plus task events and sensorimotor channels are present."
                    if suitable
                    else "No local EDFs or missing task/sensorimotor metadata in local raw tree."
                ),
            }
        )
    return pd.DataFrame(rows)


def write_local_inventory_outputs(inventory: pd.DataFrame, stage_note: str) -> None:
    write_table(inventory, "beta_escape_local_data_inventory.csv")
    present = inventory[inventory["raw_dataset_present"] == True].copy()
    lines = [
        "# Local Data Inventory",
        "",
        f"Created: {utc_now()}",
        "",
        stage_note,
        "",
        "This inventory inspected local OpenNeuro raw data trees and metadata indexes only. It did not inspect or edit manuscript files.",
        "",
    ]
    if present.empty:
        lines.append("No local raw OpenNeuro EEG datasets were present.")
    else:
        lines.append("Local raw datasets present:")
        lines.append("")
        for _, row in present.iterrows():
            lines.extend(
                [
                    f"- Dataset: `{row['dataset_id']}`",
                    f"  - Subjects: {row['local_subject_count']} (`{row['local_subjects']}`)",
                    f"  - Sessions: {row['local_session_count']} (`{row['local_sessions']}`)",
                    f"  - Files: {row['local_file_count']} total, {row['local_eeg_file_count']} EDF",
                    f"  - Channels: {len(str(row['channels']).split(';')) if row['channels'] else 0}; sensorimotor used: `{row['sensorimotor_channels_found']}`",
                    f"  - Sampling rates: `{row['sampling_rates']}`",
                    f"  - Event markers: `{row['event_markers']}`; instructions: `{row['condition_markers']}`",
                    f"  - Feedback/reward markers: `{row['feedback_reward_markers']}`",
                    f"  - Suitability: `{row['suitability_for_beta_state_persistence']}`",
                    "",
                ]
            )
    write_report("\n".join(lines) + "\n", "beta_escape_local_data_inventory.md")


def select_first_last_subset(dataset_id: str) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    index = load_openneuro_index(dataset_id)
    files = [f for f in index["snapshot"]["files"] if not f.get("directory")]
    by_name = {f["filename"]: f for f in files}
    edf_files = [f for f in files if f["filename"].endswith("_eeg.edf")]
    by_subject: dict[str, list[str]] = defaultdict(list)
    for item in edf_files:
        m = re.search(r"(sub-\d+)/(ses-\d+)/eeg/", item["filename"])
        if m:
            by_subject[m.group(1)].append(m.group(2))
    selected_names: set[str] = {
        "CHANGES",
        "README",
        "dataset_description.json",
        "participants.tsv",
        "participants.json",
        "task-smrbmi_eeg.json",
        "task-smrbmi_events.json",
    }
    subject_session_rows = []
    for subject in sorted(by_subject):
        sessions = sorted(set(by_subject[subject]), key=session_sort_key)
        if not sessions:
            continue
        first = sessions[0]
        last = sessions[-1]
        subject_session_rows.append(
            {
                "dataset_id": dataset_id,
                "subject": subject,
                "available_session_count": len(sessions),
                "available_sessions": ";".join(sessions),
                "selected_first_session": first,
                "selected_last_session": last,
                "selected_session_count": len({first, last}),
            }
        )
        for session in sorted({first, last}, key=session_sort_key):
            prefix = f"{subject}/{session}/eeg/{subject}_{session}_{TASK_NAME}"
            for suffix in ["_eeg.edf", "_eeg.json", "_channels.tsv", "_electrodes.tsv", "_events.tsv"]:
                name = f"{prefix}{suffix}"
                if name in by_name:
                    selected_names.add(name)
    selected_files = [by_name[name] for name in sorted(selected_names) if name in by_name]
    rows = []
    for item in selected_files:
        subject = ""
        session = ""
        if m := re.search(r"(sub-\d+)/(ses-\d+)", item["filename"]):
            subject, session = m.group(1), m.group(2)
        rows.append(
            {
                "dataset_id": dataset_id,
                "snapshot_tag": index["snapshot"]["tag"],
                "filename": item["filename"],
                "subject": subject,
                "session": session,
                "size_bytes": int(item.get("size") or 0),
                "size_gb": bytes_gb(int(item.get("size") or 0)),
                "annexed": bool(item.get("annexed")),
                "url_available": bool(item.get("urls")),
                "selection_rule": "all_subjects_first_and_last_available_session_plus_top_level_sidecars",
            }
        )
    return pd.DataFrame(rows), selected_files


def build_candidate_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    selected_subset, _ = select_first_last_subset(SELECTED_DATASET)
    for dataset_id in OPENNEURO_DATASETS:
        summary = dataset_summary_from_index(dataset_id)
        subset_strategy = "not_selected"
        subset_n_subjects = ""
        subset_n_sessions = ""
        subset_size = ""
        acquisition_decision = "not_selected"
        if dataset_id == SELECTED_DATASET:
            subset_strategy = "first_and_last_available_sessions_for_all_indexed_subjects"
            subset_n_subjects = int(selected_subset["subject"].replace("", np.nan).dropna().nunique())
            subset_n_sessions = int(selected_subset["session"].replace("", np.nan).dropna().nunique())
            subset_size = int(selected_subset["size_bytes"].sum())
            acquisition_decision = "selected_for_download"
        rows.append(
            {
                **summary,
                "expected_modality": "EEG-BIDS EDF",
                "expected_channels": "129 channels in sidecar; analysis predeclares E36/E104/E128 as C3/C4/Cz equivalents",
                "expected_task": "SMR-BCI/neurofeedback motor-imagery blocks with rest/task/interval markers",
                "terms_status": "acceptable_for_secondary_analysis" if summary["license"] == "CC0" and summary["public"] else "not_acceptable_or_unclear",
                "full_download_feasible": summary["full_size_gb"] <= 25.0,
                "subset_strategy": subset_strategy,
                "subset_subject_count": subset_n_subjects,
                "subset_session_label_count": subset_n_sessions,
                "subset_size_bytes": subset_size,
                "subset_size_gb": bytes_gb(subset_size) if subset_size != "" else "",
                "acquisition_decision": acquisition_decision,
            }
        )
    rows.append(
        {
            "dataset_id": "figshare_14153504",
            "dataset_name": "Continuous SMR-based BCI learning in a large population",
            "snapshot_tag": "",
            "source_url": "https://doi.org/10.6084/m9.figshare.14153504",
            "dataset_doi": "10.1038/s41597-021-00883-1",
            "license": "not_verified_in_local_metadata",
            "public": "",
            "file_count": "",
            "edf_file_count": "",
            "full_size_bytes": "",
            "full_size_gb": "",
            "subject_count_from_index": 62,
            "session_count_from_index": "up_to_11",
            "subjects_from_index": "",
            "sessions_from_index": "",
            "expected_modality": "EEG and behavioral BCI learning data",
            "expected_channels": "64 EEG channels reported by Scientific Data article",
            "expected_task": "continuous online SMR-BCI control and learning",
            "terms_status": "not_downloaded_license_or_file_index_unverified",
            "full_download_feasible": "not_estimated",
            "subset_strategy": "not_selected_because_OpenNeuro_CC0_22_subject_subset_was_available",
            "subset_subject_count": "",
            "subset_session_label_count": "",
            "subset_size_bytes": "",
            "subset_size_gb": "",
            "acquisition_decision": "not_selected",
        }
    )
    candidates = pd.DataFrame(rows)
    return candidates, selected_subset


def download_one_file(item: dict[str, Any], dest: Path, log_path: Path) -> dict[str, Any]:
    expected = int(item.get("size") or 0)
    url = item.get("urls", [""])[0]
    dest.parent.mkdir(parents=True, exist_ok=True)
    status = "downloaded"
    if dest.exists() and (not expected or dest.stat().st_size == expected):
        status = "already_present"
    else:
        tmp = dest.with_suffix(dest.suffix + ".part")
        if tmp.exists():
            tmp.unlink()
        append_log(log_path, f"GET {item['filename']} expected_size={expected}")
        with requests.get(url, stream=True, timeout=240, headers={"User-Agent": USER_AGENT}) as response:
            response.raise_for_status()
            with tmp.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        actual_tmp = tmp.stat().st_size
        if expected and actual_tmp != expected:
            raise RuntimeError(f"Downloaded size mismatch for {item['filename']}: expected {expected}, got {actual_tmp}")
        tmp.replace(dest)
    actual = dest.stat().st_size if dest.exists() else 0
    return {
        "dataset_id": SELECTED_DATASET,
        "snapshot_tag": SELECTED_TAG,
        "file_path": rel(dest),
        "filename": item["filename"],
        "file_size_bytes": actual,
        "expected_size_bytes": expected,
        "source": url.split("?")[0],
        "download_date_utc": utc_now(),
        "checksum_sha256": sha256_file(dest) if dest.exists() else "",
        "status": status if (not expected or actual == expected) else "size_mismatch",
        "annexed": bool(item.get("annexed")),
    }


def run_acquisition() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ensure_repo_structure(ROOT)
    log_path = ROOT / "outputs" / "logs" / "beta_escape_data_acquisition.log"
    log_path.write_text(f"{utc_now()} beta_escape acquisition started\n", encoding="utf-8")
    pre_inventory = scan_local_inventory("before_beta_escape_download")
    write_local_inventory_outputs(
        pre_inventory,
        "Stage: before attempting the beta_escape larger-dataset download.",
    )
    candidates, selected_subset = build_candidate_table()
    write_table(candidates, "beta_escape_candidate_datasets.csv")
    selected_row = candidates[candidates["dataset_id"] == SELECTED_DATASET].iloc[0]
    local_selected = pre_inventory[pre_inventory["dataset_id"] == SELECTED_DATASET].iloc[0]
    should_download = (
        selected_row["terms_status"] == "acceptable_for_secondary_analysis"
        and int(selected_row["subset_subject_count"]) >= 20
        and float(selected_row["subset_size_gb"]) < 10.0
        and int(local_selected["local_subject_count"]) < int(selected_row["subset_subject_count"])
    )
    plan = f"""# Data Acquisition Plan

Created: {utc_now()}

Local data status:

- The pre-download local inventory showed `{PILOT_DATASET}` as the only usable raw OpenNeuro EEG dataset if `{SELECTED_DATASET}` was not already present.
- The previous local subset is not sufficient for a conceptually novel empirical validation because it contains fewer than 20 subjects.

Candidate decision:

- OpenNeuro `{SELECTED_DATASET}` was selected because it is a sibling BMI-HDEEG SMR-BCI dataset with 22 indexed subjects and up to 20 sessions.
- Official metadata/index fields record public access and `CC0` license for `{SELECTED_DATASET}`.
- Full snapshot size is {selected_row['full_size_gb']} GB. The controlled subset selects first and last available sessions for every subject, estimated at {selected_row['subset_size_gb']} GB.
- The selected subset meets the minimum target of at least 20 subjects and preserves early/late longitudinal contrast.

Download rule:

- Download full EEG only if feasible; otherwise use the predeclared first/last-session subset.
- For this run, the subset is feasible and was selected.
- Proceed with download: `{should_download}`.

Non-selected candidates:

- `{PILOT_DATASET}` already existed locally but was too small in its local subset.
- `ds004444` and `ds004448` are larger full snapshots; they remain backup candidates.
- The Figshare/Scientific Data longitudinal dataset was not selected because a feasible CC0 OpenNeuro subset with 22 subjects was available and local file-index/license metadata for Figshare were not verified here.
"""
    write_report(plan, "beta_escape_data_acquisition_plan.md")
    selected_files_df, selected_files = select_first_last_subset(SELECTED_DATASET)
    raw_root = ROOT / "data" / "raw" / "openneuro" / SELECTED_DATASET
    rows = []
    if should_download:
        append_log(log_path, f"selected {SELECTED_DATASET} subset files={len(selected_files)} bytes={int(selected_files_df['size_bytes'].sum())}")
        for idx, item in enumerate(selected_files, start=1):
            append_log(log_path, f"download_or_verify {idx}/{len(selected_files)} {item['filename']}")
            rows.append(download_one_file(item, raw_root / item["filename"], log_path))
    else:
        append_log(log_path, "download skipped because selected subset is already locally present or decision gates failed")
        for item in selected_files:
            dest = raw_root / item["filename"]
            if dest.exists():
                rows.append(download_one_file(item, dest, log_path))
            else:
                rows.append(
                    {
                        "dataset_id": SELECTED_DATASET,
                        "snapshot_tag": SELECTED_TAG,
                        "file_path": rel(dest),
                        "filename": item["filename"],
                        "file_size_bytes": 0,
                        "expected_size_bytes": int(item.get("size") or 0),
                        "source": item.get("urls", [""])[0].split("?")[0],
                        "download_date_utc": utc_now(),
                        "checksum_sha256": "",
                        "status": "not_downloaded",
                        "annexed": bool(item.get("annexed")),
                    }
                )
    download_manifest = pd.DataFrame(rows)
    if not download_manifest.empty:
        download_manifest = download_manifest.merge(
            selected_files_df[["filename", "subject", "session", "selection_rule"]],
            on="filename",
            how="left",
        )
    write_table(download_manifest, "beta_escape_download_manifest.csv")
    post_inventory = scan_local_inventory("after_beta_escape_download")
    after_report = inventory_after_download_report(post_inventory, download_manifest)
    write_report(after_report, "beta_escape_dataset_inventory_after_download.md")
    append_log(log_path, "acquisition completed")
    return pre_inventory, candidates, download_manifest


def inventory_after_download_report(inventory: pd.DataFrame, download_manifest: pd.DataFrame) -> str:
    selected = inventory[inventory["dataset_id"] == SELECTED_DATASET].iloc[0]
    ok_files = download_manifest[download_manifest["status"].isin(["downloaded", "already_present"])] if not download_manifest.empty else pd.DataFrame()
    return f"""# Dataset Inventory After Download

Created: {utc_now()}

Selected dataset: `{SELECTED_DATASET}`.

Downloaded/verified files: {len(ok_files)} of {len(download_manifest)} selected files.

Local raw EEG inventory after download:

- Subjects: {selected['local_subject_count']} (`{selected['local_subjects']}`)
- Sessions: {selected['local_session_count']} (`{selected['local_sessions']}`)
- EDF files: {selected['local_eeg_file_count']}
- Total local size: {selected['local_size_gb']} GB
- Channels: `{selected['sensorimotor_channels_found']}` selected from the downloaded sidecar
- Sampling rates: `{selected['sampling_rates']}`
- Event markers: `{selected['event_markers']}` with condition labels `{selected['condition_markers']}`
- Feedback/reward markers: `{selected['feedback_reward_markers']}`
- Suitability for beta-state persistence analysis: `{selected['suitability_for_beta_state_persistence']}`

No true reward/feedback markers were detected in the event sidecars. Analyses below therefore use early/late session contrasts and do not treat proxy states as real reward events.
"""


def parse_subject_session(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    if not m:
        return "", ""
    return m.group(1), m.group(2)


def session_phase(session: str, subject_sessions: dict[str, list[str]], subject: str) -> str:
    sessions = subject_sessions.get(subject, [])
    if not sessions:
        return "unknown"
    if session == sessions[0]:
        return "early"
    if session == sessions[-1]:
        return "late"
    return "middle"


def read_events_for_edf(edf_path: Path, raw_duration_s: float) -> pd.DataFrame:
    subject, session_name = parse_subject_session(edf_path)
    path = edf_path.parent / f"{subject}_{session_name}_{TASK_NAME}_events.tsv"
    events = read_tsv(path)
    onset = events["onset"].astype(float).to_numpy()
    if np.nanmax(onset) > raw_duration_s * 10.0:
        onset = onset / 1000.0
    events["onset_s"] = onset
    events["duration_s"] = events["duration"].astype(float)
    return events


def band_envelope(x: np.ndarray, fs: float, band: tuple[float, float]) -> np.ndarray:
    nyq = fs / 2.0
    low = max(0.001, band[0] / nyq)
    high = min(0.999, band[1] / nyq)
    sos = signal.butter(4, [low, high], btype="bandpass", output="sos")
    filtered = signal.sosfiltfilt(sos, x)
    return np.abs(signal.hilbert(filtered))


def welch_psd(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    nperseg = min(len(x), max(128, int(round(fs * 4.0))))
    if nperseg < 128:
        return np.array([]), np.array([])
    return signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2)


def bandpower_from_psd(freqs: np.ndarray, psd: np.ndarray, band: tuple[float, float]) -> float:
    mask = (freqs >= band[0]) & (freqs <= band[1])
    if mask.sum() < 2:
        return float("nan")
    return float(np.trapz(psd[mask], freqs[mask]))


def spectral_metrics(x: np.ndarray, fs: float) -> dict[str, float]:
    freqs, psd = welch_psd(x, fs)
    if len(freqs) == 0:
        return {
            "smr_power": np.nan,
            "high_beta_power": np.nan,
            "broadband_non_target_power": np.nan,
            "noise_floor_power": np.nan,
            "spectral_slope": np.nan,
            "high_beta_residual_log10": np.nan,
        }
    smr_power = bandpower_from_psd(freqs, psd, SMR_BAND)
    beta_power = bandpower_from_psd(freqs, psd, HIGH_BETA_BAND)
    noise = bandpower_from_psd(freqs, psd, NOISE_FLOOR_BAND)
    broadband_mask = (
        (freqs >= BROADBAND_RANGE[0])
        & (freqs <= BROADBAND_RANGE[1])
        & ~((freqs >= SMR_BAND[0]) & (freqs <= SMR_BAND[1]))
        & ~((freqs >= HIGH_BETA_BAND[0]) & (freqs <= HIGH_BETA_BAND[1]))
    )
    broadband = float(np.trapz(psd[broadband_mask], freqs[broadband_mask])) if broadband_mask.sum() >= 2 else np.nan
    slope_mask = broadband_mask & (psd > 0) & (freqs > 0)
    slope = np.nan
    residual = np.nan
    if slope_mask.sum() >= 5:
        xx = np.log10(freqs[slope_mask])
        yy = np.log10(psd[slope_mask])
        slope_fit, intercept = np.polyfit(xx, yy, deg=1)
        beta_mask = (freqs >= HIGH_BETA_BAND[0]) & (freqs <= HIGH_BETA_BAND[1]) & (psd > 0)
        if beta_mask.sum() >= 2:
            actual = float(np.mean(np.log10(psd[beta_mask])))
            predicted = float(np.mean(intercept + slope_fit * np.log10(freqs[beta_mask])))
            residual = actual - predicted
        slope = float(slope_fit)
    return {
        "smr_power": smr_power,
        "high_beta_power": beta_power,
        "broadband_non_target_power": broadband,
        "noise_floor_power": noise,
        "spectral_slope": slope,
        "high_beta_residual_log10": residual,
    }


def event_segments(events: pd.DataFrame, condition: str, fs: float, n_samples: int) -> list[tuple[int, int]]:
    segments = []
    for _, row in events[events["instruction"].astype(str) == condition].iterrows():
        start = int(round(float(row["onset_s"]) * fs))
        stop = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
        start = max(0, min(start, n_samples))
        stop = max(start, min(stop, n_samples))
        if stop - start >= int(fs):
            segments.append((start, stop))
    return segments


def concat_segments(x: np.ndarray, segments: list[tuple[int, int]]) -> np.ndarray:
    if not segments:
        return np.array([], dtype=float)
    return np.concatenate([x[start:stop] for start, stop in segments])


def values_from_segments(x: np.ndarray, segments: list[tuple[int, int]], step: int) -> list[np.ndarray]:
    values = []
    for start, stop in segments:
        if stop <= start:
            continue
        idx = np.arange(start, stop, step)
        if len(idx) >= 2:
            values.append(x[idx])
    return values


def threshold_values(rest_beta: np.ndarray) -> dict[str, float]:
    clean = rest_beta[np.isfinite(rest_beta)]
    if clean.size == 0:
        return {name: np.nan for name in THRESHOLD_DEFS}
    med = float(np.nanmedian(clean))
    mad = float(np.nanmedian(np.abs(clean - med)))
    return {
        "p75": float(np.nanpercentile(clean, 75)),
        "p80": float(np.nanpercentile(clean, 80)),
        "p90": float(np.nanpercentile(clean, 90)),
        "z1": float(np.nanmean(clean) + np.nanstd(clean)),
        "mad1": float(med + 1.4826 * mad),
    }


def mask_episode_durations(mask: np.ndarray, fs_eff: float) -> list[tuple[int, int, float]]:
    if mask.size == 0:
        return []
    edges = np.diff(np.r_[False, mask.astype(bool), False].astype(int))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    episodes = []
    for start, end in zip(starts, ends):
        duration = float((end - start) / fs_eff)
        if duration >= MIN_EPISODE_S:
            episodes.append((int(start), int(end), duration))
    return episodes


def transition_counts(states: np.ndarray) -> Counter:
    counts: Counter = Counter()
    if states.size < 2:
        return counts
    for a, b in zip(states[:-1], states[1:]):
        counts[(int(a), int(b))] += 1
    return counts


def analyze_state_segments(
    beta_env: np.ndarray,
    smr_env: np.ndarray,
    broad_env: np.ndarray,
    amp_abs: np.ndarray,
    segments: list[tuple[int, int]],
    step: int,
    beta_thr: float,
    broad_thr: float,
    amp_thr: float,
    smr_thr: float,
) -> dict[str, Any]:
    durations = []
    total_bins = 0
    s_counts = Counter()
    t_counts: Counter = Counter()
    clean_smr_bins = 0
    for start, stop in segments:
        idx = np.arange(start, stop, step)
        if len(idx) < 2:
            continue
        be = beta_env[idx]
        se = smr_env[idx]
        br = broad_env[idx]
        aa = amp_abs[idx]
        s2 = (br > broad_thr) | (aa > amp_thr)
        s1 = (be > beta_thr) & ~s2
        states = np.where(s2, 2, np.where(s1, 1, 0)).astype(int)
        s_counts.update(states.tolist())
        total_bins += len(states)
        clean_smr_bins += int(np.sum((states == 0) & (se >= smr_thr)))
        t_counts.update(transition_counts(states))
        for _, _, duration in mask_episode_durations(s1, STATE_FS):
            durations.append(duration)
    if total_bins == 0:
        total_bins = 1
    n_episodes = len(durations)
    durations_arr = np.asarray(durations, dtype=float)
    total_duration_s = total_bins / STATE_FS
    non_s1_state_bins = s_counts[0] + s_counts[2]
    non_s1_to_s1 = t_counts[(0, 1)] + t_counts[(2, 1)]
    s1_exits = t_counts[(1, 0)] + t_counts[(1, 2)]
    return {
        "episode_durations_s": durations,
        "n_beta_episodes": n_episodes,
        "mean_s1_dwell_time_s": float(np.mean(durations_arr)) if n_episodes else 0.0,
        "median_s1_dwell_time_s": float(np.median(durations_arr)) if n_episodes else 0.0,
        "p90_s1_dwell_time_s": float(np.percentile(durations_arr, 90)) if n_episodes else 0.0,
        "s1_total_dwell_time_s": float(np.sum(durations_arr)) if n_episodes else 0.0,
        "s1_escape_rate_per_s": float(1.0 / np.mean(durations_arr)) if n_episodes and np.mean(durations_arr) > 0 else 0.0,
        "s1_episode_rate_per_min": float(n_episodes / (total_duration_s / 60.0)) if total_duration_s > 0 else 0.0,
        "s1_occupancy": float(s_counts[1] / total_bins),
        "s0_occupancy": float(s_counts[0] / total_bins),
        "s2_occupancy": float(s_counts[2] / total_bins),
        "clean_smr_compatible_state_occupancy": float(clean_smr_bins / total_bins),
        "s1_reentry_probability": float(non_s1_to_s1 / non_s1_state_bins) if non_s1_state_bins > 0 else 0.0,
        "s1_exit_probability": float(s1_exits / s_counts[1]) if s_counts[1] > 0 else 0.0,
        "transition_counts": t_counts,
        "state_counts": s_counts,
        "total_state_bins": total_bins,
        "duration_s_analyzed": float(total_duration_s),
    }


def transition_rows_from_counts(
    dataset_id: str,
    subject: str,
    session_name: str,
    phase: str,
    condition: str,
    threshold_def: str,
    counts: Counter,
) -> list[dict[str, Any]]:
    rows = []
    labels = {0: "S0_clean_non_beta", 1: "S1_high_beta", 2: "S2_broadband_artifact"}
    row_totals = {state: sum(counts[(state, j)] for j in [0, 1, 2]) for state in [0, 1, 2]}
    for i in [0, 1, 2]:
        for j in [0, 1, 2]:
            count = int(counts[(i, j)])
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "subject": subject,
                    "session": session_name,
                    "phase": phase,
                    "condition": condition,
                    "threshold_def": threshold_def,
                    "from_state": labels[i],
                    "to_state": labels[j],
                    "transition_count": count,
                    "transition_probability": float(count / row_totals[i]) if row_totals[i] else 0.0,
                }
            )
    return rows


def available_analysis_dataset(download_manifest: pd.DataFrame) -> tuple[str, str]:
    selected_root = ROOT / "data" / "raw" / "openneuro" / SELECTED_DATASET
    selected_edfs = list(selected_root.glob("sub-*/ses-*/eeg/*_eeg.edf"))
    selected_subjects = {parse_subject_session(p)[0] for p in selected_edfs}
    if len(selected_subjects) >= 20:
        return SELECTED_DATASET, "larger_dataset"
    pilot_root = ROOT / "data" / "raw" / "openneuro" / PILOT_DATASET
    pilot_edfs = list(pilot_root.glob("sub-*/ses-*/eeg/*_eeg.edf"))
    if pilot_edfs:
        return PILOT_DATASET, "pilot_descriptive"
    return "", "no_data"


def subject_session_map(raw_root: Path) -> dict[str, list[str]]:
    mapping: dict[str, set[str]] = defaultdict(set)
    for edf in raw_root.glob("sub-*/ses-*/eeg/*_eeg.edf"):
        sub, ses = parse_subject_session(edf)
        if sub and ses:
            mapping[sub].add(ses)
    return {sub: sorted(sessions, key=session_sort_key) for sub, sessions in mapping.items()}


def process_dataset(dataset_id: str, analysis_scope: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    log_path = ROOT / "outputs" / "logs" / "beta_escape_empirical_processing.log"
    log_path.write_text(f"{utc_now()} beta_escape empirical processing started dataset={dataset_id} scope={analysis_scope}\n", encoding="utf-8")
    raw_root = ROOT / "data" / "raw" / "openneuro" / dataset_id
    edf_files = sorted(raw_root.glob("sub-*/ses-*/eeg/*_eeg.edf"))
    subj_sessions = subject_session_map(raw_root)
    feature_rows: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    session_threshold_rows: list[dict[str, Any]] = []
    for file_idx, edf_path in enumerate(edf_files, start=1):
        subject, session_name = parse_subject_session(edf_path)
        phase = session_phase(session_name, subj_sessions, subject)
        append_log(log_path, f"loading {file_idx}/{len(edf_files)} {rel(edf_path)}")
        raw = mne.io.read_raw_edf(str(edf_path), preload=True, include=SENSORIMOTOR_CHANNELS, verbose="ERROR")
        available = [ch for ch in SENSORIMOTOR_CHANNELS if ch in raw.ch_names]
        if not available:
            append_log(log_path, f"skip {rel(edf_path)} no sensorimotor channels")
            continue
        raw.pick(available)
        fs = float(raw.info["sfreq"])
        data_uv = raw.get_data(picks=available) * 1_000_000.0
        if hasattr(raw, "close"):
            raw.close()
        x = signal.detrend(np.nanmean(data_uv, axis=0))
        n_samples = len(x)
        raw_duration_s = n_samples / fs
        events = read_events_for_edf(edf_path, raw_duration_s)
        conditions = sorted(events["instruction"].astype(str).unique().tolist())
        step = max(1, int(round(fs / STATE_FS)))
        smr_env = band_envelope(x, fs, SMR_BAND)
        beta_env = band_envelope(x, fs, HIGH_BETA_BAND)
        broad_env = band_envelope(x, fs, BROADBAND_RANGE)
        amp_abs = np.abs(x)
        rest_segments = event_segments(events, "rest", fs, n_samples)
        if not rest_segments:
            rest_segments = [(0, n_samples)]
        rest_idx_values = np.concatenate(values_from_segments(beta_env, rest_segments, step))
        rest_broad_values = np.concatenate(values_from_segments(broad_env, rest_segments, step))
        rest_amp_values = np.concatenate(values_from_segments(amp_abs, rest_segments, step))
        rest_smr_values = np.concatenate(values_from_segments(smr_env, rest_segments, step))
        beta_thresholds = threshold_values(rest_idx_values)
        broad_thr = float(np.nanpercentile(rest_broad_values, 95)) if rest_broad_values.size else np.nan
        amp_thr = float(np.nanpercentile(rest_amp_values, 99)) if rest_amp_values.size else np.nan
        smr_thr = float(np.nanmedian(rest_smr_values)) if rest_smr_values.size else np.nan
        session_threshold_rows.append(
            {
                "dataset_id": dataset_id,
                "subject": subject,
                "session": session_name,
                "phase": phase,
                "beta_threshold_p75": beta_thresholds["p75"],
                "beta_threshold_p80": beta_thresholds["p80"],
                "beta_threshold_p90": beta_thresholds["p90"],
                "beta_threshold_z1": beta_thresholds["z1"],
                "beta_threshold_mad1": beta_thresholds["mad1"],
                "broadband_s2_threshold_p95": broad_thr,
                "amplitude_s2_threshold_p99": amp_thr,
                "smr_clean_threshold_median": smr_thr,
            }
        )
        for condition in conditions:
            segments = event_segments(events, condition, fs, n_samples)
            if not segments:
                continue
            xc = concat_segments(x, segments)
            powers = spectral_metrics(xc, fs)
            robust_cut = float(np.nanpercentile(np.abs(xc), 95)) if xc.size else np.nan
            xc_trimmed = xc[np.abs(xc) <= robust_cut] if np.isfinite(robust_cut) and xc.size else xc
            robust_powers = spectral_metrics(xc_trimmed, fs) if xc_trimmed.size >= int(fs * 2) else powers
            for threshold_def in THRESHOLD_DEFS:
                state = analyze_state_segments(
                    beta_env,
                    smr_env,
                    broad_env,
                    amp_abs,
                    segments,
                    step,
                    beta_thresholds[threshold_def],
                    broad_thr,
                    amp_thr,
                    smr_thr,
                )
                feature_rows.append(
                    {
                        "dataset_id": dataset_id,
                        "analysis_scope": analysis_scope,
                        "analysis_role": "primary" if threshold_def == PRIMARY_THRESHOLD else "sensitivity",
                        "threshold_def": threshold_def,
                        "subject": subject,
                        "session": session_name,
                        "phase": phase,
                        "condition": condition,
                        "file_path": rel(edf_path),
                        "sensorimotor_channels_used": ";".join(available),
                        "sampling_rate_hz": fs,
                        "duration_s_analyzed": state["duration_s_analyzed"],
                        "smr_power": powers["smr_power"],
                        "high_beta_power": powers["high_beta_power"],
                        "broadband_non_target_power": powers["broadband_non_target_power"],
                        "noise_floor_power": powers["noise_floor_power"],
                        "spectral_slope": powers["spectral_slope"],
                        "high_beta_residual_log10": powers["high_beta_residual_log10"],
                        "high_beta_power_trimmed95": robust_powers["high_beta_power"],
                        "smr_snr": powers["smr_power"] / powers["broadband_non_target_power"] if powers["broadband_non_target_power"] else np.nan,
                        "smr_snr_log10": np.log10((powers["smr_power"] + 1e-30) / (powers["broadband_non_target_power"] + 1e-30)),
                        "mean_s1_dwell_time_s": state["mean_s1_dwell_time_s"],
                        "median_s1_dwell_time_s": state["median_s1_dwell_time_s"],
                        "p90_s1_dwell_time_s": state["p90_s1_dwell_time_s"],
                        "s1_total_dwell_time_s": state["s1_total_dwell_time_s"],
                        "s1_escape_rate_per_s": state["s1_escape_rate_per_s"],
                        "s1_reentry_probability": state["s1_reentry_probability"],
                        "s1_exit_probability": state["s1_exit_probability"],
                        "beta_state_occupancy": state["s1_occupancy"],
                        "clean_smr_compatible_state_occupancy": state["clean_smr_compatible_state_occupancy"],
                        "broadband_artifact_state_occupancy": state["s2_occupancy"],
                        "s0_occupancy": state["s0_occupancy"],
                        "s1_occupancy": state["s1_occupancy"],
                        "s2_occupancy": state["s2_occupancy"],
                        "n_beta_episodes": state["n_beta_episodes"],
                        "s1_episode_rate_per_min": state["s1_episode_rate_per_min"],
                        "beta_threshold": beta_thresholds[threshold_def],
                        "broadband_s2_threshold": broad_thr,
                        "amplitude_s2_threshold": amp_thr,
                        "status": "real_eeg_analyzed",
                    }
                )
                for ep_idx, duration in enumerate(state["episode_durations_s"], start=1):
                    episode_rows.append(
                        {
                            "dataset_id": dataset_id,
                            "analysis_scope": analysis_scope,
                            "threshold_def": threshold_def,
                            "subject": subject,
                            "session": session_name,
                            "phase": phase,
                            "condition": condition,
                            "episode_index": ep_idx,
                            "duration_s": duration,
                            "long_episode_subject_threshold_s": np.nan,
                            "is_long_episode": False,
                            "status": "real_eeg_episode",
                        }
                    )
                transition_rows.extend(
                    transition_rows_from_counts(
                        dataset_id,
                        subject,
                        session_name,
                        phase,
                        condition,
                        threshold_def,
                        state["transition_counts"],
                    )
                )
    features = pd.DataFrame(feature_rows)
    episodes = pd.DataFrame(episode_rows)
    transitions = pd.DataFrame(transition_rows)
    thresholds = pd.DataFrame(session_threshold_rows)
    if not episodes.empty:
        long_thresholds = {}
        for (subject, threshold_def), group in episodes.groupby(["subject", "threshold_def"]):
            baseline = group[(group["phase"] == "early") & (group["condition"] == "rest")]
            if len(baseline) >= 3:
                source = baseline
            else:
                rest = group[group["condition"] == "rest"]
                source = rest if len(rest) >= 3 else group
            long_thresholds[(subject, threshold_def)] = float(np.percentile(source["duration_s"], 75)) if len(source) else np.nan
        episodes["long_episode_subject_threshold_s"] = [
            long_thresholds.get((row.subject, row.threshold_def), np.nan) for row in episodes.itertuples()
        ]
        episodes["is_long_episode"] = episodes["duration_s"] > episodes["long_episode_subject_threshold_s"]
        long_frac = (
            episodes.groupby(["subject", "session", "condition", "threshold_def"], as_index=False)
            .agg(long_high_beta_burst_fraction=("is_long_episode", "mean"))
        )
        features = features.merge(long_frac, on=["subject", "session", "condition", "threshold_def"], how="left")
        features["long_high_beta_burst_fraction"] = features["long_high_beta_burst_fraction"].fillna(0.0)
    else:
        features["long_high_beta_burst_fraction"] = np.nan
    write_table(features, "beta_escape_primary_features.csv")
    write_table(episodes, "beta_escape_episode_metrics.csv")
    write_table(transitions, "beta_escape_transition_metrics.csv")
    write_table(thresholds, "beta_escape_session_thresholds.csv")
    append_log(log_path, f"processing completed features={len(features)} episodes={len(episodes)}")
    return features, episodes, transitions, thresholds


def primary_task(features: pd.DataFrame) -> pd.DataFrame:
    return features[
        (features["condition"] == PRIMARY_CONDITION)
        & (features["threshold_def"] == PRIMARY_THRESHOLD)
        & (features["analysis_role"] == "primary")
    ].copy()


def paired_changes(features: pd.DataFrame, threshold_def: str = PRIMARY_THRESHOLD, condition: str = PRIMARY_CONDITION) -> pd.DataFrame:
    frame = features[(features["condition"] == condition) & (features["threshold_def"] == threshold_def)].copy()
    rows = []
    metrics = [
        "high_beta_power",
        "mean_s1_dwell_time_s",
        "median_s1_dwell_time_s",
        "p90_s1_dwell_time_s",
        "long_high_beta_burst_fraction",
        "s1_escape_rate_per_s",
        "s1_reentry_probability",
        "beta_state_occupancy",
        "smr_power",
        "smr_snr_log10",
        "clean_smr_compatible_state_occupancy",
        "broadband_artifact_state_occupancy",
        "broadband_non_target_power",
        "spectral_slope",
        "high_beta_residual_log10",
        "noise_floor_power",
        "high_beta_power_trimmed95",
    ]
    for subject, group in frame.groupby("subject"):
        early = group[group["phase"] == "early"]
        late = group[group["phase"] == "late"]
        if early.empty or late.empty:
            continue
        early = early.sort_values("session").iloc[0]
        late = late.sort_values("session").iloc[-1]
        row = {
            "dataset_id": early["dataset_id"],
            "analysis_scope": early["analysis_scope"],
            "threshold_def": threshold_def,
            "condition": condition,
            "subject": subject,
            "early_session": early["session"],
            "late_session": late["session"],
        }
        for metric in metrics:
            pre = float(early.get(metric, np.nan))
            post = float(late.get(metric, np.nan))
            row[f"{metric}_early"] = pre
            row[f"{metric}_late"] = post
            row[f"{metric}_change"] = post - pre
            row[f"{metric}_fractional_change"] = (post - pre) / pre if np.isfinite(pre) and pre != 0 else np.nan
            row[f"{metric}_log2_ratio"] = np.log2((post + 1e-30) / (pre + 1e-30)) if np.isfinite(pre) and np.isfinite(post) and pre >= 0 and post >= 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def survival_and_hazard(episodes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ep = episodes[
        (episodes["condition"] == PRIMARY_CONDITION)
        & (episodes["threshold_def"] == PRIMARY_THRESHOLD)
        & (episodes["duration_s"].notna())
    ].copy()
    if ep.empty:
        survival = pd.DataFrame(columns=["phase", "time_s", "survival_probability", "n_episodes", "threshold_def", "condition"])
        hazard = pd.DataFrame(columns=["phase", "time_s", "hazard_probability", "at_risk", "events", "threshold_def", "condition"])
        return survival, hazard
    max_t = max(0.5, float(np.nanpercentile(ep["duration_s"], 99)))
    grid = np.arange(0.0, min(max_t + 0.1001, 10.0), 0.1)
    surv_rows = []
    haz_rows = []
    for phase, group in ep.groupby("phase"):
        durations = group["duration_s"].astype(float).to_numpy()
        for t in grid:
            surv_rows.append(
                {
                    "dataset_id": group["dataset_id"].iloc[0],
                    "condition": PRIMARY_CONDITION,
                    "threshold_def": PRIMARY_THRESHOLD,
                    "phase": phase,
                    "time_s": round(float(t), 3),
                    "survival_probability": float(np.mean(durations > t)) if len(durations) else np.nan,
                    "n_episodes": int(len(durations)),
                }
            )
            at_risk = durations >= t
            events = (durations >= t) & (durations < t + 0.1)
            haz_rows.append(
                {
                    "dataset_id": group["dataset_id"].iloc[0],
                    "condition": PRIMARY_CONDITION,
                    "threshold_def": PRIMARY_THRESHOLD,
                    "phase": phase,
                    "time_s": round(float(t), 3),
                    "hazard_probability": float(np.sum(events) / np.sum(at_risk)) if np.sum(at_risk) else np.nan,
                    "at_risk": int(np.sum(at_risk)),
                    "events": int(np.sum(events)),
                }
            )
    return pd.DataFrame(surv_rows), pd.DataFrame(haz_rows)


def sign_flip_pvalue(values: np.ndarray) -> float:
    vals = values[np.isfinite(values)]
    if len(vals) == 0:
        return np.nan
    observed = abs(float(np.mean(vals)))
    if len(vals) <= 16:
        stats_vals = []
        for mask in range(2 ** len(vals)):
            signs = np.array([1 if (mask >> i) & 1 else -1 for i in range(len(vals))])
            stats_vals.append(abs(float(np.mean(vals * signs))))
        return float((np.sum(np.asarray(stats_vals) >= observed) + 1) / (len(stats_vals) + 1))
    rng = np.random.default_rng(20260702)
    signs = rng.choice([-1, 1], size=(20000, len(vals)))
    stats_vals = np.abs(np.mean(signs * vals[None, :], axis=1))
    return float((np.sum(stats_vals >= observed) + 1) / (len(stats_vals) + 1))


def fit_survival_models(episodes: pd.DataFrame, changes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    hazard_rows = []
    ep = episodes[
        (episodes["condition"] == PRIMARY_CONDITION)
        & (episodes["threshold_def"] == PRIMARY_THRESHOLD)
        & (episodes["phase"].isin(["early", "late"]))
    ].copy()
    if not ep.empty:
        ep["late_indicator"] = (ep["phase"] == "late").astype(int)
        try:
            from statsmodels.duration.hazard_regression import PHReg

            model = PHReg(ep["duration_s"].astype(float), ep[["late_indicator"]], status=np.ones(len(ep)))
            result = model.fit(disp=False)
            coef = float(result.params[0])
            pval = float(result.pvalues[0])
            rows.append(
                {
                    "model": "cox_ph_episode_level_late_vs_early",
                    "condition": PRIMARY_CONDITION,
                    "threshold_def": PRIMARY_THRESHOLD,
                    "n_episodes": len(ep),
                    "log_hazard_ratio_late_vs_early": coef,
                    "hazard_ratio_late_vs_early": float(np.exp(coef)),
                    "p_value": pval,
                    "status": "fit_success",
                    "interpretation_note": "hazard_ratio_above_1_indicates_faster_escape_in_late_sessions",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "model": "cox_ph_episode_level_late_vs_early",
                    "condition": PRIMARY_CONDITION,
                    "threshold_def": PRIMARY_THRESHOLD,
                    "n_episodes": len(ep),
                    "log_hazard_ratio_late_vs_early": np.nan,
                    "hazard_ratio_late_vs_early": np.nan,
                    "p_value": np.nan,
                    "status": f"fit_failed_{type(exc).__name__}",
                    "interpretation_note": str(exc)[:180],
                }
            )
    for metric, direction in [
        ("high_beta_power_change", "decrease_expected_if_mean_power_suppression"),
        ("mean_s1_dwell_time_s_change", "decrease_expected_for_escape"),
        ("p90_s1_dwell_time_s_change", "decrease_expected_for_tail_escape"),
        ("long_high_beta_burst_fraction_change", "decrease_expected_for_tail_escape"),
        ("s1_escape_rate_per_s_change", "increase_expected_for_escape"),
        ("s1_reentry_probability_change", "decrease_expected_for_escape"),
        ("beta_state_occupancy_change", "decrease_expected_for_escape"),
    ]:
        if metric not in changes:
            continue
        vals = changes[metric].astype(float).to_numpy()
        vals = vals[np.isfinite(vals)]
        if len(vals) == 0:
            continue
        try:
            w_p = float(stats.wilcoxon(vals).pvalue) if len(vals) >= 2 and np.any(vals != 0) else np.nan
        except Exception:
            w_p = np.nan
        row = {
            "model": "subject_level_paired_change",
            "metric": metric.replace("_change", ""),
            "condition": PRIMARY_CONDITION,
            "threshold_def": PRIMARY_THRESHOLD,
            "n_subjects": len(vals),
            "mean_change": float(np.mean(vals)),
            "median_change": float(np.median(vals)),
            "wilcoxon_p_value": w_p,
            "sign_flip_p_value": sign_flip_pvalue(vals),
            "direction": direction,
        }
        rows.append(row)
        if metric == "s1_escape_rate_per_s_change":
            hazard_rows.append({**row, "model": "paired_escape_rate_change"})
    if not hazard_rows and "s1_escape_rate_per_s_change" in changes:
        vals = changes["s1_escape_rate_per_s_change"].astype(float).to_numpy()
        hazard_rows.append(
            {
                "model": "paired_escape_rate_change",
                "metric": "s1_escape_rate_per_s",
                "condition": PRIMARY_CONDITION,
                "threshold_def": PRIMARY_THRESHOLD,
                "n_subjects": int(np.isfinite(vals).sum()),
                "mean_change": float(np.nanmean(vals)) if np.isfinite(vals).any() else np.nan,
                "median_change": float(np.nanmedian(vals)) if np.isfinite(vals).any() else np.nan,
                "wilcoxon_p_value": np.nan,
                "sign_flip_p_value": sign_flip_pvalue(vals),
                "direction": "increase_expected_for_escape",
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(hazard_rows)


def build_discordance(changes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = changes.copy()
    if df.empty:
        return df, pd.DataFrame()
    df["mean_power_decreased"] = df["high_beta_power_change"] < 0
    df["dwell_time_decreased"] = df["mean_s1_dwell_time_s_change"] < 0
    df["long_burst_fraction_decreased"] = df["long_high_beta_burst_fraction_change"] < 0
    df["escape_rate_increased"] = df["s1_escape_rate_per_s_change"] > 0
    df["beta_occupancy_decreased"] = df["beta_state_occupancy_change"] < 0
    def quadrant(row: pd.Series) -> str:
        if row["mean_power_decreased"] and row["dwell_time_decreased"]:
            return "A_power_down_dwell_down"
        if row["mean_power_decreased"] and not row["dwell_time_decreased"]:
            return "B_power_down_dwell_not_down"
        if (not row["mean_power_decreased"]) and row["dwell_time_decreased"]:
            return "C_dwell_down_power_not_down"
        return "D_neither_down"
    df["power_dwell_quadrant"] = df.apply(quadrant, axis=1)
    corr_rows = []
    pairs = [
        ("high_beta_power_change", "mean_s1_dwell_time_s_change"),
        ("high_beta_power_change", "long_high_beta_burst_fraction_change"),
        ("high_beta_power_change", "s1_escape_rate_per_s_change"),
        ("high_beta_power_change", "beta_state_occupancy_change"),
    ]
    for xcol, ycol in pairs:
        x = df[xcol].astype(float)
        y = df[ycol].astype(float)
        ok = x.notna() & y.notna()
        if ok.sum() >= 3:
            pr = stats.pearsonr(x[ok], y[ok])
            sr = stats.spearmanr(x[ok], y[ok])
            corr_rows.append(
                {
                    "x_metric": xcol.replace("_change", ""),
                    "y_metric": ycol.replace("_change", ""),
                    "n": int(ok.sum()),
                    "pearson_r": float(pr.statistic),
                    "pearson_p": float(pr.pvalue),
                    "spearman_rho": float(sr.statistic),
                    "spearman_p": float(sr.pvalue),
                }
            )
    return df, pd.DataFrame(corr_rows)


def smr_beta_quadrants(changes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = changes.copy()
    if df.empty:
        return df, pd.DataFrame(), pd.DataFrame()
    df["smr_power_increased"] = df["smr_power_change"] > 0
    df["smr_snr_increased"] = df["smr_snr_log10_change"] > 0
    df["clean_smr_occupancy_increased"] = df["clean_smr_compatible_state_occupancy_change"] > 0
    df["smr_acquisition_score"] = df[["smr_power_increased", "smr_snr_increased", "clean_smr_occupancy_increased"]].sum(axis=1)
    df["smr_acquisition_primary"] = df["smr_acquisition_score"] >= 2
    df["dwell_time_decreased"] = df["mean_s1_dwell_time_s_change"] < 0
    df["long_burst_fraction_decreased"] = df["long_high_beta_burst_fraction_change"] < 0
    df["escape_rate_increased"] = df["s1_escape_rate_per_s_change"] > 0
    df["reentry_probability_decreased"] = df["s1_reentry_probability_change"] < 0
    df["beta_escape_score"] = df[["dwell_time_decreased", "long_burst_fraction_decreased", "escape_rate_increased", "reentry_probability_decreased"]].sum(axis=1)
    df["beta_escape_primary"] = df["beta_escape_score"] >= 3
    def quad(row: pd.Series) -> str:
        if row["smr_acquisition_primary"] and row["beta_escape_primary"]:
            return "A_SMR_acquisition_plus_beta_escape"
        if row["smr_acquisition_primary"] and not row["beta_escape_primary"]:
            return "B_SMR_acquisition_only"
        if (not row["smr_acquisition_primary"]) and row["beta_escape_primary"]:
            return "C_beta_escape_only"
        return "D_neither"
    df["smr_beta_quadrant"] = df.apply(quad, axis=1)
    robustness_rows = []
    definitions = [
        ("primary_majority", 2, 3),
        ("liberal_any", 1, 1),
        ("balanced_half", 2, 2),
        ("strict_all", 3, 4),
    ]
    for label, smr_cut, beta_cut in definitions:
        q = df.copy()
        q["smr_positive"] = q["smr_acquisition_score"] >= smr_cut
        q["beta_positive"] = q["beta_escape_score"] >= beta_cut
        robustness_rows.append(
            {
                "definition": label,
                "smr_score_cutoff": smr_cut,
                "beta_score_cutoff": beta_cut,
                "n_subjects": len(q),
                "n_smr_positive": int(q["smr_positive"].sum()),
                "n_beta_escape_positive": int(q["beta_positive"].sum()),
                "n_both": int((q["smr_positive"] & q["beta_positive"]).sum()),
                "n_smr_only": int((q["smr_positive"] & ~q["beta_positive"]).sum()),
                "n_beta_only": int((~q["smr_positive"] & q["beta_positive"]).sum()),
                "n_neither": int((~q["smr_positive"] & ~q["beta_positive"]).sum()),
            }
        )
    for threshold_def in THRESHOLD_DEFS:
        # Sensitivity rows are filled by the caller when per-threshold changes are available.
        robustness_rows.append(
            {
                "definition": f"threshold_{threshold_def}",
                "smr_score_cutoff": 2,
                "beta_score_cutoff": 3,
                "n_subjects": np.nan,
                "n_smr_positive": np.nan,
                "n_beta_escape_positive": np.nan,
                "n_both": np.nan,
                "n_smr_only": np.nan,
                "n_beta_only": np.nan,
                "n_neither": np.nan,
            }
        )
    influence_rows = []
    for subject in df["subject"]:
        loo = df[df["subject"] != subject]
        influence_rows.append(
            {
                "left_out_subject": subject,
                "n_remaining": len(loo),
                "mean_dwell_change_without_subject": float(loo["mean_s1_dwell_time_s_change"].mean()),
                "mean_power_change_without_subject": float(loo["high_beta_power_change"].mean()),
                "mean_escape_rate_change_without_subject": float(loo["s1_escape_rate_per_s_change"].mean()),
                "n_primary_beta_escape_without_subject": int(loo["beta_escape_primary"].sum()),
                "n_primary_smr_acquisition_without_subject": int(loo["smr_acquisition_primary"].sum()),
            }
        )
    return df, pd.DataFrame(robustness_rows), pd.DataFrame(influence_rows)


def fill_threshold_robustness(features: pd.DataFrame, robustness: pd.DataFrame) -> pd.DataFrame:
    rows = robustness[~robustness["definition"].astype(str).str.startswith("threshold_")].to_dict("records")
    for threshold_def in THRESHOLD_DEFS:
        changes = paired_changes(features, threshold_def=threshold_def, condition=PRIMARY_CONDITION)
        quad, _, _ = smr_beta_quadrants(changes)
        if quad.empty:
            rows.append({"definition": f"threshold_{threshold_def}", "n_subjects": 0})
            continue
        rows.append(
            {
                "definition": f"threshold_{threshold_def}",
                "smr_score_cutoff": 2,
                "beta_score_cutoff": 3,
                "n_subjects": len(quad),
                "n_smr_positive": int(quad["smr_acquisition_primary"].sum()),
                "n_beta_escape_positive": int(quad["beta_escape_primary"].sum()),
                "n_both": int((quad["smr_acquisition_primary"] & quad["beta_escape_primary"]).sum()),
                "n_smr_only": int((quad["smr_acquisition_primary"] & ~quad["beta_escape_primary"]).sum()),
                "n_beta_only": int((~quad["smr_acquisition_primary"] & quad["beta_escape_primary"]).sum()),
                "n_neither": int((~quad["smr_acquisition_primary"] & ~quad["beta_escape_primary"]).sum()),
            }
        )
    return pd.DataFrame(rows)


def broadband_controls(changes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if changes.empty:
        return pd.DataFrame(), pd.DataFrame()
    rows = []
    for _, row in changes.iterrows():
        rows.append(
            {
                "dataset_id": row["dataset_id"],
                "subject": row["subject"],
                "condition": row["condition"],
                "threshold_def": row["threshold_def"],
                "dwell_time_change": row["mean_s1_dwell_time_s_change"],
                "high_beta_power_change": row["high_beta_power_change"],
                "broadband_power_change": row["broadband_non_target_power_change"],
                "spectral_slope_change": row["spectral_slope_change"],
                "high_beta_residual_change": row["high_beta_residual_log10_change"],
                "noise_floor_change": row["noise_floor_power_change"],
                "trimmed_high_beta_power_change": row["high_beta_power_trimmed95_change"],
                "artifact_occupancy_change": row["broadband_artifact_state_occupancy_change"],
                "dwell_improved_after_broadband_direction_check": bool(row["mean_s1_dwell_time_s_change"] < 0 and row["broadband_non_target_power_change"] <= 0),
                "dwell_improved_despite_broadband_increase": bool(row["mean_s1_dwell_time_s_change"] < 0 and row["broadband_non_target_power_change"] > 0),
            }
        )
    controls = pd.DataFrame(rows)
    model_rows = []
    for ycol in ["mean_s1_dwell_time_s_change", "long_high_beta_burst_fraction_change", "s1_escape_rate_per_s_change"]:
        predictors = ["high_beta_power_change", "broadband_non_target_power_change", "spectral_slope_change", "noise_floor_power_change"]
        model_df = changes[[ycol] + predictors].replace([np.inf, -np.inf], np.nan).dropna()
        if len(model_df) >= len(predictors) + 2:
            try:
                import statsmodels.api as sm

                X = sm.add_constant(model_df[predictors])
                fit = sm.OLS(model_df[ycol], X).fit()
                for name in X.columns:
                    model_rows.append(
                        {
                            "model": f"ols_{ycol}",
                            "term": name,
                            "n_subjects": len(model_df),
                            "coefficient": float(fit.params[name]),
                            "p_value": float(fit.pvalues[name]),
                            "r_squared": float(fit.rsquared),
                            "status": "fit_success",
                        }
                    )
            except Exception as exc:
                model_rows.append({"model": f"ols_{ycol}", "term": "model", "status": f"fit_failed_{type(exc).__name__}", "note": str(exc)[:160]})
        else:
            model_rows.append({"model": f"ols_{ycol}", "term": "model", "n_subjects": len(model_df), "status": "not_fit_insufficient_complete_cases"})
    slope_rows = []
    for metric in ["high_beta_power_change", "high_beta_residual_log10_change", "mean_s1_dwell_time_s_change"]:
        x = changes["spectral_slope_change"].astype(float)
        y = changes[metric].astype(float)
        ok = x.notna() & y.notna()
        if ok.sum() >= 3:
            sr = stats.spearmanr(x[ok], y[ok])
            slope_rows.append(
                {
                    "control_metric": "spectral_slope_change",
                    "outcome_metric": metric.replace("_change", ""),
                    "n": int(ok.sum()),
                    "spearman_rho": float(sr.statistic),
                    "spearman_p": float(sr.pvalue),
                    "status": "computed",
                }
            )
    spectral = pd.DataFrame(model_rows + slope_rows)
    return controls, spectral


def make_all_figures(
    features: pd.DataFrame,
    episodes: pd.DataFrame,
    survival: pd.DataFrame,
    hazard: pd.DataFrame,
    discordance: pd.DataFrame,
    smr_quad: pd.DataFrame,
    robustness: pd.DataFrame,
    controls: pd.DataFrame,
) -> None:
    set_style()
    # Survival curves
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    for phase, group in survival.groupby("phase"):
        ax.step(group["time_s"], group["survival_probability"], where="post", label=phase)
    ax.set_xlabel("S1 dwell time t (s)")
    ax.set_ylabel("S(t) = P(T_beta > t)")
    ax.set_title("High-beta state survival")
    ax.legend()
    save_figure(fig, survival, "beta_escape_survival_curves")

    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    for phase, group in hazard.groupby("phase"):
        ax.plot(group["time_s"], group["hazard_probability"], marker="o", ms=2.5, lw=1.0, label=phase)
    ax.set_xlabel("S1 dwell time t (s)")
    ax.set_ylabel("Discrete escape hazard")
    ax.set_title("High-beta escape hazard")
    ax.legend()
    save_figure(fig, hazard, "beta_escape_hazard_functions")

    lb = primary_task(features)
    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    if not lb.empty:
        plot_df = lb.groupby(["phase", "subject"], as_index=False)["long_high_beta_burst_fraction"].mean()
        phase_order = ["early", "late"]
        data = [plot_df.loc[plot_df["phase"] == p, "long_high_beta_burst_fraction"].values for p in phase_order]
        ax.boxplot(data, labels=phase_order, widths=0.55)
        for i, p in enumerate(phase_order, start=1):
            vals = plot_df.loc[plot_df["phase"] == p, "long_high_beta_burst_fraction"].values
            ax.scatter(np.full(len(vals), i), vals, s=14, alpha=0.8)
    ax.set_ylabel("Long beta burst fraction")
    ax.set_title("Long-burst fraction")
    save_figure(fig, lb, "beta_escape_long_burst_fraction")

    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    if not discordance.empty:
        ax.scatter(discordance["high_beta_power_change"], discordance["mean_s1_dwell_time_s_change"], s=35)
        for _, row in discordance.iterrows():
            ax.text(row["high_beta_power_change"], row["mean_s1_dwell_time_s_change"], row["subject"].replace("sub-", ""), fontsize=6)
    ax.axhline(0, color="0.25", lw=0.8)
    ax.axvline(0, color="0.25", lw=0.8)
    ax.set_xlabel("Mean high-beta power change")
    ax.set_ylabel("Mean S1 dwell-time change")
    ax.set_title("Mean power vs dwell time")
    save_figure(fig, discordance, "beta_escape_mean_power_vs_dwell_time")

    quad_counts = discordance["power_dwell_quadrant"].value_counts().rename_axis("quadrant").reset_index(name="n") if not discordance.empty else pd.DataFrame(columns=["quadrant", "n"])
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    if not quad_counts.empty:
        ax.bar(quad_counts["quadrant"], quad_counts["n"], color="#4E79A7")
        ax.tick_params(axis="x", rotation=25)
    ax.set_ylabel("Subjects")
    ax.set_title("Power/dwell discordance classes")
    save_figure(fig, quad_counts, "beta_escape_power_dwell_quadrants")

    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    if not smr_quad.empty:
        colors = smr_quad["smr_beta_quadrant"].map(
            {
                "A_SMR_acquisition_plus_beta_escape": "#2ca25f",
                "B_SMR_acquisition_only": "#3182bd",
                "C_beta_escape_only": "#de8f05",
                "D_neither": "#756bb1",
            }
        )
        ax.scatter(smr_quad["smr_acquisition_score"], smr_quad["beta_escape_score"], c=colors, s=45)
        for _, row in smr_quad.iterrows():
            ax.text(row["smr_acquisition_score"] + 0.03, row["beta_escape_score"] + 0.03, row["subject"].replace("sub-", ""), fontsize=6)
    ax.axvline(1.5, color="0.4", ls="--", lw=0.8)
    ax.axhline(2.5, color="0.4", ls="--", lw=0.8)
    ax.set_xlabel("SMR acquisition score (0-3)")
    ax.set_ylabel("Beta escape score (0-4)")
    ax.set_title("SMR acquisition vs beta escape")
    save_figure(fig, smr_quad, "beta_escape_smr_vs_beta_escape_quadrants")

    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    rb = robustness.copy()
    if not rb.empty and "n_beta_escape_positive" in rb:
        ax.bar(rb["definition"], rb["n_beta_escape_positive"], color="#5F9EA0")
        ax.tick_params(axis="x", rotation=35)
    ax.set_ylabel("Beta escape positive subjects")
    ax.set_title("Definition robustness")
    save_figure(fig, rb, "beta_escape_definition_robustness")

    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.0))
    if not controls.empty:
        axes[0].scatter(controls["broadband_power_change"], controls["dwell_time_change"], s=25)
        axes[1].scatter(controls["spectral_slope_change"], controls["dwell_time_change"], s=25)
        axes[2].scatter(controls["artifact_occupancy_change"], controls["dwell_time_change"], s=25)
    for ax, xlabel in zip(axes, ["Broadband power change", "Spectral slope change", "S2 occupancy change"]):
        ax.axhline(0, color="0.25", lw=0.8)
        ax.axvline(0, color="0.25", lw=0.8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Dwell-time change")
    axes[0].set_title("Broadband")
    axes[1].set_title("1/f slope")
    axes[2].set_title("Artifact state")
    save_figure(fig, controls, "beta_escape_broadband_control_panel")

    make_manuscript_candidate_figures(features, survival, hazard, discordance, smr_quad, controls)


def make_manuscript_candidate_figures(
    features: pd.DataFrame,
    survival: pd.DataFrame,
    hazard: pd.DataFrame,
    discordance: pd.DataFrame,
    smr_quad: pd.DataFrame,
    controls: pd.DataFrame,
) -> None:
    # Figure 1: three-state model schematic.
    model_source = pd.DataFrame(
        [
            {"from_state": "S0", "to_state": "S1", "quantity": "entry/re-entry probability"},
            {"from_state": "S1", "to_state": "S0", "quantity": "escape hazard"},
            {"from_state": "S0", "to_state": "S2", "quantity": "broadband/artifact excursion"},
            {"from_state": "S2", "to_state": "S0", "quantity": "artifact recovery"},
            {"from_state": "S1", "to_state": "S2", "quantity": "beta plus broadband contamination"},
        ]
    )
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    ax.axis("off")
    positions = {"S0": (0.15, 0.55), "S1": (0.55, 0.75), "S2": (0.75, 0.30)}
    labels = {"S0": "S0\nclean SMR-compatible", "S1": "S1\nhigh-beta occupied", "S2": "S2\nbroadband/artifact"}
    for state, (x, y) in positions.items():
        ax.scatter([x], [y], s=1800, color={"S0": "#80b1d3", "S1": "#fb8072", "S2": "#b3de69"}[state], edgecolor="0.2")
        ax.text(x, y, labels[state], ha="center", va="center", fontsize=8)
    for _, row in model_source.iterrows():
        x0, y0 = positions[row["from_state"]]
        x1, y1 = positions[row["to_state"]]
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", lw=1.0, color="0.25"))
    ax.set_title("Metastable beta-escape model")
    save_figure(fig, model_source, "beta_escape_figure_1_model")

    # Figure 2: survival.
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    for phase, group in survival.groupby("phase"):
        ax.step(group["time_s"], group["survival_probability"], where="post", label=phase)
    ax.set_xlabel("S1 dwell time t (s)")
    ax.set_ylabel("S(t)")
    ax.set_title("High-beta dwell-time survival")
    ax.legend()
    save_figure(fig, survival, "beta_escape_figure_2_survival")

    # Figure 3: power vs dwell.
    fig, ax = plt.subplots(figsize=(4.8, 3.5))
    if not discordance.empty:
        ax.scatter(discordance["high_beta_power_change"], discordance["mean_s1_dwell_time_s_change"], s=35, c="#4E79A7")
    ax.axhline(0, color="0.25", lw=0.8)
    ax.axvline(0, color="0.25", lw=0.8)
    ax.set_xlabel("Mean high-beta change")
    ax.set_ylabel("S1 dwell change")
    ax.set_title("Power/dwell non-identifiability")
    save_figure(fig, discordance, "beta_escape_figure_3_power_vs_dwell")

    # Figure 4: SMR vs beta quadrants.
    fig, ax = plt.subplots(figsize=(4.8, 3.5))
    if not smr_quad.empty:
        ax.scatter(smr_quad["smr_acquisition_score"], smr_quad["beta_escape_score"], s=45, c="#59A14F")
    ax.axvline(1.5, color="0.4", ls="--", lw=0.8)
    ax.axhline(2.5, color="0.4", ls="--", lw=0.8)
    ax.set_xlabel("SMR score")
    ax.set_ylabel("Beta escape score")
    ax.set_title("Separable control outcomes")
    save_figure(fig, smr_quad, "beta_escape_figure_4_smr_beta_quadrants")

    # Figure 5: transition matrix/escape panel.
    pt = primary_task(features)
    transition_summary = pd.DataFrame()
    if not pt.empty:
        transition_summary = pt.groupby("phase", as_index=False).agg(
            s1_exit_probability=("s1_exit_probability", "mean"),
            s1_reentry_probability=("s1_reentry_probability", "mean"),
            beta_state_occupancy=("beta_state_occupancy", "mean"),
            s1_escape_rate_per_s=("s1_escape_rate_per_s", "mean"),
        )
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    if not transition_summary.empty:
        axes[0].bar(transition_summary["phase"], transition_summary["s1_escape_rate_per_s"], color="#9c755f")
        axes[1].bar(transition_summary["phase"], transition_summary["s1_reentry_probability"], color="#bab0ab")
    axes[0].set_title("Escape rate")
    axes[1].set_title("Re-entry probability")
    axes[0].set_ylabel("Mean")
    save_figure(fig, transition_summary, "beta_escape_figure_5_transition_matrix")

    # Figure 6: controls.
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.2))
    if not controls.empty:
        axes[0].scatter(controls["broadband_power_change"], controls["dwell_time_change"], s=25)
        axes[1].scatter(controls["noise_floor_change"], controls["dwell_time_change"], s=25)
    for ax, xlabel in zip(axes, ["Broadband change", "Noise floor change"]):
        ax.axhline(0, color="0.25", lw=0.8)
        ax.axvline(0, color="0.25", lw=0.8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Dwell-time change")
    axes[0].set_title("Broadband control")
    axes[1].set_title("Noise control")
    save_figure(fig, controls, "beta_escape_figure_6_broadband_controls")

    # Figure 7: summary mechanism.
    summary_rows = []
    if not discordance.empty:
        summary_rows.extend(
            [
                {"metric": "mean high-beta power", "mean_change": float(discordance["high_beta_power_change"].mean()), "expected_direction": "decrease"},
                {"metric": "S1 dwell time", "mean_change": float(discordance["mean_s1_dwell_time_s_change"].mean()), "expected_direction": "decrease"},
                {"metric": "long-burst fraction", "mean_change": float(discordance["long_high_beta_burst_fraction_change"].mean()), "expected_direction": "decrease"},
                {"metric": "escape rate", "mean_change": float(discordance["s1_escape_rate_per_s_change"].mean()), "expected_direction": "increase"},
                {"metric": "re-entry probability", "mean_change": float(discordance["s1_reentry_probability_change"].mean()), "expected_direction": "decrease"},
            ]
        )
    summary = pd.DataFrame(summary_rows)
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    if not summary.empty:
        ax.bar(summary["metric"], summary["mean_change"], color=["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F"])
        ax.tick_params(axis="x", rotation=25)
    ax.axhline(0, color="0.25", lw=0.8)
    ax.set_ylabel("Mean late - early change")
    ax.set_title("Beta-state persistence summary")
    save_figure(fig, summary, "beta_escape_figure_7_summary_mechanism")


def write_analysis_reports(
    dataset_id: str,
    analysis_scope: str,
    features: pd.DataFrame,
    episodes: pd.DataFrame,
    survival_models: pd.DataFrame,
    hazard_models: pd.DataFrame,
    discordance: pd.DataFrame,
    correlations: pd.DataFrame,
    smr_quad: pd.DataFrame,
    robustness: pd.DataFrame,
    controls: pd.DataFrame,
    spectral_controls: pd.DataFrame,
) -> None:
    changes = paired_changes(features, PRIMARY_THRESHOLD, PRIMARY_CONDITION)
    n_subjects = int(changes["subject"].nunique()) if not changes.empty else 0
    scope_line = "larger empirical dataset" if analysis_scope == "larger_dataset" else "pilot/descriptive local dataset"
    metric_summary = {}
    for metric in [
        "high_beta_power_change",
        "mean_s1_dwell_time_s_change",
        "long_high_beta_burst_fraction_change",
        "s1_escape_rate_per_s_change",
        "s1_reentry_probability_change",
        "smr_power_change",
        "smr_snr_log10_change",
        "clean_smr_compatible_state_occupancy_change",
    ]:
        metric_summary[metric] = float(changes[metric].mean()) if metric in changes and not changes.empty else np.nan
    primary_text = f"""# Primary Beta-State Persistence Analysis

Created: {utc_now()}

Dataset analyzed: `{dataset_id}` ({scope_line}).

Predeclared definitions:

- SMR band: 12-15 Hz.
- High-beta band: 20-30 Hz.
- Broadband control: 4-45 Hz excluding SMR and high-beta for power metrics.
- Sensorimotor channels: E36, E104, E128, following the family helper-code C3/C4/Cz equivalents.
- Primary high-beta episode threshold: subject/session rest-baseline 75th percentile high-beta envelope.
- Sensitivity thresholds computed: 80th percentile, 90th percentile, z-score, MAD.
- S1 high-beta state excludes bins classified as S2 broadband/artifact state.

Primary task-condition sample:

- Subjects with early/late task contrasts: {n_subjects}.
- Mean high-beta power change: {metric_summary['high_beta_power_change']:.6g}.
- Mean S1 dwell-time change: {metric_summary['mean_s1_dwell_time_s_change']:.6g} s.
- Mean long-burst fraction change: {metric_summary['long_high_beta_burst_fraction_change']:.6g}.
- Mean escape-rate change: {metric_summary['s1_escape_rate_per_s_change']:.6g} per s.
- Mean S1 re-entry probability change: {metric_summary['s1_reentry_probability_change']:.6g}.

Interpretation boundary:

These are real-EEG early/late contrasts. They do not establish causality and they do not treat event-derived states as reward states because no true reward/feedback markers were detected.
"""
    write_report(primary_text, "beta_escape_primary_analysis.md")

    surv_line = "not_fit"
    if not survival_models.empty and "hazard_ratio_late_vs_early" in survival_models:
        cox = survival_models[survival_models["model"] == "cox_ph_episode_level_late_vs_early"]
        if not cox.empty:
            surv_line = f"hazard ratio late vs early = {cox.iloc[0].get('hazard_ratio_late_vs_early', np.nan)}; status = {cox.iloc[0].get('status', '')}"
    survival_text = f"""# Survival And Hazard Analysis

Created: {utc_now()}

Primary hypothesis tested:

Successful high-beta inhibition should reduce the survival tail of S1 beta episodes and increase escape hazard more clearly than it reduces mean high-beta power.

Model status:

- Cox/PH episode-level summary: {surv_line}.
- Subject-level paired and permutation tests are in `beta_escape_survival_models.csv`.
- Escape-rate model rows are in `beta_escape_hazard_models.csv`.

Observed primary mean changes:

- Mean high-beta power: {metric_summary['high_beta_power_change']:.6g}.
- Mean S1 dwell time: {metric_summary['mean_s1_dwell_time_s_change']:.6g}.
- Mean long-burst fraction: {metric_summary['long_high_beta_burst_fraction_change']:.6g}.
- Mean escape rate: {metric_summary['s1_escape_rate_per_s_change']:.6g}.

No result is hidden if null or directionally mixed; see the model tables for exact p-values and effect directions.
"""
    write_report(survival_text, "beta_escape_survival_analysis.md")

    q_counts = discordance["power_dwell_quadrant"].value_counts().to_dict() if not discordance.empty else {}
    nonid_text = f"""# Mean-Power Versus Dwell-Time Non-Identifiability

Created: {utc_now()}

Subject classification counts:

{json.dumps(q_counts, indent=2)}

Correlation tests between mean high-beta power change and persistence metrics are in `beta_escape_power_dwell_correlations.csv`.

Decision-relevant point:

Mean high-beta power is mechanistically non-diagnostic if subjects appear in discordant classes where power and dwell-time changes diverge. This report tests that empirical dissociation without claiming that either direction is causal.
"""
    write_report(nonid_text, "beta_escape_nonidentifiability_analysis.md")

    smr_counts = smr_quad["smr_beta_quadrant"].value_counts().to_dict() if not smr_quad.empty else {}
    smr_text = f"""# SMR Acquisition Versus Beta Escape Separability

Created: {utc_now()}

Primary classification:

{json.dumps(smr_counts, indent=2)}

Definitions:

- SMR acquisition primary positive: at least two of SMR power increase, SMR SNR increase, clean SMR-compatible occupancy increase.
- Beta escape primary positive: at least three of dwell-time decrease, long-burst fraction decrease, escape-rate increase, re-entry probability decrease.

Robustness across stricter/liberal definitions and threshold variants is reported in `beta_escape_definition_robustness.csv`.
"""
    write_report(smr_text, "beta_escape_smr_separability_analysis.md")

    control_text = f"""# Broadband And Artifact Controls

Created: {utc_now()}

Controls computed:

- Broadband non-target power.
- Spectral slope over 4-45 Hz excluding SMR and high-beta.
- High-beta residual after log-log aperiodic fit.
- 35-45 Hz noise-floor power.
- High-amplitude influence via 95th-percentile trimming.
- S2 broadband/artifact occupancy.

Complete subject-level controls are in `beta_escape_broadband_controls.csv`; regression/correlation controls are in `beta_escape_spectral_slope_controls.csv`.

Interpretation:

Persistence effects should not be treated as clean beta-state evidence unless they remain directionally interpretable after these broadband/noise checks.
"""
    write_report(control_text, "beta_escape_broadband_artifact_controls.md")

    math_text = """# Mathematical Support For Beta-State Persistence / Escape-Rate Control

This technical report supports the empirical analysis framework only. It is not manuscript prose.

## 1. Three-state metastable model

Let X_t in {S0, S1, S2}, where S0 is a clean SMR-compatible state, S1 is a high-beta occupied state, and S2 is a broadband/artifact-contaminated state. In discrete time with bin width Delta t, transitions are described by a stochastic matrix P with entries P_ij = P(X_{t+Delta t}=Sj | X_t=Si).

## 2. Beta episode definition

A beta episode is a maximal contiguous interval in which the high-beta envelope exceeds a predeclared subject/session baseline threshold and the bin is not classified as S2. Its duration is T_beta.

## 3. Survival function

The dwell-time survival function is S(t) = P(T_beta > t). Longer right tails imply more persistent S1 occupation even if mean high-beta power is unchanged.

## 4. Hazard / escape-rate formulation

The discrete escape hazard is h(t) = P(t <= T_beta < t + Delta t | T_beta >= t). A larger hazard means faster exit from S1. The reciprocal mean dwell time is a compact escape-rate summary when the distribution is not too heavy-tailed.

## 5. Transition matrix formulation

S1 persistence is encoded by P_11 and the distribution of consecutive S1 runs. Re-entry is encoded by P_01 and P_21 or by P(X_{t+Delta t}=S1 | X_t != S1). S0 occupancy and clean SMR-compatible occupancy are separable from S1 escape.

## 6. Mean power and dwell time are not identifiable from one another

Let high-beta power be A during S1 and B outside S1. The time average is mean_power = pi_1 A + (1 - pi_1) B, where pi_1 is S1 occupancy. Many combinations of A, B, and pi_1 give the same mean. Dwell times further depend on transition probability P_11, not just pi_1. Therefore equal mean high-beta power can arise from short frequent episodes, rare long episodes, or amplitude changes within episodes.

## 7. Prediction for high-beta inhibition

If high-beta inhibition acts through state persistence, the most direct empirical signature is reduced S1 dwell-time tail, reduced long-burst fraction, reduced occupancy/re-entry, and increased escape hazard. Mean power may move with those quantities but is not the mechanism by itself.

## 8. Prediction for separability

SMR acquisition and beta escape are distinct control objectives: SMR metrics depend on SMR-band enhancement and clean compatible occupancy, whereas beta escape depends on S1 dwell, hazard, and re-entry. The four-quadrant empirical classification tests whether those objectives dissociate.
"""
    write_report(math_text, "beta_escape_mathematical_support.md")

    figure_notes = """# Figure Notes

Every `beta_escape_` figure was saved as PDF, SVG, and PNG and has a matching CSV source table in `outputs/tables`.

Figures 1-7 are manuscript-candidate technical figures. They should be used only if the final go/no-go report supports the corresponding claim.
"""
    write_report(figure_notes, "beta_escape_figure_notes.md")

    write_final_reports(
        dataset_id,
        analysis_scope,
        n_subjects,
        metric_summary,
        discordance,
        smr_quad,
        robustness,
        controls,
        spectral_controls,
    )


def write_final_reports(
    dataset_id: str,
    analysis_scope: str,
    n_subjects: int,
    metric_summary: dict[str, float],
    discordance: pd.DataFrame,
    smr_quad: pd.DataFrame,
    robustness: pd.DataFrame,
    controls: pd.DataFrame,
    spectral_controls: pd.DataFrame,
) -> None:
    larger_obtained = analysis_scope == "larger_dataset" and n_subjects >= 20
    dwell_directional = (
        metric_summary.get("mean_s1_dwell_time_s_change", np.nan) < 0
        or metric_summary.get("p90_s1_dwell_time_s_change", np.nan) < 0
        or metric_summary.get("long_high_beta_burst_fraction_change", np.nan) < 0
        or metric_summary.get("s1_reentry_probability_change", np.nan) < 0
    )
    power_decreased = metric_summary.get("high_beta_power_change", np.nan) < 0
    discordant = bool(not discordance.empty and discordance["power_dwell_quadrant"].isin(["B_power_down_dwell_not_down", "C_dwell_down_power_not_down"]).any())
    separable = bool(not smr_quad.empty and smr_quad["smr_beta_quadrant"].isin(["B_SMR_acquisition_only", "C_beta_escape_only"]).any())
    controls_ok = bool(not controls.empty and controls["dwell_improved_despite_broadband_increase"].sum() + controls["dwell_improved_after_broadband_direction_check"].sum() > 0)
    robust_ok = bool(not robustness.empty and robustness.get("n_beta_escape_positive", pd.Series(dtype=float)).fillna(0).max() > 0)
    cox_p = np.nan
    dwell_p = np.nan
    tail_p = np.nan
    survival_path = ROOT / "outputs" / "tables" / "beta_escape_survival_models.csv"
    if survival_path.exists():
        survival_models = pd.read_csv(survival_path)
        cox = survival_models[survival_models["model"] == "cox_ph_episode_level_late_vs_early"]
        if not cox.empty:
            cox_p = float(cox.iloc[0].get("p_value", np.nan))
        paired = survival_models[survival_models["model"] == "subject_level_paired_change"]
        dwell_row = paired[paired["metric"] == "mean_s1_dwell_time_s"]
        tail_row = paired[paired["metric"].isin(["p90_s1_dwell_time_s", "long_high_beta_burst_fraction"])]
        if not dwell_row.empty:
            dwell_p = float(dwell_row.iloc[0].get("sign_flip_p_value", np.nan))
        if not tail_row.empty:
            tail_p = float(np.nanmin(tail_row["sign_flip_p_value"].astype(float).to_numpy()))
    inferential_escape_support = bool(
        (np.isfinite(cox_p) and cox_p < 0.05)
        or (np.isfinite(dwell_p) and dwell_p < 0.05)
        or (np.isfinite(tail_p) and tail_p < 0.05)
    )
    dwell_better_than_mean_power = bool(discordant and dwell_directional)
    single_subject_risk = False
    if not smr_quad.empty:
        single_subject_risk = int(smr_quad["beta_escape_primary"].sum()) <= 1
    if not larger_obtained:
        label = "No-go: empirical support insufficient."
    elif inferential_escape_support and discordant and separable and controls_ok and robust_ok and not single_subject_risk:
        label = "Go: strong empirical support with mathematical mechanism."
    elif dwell_directional or discordant or separable:
        label = "Conditional go: promising empirical support but needs cautious framing."
    else:
        label = "No-go: empirical support insufficient."

    results = f"""# Results For Revision

Dataset analyzed: `{dataset_id}`.

Larger dataset obtained: {larger_obtained}.

Subjects with primary early/late task contrasts: {n_subjects}.

Primary mean changes:

- High-beta power: {metric_summary.get('high_beta_power_change', np.nan):.6g}.
- S1 dwell time: {metric_summary.get('mean_s1_dwell_time_s_change', np.nan):.6g}.
- Long-burst fraction: {metric_summary.get('long_high_beta_burst_fraction_change', np.nan):.6g}.
- Escape rate: {metric_summary.get('s1_escape_rate_per_s_change', np.nan):.6g}.
- Re-entry probability: {metric_summary.get('s1_reentry_probability_change', np.nan):.6g}.

Inferential check:

- Cox late-vs-early hazard p-value: {cox_p:.6g}.
- Subject-level dwell sign-flip p-value: {dwell_p:.6g}.
- Best tail/persistence sign-flip p-value: {tail_p:.6g}.

Final label: {label}
"""
    write_report(results, "beta_escape_results_for_revision.md")

    claims = f"""# Claims Supported Versus Unsupported

Supported only if matching tables show empirical backing:

- Larger empirical validation dataset obtained: {larger_obtained}.
- Mean power and dwell/persistence can be empirically discordant: {discordant}.
- SMR acquisition and beta escape can be separable: {separable}.
- Strong survival/hazard evidence for dwell-tail improvement: {inferential_escape_support}.

Unsupported or not claimed:

- High-beta suppression causes SMR learning.
- High-beta suppression is necessary or sufficient for SMR acquisition.
- Mean high-beta power is the mechanism.
- Dwell-time/escape metrics conclusively outperform mean high-beta power.
- Proxy state labels are real reward markers.
- Simulations prove the empirical mechanism.
"""
    write_report(claims, "beta_escape_claims_supported_vs_unsupported.md")

    hypothesis = f"""# Hypothesis Assessment

Central hypothesis:

High-beta inhibition in SMR neurofeedback is better understood as control of beta-state persistence than as mean high-beta power suppression.

Assessment:

- Dwell/persistence direction improved on at least one primary summary: {dwell_directional}.
- Mean power decrease observed on average: {power_decreased}.
- Discordance between power and dwell classes observed: {discordant}.
- Escape/separability evidence observed: {separable}.
- Broadband/artifact controls provide at least partial directional support: {controls_ok}.
- Strong survival/hazard inferential support: {inferential_escape_support}.

Final label: {label}
"""
    write_report(hypothesis, "beta_escape_hypothesis_assessment.md")

    readiness = f"""# Submission Readiness

Readiness is conditional on the empirical tables, not on the mathematical framework alone.

- Larger dataset: {larger_obtained}.
- Robustness across definitions: {robust_ok}.
- Single-subject risk flag: {single_subject_risk}.
- Broadband/artifact control flag: {controls_ok}.
- Strong inferential survival/hazard flag: {inferential_escape_support}.

Recommendation label: {label}
"""
    write_report(readiness, "beta_escape_submission_readiness.md")

    go_no_go = f"""# Go / No-Go

1. Was a larger dataset obtained?
   - {larger_obtained}. `{dataset_id}` contributed {n_subjects} early/late task contrasts.

2. Is there empirical evidence that dwell-time/escape metrics outperform mean high-beta power?
   - Mixed. Directional dwell/persistence improvement: {dwell_directional}. Mean power decrease: {power_decreased}. Discordance present: {discordant}. Strong survival/hazard inferential support: {inferential_escape_support} (Cox p={cox_p:.6g}, dwell sign-flip p={dwell_p:.6g}, best tail p={tail_p:.6g}).

3. Is there evidence that SMR acquisition and beta escape are separable?
   - {separable}.

4. Do results survive broadband/artifact controls?
   - {controls_ok}. See `beta_escape_broadband_controls.csv` and `beta_escape_spectral_slope_controls.csv`.

5. Are results robust across definitions?
   - {robust_ok}. See `beta_escape_definition_robustness.csv`.

6. Are results driven by one subject or dataset?
   - Single-subject risk flag: {single_subject_risk}. Only one larger dataset was analyzed in this run.

7. Is the manuscript viable as a conceptually novel empirical paper with mathematical support?
   - Viability is conditional. The larger dataset supports feasibility, discordance, and separability tests, but the primary survival/hazard evidence is mixed rather than strong.

8. Should the manuscript proceed, require more data, or stop?
   - {label}

Final label: {label}
"""
    write_report(go_no_go, "beta_escape_go_no_go.md")


def run_analysis(download_manifest: pd.DataFrame) -> None:
    dataset_id, analysis_scope = available_analysis_dataset(download_manifest)
    if not dataset_id:
        stop_text = "Larger empirical validation could not be completed because no suitable additional dataset was available locally or feasible to download."
        write_report(stop_text + "\n", "beta_escape_go_no_go.md")
        return
    features, episodes, transitions, thresholds = process_dataset(dataset_id, analysis_scope)
    survival, hazard = survival_and_hazard(episodes)
    write_table(survival, "beta_escape_survival_metrics.csv")
    # Hazard is also saved as the CSV source for hazard figures and a model table below.
    changes = paired_changes(features, PRIMARY_THRESHOLD, PRIMARY_CONDITION)
    survival_models, hazard_models = fit_survival_models(episodes, changes)
    write_table(survival_models, "beta_escape_survival_models.csv")
    write_table(hazard_models, "beta_escape_hazard_models.csv")
    discordance, correlations = build_discordance(changes)
    write_table(discordance, "beta_escape_power_dwell_discordance.csv")
    write_table(correlations, "beta_escape_power_dwell_correlations.csv")
    smr_quad, robustness, influence = smr_beta_quadrants(changes)
    robustness = fill_threshold_robustness(features, robustness)
    write_table(smr_quad, "beta_escape_smr_beta_quadrants.csv")
    write_table(robustness, "beta_escape_definition_robustness.csv")
    write_table(influence, "beta_escape_subject_influence.csv")
    controls, spectral_controls = broadband_controls(changes)
    write_table(controls, "beta_escape_broadband_controls.csv")
    write_table(spectral_controls, "beta_escape_spectral_slope_controls.csv")
    make_all_figures(features, episodes, survival, hazard, discordance, smr_quad, robustness, controls)
    write_analysis_reports(
        dataset_id,
        analysis_scope,
        features,
        episodes,
        survival_models,
        hazard_models,
        discordance,
        correlations,
        smr_quad,
        robustness,
        controls,
        spectral_controls,
    )


def main() -> None:
    started = time.time()
    ensure_repo_structure(ROOT)
    _, _, download_manifest = run_acquisition()
    run_analysis(download_manifest)
    manifest_path = write_manifest(ROOT)
    append_log(ROOT / "outputs" / "logs" / "beta_escape_empirical_processing.log", f"analysis_manifest updated {rel(manifest_path)} elapsed_s={time.time() - started:.1f}")


if __name__ == "__main__":
    main()
