import os
from pathlib import Path
import subprocess

TARGET_ROOT = Path('c:/work/smr-neurofeedback-reanalysis-2026')
LOCAL_ROOT = Path('c:/work/smr_gate_stability')

TEMP_DIR = LOCAL_ROOT / 'temp_k_sensitivity'
TEMP_DIR.mkdir(parents=True, exist_ok=True)

with open(TARGET_ROOT / 'scripts' / '15_nonlinear_dynamics_extraction.py', 'r') as f:
    orig_15 = f.read()

with open(TARGET_ROOT / 'scripts' / '28_benchmark_phase_geometry.py', 'r') as f:
    orig_28 = f.read()

for k in [5, 10, 20, 30]:
    print(f'Creating scripts for k={k}...')
    new_15 = orig_15.replace('grad_mag = phase_gradient(X, phase, k=10)', f'grad_mag = phase_gradient(X, phase, k={k})')
    
    path_15 = TEMP_DIR / f'15_ext_k{k}.py'
    with open(path_15, 'w') as f:
        f.write(new_15)

    new_28 = orig_28.replace(
        'ROOT = Path(__file__).resolve().parents[1]',
        f'ROOT = Path("{TARGET_ROOT.as_posix()}")'
    )
    new_28 = new_28.replace(
        'ROOT / "scripts" / "15_nonlinear_dynamics_extraction.py"',
        f'Path("{path_15.as_posix()}")'
    )
    
    out_dir = LOCAL_ROOT / "results" / "k_sensitivity" / f"k_{k}"
    new_28 = new_28.replace(
        'TABLE_ROOT = ROOT / "results" / "tables"',
        f'TABLE_ROOT = Path("{(out_dir / "tables").as_posix()}")'
    )
    new_28 = new_28.replace(
        'FIGURE_ROOT = ROOT / "results" / "figures"',
        f'FIGURE_ROOT = Path("{(out_dir / "figures").as_posix()}")'
    )
    new_28 = new_28.replace(
        'DOC_PATH = ROOT / "docs" / "benchmark_phase_geometry_audit.md"',
        f'DOC_PATH = Path("{(out_dir / "docs" / "benchmark_phase_geometry_audit.md").as_posix()}")'
    )
    new_28 = new_28.replace(
        'MANUSCRIPT_SUMMARY_PATH = ROOT / "docs" / "benchmark_phase_geometry_manuscript_ready_results.md"',
        f'MANUSCRIPT_SUMMARY_PATH = Path("{(out_dir / "docs" / "benchmark_phase_geometry_manuscript_ready_results.md").as_posix()}")'
    )
    
    path_28 = TEMP_DIR / f'28_bench_k{k}.py'
    with open(path_28, 'w') as f:
        f.write(new_28)

    print(f'Running analysis for k={k}...')
    
    # Copy existing tables to avoid FileNotFoundError for external dependencies
    import shutil
    src_tables = TARGET_ROOT / "results" / "tables"
    dst_tables = out_dir / "tables"
    shutil.copytree(src_tables, dst_tables, dirs_exist_ok=True)
        
    py_bin = TARGET_ROOT / ".venv" / "Scripts" / "python.exe"
    subprocess.run([str(py_bin), str(path_28), "--stage", "analyze"], check=True)
    subprocess.run([str(py_bin), str(path_28), "--stage", "robustness"], check=True)
    subprocess.run([str(py_bin), str(path_28), "--stage", "figures"], check=True)
    
print("All k completed.")
