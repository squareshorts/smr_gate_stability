from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from .paths import repo_root


FIGURE_EXTENSIONS = ("pdf", "svg", "png")


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 130,
            "savefig.dpi": 220,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save_csv_backed_figure(
    fig: plt.Figure,
    source: pd.DataFrame,
    stem: str,
    root: Path | None = None,
    close: bool = True,
    extra_sources: Iterable[tuple[str, pd.DataFrame]] | None = None,
) -> list[Path]:
    root = root or repo_root()
    fig_dir = root / "outputs" / "figures"
    table_dir = root / "outputs" / "tables"
    fig_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    source_path = table_dir / f"{stem}_source.csv"
    source.to_csv(source_path, index=False)
    paths = [source_path]

    if extra_sources:
        for suffix, frame in extra_sources:
            extra_path = table_dir / f"{stem}_{suffix}_source.csv"
            frame.to_csv(extra_path, index=False)
            paths.append(extra_path)

    for ext in FIGURE_EXTENSIONS:
        path = fig_dir / f"{stem}.{ext}"
        fig.savefig(path, bbox_inches="tight")
        paths.append(path)
    if close:
        plt.close(fig)
    return paths


def simple_heatmap(ax: plt.Axes, pivot: pd.DataFrame, title: str, cmap: str, vmin=None, vmax=None):
    image = ax.imshow(pivot.values, aspect="auto", origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([str(x) for x in pivot.columns], rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([str(x) for x in pivot.index])
    return image

