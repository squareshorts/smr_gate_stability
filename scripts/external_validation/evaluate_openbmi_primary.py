import pandas as pd
import numpy as np
from tqdm import tqdm
from itertools import combinations
from utils import *

from editor_hardening_audit.engine import CRITERIA, CRIT_ORDER, nonempty_subsets, subset_id, jaccard

def process():
    files = list(CACHE_DIR.glob("*.parquet"))
    print(f"Loaded {len(files)} cache files.")
    
    q1_rows = []
    q2_rows = []
    q3_rows = []
    q4_rows = []
    q5_rows = []
    q6_rows = []

    FROZEN_PCT = {c: p for c, (_, p) in CRITERIA.items()}

    for f in tqdm(files):
        df = pd.read_parquet(f)
        subj = f.name.split('_')[1] # e.g. subj01
        sess = f.name.split('_')[0] # e.g. sess01
        
        # PRIMARY: train block
        df_train = df[df['block'] == 'EEG_MI_train'].copy()
        if df_train.empty: continue
        
        rest = df_train[df_train['condition'] == 'rest'].sort_values('window_start_s').reset_index(drop=True)
        task = df_train[df_train['condition'] == 'task'].sort_values('window_start_s').reset_index(drop=True)
        if len(rest) < 30 or len(task) == 0: continue
        
        valid = task["raw_feature_valid"].to_numpy(bool)
        n = len(task)
        
        # Split half calibration
        b1 = rest.iloc[:30]
        b2 = rest.iloc[-30:] if len(rest) >= 60 else rest.iloc[30:]
        
        if len(b1) == 0 or len(b2) == 0: continue
        
        thr1, base1 = criterion_thresholds(b1, FROZEN_PCT)
        thr2, base2 = criterion_thresholds(b2, FROZEN_PCT)
        
        A1 = pass_indicators_local(task, thr1, base1, valid)
        A2 = pass_indicators_local(task, thr2, base2, valid)
        
        # --- Q1 & Q2 Logic ---
        gates = {}
        for s in nonempty_subsets():
            g1 = np.ones(n, bool); g2 = np.ones(n, bool)
            for c in s:
                g1 &= A1[c]; g2 &= A2[c]
            sid = subset_id(s)
            gates[sid] = (g1, g2)
            
            # Independence predicted
            pp1 = float(np.prod([A1[c].mean() for c in s]))
            pp2 = float(np.prod([A2[c].mean() for c in s]))
            pq = float(np.prod([(A1[c] & A2[c]).mean() for c in s]))
            den = pp1 + pp2 - pq
            jpred = 1.0 if den <= 1e-12 else pq / den
            
            q1_rows.append(dict(
                participant=subj, session=sess, subset_id=sid, cardinality=len(s),
                observed_jaccard=jaccard(g1, g2), predicted_jaccard=jpred,
                accept_g1=float(g1.mean()), accept_g2=float(g2.mean())
            ))
            
        for k in range(1, 5):
            for s in combinations(CRIT_ORDER, k):
                sid = subset_id(s)
                g1, g2 = gates[sid]
                M = g1 & g2; D1 = g1 & ~g2; D2 = g2 & ~g1
                m = int(M.sum()); d1 = int(D1.sum()); d2 = int(D2.sum())
                for add in CRIT_ORDER:
                    if add in s: continue
                    a1, a2 = A1[add], A2[add]
                    ng1, ng2 = gates[subset_id(tuple(sorted(s + (add,), key=CRIT_ORDER.index)))]
                    
                    c_cnt = int((M & a1 & a2).sum())
                    x1 = int((M & a1 & ~a2).sum())
                    x2 = int((M & a2 & ~a1).sum())
                    e1 = int((D1 & a1).sum()); e2 = int((D2 & a2).sum())
                    
                    den_new = c_cnt + x1 + x2 + e1 + e2
                    j_recon = 1.0 if den_new == 0 else c_cnt / den_new
                    
                    q2_rows.append(dict(
                        participant=subj, session=sess, from_subset=sid,
                        to_subset=subset_id(tuple(sorted(s + (add,), key=CRIT_ORDER.index))),
                        added_criterion=add, from_cardinality=k,
                        observed_delta=jaccard(ng1, ng2) - jaccard(g1, g2),
                        reconstructed_jnew=j_recon, reconstructed_delta=j_recon - jaccard(g1, g2)
                    ))
                    
        # --- Q3 Logic (Aggregation) ---
        agg1 = aggregate_scores(task, thr1, base1)
        agg2 = aggregate_scores(task, thr2, base2)
        # Using 1.0 threshold for normalized score
        mean1 = valid & (agg1["mean"] <= 1.0); mean2 = valid & (agg2["mean"] <= 1.0)
        rms1 = valid & (agg1["rms"] <= 1.0); rms2 = valid & (agg2["rms"] <= 1.0)
        
        conj1, conj2 = gates["Q12345"]
        
        q3_rows.append(dict(
            participant=subj, session=sess, 
            jaccard_conj=jaccard(conj1, conj2), accept_conj=float(conj1.mean()),
            jaccard_mean=jaccard(mean1, mean2), accept_mean=float(mean1.mean()),
            jaccard_rms=jaccard(rms1, rms2), accept_rms=float(rms1.mean())
        ))
        
        # --- Q4 Logic (Frozen H1) ---
        # H1 = mean-percentile aggregate AND hard interlocks {A, B, C, D}
        il_A = task["A_missing_nonfinite"].to_numpy(bool)
        il_B = task["B_constant_freeze"].to_numpy(bool)
        il_C = task["C_saturation_clipping"].to_numpy(bool)
        il_D = task["D_variance_collapse"].to_numpy(bool)
        any_il = il_A | il_B | il_C | il_D
        
        h1_1 = mean1 & ~any_il
        h1_2 = mean2 & ~any_il
        
        q4_rows.append(dict(
            participant=subj, session=sess,
            jaccard_h1=jaccard(h1_1, h1_2), accept_h1=float(h1_1.mean()),
            il_A_rate=float(il_A.mean()), il_B_rate=float(il_B.mean()),
            il_C_rate=float(il_C.mean()), il_D_rate=float(il_D.mean()),
            any_il_rate=float(any_il.mean())
        ))
        
        # --- Q5 Logic (Calibration duration) ---
        for dur in [15, 30, 45, 60]:
            if dur > len(rest): continue
            bdur = rest.iloc[:dur]
            thrd, based = criterion_thresholds(bdur, FROZEN_PCT)
            Ad = pass_indicators_local(task, thrd, based, valid)
            g_dur = np.ones(n, bool)
            for c in CRIT_ORDER: g_dur &= Ad[c]
            aggd = aggregate_scores(task, thrd, based)
            mean_dur = valid & (aggd["mean"] <= 1.0)
            rms_dur = valid & (aggd["rms"] <= 1.0)
            h1_dur = mean_dur & ~any_il
            
            q5_rows.append(dict(
                participant=subj, session=sess, duration=dur,
                accept_conj=float(g_dur.mean()), accept_mean=float(mean_dur.mean()),
                accept_rms=float(rms_dur.mean()), accept_h1=float(h1_dur.mean())
            ))
            
    pd.DataFrame(q1_rows).to_csv(OUT_DIR / "q1_cardinality.csv", index=False)
    pd.DataFrame(q2_rows).to_csv(OUT_DIR / "q2_composition.csv", index=False)
    pd.DataFrame(q3_rows).to_csv(OUT_DIR / "q3_aggregation.csv", index=False)
    pd.DataFrame(q4_rows).to_csv(OUT_DIR / "q4_h1.csv", index=False)
    pd.DataFrame(q5_rows).to_csv(OUT_DIR / "q5_duration.csv", index=False)
    print("Completed primary evaluations.")

if __name__ == "__main__":
    process()
