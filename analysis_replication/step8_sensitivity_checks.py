import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main():
    os.makedirs(ROOT / 'outputs/replication_tables', exist_ok=True)
    os.makedirs(ROOT / 'outputs/replication_figures', exist_ok=True)

    datasets = ['ds004447', 'ds004444', 'ds004446', 'ds004448']
    thresholds = ['p70', 'p75', 'p80', 'p90', 'mad']
    results = []

    for d_id in datasets:
        if d_id == 'ds004447':
            feat_path = ROOT / 'outputs/tables/nf_sqi_window_features.csv'
        else:
            feat_path = ROOT / f'outputs/replication_tables/{d_id}_window_features.csv'

        if not feat_path.exists():
            continue

        df = pd.read_csv(feat_path)

        df_rest = df[df['condition'] == 'rest']

        from scipy.stats import median_abs_deviation

        thr_dict = {}
        for (sub, ses), group in df_rest.groupby(['subject', 'session']):
            hb = group['high_beta_power'].dropna()
            if len(hb) == 0: continue
            thr_dict[(sub, ses)] = {
                'p70': hb.quantile(0.70),
                'p75': hb.quantile(0.75),
                'p80': hb.quantile(0.80),
                'p90': hb.quantile(0.90),
                'mad': hb.median() + 1.4826 * median_abs_deviation(hb)
            }

        task_path = ROOT / 'outputs/tables/nf_sqi_task_labeled_windows.csv' if d_id == 'ds004447' else ROOT / f'outputs/replication_tables/{d_id}_task_labeled_windows.csv'
        if not task_path.exists(): continue

        df_lbl = pd.read_csv(task_path)

        for thr in thresholds:
            blocked_fractions = []
            for (sub, ses), group in df_lbl[df_lbl['gate_A'] == True].groupby(['subject', 'session']):
                if (sub, ses) not in thr_dict: continue
                val = thr_dict[(sub, ses)][thr]

                # False admissibles: contaminated by bb/noise/ch_inc/transient
                fa = group[group['is_contaminated'] == True]
                fa_total = len(fa)
                if fa_total > 0:
                    blocked = (fa['high_beta_power'] > val).sum()
                    blocked_fractions.append(blocked / fa_total)

            if blocked_fractions:
                results.append({
                    'Dataset': d_id,
                    'Threshold': thr,
                    'Blocked_Fraction': np.mean(blocked_fractions)
                })

    df_res = pd.DataFrame(results)
    df_res.to_csv(ROOT / 'outputs/replication_tables/threshold_sensitivity_by_dataset.csv', index=False)

    # Plot
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    fig, ax = plt.subplots(figsize=(6, 4))

    for d_id in df_res['Dataset'].unique():
        d_df = df_res[df_res['Dataset'] == d_id]
        ax.plot(d_df['Threshold'], d_df['Blocked_Fraction'] * 100, marker='o', label=d_id.replace('ds00', 'DS'))

    ax.set_ylabel('% False-Admissible Blocked by High Beta')
    ax.set_xlabel('High Beta Threshold Definition')
    ax.legend()
    fig.tight_layout()
    fig.savefig(ROOT / 'outputs/replication_figures/fig_threshold_sensitivity.pdf', bbox_inches='tight')
    plt.close(fig)
    print("Sensitivity analysis complete.")

if __name__ == '__main__':
    main()
