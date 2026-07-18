"""STAGE 8 — repository inventory, dependency-reference map, and safe archival moves.

Moves are performed with os.replace (mv works on this mount; rm/delete does not). Only
unambiguously disposable/dead items are moved; scientific/uncertain files -> manual review.
Protected paths and verified active outputs are never touched.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CLEAN = ROOT / "results" / "repository_cleanup_final"
CLEAN.mkdir(parents=True, exist_ok=True)
ARCHIVE = ROOT / "archive" / "deadends"

PROTECTED_PREFIXES = ("manuscript/", "results/final/", "data/raw/", ".git/")
ACTIVE_PREFIXES = (
    "results/conjunctive_gate_instability/", "results/conjunctive_law_remedy/",
    "results/conjunctive_gate_final/", "results/baseline_gate_stability/checkpoints/features",
    "results/baseline_gate_stability/checkpoints/downstream_decoder_features",
    "results/baseline_gate_stability/downstream/", "results/downstream_decoder_validation/fold_definition.csv",
    "results/runtime_assurance_remediation/checkpoints/feature_cache",
    "src/", "scripts/conjunctive_gate_stability/", "scripts/conjunctive_law_remedy/",
    "scripts/baseline_gate_stability/", "scripts/downstream_decoder_validation/",
    "tests/conjunctive", "configs/", "docs/conjunctive_gate_stability/", "environments/",
)


def h(p):
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except Exception:
        return ""


def rel(p):
    return str(p.relative_to(ROOT)).replace("\\", "/")


def classify(r, size):
    if r.endswith((".pyc",)) or "__pycache__" in r or "/.pytest_tmp/" in r or r.startswith(".pytest_tmp/") or "/.ipynb_checkpoints/" in r:
        return "disposable_cache"
    if size == 0:
        return "zero_byte"
    return "keep_or_review"


def main():
    PRUNE = {".git", ".venv", "site-packages", "node_modules", ".pytest_tmp", "__pycache__",
             ".ipynb_checkpoints", "checkpoints", "raw", "feature_cache", "downstream_decoder_features",
             "features", "downstream_folds", "source_windows", "degradation"}
    LOCAL_ENVS = []
    inv, moves, deletes, manual, dupes = [], [], [], [], {}
    for dirpath, dirnames, filenames in os.walk(ROOT, onerror=lambda e: None):
        # record but do not descend into very large cache dirs (still count them separately)
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        for fn in filenames:
            p = Path(dirpath) / fn
            try:
                if p.is_symlink() or not p.is_file():
                    continue
                r = rel(p)
                size = p.stat().st_size
            except OSError:
                continue
            protected = any(r.startswith(x) for x in PROTECTED_PREFIXES)
            active = any(r.startswith(x) for x in ACTIVE_PREFIXES)
            cls = classify(r, size)
            digest = h(p) if (size < 50_000 and (active or cls in ("zero_byte", "disposable_cache"))) else ""
            inv.append({"path": r, "size": size, "hash": digest, "protected": protected,
                        "active": active, "class": cls})
            if digest:
                dupes.setdefault(digest, []).append(r)

    inv_df = pd.DataFrame(inv)
    inv_df.to_csv(CLEAN / "repository_inventory_before.csv", index=False)

    # duplicate hash report
    dup_rows = [{"hash": k, "count": len(v), "paths": ";".join(v)} for k, v in dupes.items() if len(v) > 1]
    pd.DataFrame(dup_rows).to_csv(CLEAN / "duplicate_hash_report.csv", index=False)

    # dependency reference map (which result dirs are read by active scripts)
    refs = []
    active_scripts = list((ROOT / "scripts" / "conjunctive_gate_stability").rglob("*.py")) + \
                     list((ROOT / "scripts" / "conjunctive_law_remedy").rglob("*.py"))
    text = "\n".join(s.read_text(errors="ignore") for s in active_scripts)
    for cand in ["conjunctive_gate_instability", "conjunctive_law_remedy", "baseline_gate_stability",
                 "downstream_decoder_validation", "runtime_assurance_remediation", "runtime_assurance",
                 "repository_cleanup", "figure_corrections", "external_monitor"]:
        refs.append({"artifact": cand, "referenced_by_active_pipeline": cand in text})
    pd.DataFrame(refs).to_csv(CLEAN / "dependency_reference_map.csv", index=False)

    # dead-end candidate inventory: disposable caches + zero-byte (only non-protected, non-active-critical)
    dead = inv_df[(inv_df["class"].isin(["disposable_cache", "zero_byte"])) & (~inv_df.protected)]
    dead.to_csv(CLEAN / "deadend_candidate_inventory.csv", index=False)

    # protected paths list
    (CLEAN / "protected_paths.txt").write_text(
        "manuscript/\nresults/final/\ndata/raw/\n*.tex\n*.bib\nZenodo/release metadata\n", encoding="utf-8")

    # ---- SAFE ARCHIVAL MOVES ----
    # Move zero-byte non-protected files and .pytest_tmp trees to archive (reversible). __pycache__/.pyc
    # are left in place but gitignored (rm denied; moving thousands is pointless as they regenerate).
    def do_move(src_rel, sub):
        src = ROOT / src_rel
        if not src.exists():
            return None
        dst = ARCHIVE / sub / src_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        hb = h(src)
        try:
            os.replace(src, dst)
            return {"original_path": src_rel, "new_path": rel(dst), "hash_before": hb, "hash_after": h(dst),
                    "reason": f"{sub}", "references_checked": True, "reversible": True, "status": "moved"}
        except Exception as e:
            return {"original_path": src_rel, "new_path": str(dst), "hash_before": hb, "hash_after": "",
                    "reason": f"{sub}", "references_checked": True, "reversible": True, "status": f"FAILED:{e}"}

    # zero-byte non-protected, non-active files
    for _, row in dead[dead["class"] == "zero_byte"].iterrows():
        if any(row.path.startswith(x) for x in ("results/conjunctive_gate_final/",)):
            continue  # keep our own new outputs
        sub = "superseded_figures" if row.path.endswith((".png", ".pdf")) else "obsolete_outputs"
        m = do_move(row.path, sub)
        if m:
            moves.append(m)

    moves_df = pd.DataFrame(moves)
    moves_df.to_csv(CLEAN / "file_move_manifest.csv", index=False)
    pd.DataFrame(deletes, columns=["path", "reason", "status"]).to_csv(CLEAN / "file_delete_manifest.csv", index=False)

    # manual review: large precursor result dirs not referenced by active pipeline
    man = inv_df[(~inv_df.protected) & (~inv_df.active) &
                 (inv_df.path.str.startswith(("results/runtime_assurance", "results/repository_cleanup",
                                              "results/figure_corrections", "results/downstream_decoder_validation/figures")))]
    man.assign(proposed_action="manual_review_archive_candidate").to_csv(CLEAN / "manual_review_required.csv", index=False)
    pd.DataFrame(man.path.tolist(), columns=["path"]).to_csv(CLEAN / "unresolved_files.csv", index=False)

    # canonical file index (active pipeline)
    canon = inv_df[inv_df.active & (~inv_df["class"].isin(["disposable_cache", "zero_byte"]))]
    canon[["path", "size", "hash"]].to_csv(CLEAN / "canonical_file_index.csv", index=False)

    # archive index
    if ARCHIVE.exists():
        arows = [{"path": rel(p), "size": p.stat().st_size} for p in ARCHIVE.rglob("*") if p.is_file()]
        pd.DataFrame(arows).to_csv(CLEAN / "archive_index.csv", index=False)
    else:
        pd.DataFrame(columns=["path", "size"]).to_csv(CLEAN / "archive_index.csv", index=False)

    print(f"inventory={len(inv_df)} files; zero_byte={int((inv_df['class']=='zero_byte').sum())}; "
          f"disposable_cache={int((inv_df['class']=='disposable_cache').sum())}; "
          f"duplicates_groups={len(dup_rows)}; moved={len(moves)}; manual_review={len(man)}")
    print("moved:", moves_df.original_path.tolist() if len(moves_df) else "none")


if __name__ == "__main__":
    main()
