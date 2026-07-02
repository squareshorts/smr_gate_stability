from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import requests

from utils.paths import ensure_repo_structure


GRAPHQL_URL = "https://openneuro.org/crn/graphql"
OPENNEURO_CANDIDATES = ["ds004444", "ds004446", "ds004447", "ds004448"]
SELECTED_DATASET = "ds004446"
SELECTED_TAG = "1.0.1"
SELECTED_SUBJECTS = ["sub-013", "sub-018", "sub-004", "sub-005", "sub-012"]
SELECTED_SESSIONS = ["ses-01", "ses-08"]
MAX_SUBSET_BYTES = 2_500_000_000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bytes_gb(n_bytes: int | float | str | None) -> float | None:
    try:
        return round(float(n_bytes) / 1_000_000_000.0, 3)
    except Exception:
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def graph_query(query: str, variables: dict[str, Any] | None = None, log_lines: list[str] | None = None) -> dict[str, Any]:
    response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables or {}}, timeout=120)
    if log_lines is not None:
        log_lines.append(f"{utc_now()} POST {GRAPHQL_URL} -> {response.status_code} {len(response.content)} bytes")
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], indent=2))
    return payload["data"]


def fetch_snapshot_index(dataset_id: str, tag: str | None, log_lines: list[str]) -> dict[str, Any]:
    if tag is None:
        q = """
        query($datasetId: ID!) {
          dataset(id: $datasetId) {
            id
            name
            public
            latestSnapshot { tag }
          }
        }
        """
        data = graph_query(q, {"datasetId": dataset_id}, log_lines)
        tag = data["dataset"]["latestSnapshot"]["tag"]
    q = """
    query($datasetId: ID!, $tag: String!) {
      dataset(id: $datasetId) {
        id
        name
        public
      }
      snapshot(datasetId: $datasetId, tag: $tag) {
        id
        tag
        size
        description {
          Name
          DatasetDOI
          License
          Authors
          ReferencesAndLinks
        }
        files(recursive: true) {
          id
          filename
          size
          directory
          annexed
          urls
        }
      }
    }
    """
    data = graph_query(q, {"datasetId": dataset_id, "tag": tag}, log_lines)
    out = {
        "dataset": data["dataset"],
        "snapshot": data["snapshot"],
    }
    index_path = ROOT / "data" / "manifests" / f"openneuro_{dataset_id}_{tag}_file_index.json"
    index_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    file_rows = []
    for item in out["snapshot"]["files"]:
        if item.get("directory"):
            continue
        file_rows.append(
            {
                "dataset_id": dataset_id,
                "snapshot_tag": tag,
                "filename": item["filename"],
                "size_bytes": item.get("size", 0) or 0,
                "annexed": bool(item.get("annexed")),
                "url_available": bool(item.get("urls")),
            }
        )
    pd.DataFrame(file_rows).to_csv(ROOT / "data" / "manifests" / f"openneuro_{dataset_id}_{tag}_file_index.csv", index=False)
    return out


