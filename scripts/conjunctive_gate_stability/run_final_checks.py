"""Default final check (Windows + Linux): validate outputs, figure data, tests, protected paths, manifest."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def run(args):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "src"), env.get("PYTHONPATH", "")])
    return subprocess.run(args, cwd=str(ROOT), env=env, capture_output=True, text=True)


def main():
    res = {}
    res["validate"] = run([sys.executable, "scripts/conjunctive_gate_stability/validate_existing_results.py"]).returncode == 0
    res["figure_data"] = len(list((ROOT / "results/conjunctive_gate_final/figure_data").glob("fig*.csv"))) >= 10
    res["tests"] = run([sys.executable, "-m", "pytest",
                        "tests/conjunctive_gate_instability", "tests/conjunctive_law_remedy",
                        "tests/conjunctive_gate_stability", "-q"]).returncode == 0
    res["protected"] = run(["git", "diff", "--ignore-cr-at-eol", "--exit-code", "--", "manuscript", "results/final"]).returncode == 0
    man = [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "size": p.stat().st_size}
           for p in (ROOT / "results/conjunctive_gate_final").rglob("*") if p.is_file()]
    pd.DataFrame(man).to_csv(ROOT / "results/conjunctive_gate_final/final_output_manifest.csv", index=False)
    res["manifest_files"] = len(man)
    print("run_final_checks:", res)
    return 0 if all(v is True for k, v in res.items() if k != "manifest_files") else 1


if __name__ == "__main__":
    raise SystemExit(main())
