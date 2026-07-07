import os
import sys
import subprocess
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run_script(script_name):
    print(f"Running {script_name}...")
    subprocess.check_call([sys.executable, str(ROOT / 'empirical' / script_name)], cwd=str(ROOT))

def assert_close(actual, expected, name, tol=0.1):
    if abs(actual - expected) > tol:
        raise ValueError(f"{name} discrepancy: actual {actual:.1f}, expected {expected:.1f}")
    print(f"  [PASS] {name}: {actual:.1f}% == {expected:.1f}%")

def main():
    # Rerun the core analytical pipeline for ds004447 (assuming t1 features exist to save 15+ mins,
    # but recomputing all gates and stats to ensure zero drift).
    run_script('nf_sqi_t2_t3_gates_and_admissibility.py')
    run_script('nf_sqi_overlap_decomposition.py')
    run_script('nf_sqi_t4_t5_modeling.py')

    # 1. Candidate-window composition
    df_overlap = pd.read_csv(ROOT / 'outputs/tables/nf_sqi_contamination_overlap.csv')

    # We aggregate across all subjects and sessions to get the global percentages (unweighted means)
    clean = df_overlap['clean'].mean() * 100
    hb_only = df_overlap['high_beta_excl'].mean() * 100
    bb_only = df_overlap['broadband_noise_excl'].mean() * 100
    ch_only = df_overlap['channel_inc_excl'].mean() * 100
    tr_only = df_overlap['transient_excl'].mean() * 100
    multi = df_overlap['multi_contam'].mean() * 100

    print("\n--- Candidate-window composition ---")
    assert_close(clean, 53.5, "Clean")
    assert_close(hb_only, 4.5, "High beta only")
    assert_close(bb_only, 15.2, "Broadband/noise only")
    assert_close(ch_only, 9.0, "Channel inconsistency only")
    assert_close(tr_only, 0.2, "Transient amplitude only")
    assert_close(multi, 17.7, "Multi-contaminated")

    # 2. False-admissible blocking
    # A candidate is false-admissible if it is contaminated
    fa_hb = df_overlap['blocked_by_hb_single'].mean() * 100
    fa_bb = df_overlap['blocked_by_bbnf_single'].mean() * 100
    fa_tr = df_overlap['blocked_by_tr_single'].mean() * 100
    fa_ch = df_overlap['blocked_by_ch_single'].mean() * 100
    fa_full = df_overlap['blocked_by_full'].mean() * 100

    print("\n--- False-admissible blocking ---")
    assert_close(fa_hb, 30.4, "High beta")
    assert_close(fa_bb, 62.0, "Broadband/noise floor")
    assert_close(fa_tr, 4.1, "Transient amplitude")
    assert_close(fa_ch, 47.9, "Channel inconsistency")
    assert_close(fa_full, 97.7, "Full NF-SQI")

    # 3. Contamination detection
    df_models = pd.read_csv(ROOT / 'outputs/tables/nf_sqi_model_comparison.csv')

    # broadband/noise = "Broadband/Noise Floor Only"
    # high beta only = "High Beta Only"
    # bb + hb = "Broadband/Noise Floor + High Beta"
    # full = "Full NF-SQI"

    models = {
        'Model A: Broadband/Noise': ('Broadband/Noise Floor Only', 0.714, 0.662),
        'Model B: High Beta Only': ('High Beta Only', 0.558, 0.544),
        'Model C: Broadband/Noise + High Beta': ('Broadband/Noise Floor + High Beta', 0.700, 0.660),
        'Model D: Full NF-SQI': ('Full NF-SQI', 0.702, 0.656)
    }

    print("\n--- Contamination detection ---")
    for name, (disp_name, exp_auc, exp_acc) in models.items():
        row = df_models[df_models['Model'] == name].iloc[0]
        act_auc = row['AUC']
        act_acc = row['Balanced_Accuracy']

        # Scale to percentages for assert_close
        assert_close(act_auc*100, exp_auc*100, f"{disp_name} AUC", tol=0.1)
        assert_close(act_acc*100, exp_acc*100, f"{disp_name} Balanced Accuracy", tol=0.1)

    print("\n[SUCCESS] ds004447 reproduced exactly within rounding tolerance.")

if __name__ == '__main__':
    main()
