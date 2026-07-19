from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]

OPENNEURO_DATASETS = {
    "ds004444": "1.0.1",
    "ds004446": "1.0.1",
    "ds004447": "1.0.1",
    "ds004448": "1.0.2",
}
TASK_NAME = "task-smrbmi"
SENSORIMOTOR_CHANNELS = ["E36", "E104", "E128"]
SMR_BAND = (12.0, 15.0)
HIGH_BETA_BAND = (20.0, 30.0)
BROADBAND_RANGE = (4.0, 45.0)
NOISE_FLOOR_BAND = (35.0, 45.0)
USER_AGENT = "smr-nfsqi-revision/1.0"


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


def session_sort_key(session: str) -> int:
    try:
        return int(session.split("-")[1])
    except Exception:
        return 0


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_openneuro_index(dataset_id: str) -> dict[str, Any]:
    tag = OPENNEURO_DATASETS[dataset_id]
    path = ROOT / "data" / "manifests" / f"openneuro_{dataset_id}_{tag}_file_index.json"
    if not path.exists():
        raise FileNotFoundError(f"OpenNeuro index missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_summary_from_index(dataset_id: str) -> dict[str, Any]:
    index = load_openneuro_index(dataset_id)
    desc = index.get("snapshot", {}).get("description") or {}
    files = [f for f in index["snapshot"]["files"] if not f.get("directory")]
    edf_files = [f for f in files if f["filename"].lower().endswith(".edf")]
    subjects = sorted({m.group(1) for f in edf_files if (m := re.search(r"(sub-\d+)", f["filename"]))})
    sessions = sorted(
        {m.group(1) for f in edf_files if (m := re.search(r"(ses-\d+)", f["filename"]))},
        key=session_sort_key,
    )
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
        sessions = sorted(
            {m.group(1) for p in edfs if (m := re.search(r"(ses-\d+)", str(p)))},
            key=session_sort_key,
        )
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
        suitable = bool(edfs and len(subjects) >= 1 and sensorimotor and sampling_rates and "task" in instructions)
        suitability = "suitable" if suitable else "not_suitable_or_metadata_only"
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
                "suitability_for_nfsqi": suitability,
                "suitability_for_beta_state_persistence": suitability,
                "suitability_notes": (
                    "Raw EDFs plus task events and sensorimotor channels are present."
                    if suitable
                    else "No local EDFs or missing task/sensorimotor metadata in local raw tree."
                ),
            }
        )
    return pd.DataFrame(rows)


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
    for subject in sorted(by_subject):
        sessions = sorted(set(by_subject[subject]), key=session_sort_key)
        if not sessions:
            continue
        for session in sorted({sessions[0], sessions[-1]}, key=session_sort_key):
            prefix = f"{subject}/{session}/eeg/{subject}_{session}_{TASK_NAME}"
            for suffix in ["_eeg.edf", "_eeg.json", "_channels.tsv", "_electrodes.tsv", "_events.tsv"]:
                name = f"{prefix}{suffix}"
                if name in by_name:
                    selected_names.add(name)
    selected_files = []
    for name in sorted(selected_names):
        if name in by_name:
            item = dict(by_name[name])
            item["_dataset_id"] = dataset_id
            selected_files.append(item)
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
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{utc_now()} GET {item['filename']} expected_size={expected}\n")
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
        "dataset_id": item.get("_dataset_id", ""),
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


def parse_subject_session(path: Path) -> tuple[str, str]:
    m = re.search(r"(sub-\d+)[/\\](ses-\d+)", str(path))
    if not m:
        return "", ""
    return m.group(1), m.group(2)


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


def welch_psd(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    nperseg = min(len(x), max(128, int(round(fs * 4.0))))
    if nperseg < 128:
        return np.array([]), np.array([])
    return signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2)


def bandpower_from_psd(freqs: np.ndarray, psd: np.ndarray, band: tuple[float, float]) -> float:
    mask = (freqs >= band[0]) & (freqs <= band[1])
    if mask.sum() < 2:
        return float("nan")
    return float(np.trapezoid(psd[mask], freqs[mask]))
