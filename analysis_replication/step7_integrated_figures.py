import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def load_data():
    csv_path = ROOT / 'outputs/replication_tables/bootstrap_ci_by_dataset.csv'
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)

def set_style():
    plt.rcParams['pdf.fonttype'] = 42
    plt.rcParams['ps.fonttype'] = 42
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

def plot_auc(df, datasets):
    set_style()
    models = ['Broadband_Noise_Floor_Only', 'High_Beta_Only', 'Broadband_Noise_Floor_+_High_Beta', 'Full_NF-SQI']
    labels = ['BB/Noise', 'HB', 'BB/Noise + HB', 'Full NF-SQI']
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(datasets))
    width = 0.2

    for i, (m, label, color) in enumerate(zip(models, labels, colors)):
        means, yerr = [], []
        for d in datasets:
            row = df[(df['Dataset'] == d) & (df['Metric'] == f'{m}_AUC')]
            if len(row) > 0:
                mean = row.iloc[0]['Mean']
                low = row.iloc[0]['CI_Lower']
                high = row.iloc[0]['CI_Upper']
                means.append(mean)
                yerr.append([mean - low, high - mean])
            else:
                means.append(0)
                yerr.append([0, 0])

        means = np.array(means)
        yerr = np.array(yerr).T
        pos = x + (i - 1.5) * width

        ax.bar(pos, means, width, label=label, color=color, alpha=0.8)
        # Fix yerr if all elements are 0 to avoid matplotlib errors
        if not np.all(yerr == 0):
            ax.errorbar(pos, means, yerr=yerr, fmt='none', ecolor='black', capsize=3)

    ax.set_xticks(x)
    ax.set_xticklabels([d.replace('ds00', 'DS') for d in datasets])
    ax.set_ylabel('ROC AUC')
    ax.set_ylim(0.4, 1.0)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    fig.tight_layout()
    fig.savefig(ROOT / 'outputs/replication_figures/fig_replication_auc_by_dataset.pdf', bbox_inches='tight')
    plt.close(fig)

def plot_composition(df, datasets):
    set_style()
    metrics = ['Clean_Pct', 'HB_Only_Pct', 'BB_Only_Pct', 'Ch_Inc_Only_Pct', 'Multi_Contam_Pct']
    labels = ['Clean', 'High beta only', 'Broadband/noise only', 'Channel inc. only', 'Multi-contam.']
    colors = ['#2ca02c', '#ff7f0e', '#1f77b4', '#9467bd', '#d62728']

    fig, ax = plt.subplots(figsize=(7, 5))

    bottoms = np.zeros(len(datasets))
    x = np.arange(len(datasets))

    for m, label, color in zip(metrics, labels, colors):
        vals = []
        for d in datasets:
            row = df[(df['Dataset'] == d) & (df['Metric'] == m)]
            vals.append(row.iloc[0]['Mean'] if len(row) > 0 else 0)

        vals = np.array(vals)
        ax.bar(x, vals, bottom=bottoms, label=label, color=color, alpha=0.8, width=0.6)
        bottoms += vals

    ax.set_xticks(x)
    ax.set_xticklabels([d.replace('ds00', 'DS') for d in datasets])
    ax.set_ylabel('Candidate Window Composition (%)')
    ax.set_ylim(0, 100)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    fig.tight_layout()
    fig.savefig(ROOT / 'outputs/replication_figures/fig_candidate_composition_by_dataset.pdf', bbox_inches='tight')
    plt.close(fig)

def plot_added_value(df, datasets):
    set_style()
    metrics = ['Delta_AUC_A_minus_B', 'Delta_AUC_C_minus_A', 'Delta_AUC_D_minus_B']
    labels = ['BB/Noise > HB', '(BB/Noise+HB) > BB/Noise', 'Full > HB']

    fig, ax = plt.subplots(figsize=(6, 4))

    y_pos = np.arange(len(metrics)) * 2

    for i, d in enumerate(datasets):
        means, xerr = [], []
        for m in metrics:
            row = df[(df['Dataset'] == d) & (df['Metric'] == m)]
            if len(row) > 0:
                mean = row.iloc[0]['Mean']
                low = row.iloc[0]['CI_Lower']
                high = row.iloc[0]['CI_Upper']
                means.append(mean)
                xerr.append([mean - low, high - mean])
            else:
                means.append(np.nan)
                xerr.append([np.nan, np.nan])

        means = np.array(means)
        xerr = np.array(xerr).T
        pos = y_pos + (i - len(datasets)/2) * 0.3 + 0.15

        # Only plot non-nan values
        valid = ~np.isnan(means)
        if np.any(valid):
            ax.errorbar(means[valid], pos[valid], xerr=xerr[:, valid], fmt='o', label=d.replace('ds00', 'DS'))

    ax.axvline(0, color='black', linestyle='--', alpha=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel('$\Delta$ ROC AUC (95% CI)')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    fig.tight_layout()
    fig.savefig(ROOT / 'outputs/replication_figures/fig_auc_added_value.pdf', bbox_inches='tight')
    plt.close(fig)

def main():
    os.makedirs(ROOT / 'outputs/replication_figures', exist_ok=True)
    df = load_data()
    if df is None:
        print("Missing data.")
        return

    datasets = [d for d in ['ds004447', 'ds004444', 'ds004446', 'ds004448'] if d in df['Dataset'].unique()]
    if not datasets:
        return

    plot_auc(df, datasets)
    plot_composition(df, datasets)
    plot_added_value(df, datasets)
    print("Figures generated.")

if __name__ == '__main__':
    main()
