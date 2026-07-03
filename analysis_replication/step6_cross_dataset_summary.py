import os
import sys
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def format_ci(mean, low, high):
    return f"{mean:.1f} [{low:.1f}, {high:.1f}]"

def main():
    bootstrap_file = ROOT / 'outputs/replication_tables/bootstrap_ci_by_dataset.csv'
    if not bootstrap_file.exists():
        print("Missing bootstrap results.")
        return

    df = pd.read_csv(bootstrap_file)

    datasets = ['ds004447', 'ds004444', 'ds004446', 'ds004448']

    metrics = {
        'Clean_Pct': 'Clean Candidate (%)',
        'Blk_Full_Pct': 'Blocked by Full NF-SQI (%)',
        'Broadband_Noise_Floor_Only_AUC': 'BB/Noise AUC (%)',
        'Broadband_Noise_Floor_+_High_Beta_AUC': 'BB/Noise + High Beta AUC (%)',
        'Delta_AUC_C_minus_A': 'Delta AUC (Added Value, %)'
    }

    summary = []

    for d_id in datasets:
        d_df = df[df['Dataset'] == d_id]
        if len(d_df) == 0:
            continue

        row = {'Dataset': 'ds004447 (Primary)' if d_id == 'ds004447' else f'{d_id} (Replication)'}
        for m_key, m_name in metrics.items():
            if m_key.endswith('_AUC') or m_key.startswith('Delta_'):
                lookup_key = m_key
                m_rows = d_df[d_df['Metric'] == lookup_key]
                if len(m_rows) > 0:
                    r = m_rows.iloc[0]
                    row[m_name] = format_ci(r['Mean']*100, r['CI_Lower']*100, r['CI_Upper']*100)
                else:
                    row[m_name] = "N/A"
            else:
                m_rows = d_df[d_df['Metric'] == m_key]
                if len(m_rows) > 0:
                    r = m_rows.iloc[0]
                    row[m_name] = format_ci(r['Mean'], r['CI_Lower'], r['CI_Upper'])
                else:
                    row[m_name] = "N/A"

        summary.append(row)

    df_sum = pd.DataFrame(summary)
    df_sum.to_csv(ROOT / 'outputs/replication_tables/primary_replication_summary.csv', index=False)

    with open(ROOT / 'outputs/replication_tables/primary_replication_summary.tex', 'w') as f:
        f.write(df_sum.to_latex(index=False))

    print("Cross-dataset summary generated.")

if __name__ == '__main__':
    main()
