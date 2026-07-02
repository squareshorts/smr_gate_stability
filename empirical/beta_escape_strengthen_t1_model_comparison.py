import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import roc_auc_score, r2_score, accuracy_score
import warnings

warnings.filterwarnings('ignore')

def load_data():
    df = pd.read_csv('outputs/tables/beta_escape_smr_beta_quadrants.csv')
    df = df[(df['dataset_id'] == 'ds004447') & (df['threshold_def'] == 'p75')].copy()
    if len(df) == 0:
        df = pd.read_csv('outputs/tables/beta_escape_smr_beta_quadrants.csv')
        df = df[df['dataset_id'] == 'ds004447'].copy()
        # use the first available threshold
        if len(df) > 0:
            thresh = df['threshold_def'].iloc[0]
            df = df[df['threshold_def'] == thresh].copy()
    return df

def fit_evaluate_continuous(X, y):
    loo = LeaveOneOut()
    y_pred = np.zeros_like(y, dtype=float)
    
    if X.shape[1] == 0:
        return 0, 0
    
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)
        
        model = Ridge(alpha=1.0)
        model.fit(X_train_s, y_train)
        y_pred[test_index] = model.predict(X_test_s)
        
    r2 = r2_score(y, y_pred)
    corr = np.corrcoef(y, y_pred)[0, 1] if np.std(y_pred) > 0 else 0
    return r2, corr

def fit_evaluate_binary(X, y):
    loo = LeaveOneOut()
    y_pred_proba = np.zeros(len(y), dtype=float)
    y_pred = np.zeros(len(y))
    
    if X.shape[1] == 0 or len(np.unique(y)) < 2:
        return 0, 0
    
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)
        
        model = LogisticRegression(penalty='l2', C=1.0, solver='liblinear')
        model.fit(X_train_s, y_train)
        y_pred_proba[test_index] = model.predict_proba(X_test_s)[:, 1]
        y_pred[test_index] = model.predict(X_test_s)
        
    auc = roc_auc_score(y, y_pred_proba)
    acc = accuracy_score(y, y_pred)
    return auc, acc

