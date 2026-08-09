import sys
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from editor_hardening_audit.engine import (
    CRITERIA, CRIT_ORDER, nonempty_subsets, subset_id, jaccard, pass_indicators,
    empirical_threshold, channel_inconsistency
)
from utils import (
    criterion_thresholds, pass_indicators_local, aggregate_scores, CACHE_DIR, OUT_DIR
)

def process_q6():
    files = list(CACHE_DIR.glob("*.parquet"))
    subjs = set(f.name.split('_')[1] for f in files)
    
    q6_rows = []
    FROZEN_PCT = {c: p for c, (_, p) in CRITERIA.items()}

    for subj in tqdm(list(subjs)):
        f1 = CACHE_DIR / f"sess01_{subj}_EEG_MI.parquet"
        f2 = CACHE_DIR / f"sess02_{subj}_EEG_MI.parquet"
        
        if not f1.exists() or not f2.exists(): continue
        
        df1 = pd.read_parquet(f1)
        df2 = pd.read_parquet(f2)
        
        train1 = df1[df1['block'] == 'EEG_MI_train']
        train2 = df2[df2['block'] == 'EEG_MI_train']
        
        rest1 = train1[train1['condition'] == 'rest'].sort_values('window_start_s').reset_index(drop=True)
        rest2 = train2[train2['condition'] == 'rest'].sort_values('window_start_s').reset_index(drop=True)
        task2 = train2[train2['condition'] == 'task'].sort_values('window_start_s').reset_index(drop=True)
        
        if len(rest1) < 30 or len(rest2) < 30 or len(task2) == 0: continue
        
        valid2 = task2["raw_feature_valid"].to_numpy(bool)
        n = len(task2)
        
        # Calibrate on sess01 full 60s
        thr1, base1 = criterion_thresholds(rest1, FROZEN_PCT)
        
        # Calibrate on sess02 full 60s
        thr2, base2 = criterion_thresholds(rest2, FROZEN_PCT)
        
        # Apply to sess02 task
        A1 = pass_indicators_local(task2, thr1, base1, valid2)
        A2 = pass_indicators_local(task2, thr2, base2, valid2)
        
        g1_conj = np.ones(n, bool); g2_conj = np.ones(n, bool)
        for c in CRIT_ORDER:
            g1_conj &= A1[c]; g2_conj &= A2[c]
            
        agg1 = aggregate_scores(task2, thr1, base1)
        agg2 = aggregate_scores(task2, thr2, base2)
        
        g1_mean = valid2 & (agg1["mean"] <= 1.0)
        g2_mean = valid2 & (agg2["mean"] <= 1.0)
        
        g1_rms = valid2 & (agg1["rms"] <= 1.0)
        g2_rms = valid2 & (agg2["rms"] <= 1.0)
        
        # H1 Logic
        il_A = task2["A_missing_nonfinite"].to_numpy(bool)
        il_B = task2["B_constant_freeze"].to_numpy(bool)
        il_C = task2["C_saturation_clipping"].to_numpy(bool)
        il_D = task2["D_variance_collapse"].to_numpy(bool)
        any_il = il_A | il_B | il_C | il_D
        
        g1_h1 = g1_mean & ~any_il
        g2_h1 = g2_mean & ~any_il
        
        q6_rows.append(dict(
            participant=subj,
            jaccard_conj=jaccard(g1_conj, g2_conj), accept_conj_1=float(g1_conj.mean()), accept_conj_2=float(g2_conj.mean()),
            jaccard_mean=jaccard(g1_mean, g2_mean), accept_mean_1=float(g1_mean.mean()), accept_mean_2=float(g2_mean.mean()),
            jaccard_rms=jaccard(g1_rms, g2_rms), accept_rms_1=float(g1_rms.mean()), accept_rms_2=float(g2_rms.mean()),
            jaccard_h1=jaccard(g1_h1, g2_h1), accept_h1_1=float(g1_h1.mean()), accept_h1_2=float(g2_h1.mean()),
        ))
        
    pd.DataFrame(q6_rows).to_csv(OUT_DIR / "q6_transport.csv", index=False)
    print("Completed Q6.")

if __name__ == "__main__":
    process_q6()
