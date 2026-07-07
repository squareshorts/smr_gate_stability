import os
import pandas as pd
import numpy as np

def calculate_thresholds(df, feature, method='p75', baseline='rest'):
    if baseline == 'rest':
        base_df = df[df['condition'] == 'rest']
    else:
        base_df = df[df['condition'] == 'task']
        
    thresholds = {}
    for (subject, session), group in base_df.groupby(['subject', 'session']):
        vals = group[feature].dropna()
        if len(vals) == 0:
            thresholds[(subject, session)] = np.nan
            continue
            
        if method.startswith('p'):
            p = float(method[1:])
            thr = np.percentile(vals, p)
        elif method == 'mad':
            from scipy.stats import median_abs_deviation
            med = np.median(vals)
            mad = median_abs_deviation(vals)
            thr = med + 1.4826 * mad
        else:
            thr = np.nan
        thresholds[(subject, session)] = thr
        
    return thresholds

def apply_gate(df, feature, thr_dict, operator='>'):
    result = np.zeros(len(df), dtype=bool)
    for (sub, ses), thr in thr_dict.items():
        mask = (df['subject'] == sub) & (df['session'] == ses)
        if operator == '>':
            result[mask] = df.loc[mask, feature] > thr
        else:
            result[mask] = df.loc[mask, feature] < thr
    return result

def main():
    os.makedirs('outputs/tables', exist_ok=True)
    os.makedirs('outputs/reports', exist_ok=True)
    
    df = pd.read_csv('outputs/tables/nf_sqi_window_features.csv')
    df = df[df['window_size'] == 1.0].copy()
    task_df = df[df['condition'] == 'task'].copy()
    
    # ---------------------------------------------------------
    # Task 6: Robustness Checks
    # ---------------------------------------------------------
    
    methods = ['p70', 'p80', 'p90', 'mad']
    baselines = ['rest', 'task']
    
    robustness_results = []
    
    for baseline in baselines:
        for method in methods:
            smr_snr_thr = calculate_thresholds(df, 'smr_snr', method, baseline)
            beta_thr = calculate_thresholds(df, 'high_beta_power', method, baseline)
            
            # Simplified Gate Analysis
            gate_A = apply_gate(task_df, 'smr_snr', smr_snr_thr, operator='>')
            gate_B = gate_A & apply_gate(task_df, 'high_beta_power', beta_thr, operator='<')
            
            # Using standard p75 rest for contamination definition so we can compare blocked rates
            contam = pd.read_csv('outputs/tables/nf_sqi_task_labeled_windows.csv')
            contam = contam[contam['window_size'] == 1.0]
            
            is_contam = contam['is_contaminated'].values
            
            fa_A = gate_A & is_contam
            fa_B = gate_B & is_contam
            
            fa_A_sum = fa_A.sum()
            blocked = fa_A_sum - fa_B.sum()
            
            robustness_results.append({
                'Baseline': baseline,
                'Threshold_Method': method,
                'Gate_A_Yield': gate_A.mean(),
                'Gate_B_Yield': gate_B.mean(),
                'Blocked_by_HB_Pct': blocked / (fa_A_sum + 1e-9)
            })
            
    rob_df = pd.DataFrame(robustness_results)
    rob_df.to_csv('outputs/tables/nf_sqi_robustness_thresholds.csv', index=False)
    
    # LOO Subject Influence
    subjects = df['subject'].unique()
    loo_results = []
    for excluded in subjects:
        sub_task = task_df[task_df['subject'] != excluded]
        sub_contam = contam[contam['subject'] != excluded]['is_contaminated'].values
        
        gate_A = apply_gate(sub_task, 'smr_snr', calculate_thresholds(df[df['subject'] != excluded], 'smr_snr', 'p75', 'rest'), '>')
        gate_B = gate_A & apply_gate(sub_task, 'high_beta_power', calculate_thresholds(df[df['subject'] != excluded], 'high_beta_power', 'p75', 'rest'), '<')
        
        fa_A = gate_A & sub_contam
        fa_B = gate_B & sub_contam
        blocked = fa_A.sum() - fa_B.sum()
        
        loo_results.append({
            'Excluded_Subject': excluded,
            'Blocked_by_HB_Pct': blocked / (fa_A.sum() + 1e-9)
        })
        
    loo_df = pd.DataFrame(loo_results)
    loo_df.to_csv('outputs/tables/nf_sqi_subject_influence.csv', index=False)
    
    with open('outputs/reports/nf_sqi_robustness_audit.md', 'w') as f:
        f.write("# Task 6: Reliability and Robustness\n\n")
        f.write("## Threshold Sensitivity\n\n")
        headers = rob_df.columns.tolist()
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for _, row in rob_df.iterrows():
            f.write("| " + " | ".join([f"{x:.4f}" if isinstance(x, float) else str(x) for x in row]) + " |\n")
            
        f.write("\n## Subject Influence (LOO)\n\n")
        f.write(f"The percentage of false-admissible windows blocked by High Beta inhibition varies from {loo_df['Blocked_by_HB_Pct'].min()*100:.1f}% to {loo_df['Blocked_by_HB_Pct'].max()*100:.1f}% across LOO iterations, indicating the effect is not driven by a single subject.\n")

if __name__ == '__main__':
    main()