def main():
    os.makedirs('outputs/tables', exist_ok=True)
    os.makedirs('outputs/figures', exist_ok=True)
    os.makedirs('outputs/reports', exist_ok=True)
    
    df = load_data()
    print(f"Loaded N={len(df)} subjects")
    
    if len(df) == 0:
        print("No data found for ds004447")
        return

    # Outcomes
    df['smr_acquisition_primary_binary'] = df['smr_acquisition_primary'].apply(lambda x: 1 if x == 'Acquired' else 0)
    df['beta_escape_primary_binary'] = df['beta_escape_primary'].apply(lambda x: 1 if x == 'Escaped' else 0)
    
    outcomes_continuous = {
        'smr_snr_change': df['smr_snr_log10_change'],
        'clean_smr_occupancy_change': df['clean_smr_compatible_state_occupancy_change']
    }
    
    outcomes_binary = {
        'smr_acquisition': df['smr_acquisition_primary_binary'],
        'beta_escape': df['beta_escape_primary_binary']
    }
    
    # Predictor sets
    models = {
        'Model A: Mean Power': ['high_beta_power_change'],
        'Model B: Mean Power + Controls': ['high_beta_power_change', 'broadband_non_target_power_change', 'spectral_slope_change'],
        'Model C: Persistence': ['mean_s1_dwell_time_s_change', 'long_high_beta_burst_fraction_change', 
                                 's1_escape_rate_per_s_change', 's1_reentry_probability_change', 'beta_state_occupancy_change'],
        'Model D: Persistence + Controls': ['mean_s1_dwell_time_s_change', 'long_high_beta_burst_fraction_change', 
                                            's1_escape_rate_per_s_change', 's1_reentry_probability_change', 'beta_state_occupancy_change',
                                            'broadband_non_target_power_change', 'spectral_slope_change'],
        'Model E: Combined': ['high_beta_power_change', 'mean_s1_dwell_time_s_change', 'long_high_beta_burst_fraction_change', 
                              's1_escape_rate_per_s_change', 's1_reentry_probability_change', 'beta_state_occupancy_change',
                              'broadband_non_target_power_change', 'spectral_slope_change']
    }
    
    results = []
    
    for outcome_name, y in outcomes_continuous.items():
        y = y.fillna(y.mean())
        for model_name, features in models.items():
            valid_features = [f for f in features if f in df.columns]
            X = df[valid_features].fillna(0)
            r2, corr = fit_evaluate_continuous(X, y)
            results.append({
                'Outcome': outcome_name,
                'Outcome_Type': 'Continuous',
                'Model': model_name,
                'Metric1_Name': 'R2 (LOOCV)',
                'Metric1_Value': r2,
                'Metric2_Name': 'Pearson r (LOOCV)',
                'Metric2_Value': corr
            })
            
    for outcome_name, y in outcomes_binary.items():
        y = y.fillna(0)
        for model_name, features in models.items():
            valid_features = [f for f in features if f in df.columns]
            X = df[valid_features].fillna(0)
            auc, acc = fit_evaluate_binary(X, y)
            results.append({
                'Outcome': outcome_name,
                'Outcome_Type': 'Binary',
                'Model': model_name,
                'Metric1_Name': 'AUC (LOOCV)',
                'Metric1_Value': auc,
                'Metric2_Name': 'Accuracy (LOOCV)',
                'Metric2_Value': acc
            })
            
    res_df = pd.DataFrame(results)
    res_df.to_csv('outputs/tables/beta_escape_strengthen_model_comparison.csv', index=False)
    
    # Plotting
    import seaborn as sns
    sns.set_theme(style="whitegrid")
    
    plt.figure(figsize=(12, 10))
    
    # Plot Continuous (Pearson r)
    plt.subplot(2, 1, 1)
    cont_df = res_df[res_df['Outcome_Type'] == 'Continuous']
    sns.barplot(data=cont_df, x='Outcome', y='Metric2_Value', hue='Model')
    plt.ylabel('LOOCV Pearson r')
    plt.title('Predicting Continuous SMR Metrics')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Plot Binary (AUC)
    plt.subplot(2, 1, 2)
    bin_df = res_df[res_df['Outcome_Type'] == 'Binary']
    sns.barplot(data=bin_df, x='Outcome', y='Metric1_Value', hue='Model')
    plt.ylabel('LOOCV AUC')
    plt.axhline(0.5, ls='--', color='gray')
    plt.title('Predicting Binary SMR Metrics')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig('outputs/figures/beta_escape_strengthen_model_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/figures/beta_escape_strengthen_model_comparison.pdf', bbox_inches='tight')
    plt.savefig('outputs/figures/beta_escape_strengthen_model_comparison.svg', bbox_inches='tight')
    
    # Markdown report
    with open('outputs/reports/beta_escape_strengthen_model_comparison.md', 'w') as f:
        f.write("# Task 1: Incremental Model Comparison\n\n")
        f.write("## Does beta-state persistence add explanatory value beyond mean high-beta power?\n\n")
        
        # Determine if C > A
        corr_smr = cont_df[(cont_df['Outcome'] == 'smr_snr_change') & (cont_df['Model'] == 'Model C: Persistence')]['Metric2_Value'].values[0]
        corr_pwr = cont_df[(cont_df['Outcome'] == 'smr_snr_change') & (cont_df['Model'] == 'Model A: Mean Power')]['Metric2_Value'].values[0]
        
        auc_smr = bin_df[(bin_df['Outcome'] == 'smr_acquisition') & (bin_df['Model'] == 'Model C: Persistence')]['Metric1_Value'].values[0]
        auc_pwr = bin_df[(bin_df['Outcome'] == 'smr_acquisition') & (bin_df['Model'] == 'Model A: Mean Power')]['Metric1_Value'].values[0]
        
        if corr_smr > corr_pwr or auc_smr > auc_pwr:
            f.write("Yes. Beta-state persistence metrics improve prediction of SMR outcomes beyond what mean high-beta power provides alone.\n\n")
        else:
            f.write("Mixed/No. Beta-state persistence metrics do not clearly outperform mean high-beta power in this dataset.\n\n")
            
        f.write("## Summary of Predictive Performance\n\n")
        # Manual markdown formatting
        headers = res_df.columns.tolist()
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for _, row in res_df.iterrows():
            f.write("| " + " | ".join([str(x) for x in row]) + " |\n")
        
if __name__ == '__main__':
    main()
