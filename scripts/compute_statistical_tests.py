import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRED_DIR = ROOT / "archive/stale_pending_delete/results_submission_readiness/predictions"

def compute_ci(values):
    return np.percentile(values, 2.5), np.percentile(values, 97.5)

def get_p_value(diffs, expected_direction):
    if expected_direction == 'positive':
        p = np.mean(np.array(diffs) <= 0) * 2
    else:
        p = np.mean(np.array(diffs) >= 0) * 2
    return min(p, 1.0)

def compute_auc(yt, yp):
    if len(np.unique(yt)) < 2: return np.nan
    return roc_auc_score(yt, yp)

def bootstrap_differences(d_id, rng, n_boot=5000):
    print(f"Bootstrapping differences for {d_id}...")
    
    # Load overlaps
    overlap_path = ROOT / f'archive/stale_pending_delete/results_submission_readiness/{d_id}_snr_primary_contamination_overlap.csv'
    if not overlap_path.exists():
        print(f"Missing {overlap_path}")
        return []
        
    df_ov = pd.read_csv(overlap_path)
    subjects = df_ov['subject'].unique()
    
    # Load predictions
    preds = {}
    for var in ['High_Beta_Only', 'Broadband_Noise_Floor_Only', 'Broadband_Noise_Floor_+_High_Beta', 'Full_NF-SQI']:
        p_path = PRED_DIR / f"{d_id}_{var}_snr_primary_predictions.csv"
        if p_path.exists():
            preds[var] = pd.read_csv(p_path)
            
    sub_data = {s: df_ov[df_ov['subject'] == s] for s in subjects}
    sub_preds = {var: {s: preds[var][preds[var]['subject'] == s] for s in subjects} for var in preds}
    
    boot_diffs = defaultdict(list)
    
    for _ in range(n_boot):
        boot_subs = rng.choice(subjects, size=len(subjects), replace=True)
        
        # Overlap Blocking
        total = sum(sub_data[s]['total_candidates'].sum() for s in boot_subs)
        if total > 0:
            hb_blk = sum(sub_data[s]['blocked_by_hb_single'].sum() for s in boot_subs) / total * 100
            bb_blk = sum(sub_data[s]['blocked_by_bbnf_single'].sum() for s in boot_subs) / total * 100
            full_blk = sum(sub_data[s]['blocked_by_full'].sum() for s in boot_subs) / total * 100
            
            boot_diffs['ΔBlocking BB/NF minus HB'].append(bb_blk - hb_blk)
            boot_diffs['ΔBlocking Full minus HB'].append(full_blk - hb_blk)
            boot_diffs['ΔBlocking Full minus BB/NF'].append(full_blk - bb_blk)
            
        # AUC
        aucs = {}
        for var in preds:
            yt = np.concatenate([sub_preds[var][s]['y_true'].values for s in boot_subs])
            yp = np.concatenate([sub_preds[var][s]['y_pred_proba'].values for s in boot_subs])
            aucs[var] = compute_auc(yt, yp)
            
        if not np.isnan(aucs.get('High_Beta_Only', np.nan)):
            boot_diffs['ΔAUC BB/NF minus HB'].append(aucs['Broadband_Noise_Floor_Only'] - aucs['High_Beta_Only'])
            boot_diffs['ΔAUC Full minus HB'].append(aucs['Full_NF-SQI'] - aucs['High_Beta_Only'])
            boot_diffs['ΔAUC BB/NF+HB minus BB/NF'].append(aucs['Broadband_Noise_Floor_+_High_Beta'] - aucs['Broadband_Noise_Floor_Only'])

    res = []
    for k, diffs in boot_diffs.items():
        diffs = [d for d in diffs if not np.isnan(d)]
        if not diffs: continue
        mean_d = np.mean(diffs)
        ci_l, ci_u = compute_ci(diffs)
        direction = 'positive' if mean_d > 0 else 'negative'
        p = get_p_value(diffs, direction)
        
        res.append({
            'Dataset': d_id,
            'Comparison': k,
            'Δ Estimate': mean_d,
            'CI Lower': ci_l,
            'CI Upper': ci_u,
            'p-value': p,
            'Direction': direction
        })
        
    return res

def main():
    rng = np.random.RandomState(20260702)
    all_res = []
    for d_id in ['ds004447', 'ds004444', 'ds004446']:
        all_res.extend(bootstrap_differences(d_id, rng))
        
    df = pd.DataFrame(all_res)
    out_dir = ROOT / 'results/final'
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / 'nfsqi_statistical_tests.csv', index=False)
    df.to_markdown(out_dir / 'nfsqi_statistical_tests.md', index=False)

if __name__ == '__main__':
    main()