def figshare_resolution(log_lines: list[str]) -> dict[str, Any]:
    doi_url = "https://doi.org/10.6084/m9.figshare.14153504"
    result = {
        "dataset_id": "figshare_14153504",
        "source": "figshare DOI",
        "doi_url": doi_url,
        "resolved_url": "",
        "status_code": "",
        "content_length_bytes": "",
        "license": "not_verified",
        "size_estimate_status": "not_estimated_no_file_index",
        "notes": "DOI resolution attempted; generic Figshare article API did not expose file metadata in this environment.",
    }
    try:
        response = requests.get(doi_url, timeout=30, allow_redirects=True, headers={"User-Agent": "smr-cn-revision/0.2"})
        result.update(
            {
                "resolved_url": response.url,
                "status_code": response.status_code,
                "content_length_bytes": len(response.content),
            }
        )
        log_lines.append(f"{utc_now()} GET {doi_url} -> {response.status_code} {len(response.content)} bytes final_url={response.url}")
    except Exception as exc:
        result["notes"] = f"DOI resolution failed: {type(exc).__name__}: {exc}"
        log_lines.append(f"{utc_now()} GET {doi_url} -> ERROR {type(exc).__name__}: {exc}")
    (ROOT / "data" / "manifests" / "figshare_14153504_resolution.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def candidate_rows(indexes: dict[str, dict[str, Any]], figshare: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for dataset_id, index in indexes.items():
        desc = index["snapshot"]["description"] or {}
        files = [f for f in index["snapshot"]["files"] if not f.get("directory")]
        edfs = [f for f in files if f["filename"].lower().endswith(".edf")]
        subjects = sorted({m.group(1) for f in edfs if (m := re.search(r"(sub-\d+)", f["filename"]))})
        sessions = sorted({m.group(1) for f in edfs if (m := re.search(r"(ses-\d+)", f["filename"]))})
        rows.append(
            {
                "dataset_name": desc.get("Name") or index["dataset"].get("name"),
                "dataset_id": dataset_id,
                "source": f"https://openneuro.org/datasets/{dataset_id}/versions/{index['snapshot']['tag']}",
                "snapshot_tag": index["snapshot"]["tag"],
                "expected_modality": "EEG-BIDS EDF",
                "expected_sample_size": len(subjects),
                "expected_channels": "128 high-density EEG plus reference channel in downloaded sidecars",
                "expected_task": "SMR-BCI/neurofeedback motor-imagery blocks with rest/task/interval events",
                "download_method": "OpenNeuro GraphQL DatasetFile.urls followed by HTTPS GET of selected files",
                "license_status": desc.get("License", ""),
                "suitability": "candidate for SMR/high-beta analysis; size requires subset download",
                "full_size_bytes": sum(int(f.get("size") or 0) for f in files),
                "edf_file_count": len(edfs),
                "subject_count_from_index": len(subjects),
                "session_labels_from_index": ";".join(sessions),
            }
        )
    rows.append(
        {
            "dataset_name": "Continuous SMR-based BCI learning in a large population",
            "dataset_id": "figshare_14153504",
            "source": figshare.get("resolved_url") or figshare.get("doi_url"),
            "snapshot_tag": "",
            "expected_modality": "EEG and behavioral BCI learning data",
            "expected_sample_size": "62",
            "expected_channels": "64 EEG channels expected from Scientific Data article",
            "expected_task": "longitudinal continuous SMR-BCI learning",
            "download_method": "Figshare official metadata/file API, if accessible",
            "license_status": figshare.get("license", "not_verified"),
            "suitability": "not selected in this pass because license and file-size metadata were not verified",
            "full_size_bytes": "",
            "edf_file_count": "",
            "subject_count_from_index": "",
            "session_labels_from_index": "",
        }
    )
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data" / "manifests" / "candidate_datasets_updated.csv", index=False)
    return df


def select_subset_files(index: dict[str, Any]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    files = [f for f in index["snapshot"]["files"] if not f.get("directory")]
    by_name = {f["filename"]: f for f in files}
    selected_names: set[str] = {
        "CHANGES",
        "README",
        "dataset_description.json",
        "participants.tsv",
        "participants.json",
        "task-smrbmi_eeg.json",
        "task-smrbmi_events.json",
    }
    for subject in SELECTED_SUBJECTS:
        for session in SELECTED_SESSIONS:
            prefix = f"{subject}/{session}/eeg/{subject}_{session}_task-smrbmi"
            for suffix in ["_eeg.edf", "_eeg.json", "_channels.tsv", "_electrodes.tsv", "_events.tsv"]:
                name = f"{prefix}{suffix}"
                if name in by_name:
                    selected_names.add(name)
    selected = [by_name[name] for name in sorted(selected_names) if name in by_name]
    rows = []
    for f in selected:
        subject = ""
        session = ""
        if m := re.search(r"(sub-\d+)/(ses-\d+)", f["filename"]):
            subject, session = m.group(1), m.group(2)
        rows.append(
            {
                "dataset_id": SELECTED_DATASET,
                "snapshot_tag": SELECTED_TAG,
                "filename": f["filename"],
                "subject": subject,
                "session": session,
                "size_bytes": int(f.get("size") or 0),
                "size_gb": bytes_gb(f.get("size") or 0),
                "annexed": bool(f.get("annexed")),
                "url_available": bool(f.get("urls")),
                "selected_for_subset": True,
            }
        )
    return pd.DataFrame(rows), selected


def write_size_and_license_tables(indexes: dict[str, dict[str, Any]], figshare: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    size_rows = []
    license_rows = []
    selected_df = pd.DataFrame()
    selected_files: list[dict[str, Any]] = []
    for dataset_id, index in indexes.items():
        files = [f for f in index["snapshot"]["files"] if not f.get("directory")]
        edfs = [f for f in files if f["filename"].lower().endswith(".edf")]
        full_size = sum(int(f.get("size") or 0) for f in files)
        desc = index["snapshot"]["description"] or {}
        if dataset_id == SELECTED_DATASET:
            selected_df, selected_files = select_subset_files(index)
            subset_size = int(selected_df["size_bytes"].sum()) if len(selected_df) else 0
            subset_desc = f"{len(SELECTED_SUBJECTS)} subjects ({','.join(SELECTED_SUBJECTS)}), sessions {','.join(SELECTED_SESSIONS)}"
        else:
            subset_size = ""
            subset_desc = "not selected"
        size_rows.append(
            {
                "dataset_id": dataset_id,
                "snapshot_tag": index["snapshot"]["tag"],
                "full_size_bytes": full_size,
                "full_size_gb": bytes_gb(full_size),
                "edf_file_count": len(edfs),
                "subset_strategy": subset_desc,
                "subset_size_bytes": subset_size,
                "subset_size_gb": bytes_gb(subset_size) if subset_size != "" else "",
                "size_decision": "subset_required" if full_size > MAX_SUBSET_BYTES else "full_feasible_by_threshold",
            }
        )
        license_rows.append(
            {
                "dataset_id": dataset_id,
                "source": f"https://openneuro.org/datasets/{dataset_id}/versions/{index['snapshot']['tag']}",
                "license_field": desc.get("License", ""),
                "public_field": bool(index["dataset"].get("public")),
                "terms_status": "acceptable_for_secondary_analysis" if desc.get("License") == "CC0" and index["dataset"].get("public") else "not_acceptable_or_unclear",
                "notes": "License read from OpenNeuro dataset_description via official GraphQL API.",
            }
        )
    size_rows.append(
        {
            "dataset_id": "figshare_14153504",
            "snapshot_tag": "",
            "full_size_bytes": "",
            "full_size_gb": "",
            "edf_file_count": "",
            "subset_strategy": "not selected",
            "subset_size_bytes": "",
            "subset_size_gb": "",
            "size_decision": figshare.get("size_estimate_status", "not_estimated"),
        }
    )
    license_rows.append(
        {
            "dataset_id": "figshare_14153504",
            "source": figshare.get("resolved_url") or figshare.get("doi_url"),
            "license_field": figshare.get("license", "not_verified"),
            "public_field": "",
            "terms_status": "not_downloaded_license_or_file_index_unverified",
            "notes": figshare.get("notes", ""),
        }
    )
    sizes = pd.DataFrame(size_rows)
    licenses = pd.DataFrame(license_rows)
    sizes.to_csv(ROOT / "data" / "manifests" / "download_size_estimates.csv", index=False)
    licenses.to_csv(ROOT / "data" / "manifests" / "license_and_terms_check.csv", index=False)
    selected_df.to_csv(ROOT / "data" / "manifests" / f"{SELECTED_DATASET}_selected_subset_files.csv", index=False)
    return sizes, licenses, selected_df, selected_files


def write_decision_report(sizes: pd.DataFrame, licenses: pd.DataFrame, selected_df: pd.DataFrame) -> bool:
    selected_size = int(selected_df["size_bytes"].sum()) if len(selected_df) else 0
    selected_license = licenses.loc[licenses["dataset_id"] == SELECTED_DATASET].iloc[0]
    acceptable_license = selected_license["terms_status"] == "acceptable_for_secondary_analysis"
    acceptable_size = selected_size <= MAX_SUBSET_BYTES
    do_download = bool(acceptable_license and acceptable_size and len(selected_df) > 0)
    report = f"""# Data Acquisition Decision

Created: {utc_now()}

Selected first dataset: `{SELECTED_DATASET}` (`The BMI-HDEEG dataset 2`, OpenNeuro snapshot `{SELECTED_TAG}`).

Why selected:

- It is part of the 2023 Scientific Data high-density SMR-BCI/neurofeedback collection.
- The official OpenNeuro metadata reports `CC0` license and public access.
- It is smaller than several sibling high-density snapshots but still has 30 subjects and 8-session structure for most subjects.
- A five-subject pre/post subset is sufficient for proof-of-pipeline empirical anchoring while avoiding a 31 GB full download.

Expected size:

- Full snapshot estimate: {sizes.loc[sizes['dataset_id'] == SELECTED_DATASET, 'full_size_gb'].iloc[0]} GB.
- Selected subset estimate: {bytes_gb(selected_size)} GB ({selected_size} bytes).

License/terms status:

- OpenNeuro `dataset_description.json` license field: `{selected_license['license_field']}`.
- Terms decision: `{selected_license['terms_status']}`.

Download decision:

- Full download will not be used in this pass.
- Subset download will be used: subjects `{','.join(SELECTED_SUBJECTS)}`, sessions `{','.join(SELECTED_SESSIONS)}`.
- Proceed with EEG download: `{do_download}`.

Exact API/command used:

- Metadata and file URLs are obtained with `POST {GRAPHQL_URL}` using the `snapshot(datasetId, tag) {{ files(recursive: true) {{ filename size annexed urls }} }}` query.
- Files are downloaded with HTTPS `GET` from the official `DatasetFile.urls[0]` values returned by OpenNeuro.
- Local command: `python empirical\\wp7_dataset_plan_inventory.py --download`.

Priority-2 dataset status:

- The 2021 longitudinal SMR-BCI figshare DOI was resolved, but file-size and license metadata were not exposed through the attempted official endpoint in this environment. It was therefore not downloaded.
"""
    (ROOT / "outputs" / "reports" / "data_acquisition_decision.md").write_text(report, encoding="utf-8")
    return do_download


def download_file(item: dict[str, Any], dest: Path, log_lines: list[str]) -> dict[str, Any]:
    url = item["urls"][0]
    expected = int(item.get("size") or 0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    status = "downloaded"
    if dest.exists() and dest.stat().st_size == expected:
        status = "already_present"
    else:
        tmp = dest.with_suffix(dest.suffix + ".part")
        if tmp.exists():
            tmp.unlink()
        with requests.get(url, stream=True, timeout=180, headers={"User-Agent": "smr-cn-revision/0.2"}) as response:
            log_lines.append(f"{utc_now()} GET {url.split('?')[0]} -> {response.status_code} expected={expected}")
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
        "file_path": str(dest.relative_to(ROOT)).replace("\\", "/"),
        "file_size_bytes": actual,
        "expected_size_bytes": expected,
        "source": url.split("?")[0],
        "download_date_utc": utc_now(),
        "checksum": sha256_file(dest) if dest.exists() else "",
        "status": status if actual == expected else "size_mismatch",
        "annexed": bool(item.get("annexed")),
    }


def download_subset(selected_files: list[dict[str, Any]], log_lines: list[str]) -> pd.DataFrame:
    rows = []
    raw_root = ROOT / "data" / "raw" / "openneuro" / SELECTED_DATASET
    for idx, item in enumerate(selected_files, start=1):
        dest = raw_root / item["filename"]
        log_lines.append(f"{utc_now()} downloading {idx}/{len(selected_files)} {item['filename']} ({item.get('size', 0)} bytes)")
        rows.append(download_file(item, dest, log_lines))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data" / "manifests" / "download_manifest.csv", index=False)
    return df


def inventory_download(download_manifest: pd.DataFrame | None = None) -> pd.DataFrame:
    manifest_path = ROOT / "data" / "manifests" / "download_manifest.csv"
    if download_manifest is None and manifest_path.exists():
        download_manifest = pd.read_csv(manifest_path)
    if download_manifest is None or download_manifest.empty:
        rows = [
            {
                "dataset_id": SELECTED_DATASET,
                "downloaded_file_count": 0,
                "total_downloaded_size_bytes": 0,
                "subject_count": 0,
                "session_count": 0,
                "available_channel_names": "",
                "sampling_rate": "",
                "event_markers": "",
                "task_condition_labels": "",
                "prepost_evaluation_blocks_exist": "no",
                "feedback_training_blocks_exist": "unknown_no_download",
                "suitable_for_smr_high_beta_analysis": "no",
                "notes": "No download manifest available.",
            }
        ]
        df = pd.DataFrame(rows)
        df.to_csv(ROOT / "outputs" / "tables" / "wp7_dataset_inventory.csv", index=False)
        return df
    local_files = [ROOT / p for p in download_manifest["file_path"].astype(str)]
    edf_files = [p for p in local_files if p.suffix.lower() == ".edf" and p.exists()]
    subjects = sorted({m.group(1) for p in edf_files if (m := re.search(r"(sub-\d+)", str(p)))})
    sessions = sorted({m.group(1) for p in edf_files if (m := re.search(r"(ses-\d+)", str(p)))})
    channel_names: list[str] = []
    sampling_rates: set[str] = set()
    event_values: set[str] = set()
    conditions: set[str] = set()
    for path in local_files:
        if path.name.endswith("_channels.tsv") and not channel_names:
            ch = pd.read_csv(path, sep="\t")
            channel_names = ch["name"].astype(str).tolist()
        if path.name.endswith("_eeg.json"):
            try:
                meta = json.loads(path.read_text(encoding="utf-8"))
                if "SamplingFrequency" in meta:
                    sampling_rates.add(str(meta["SamplingFrequency"]))
            except Exception:
                pass
        if path.name.endswith("_events.tsv"):
            ev = pd.read_csv(path, sep="\t")
            if "value" in ev:
                event_values.update(ev["value"].astype(str).unique().tolist())
            if "instruction" in ev:
                conditions.update(ev["instruction"].astype(str).unique().tolist())
    prepost = {"ses-01", "ses-08"}.issubset(set(sessions))
    sensorimotor = [name for name in ["E36", "E104", "E128"] if name in set(channel_names)]
    suitable = bool(edf_files and sensorimotor and conditions.intersection({"rest", "task"}) and sampling_rates)
    rows = [
        {
            "dataset_id": SELECTED_DATASET,
            "downloaded_file_count": int(len(local_files)),
            "downloaded_eeg_file_count": int(len(edf_files)),
            "total_downloaded_size_bytes": int(sum(p.stat().st_size for p in local_files if p.exists())),
            "total_downloaded_size_gb": bytes_gb(sum(p.stat().st_size for p in local_files if p.exists())),
            "subject_count": int(len(subjects)),
            "subjects": ";".join(subjects),
            "session_count": int(len(sessions)),
            "sessions": ";".join(sessions),
            "available_channel_names": ";".join(channel_names),
            "sensorimotor_channels_for_analysis": ";".join(sensorimotor),
            "sampling_rate": ";".join(sorted(sampling_rates)),
            "event_markers": ";".join(sorted(event_values)),
            "task_condition_labels": ";".join(sorted(conditions)),
            "prepost_evaluation_blocks_exist": "yes" if prepost else "no",
            "feedback_training_blocks_exist": "yes_in_source_sessions_02_to_07_not_downloaded",
            "suitable_for_smr_high_beta_analysis": "yes" if suitable else "no",
            "notes": "Subset preserves BIDS-relative paths and includes pre/post sessions for five subjects.",
        }
    ]
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "outputs" / "tables" / "wp7_dataset_inventory.csv", index=False)
    report = f"""# WP7 Dataset Inventory

Dataset ID: `{SELECTED_DATASET}`.

Downloaded files: {rows[0]['downloaded_file_count']} total, including {rows[0]['downloaded_eeg_file_count']} EDF files.

Total downloaded size: {rows[0]['total_downloaded_size_gb']} GB.

Subjects: {rows[0]['subjects']}.

Sessions: {rows[0]['sessions']}.

Sampling rate: {rows[0]['sampling_rate']} Hz.

Event markers: {rows[0]['event_markers']}.

Task/condition labels: {rows[0]['task_condition_labels']}.

Sensorimotor channels used for analysis: {rows[0]['sensorimotor_channels_for_analysis']}.

Pre/post evaluation blocks exist in subset: {rows[0]['prepost_evaluation_blocks_exist']}.

Feedback/training blocks exist in source: {rows[0]['feedback_training_blocks_exist']}.

Suitable for SMR/high-beta analysis: {rows[0]['suitable_for_smr_high_beta_analysis']}.
"""
    (ROOT / "outputs" / "reports" / "wp7_dataset_inventory.md").write_text(report, encoding="utf-8")
    return df


def run(download: bool = False) -> None:
    ensure_repo_structure(ROOT)
    log_lines = [f"{utc_now()} WP7 acquisition started. download={download}"]
    indexes = {}
    for dataset_id in OPENNEURO_CANDIDATES:
        indexes[dataset_id] = fetch_snapshot_index(dataset_id, None, log_lines)
    figshare = figshare_resolution(log_lines)
    candidate_rows(indexes, figshare)
    sizes, licenses, selected_df, selected_files = write_size_and_license_tables(indexes, figshare)
    do_download = write_decision_report(sizes, licenses, selected_df)
    if download and do_download:
        free = shutil.disk_usage(ROOT).free
        selected_size = int(selected_df["size_bytes"].sum())
        log_lines.append(f"{utc_now()} disk_free_bytes={free} selected_subset_bytes={selected_size}")
        if free < selected_size * 2:
            raise RuntimeError(f"Insufficient free disk for safe download: free={free}, selected={selected_size}")
        download_manifest = download_subset(selected_files, log_lines)
        inventory_download(download_manifest)
    else:
        inventory_download(pd.DataFrame())
        log_lines.append(f"{utc_now()} download skipped. download_arg={download} decision={do_download}")
    (ROOT / "outputs" / "logs" / "wp7_acquisition.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Proceed with selected subset download after metadata/license/size checks.")
    parser.add_argument("--metadata-only", action="store_true", help="Write metadata/decision outputs but do not download EEG.")
    args = parser.parse_args()
    run(download=bool(args.download and not args.metadata_only))


if __name__ == "__main__":
    main()
