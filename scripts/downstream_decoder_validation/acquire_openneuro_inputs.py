#!/usr/bin/env python3
"""Acquire the fixed, selective OpenNeuro inputs needed for count replay.

This intentionally downloads no more than the sessions represented by the
released pseudo-online count reports. Raw data and full API manifests remain
under the repository's ignored ``data/`` tree; the durable audit is the small
CSV under ``results/downstream_decoder_validation``.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import requests

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "raw" / "openneuro"
MANIFEST_ROOT = ROOT / "data" / "manifests"
AUDIT_PATH = ROOT / "results" / "downstream_decoder_validation" / "data_acquisition_manifest.csv"
ENDPOINT = "https://openneuro.org/crn/graphql"
DATASETS = ("ds004447", "ds004444", "ds004446")
VERSION = "1.0.1"
TOP_LEVEL = {
    "CHANGES",
    "README",
    "dataset_description.json",
    "participants.tsv",
    "participants.json",
    "task-smrbmi_eeg.json",
    "task-smrbmi_events.json",
}
REQUIRED_SUFFIX = re.compile(
    r"_task-smrbmi_(?:eeg\.edf|eeg\.json|channels\.tsv|electrodes\.tsv|events\.tsv)$"
)
DS004446_SUBJECTS = {"sub-004", "sub-005", "sub-012", "sub-013", "sub-018"}
DS004446_SESSIONS = {"ses-01", "ses-08"}


def graphql_files() -> dict[str, list[dict[str, object]]]:
    aliases = "\n".join(
        f'{dataset}: snapshot(datasetId: "{dataset}", tag: "{VERSION}") '
        "{ id tag description { Name DatasetDOI } files(recursive: true) "
        "{ id filename size directory annexed urls } }"
        for dataset in DATASETS
    )
    payload = {"query": f"query FixedSnapshots {{\n{aliases}\n}}"}
    response = requests.post(ENDPOINT, json=payload, timeout=120)
    response.raise_for_status()
    value = response.json()
    if value.get("errors"):
        raise RuntimeError(f"OpenNeuro GraphQL error: {value['errors']}")
    output: dict[str, list[dict[str, object]]] = {}
    for dataset in DATASETS:
        snapshot = value["data"][dataset]
        if snapshot["tag"] != VERSION:
            raise RuntimeError(f"Unexpected tag for {dataset}: {snapshot['tag']}")
        files = [dict(item) for item in snapshot["files"]]
        output[dataset] = files
        MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)
        (MANIFEST_ROOT / f"openneuro_{dataset}_{VERSION}_file_index.json").write_text(
            json.dumps({"dataset": {"id": dataset}, "snapshot": snapshot}, indent=2) + "\n",
            encoding="utf-8",
        )
    return output


def session_key(session: str) -> tuple[int, str]:
    match = re.fullmatch(r"ses-(\d+)", session)
    return (int(match.group(1)), session) if match else (sys.maxsize, session)


def chosen_sessions(dataset: str, files: list[dict[str, object]]) -> dict[str, set[str]]:
    if dataset == "ds004446":
        return {subject: set(DS004446_SESSIONS) for subject in DS004446_SUBJECTS}
    by_subject: dict[str, set[str]] = defaultdict(set)
    for item in files:
        filename = str(item["filename"])
        match = re.match(r"^(sub-[^/]+)/(ses-[^/]+)/eeg/.*_task-smrbmi_eeg\.edf$", filename)
        if match:
            by_subject[match.group(1)].add(match.group(2))
    selected: dict[str, set[str]] = {}
    for subject, sessions in by_subject.items():
        ordered = sorted(sessions, key=session_key)
        selected[subject] = {ordered[0], ordered[-1]}
    return selected


def select_files(dataset: str, files: list[dict[str, object]]) -> list[dict[str, object]]:
    selected = chosen_sessions(dataset, files)
    required: list[dict[str, object]] = []
    for item in files:
        if bool(item.get("directory")):
            continue
        filename = str(item["filename"])
        if filename in TOP_LEVEL:
            required.append(item)
            continue
        match = re.match(r"^(sub-[^/]+)/(ses-[^/]+)/eeg/(.+)$", filename)
        if not match:
            continue
        subject, session, basename = match.groups()
        if session in selected.get(subject, set()) and REQUIRED_SUFFIX.search(basename):
            required.append(item)
    expected_edfs = 10 if dataset == "ds004446" else (44 if dataset == "ds004447" else 60)
    actual_edfs = sum(str(item["filename"]).endswith("_eeg.edf") for item in required)
    if actual_edfs != expected_edfs:
        raise RuntimeError(f"{dataset}: selected {actual_edfs} EDFs; expected {expected_edfs}")
    return sorted(required, key=lambda item: str(item["filename"]))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(item: dict[str, object], destination: Path) -> tuple[str, int]:
    expected = int(item["size"])
    if destination.exists() and destination.stat().st_size == expected:
        return "already_present", expected
    urls = item.get("urls") or []
    if not urls:
        raise RuntimeError(f"No download URL for {item['filename']}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    if partial.exists():
        partial.unlink()
    request = Request(str(urls[0]), headers={"User-Agent": "smr-nfsqi-downstream-validation/1.0"})
    with urlopen(request, timeout=300) as response, partial.open("wb") as handle:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            handle.write(block)
    actual = partial.stat().st_size
    if actual != expected:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Size mismatch for {item['filename']}: expected {expected}, got {actual}")
    partial.replace(destination)
    return "downloaded", actual


def main() -> int:
    all_files = graphql_files()
    rows: list[dict[str, object]] = []
    for dataset in DATASETS:
        selected = select_files(dataset, all_files[dataset])
        print(f"{dataset}: acquiring {len(selected)} files", flush=True)
        for index, item in enumerate(selected, start=1):
            filename = str(item["filename"])
            destination = DATA_ROOT / dataset / filename
            status, actual = download(item, destination)
            rows.append({
                "dataset": dataset,
                "version": VERSION,
                "filename": filename,
                "file_type": destination.suffix.lower().lstrip("."),
                "annexed": bool(item.get("annexed")),
                "expected_bytes": int(item["size"]),
                "actual_bytes": actual,
                "sha256": sha256(destination),
                "source_url": str((item.get("urls") or [""])[0]).split("?")[0],
                "acquisition_method": "OpenNeuro GraphQL snapshot URL",
                "acquisition_utc": datetime.now(timezone.utc).isoformat(),
                "status": status,
            })
            if index % 10 == 0 or index == len(selected):
                print(f"{dataset}: {index}/{len(selected)}", flush=True)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {AUDIT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
