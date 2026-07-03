import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, precision_score, recall_score, f1_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]

def main():
    print("Starting main()")
    os.makedirs('outputs/tables', exist_ok=True)
    os.makedirs('outputs/figures', exist_ok=True)
    os.makedirs('outputs/reports', exist_ok=True)

    # Load labeled windows from Task 2/3
    print("Loading data...")
    df = pd.read_csv('outputs/tables/nf_sqi_task_labeled_windows.csv')
    df_1s = df[df['window_size'] == 1.0].copy()

    # ---------------------------------------------------------
    # Task 4: Added Value of High Beta (Modeling)
    # ---------------------------------------------------------

    target = 'is_contaminated'
    groups = df_1s['subject'].values

    models = {
        'Model A: Broadband/Noise': ['broadband_power', 'noise_floor_power'],
        'Model B: High Beta Only': ['high_beta_power'],
        'Model C: Broadband/Noise + High Beta': ['broadband_power', 'noise_floor_power', 'high_beta_power'],
        'Model D: Full NF-SQI': ['broadband_power', 'noise_floor_power', 'high_beta_power', 'transient_score', 'channel_inconsistency', 'nonstationarity']
    }
    prediction_keys = {
        'Model A: Broadband/Noise': 'Broadband_Noise_Floor_Only',
        'Model B: High Beta Only': 'High_Beta_Only',
        'Model C: Broadband/Noise + High Beta': 'Broadband_Noise_Floor_+_High_Beta',
        'Model D: Full NF-SQI': 'Full_NF-SQI',
    }

    results = []

    for name, features in models.items():
        y_true = []
        y_pred = []
        y_pred_proba = []
        test_sub_col = []

        subjects = df_1s['subject'].unique()

        for test_sub in subjects:
            train_df = df_1s[df_1s['subject'] != test_sub]
            test_df = df_1s[df_1s['subject'] == test_sub]

            if len(train_df) == 0 or len(test_df) == 0 or train_df[target].nunique() < 2:
                continue

            scaler = StandardScaler()
            X_train = scaler.fit_transform(train_df[features].fillna(0))
            X_test = scaler.transform(test_df[features].fillna(0))

            clf = LogisticRegression(class_weight='balanced', random_state=20260702, solver='lbfgs', max_iter=1000)
            clf.fit(X_train, train_df[target])

            y_true.extend(test_df[target].values)
            y_pred.extend(clf.predict(X_test))
            y_pred_proba.extend(clf.predict_proba(X_test)[:, 1])
            test_sub_col.extend([test_sub] * len(test_df))

        if len(y_true) > 0 and len(np.unique(y_true)) > 1:
            auc = roc_auc_score(y_true, y_pred_proba)
            bacc = balanced_accuracy_score(y_true, y_pred)
            f1 = f1_score(y_true, y_pred)
            prec = precision_score(y_true, y_pred, zero_division=0)
            rec = recall_score(y_true, y_pred)

            results.append({
                'Model': name,
                'AUC': auc,
                'Balanced_Accuracy': bacc,
                'F1': f1,
                'Precision': prec,
                'Recall': rec
            })

            # Save predictions for bootstrap (needed by replication steps)
            df_preds = pd.DataFrame({
                'subject': test_sub_col,
                'y_true': y_true,
                'y_pred_proba': y_pred_proba
            })
            df_preds.to_csv(ROOT / f'outputs/tables/ds004447_{prediction_keys[name]}_predictions.csv', index=False)

    res_df = pd.DataFrame(results)
    res_df.to_csv('outputs/tables/nf_sqi_model_comparison.csv', index=False)

    print("Plotting model comparison...")
    # Plotting Model Comparison as a dot/lollipop plot
    plt.rcParams.update({'font.size': 14})

    # Sort for cleaner presentation if needed, but keeping the predefined order is better for models A, B, C, D
    fig, ax = plt.subplots(figsize=(10, 6))

    y_pos = np.arange(len(res_df))
    auc_vals = res_df['AUC'].values
    acc_vals = res_df['Balanced_Accuracy'].values
    model_labels = res_df['Model'].str.replace('Model A: ', '').str.replace('Model B: ', '').str.replace('Model C: ', '').str.replace('Model D: ', '')

    ax.hlines(y=y_pos - 0.15, xmin=0.5, xmax=auc_vals, color='steelblue', alpha=0.4, linewidth=3)
    ax.plot(auc_vals, y_pos - 0.15, 'o', color='steelblue', markersize=10, label='AUC')

    ax.hlines(y=y_pos + 0.15, xmin=0.5, xmax=acc_vals, color='indianred', alpha=0.4, linewidth=3)
    ax.plot(acc_vals, y_pos + 0.15, 'o', color='indianred', markersize=10, label='Balanced accuracy')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(model_labels)
    ax.axvline(0.5, ls='--', color='gray', alpha=0.7)

    ax.set_xlim(0.45, 0.8)
    ax.set_xlabel('Performance Score', fontsize=16)
    ax.legend(loc='lower right', frameon=False)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig('outputs/figures/nf_sqi_model_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/figures/nf_sqi_model_comparison.pdf', bbox_inches='tight')
    plt.savefig('outputs/figures/nf_sqi_model_comparison.svg', bbox_inches='tight')

    # ---------------------------------------------------------
    # Task 5: Reward Window Decomposition
    # ---------------------------------------------------------

    print("Decomposing candidates...")
    # Analyze only candidate reward windows (Gate A == True)
    cands = df_1s[df_1s['gate_A'] == True].copy()

    # We need the full window features to compute thresholds
    full_df = pd.read_csv('outputs/tables/nf_sqi_window_features.csv')
    full_df_1s = full_df[full_df['window_size'] == 1.0].copy()

    from scipy.stats import median_abs_deviation

    decomp_results = []

    for (sub, ses), group in cands.groupby(['subject', 'session']):
        # Find rest for this subject/session to get thresholds
        sub_rest = full_df_1s[(full_df_1s['subject'] == sub) & (full_df_1s['session'] == ses) & (full_df_1s['condition'] == 'rest')]
        if len(sub_rest) == 0:
            continue

        hb_thr = np.percentile(sub_rest['high_beta_power'].dropna(), 75)
        bb_thr = np.percentile(sub_rest['broadband_power'].dropna(), 75)
        nf_thr = np.percentile(sub_rest['noise_floor_power'].dropna(), 75)
        tr_thr = np.percentile(sub_rest['transient_score'].dropna(), 90)

        hb_contam = group['high_beta_power'] > hb_thr
        bb_contam = group['broadband_power'] > bb_thr
        nf_contam = group['noise_floor_power'] > nf_thr
        tr_contam = group['transient_score'] > tr_thr

        sum_contam = hb_contam.astype(int) + bb_contam.astype(int) + nf_contam.astype(int) + tr_contam.astype(int)

        clean = sum_contam == 0
        multi = sum_contam > 1
        only_hb = (sum_contam == 1) & hb_contam
        only_bb = (sum_contam == 1) & bb_contam
        only_nf = (sum_contam == 1) & nf_contam
        only_tr = (sum_contam == 1) & tr_contam

        n_cands = len(group)
        if n_cands == 0: continue

        decomp_results.append({
            'subject': sub,
            'session': ses,
            'total_candidates': n_cands,
            'clean': clean.sum() / n_cands,
            'multi_contaminated': multi.sum() / n_cands,
            'high_beta_only': only_hb.sum() / n_cands,
            'broadband_only': only_bb.sum() / n_cands,
            'noise_floor_only': only_nf.sum() / n_cands,
            'transient_only': only_tr.sum() / n_cands
        })

    decomp_df = pd.DataFrame(decomp_results)
    decomp_df.to_csv('outputs/tables/nf_sqi_reward_window_decomposition.csv', index=False)

    # Plotting decomposition as horizontal bar chart
    mean_decomp = decomp_df[['clean', 'high_beta_only', 'broadband_only', 'noise_floor_only', 'transient_only', 'multi_contaminated']].mean()

    # Replace variable names
    mean_decomp = mean_decomp.rename({
        'clean': 'Clean',
        'high_beta_only': 'High beta only',
        'broadband_only': 'Broadband only',
        'noise_floor_only': 'Noise floor only',
        'transient_only': 'Transient amplitude only',
        'multi_contaminated': 'Multi-contaminated'
    })

    # Assertion check
    assert np.all(np.abs(mean_decomp.sum() - 1.0) < 1e-3), "Pie chart values do not sum to 100%"

    mean_decomp_pct = mean_decomp * 100
    mean_decomp_sorted = mean_decomp_pct.sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(mean_decomp_sorted.index, mean_decomp_sorted.values, color='mediumseagreen')
    ax.set_xlabel('Proportion of candidate reward windows (%)', fontsize=16)

    for bar in bars:
        width = bar.get_width()
        ax.annotate(f'{width:.1f}%',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(3, 0),
                    textcoords="offset points",
                    ha='left', va='center', fontsize=12)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig('outputs/figures/nf_sqi_reward_window_decomposition.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/figures/nf_sqi_reward_window_decomposition.pdf', bbox_inches='tight')
    plt.savefig('outputs/figures/nf_sqi_reward_window_decomposition.svg', bbox_inches='tight')

    # Reports
    with open('outputs/reports/nf_sqi_high_beta_added_value.md', 'w') as f:
        f.write("# Task 4: Added Value of High Beta\n\n")
        f.write("Cross-validated logistic regression models were trained to detect contaminated windows (broadband/noise/transient contamination).\n\n")
        f.write("## Model Performance\n\n")
        headers = res_df.columns.tolist()
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for _, row in res_df.iterrows():
            f.write("| " + " | ".join([f"{x:.4f}" if isinstance(x, float) else str(x) for x in row]) + " |\n")
        auc_by_model = res_df.set_index('Model')['AUC'].to_dict()
        auc_a = auc_by_model.get('Model A: Broadband/Noise', np.nan)
        auc_b = auc_by_model.get('Model B: High Beta Only', np.nan)
        auc_c = auc_by_model.get('Model C: Broadband/Noise + High Beta', np.nan)
        f.write("\n**Conclusion**: In this model comparison, high beta alone performs below broadband/noise-floor predictors, and adding high beta to broadband/noise-floor predictors does not improve AUC ")
        f.write(f"(Model A AUC={auc_a:.4f}; Model B AUC={auc_b:.4f}; Model C AUC={auc_c:.4f}). ")
        f.write("High beta is therefore supported here as a gate-level safeguard for a subset of candidate windows, not as an incremental predictive feature beyond broadband/noise-floor metrics.\n")

    with open('outputs/reports/nf_sqi_reward_window_decomposition.md', 'w') as f:
        f.write("# Task 5: Signal-Quality Decomposition of Reward Windows\n\n")
        f.write("SMR-only candidate reward windows are highly heterogeneous. By decomposing the windows based on signal-quality thresholds, we find:\n")
        f.write(f"- Clean SMR: {mean_decomp['Clean']*100:.1f}%\n")
        f.write(f"- High-Beta Only Contamination: {mean_decomp['High beta only']*100:.1f}%\n")
        f.write(f"- Multi-Contaminated: {mean_decomp['Multi-contaminated']*100:.1f}%\n\n")
        f.write("This supports reporting high-beta inhibition as one safeguard within NF-SQI while retaining broadband/noise-floor and other quality checks as the dominant contamination controls.\n")

if __name__ == '__main__':
    try:
        main()
    except BaseException as e:
        import traceback
        with open('error.log', 'w') as f:
            f.write(traceback.format_exc())
        raise
