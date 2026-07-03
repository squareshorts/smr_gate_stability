import sys
import subprocess
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]

def run_step(script_name):
    print(f"\n{'='*50}\nRunning {script_name}\n{'='*50}")
    start = time.time()
    subprocess.check_call([sys.executable, str(ROOT / 'analysis_replication' / script_name)], cwd=str(ROOT))
    print(f"-> Completed in {time.time() - start:.1f}s")

def main():
    steps = [
        'step1_dataset_inventory.py',
        'step2_reproduce_ds004447.py',
        'step3_apply_companion_datasets.py',
        'step4_5_bootstrap_and_added_value.py',
        'step6_cross_dataset_summary.py',
        'step7_integrated_figures.py',
        'step8_sensitivity_checks.py',
        'step9_10_11_reports.py'
    ]

    start_time = time.time()
    for step in steps:
        run_step(step)

    print(f"\nTotal replication time: {(time.time() - start_time) / 60:.1f} minutes")

if __name__ == '__main__':
    main()
