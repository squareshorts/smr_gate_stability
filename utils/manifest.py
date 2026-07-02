from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    from .paths import repo_root
except ImportError:
    import sys

    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from utils.paths import repo_root


GENERATED_ROOTS = [
    "outputs",
    "data/manifests",
    "data/raw",
    "data/derivatives",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".pdf", ".svg"}:
        return "figure"
    if suffix == ".csv":
        return "table"
    if suffix in {".md", ".txt", ".log"}:
        return "report_or_log"
    return "other"


def build_manifest(root: Path | None = None) -> pd.DataFrame:
    root = root or repo_root()
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for rel_root in GENERATED_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            rows.append(
                {
                    "path": rel,
                    "file_type": classify_path(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "generated_utc": now,
                    "status": "present",
                }
            )
    rows.append(
        {
            "path": "analysis_manifest.csv",
            "file_type": "manifest",
            "bytes": "",
            "sha256": "self-referential",
            "generated_utc": now,
            "status": "present",
        }
    )
    return pd.DataFrame(rows)


def write_manifest(root: Path | None = None) -> Path:
    root = root or repo_root()
    manifest = build_manifest(root)
    path = root / "analysis_manifest.csv"
    manifest.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    print(write_manifest())
