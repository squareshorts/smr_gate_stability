from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_repo_structure(root: Path | None = None) -> Path:
    root = root or repo_root()
    dirs = [
        "code",
        "models",
        "simulations",
        "empirical",
        "figures",
        "utils",
        "data",
        "data/raw",
        "data/derivatives",
        "data/manifests",
        "raw",
        "derivatives",
        "manifests",
        "docs",
        "outputs",
        "outputs/figures",
        "outputs/tables",
        "outputs/logs",
        "outputs/reports",
        "tests",
    ]
    for rel in dirs:
        (root / rel).mkdir(parents=True, exist_ok=True)
    return root


def out_path(*parts: str, root: Path | None = None) -> Path:
    root = root or repo_root()
    path = root.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
