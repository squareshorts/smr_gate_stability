import pandas as pd
from pathlib import Path

files = [
    'archive/stale_pending_delete/results_submission_readiness/ds004447_snr_primary_contamination_overlap.csv',
    'archive/stale_pending_delete/results_submission_readiness/ds004444_snr_primary_contamination_overlap.csv',
    'archive/stale_pending_delete/results_submission_readiness/ds004446_snr_primary_contamination_overlap.csv'
]

task_win_map = {
    'ds004447': 5218,
    'ds004444': 14400,
    'ds004446': 2800
}

edf_files_map = {'ds004447': 44, 'ds004444': 60, 'ds004446': 10}
subs_map = {'ds004447': 22, 'ds004444': 30, 'ds004446': 5}

for f in files:
    df = pd.read_csv(f)
    ds = df['dataset'].iloc[0]
    
    task_windows_n = task_win_map[ds]
    
    gate_a_n = df['total_candidates'].sum()
    gate_a_pct = gate_a_n / task_windows_n * 100
    
    clean_n = df['clean'].sum()
    clean_pct = clean_n / gate_a_n * 100
    
    quality_flagged_n = df['contaminated'].sum()
    qf_pct = quality_flagged_n / gate_a_n * 100
    
    # Gate B: Gate A minus HB blocks
    hb_blocks_n = df['blocked_by_hb_single'].sum()
    gate_b_n = gate_a_n - hb_blocks_n
    gate_b_pct = gate_b_n / task_windows_n * 100
    
    # Gate C: Clean
    gate_c_n = clean_n
    gate_c_pct = gate_c_n / task_windows_n * 100
    
    hb_blocks_pct_qf = hb_blocks_n / quality_flagged_n * 100
    
    full_blocks_n = df['blocked_by_full'].sum()
    full_blocks_pct_qf = full_blocks_n / quality_flagged_n * 100
    
    print(f"{ds},{edf_files_map[ds]},{subs_map[ds]},{task_windows_n},{gate_a_n},{gate_a_pct:.1f},{clean_n},{clean_pct:.1f},{quality_flagged_n},{qf_pct:.1f},{gate_b_n},{gate_b_pct:.1f},{gate_c_n},{gate_c_pct:.1f},{hb_blocks_n},{hb_blocks_pct_qf:.1f},{full_blocks_n},{full_blocks_pct_qf:.1f}")
