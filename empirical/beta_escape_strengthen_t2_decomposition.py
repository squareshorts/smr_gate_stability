import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')

def load_and_preprocess_data():
    df = pd.read_csv('outputs/tables/beta_escape_primary_features.csv')
    df = df[(df['dataset_id'] == 'ds004447') & (df['threshold_def'] == 'p75')].copy()
    if len(df) == 0:
        df = pd.read_csv('outputs/tables/beta_escape_primary_features.csv')
        df = df[df['dataset_id'] == 'ds004447'].copy()
        thresh = df['threshold_def'].iloc[0]
        df = df[df['threshold_def'] == thresh].copy()
        
    # Pivot to get early and late
    features_to_diff = [
        'high_beta_power',
        'high_beta_power_trimmed95', 
        'beta_state_occupancy',
        's1_episode_rate_per_min',
        'mean_s1_dwell_time_s',
        'long_high_beta_burst_fraction',
        's1_escape_rate_per_s',
        's1_reentry_probability',
        'broadband_non_target_power',
        'spectral_slope'
    ]
    
    # Aggregate over any duplicate condition/sessions per subject/phase
    df = df.groupby(['subject', 'phase'])[features_to_diff].mean().reset_index()
    
    pivot_df = df.pivot(index='subject', columns='phase', values=features_to_diff)
    pivot_df.columns = [f'{col[0]}_{col[1]}' for col in pivot_df.columns]
    
    # Calculate change (late - early)
    change_df = pd.DataFrame(index=pivot_df.index)
    for feat in features_to_diff:
        if f'{feat}_early' in pivot_df.columns and f'{feat}_late' in pivot_df.columns:
            change_df[f'{feat}_change'] = pivot_df[f'{feat}_late'] - pivot_df[f'{feat}_early']
            
    # Include original raw metrics for later inspection if needed
    for col in pivot_df.columns:
        change_df[col] = pivot_df[col]

            
    return change_df.dropna()

def main():
    os.makedirs('outputs/tables', exist_ok=True)
    os.makedirs('outputs/figures', exist_ok=True)
    os.makedirs('outputs/reports', exist_ok=True)
    
    df = load_and_preprocess_data()
    print(f"Loaded N={len(df)} subjects for decomposition")
    
    if len(df) == 0:
        return
        
    target = 'high_beta_power_change'
    predictors = [
        'high_beta_power_trimmed95_change',
        'beta_state_occupancy_change',
        's1_episode_rate_per_min_change',
        'mean_s1_dwell_time_s_change',
        'long_high_beta_burst_fraction_change',
        's1_escape_rate_per_s_change',
        's1_reentry_probability_change',
        'broadband_non_target_power_change'
    ]
    
    # 1. Bivariate correlations
    results = []
    for p in predictors:
        if p in df.columns:
            r = np.corrcoef(df[target], df[p])[0, 1]
            results.append({
                'Predictor': p.replace('_change', ''),
                'Pearson_r_with_Mean_Power_Change': r,
                'R2_Marginal': r**2
            })
            
    res_df = pd.DataFrame(results)
    res_df = res_df.sort_values('R2_Marginal', ascending=False)
    res_df.to_csv('outputs/tables/beta_escape_strengthen_decomposition.csv', index=False)
    
    # 2. Multiple Regression to get relative importance (standardized coefficients)
    scaler = StandardScaler()
    valid_preds = [p for p in predictors if p in df.columns]
    X = df[valid_preds]
    X_s = pd.DataFrame(scaler.fit_transform(X), columns=X.columns, index=X.index)
    y_s = scaler.fit_transform(df[[target]])[:, 0]
    
    X_s = sm.add_constant(X_s)
    model = sm.OLS(y_s, X_s).fit()
    
    # 3. Plotting waterfall/bar chart
    plt.figure(figsize=(10, 6))
    sns.barplot(data=res_df, x='R2_Marginal', y='Predictor', palette='viridis')
    plt.title('Variance in High-Beta Power Change Explained by State Metrics')
    plt.xlabel('Marginal R^2')
    plt.tight_layout()
    plt.savefig('outputs/figures/beta_escape_strengthen_decomposition_waterfall.png', dpi=300)
    plt.savefig('outputs/figures/beta_escape_strengthen_decomposition_waterfall.pdf')
    plt.savefig('outputs/figures/beta_escape_strengthen_decomposition_waterfall.svg')
    
    # Plotting Amplitude vs Occupancy vs Persistence
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 3, 1)
    sns.regplot(data=df, x='high_beta_power_trimmed95_change', y=target)
    plt.title('Amplitude vs Mean Power')
    
    plt.subplot(1, 3, 2)
    sns.regplot(data=df, x='beta_state_occupancy_change', y=target)
    plt.title('Occupancy vs Mean Power')
    
    plt.subplot(1, 3, 3)
    sns.regplot(data=df, x='mean_s1_dwell_time_s_change', y=target)
    plt.title('Dwell Time vs Mean Power')
    
    plt.tight_layout()
    plt.savefig('outputs/figures/beta_escape_strengthen_amplitude_occupancy_persistence.png', dpi=300)
    plt.savefig('outputs/figures/beta_escape_strengthen_amplitude_occupancy_persistence.pdf')
    plt.savefig('outputs/figures/beta_escape_strengthen_amplitude_occupancy_persistence.svg')
    
    # Markdown report
    with open('outputs/reports/beta_escape_strengthen_decomposition.md', 'w') as f:
        f.write("# Task 2: Amplitude-Occupancy-Persistence Decomposition\n\n")
        f.write("## What does 'high-beta suppression' mean empirically?\n\n")
        
        top_driver = res_df.iloc[0]['Predictor']
        f.write(f"The variance in mean high-beta power change is primarily driven by: **{top_driver}**.\n\n")
        
        f.write("### Multiple Regression (Standardized Coefficients)\n\n")
        f.write("```text\n")
        f.write(model.summary().as_text())
        f.write("\n```\n\n")
        
        f.write("### Bivariate Relationships\n\n")
        # Manual markdown formatting
        headers = res_df.columns.tolist()
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for _, row in res_df.iterrows():
            f.write("| " + " | ".join([f"{x:.4f}" if isinstance(x, float) else str(x) for x in row]) + " |\n")

if __name__ == '__main__':
    main()
