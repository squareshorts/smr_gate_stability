import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score, balanced_accuracy_score
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def compute_ci(values):
    return np.percentile(values, 2.5), np.percentile(values, 97.5)

def main():
    os.makedirs(ROOT / 'outputs/replication_tables', exist_ok=True)

    datasets = ['ds004447', 'ds004444', 'ds004446', 'ds004448']
    results = []

    for d_id in datasets:
        print(f"Bootstrapping metrics for {d_id}...")

        # 1. Proportions from overlap
        if d_id == 'ds004447':
            overlap_path = ROOT / 'outputs/tables/nf_sqi_contamination_overlap.csv'
        else:
            overlap_path = ROOT / f'outputs/replication_tables/{d_id}_contamination_overlap.csv'

        if not overlap_path.exists():
            print(f"  Missing {overlap_path.name}")
            continue

        df_ov = pd.read_csv(overlap_path)
        subjects = df_ov['subject'].unique()

        boot_metrics = defaultdict(list)
        rng = np.random.RandomState(20260702)

        # Precompute subject data for fast resampling
        sub_data = {s: df_ov[df_ov['subject'] == s] for s in subjects}

        for _ in range(5000):
            boot_subs = rng.choice(subjects, size=len(subjects), replace=True)
            # Aggregate sums directly
            total = sum(sub_data[s]['total_candidates'].sum() for s in boot_subs)
            if total == 0: continue

            clean = sum(sub_data[s]['clean'].sum() for s in boot_subs) / total * 100
            if 'high_beta_excl' in df_ov.columns:
                hb_only = sum(sub_data[s]['high_beta_excl'].sum() for s in boot_subs) / total * 100
                bb_only = sum(sub_data[s]['broadband_noise_excl'].sum() for s in boot_subs) / total * 100
                ch_only = sum(sub_data[s]['channel_inc_excl'].sum() for s in boot_subs) / total * 100
                multi = sum(sub_data[s]['multi_contam'].sum() for s in boot_subs) / total * 100
            else:
                hb_only = bb_only = ch_only = multi = np.nan

            fa_total = sum(sub_data[s]['contaminated'].sum() for s in boot_subs) if 'contaminated' in df_ov.columns else 0
            if fa_total > 0 and 'blocked_by_hb_single' in df_ov.columns:
                fa_hb = sum(sub_data[s]['blocked_by_hb_single'].sum() for s in boot_subs) / fa_total * 100
                fa_bb = sum(sub_data[s]['blocked_by_bbnf_single'].sum() for s in boot_subs) / fa_total * 100
                fa_ch = sum(sub_data[s]['blocked_by_ch_single'].sum() for s in boot_subs) / fa_total * 100
                fa_full = sum(sub_data[s]['blocked_by_full'].sum() for s in boot_subs) / fa_total * 100
            else:
                fa_hb = fa_bb = fa_ch = fa_full = np.nan

            boot_metrics['Clean_Pct'].append(clean)
            boot_metrics['HB_Only_Pct'].append(hb_only)
            boot_metrics['BB_Only_Pct'].append(bb_only)
            boot_metrics['Ch_Inc_Only_Pct'].append(ch_only)
            boot_metrics['Multi_Contam_Pct'].append(multi)
            boot_metrics['Blk_HB_Pct'].append(fa_hb)
            boot_metrics['Blk_BBNF_Pct'].append(fa_bb)
            boot_metrics['Blk_Ch_Inc_Pct'].append(fa_ch)
            boot_metrics['Blk_Full_Pct'].append(fa_full)

        for k, v in boot_metrics.items():
            if v and not np.isnan(v[0]):
                low, high = compute_ci(v)
                results.append({
                    'Dataset': d_id,
                    'Metric': k,
                    'Mean': np.mean(v),
                    'CI_Lower': low,
                    'CI_Upper': high
                })

        # 2. Model performance and Delta AUCs
        models = [
            'Broadband_Noise_Floor_Only',
            'High_Beta_Only',
            'Broadband_Noise_Floor_+_High_Beta',
            'Full_NF-SQI'
        ]

        preds_dict = {}
        for m in models:
            if d_id == 'ds004447':
                p_path = ROOT / f'outputs/tables/ds004447_{m}_predictions.csv'
            else:
                p_path = ROOT / f'outputs/replication_tables/{d_id}_{m}_predictions.csv'
            if p_path.exists():
                preds_dict[m] = pd.read_csv(p_path)

        if len(preds_dict) == len(models):
            subs = preds_dict[models[0]]['subject'].unique()

            # Precompute subject indices for each model to speed up resampling
            sub_idx = {m: {s: np.where(preds_dict[m]['subject'] == s)[0] for s in subs} for m in models}
            y_true_dict = {m: preds_dict[m]['y_true'].values for m in models}
            y_pred_dict = {m: preds_dict[m]['y_pred_proba'].values for m in models}

            b_auc = {m: [] for m in models}
            b_bacc = {m: [] for m in models}
            b_delta_c_minus_a = []
            b_delta_a_minus_b = []
            b_delta_d_minus_b = []

            for _ in range(5000):
                boot_subs = rng.choice(subs, size=len(subs), replace=True)

                # A: BB/Noise, B: HB, C: BB/Noise+HB, D: Full
                m_a = 'Broadband_Noise_Floor_Only'
                m_b = 'High_Beta_Only'
                m_c = 'Broadband_Noise_Floor_+_High_Beta'
                m_d = 'Full_NF-SQI'

                aucs = {}
                for m in models:
                    idx = np.concatenate([sub_idx[m][s] for s in boot_subs])
                    yt = y_true_dict[m][idx]
                    yp = y_pred_dict[m][idx]
                    if len(np.unique(yt)) > 1:
                        a = roc_auc_score(yt, yp)
                        ba = balanced_accuracy_score(yt, yp > 0.5)
                        b_auc[m].append(a)
                        b_bacc[m].append(ba)
                        aucs[m] = a
                    else:
                        b_auc[m].append(np.nan)
                        b_bacc[m].append(np.nan)
                        aucs[m] = np.nan

                b_delta_c_minus_a.append(aucs[m_c] - aucs[m_a])
                b_delta_a_minus_b.append(aucs[m_a] - aucs[m_b])
                b_delta_d_minus_b.append(aucs[m_d] - aucs[m_b])

            for m in models:
                v_auc = [v for v in b_auc[m] if not np.isnan(v)]
                if v_auc:
                    low, high = compute_ci(v_auc)
                    results.append({'Dataset': d_id, 'Metric': f'{m}_AUC', 'Mean': np.mean(v_auc), 'CI_Lower': low, 'CI_Upper': high})
                v_ba = [v for v in b_bacc[m] if not np.isnan(v)]
                if v_ba:
                    low, high = compute_ci(v_ba)
                    results.append({'Dataset': d_id, 'Metric': f'{m}_BACC', 'Mean': np.mean(v_ba), 'CI_Lower': low, 'CI_Upper': high})

            v_dc = [v for v in b_delta_c_minus_a if not np.isnan(v)]
            if v_dc:
                low, high = compute_ci(v_dc)
                results.append({'Dataset': d_id, 'Metric': 'Delta_AUC_C_minus_A', 'Mean': np.mean(v_dc), 'CI_Lower': low, 'CI_Upper': high})

            v_da = [v for v in b_delta_a_minus_b if not np.isnan(v)]
            if v_da:
                low, high = compute_ci(v_da)
                results.append({'Dataset': d_id, 'Metric': 'Delta_AUC_A_minus_B', 'Mean': np.mean(v_da), 'CI_Lower': low, 'CI_Upper': high})

            v_dd = [v for v in b_delta_d_minus_b if not np.isnan(v)]
            if v_dd:
                low, high = compute_ci(v_dd)
                results.append({'Dataset': d_id, 'Metric': 'Delta_AUC_D_minus_B', 'Mean': np.mean(v_dd), 'CI_Lower': low, 'CI_Upper': high})

        print("  Done.")

    df_res = pd.DataFrame(results)
    df_res.to_csv(ROOT / 'outputs/replication_tables/bootstrap_ci_by_dataset.csv', index=False)

    # Save a minimal tex fragment
    with open(ROOT / 'outputs/replication_tables/bootstrap_ci_by_dataset.tex', 'w') as f:
        f.write(df_res.to_latex(index=False, float_format="%.3f"))

if __name__ == '__main__':
    main()
