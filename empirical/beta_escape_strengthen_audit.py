import os
import pandas as pd
import numpy as np

def main():
    os.makedirs('outputs/reports', exist_ok=True)
    os.makedirs('outputs/tables', exist_ok=True)
    
    # ---------------------------------------------------------
    # Audit 1: Model Comparison
    # ---------------------------------------------------------
    # The binary model evaluation code had 0 AUC/Accuracy because it failed to correctly binarize classes (e.g. string casing or missing classes).
    # The continuous models (R2) showed Model C (0.13) > Model A (-0.23). However, R2 of 0.13 is extremely low and negative R2 means worse than simply predicting the mean.
    
    mc_df = pd.read_csv('outputs/tables/beta_escape_strengthen_model_comparison.csv')
    
    audit1_table = []
    for _, row in mc_df.iterrows():
        status = "Failed/Leakage" if row['Outcome_Type'] == 'Binary' and row['Metric1_Value'] == 0 else "Valid but weak"
        audit1_table.append({
            'Outcome': row['Outcome'],
            'Model': row['Model'],
            'Metric': row['Metric1_Name'],
            'Value': row['Metric1_Value'],
            'Audit_Status': status,
            'Notes': "Negative R2 for Model A means predicting the mean is better." if 'R2' in row['Metric1_Name'] and float(row['Metric1_Value']) < 0 else ""
        })
    pd.DataFrame(audit1_table).to_csv('outputs/tables/beta_escape_strengthen_audit_model_comparison.csv', index=False)
    
    with open('outputs/reports/beta_escape_strengthen_audit_model_comparison.md', 'w') as f:
        f.write("# Audit 1: Incremental Model Comparison\n\n")
        f.write("1. **What exact outcomes were predicted?** SNR change and clean SMR occupancy change (continuous), SMR acquisition and Beta escape (binary).\n")
        f.write("2. **Which predictors were used in each model?** Model A (mean power), Model B (+ controls), Model C (persistence: dwell, burst frac, escape, reentry, occupancy), Model D (+ controls), Model E (all).\n")
        f.write("3. **Was LOOCV used correctly?** Yes, but continuous predictions yielded negative R2 for Model A, indicating extreme overfitting or poor signal. Binary prediction failed entirely due to label mismatch.\n")
        f.write("4. **Was all scaling/tuning inside training folds?** Yes, StandardScaler was inside the LOOCV loop.\n")
        f.write("5. **Were predictors independent of the outcome definition?** Yes, mostly, though SNR change and power change can be mathematically coupled if bands overlap.\n")
        f.write("6. **Did Model C outperform Model A by a meaningful margin?** Yes, but Model C's R2 was only ~0.13, which is very weak absolute performance.\n")
        f.write("7. **Did Model C outperform Model B?** Model C (0.13) > Model B (-0.14).\n")
        f.write("8. **Are performance gains stable under permutation/bootstrap?** We didn't run permutation tests on the LOOCV predictions, which is a weakness.\n")
        f.write("9. **Are results driven by one subject?** The overall R2 is so low that it's sensitive to outliers.\n")
        f.write("10. **Are p-values/CIs reported?** No permutation probabilities were reported for the R2 values.\n")
        
    # ---------------------------------------------------------
    # Audit 2: Decomposition
    # ---------------------------------------------------------
    dec_df = pd.read_csv('outputs/tables/beta_escape_strengthen_decomposition.csv')
    
    with open('outputs/reports/beta_escape_strengthen_audit_decomposition.md', 'w') as f:
        f.write("# Audit 2: Decomposition Validity\n\n")
        f.write("1. **Is the conclusion that occupancy/dwell drives mean power partly algebraic?** Mean power is mathematically the integral of (amplitude^2 * time). If amplitude is constant, occupancy drives power. \n")
        f.write("2. **Does the decomposition distinguish amplitude within S1 from time spent in S1?** Yes, via `high_beta_power_trimmed95` vs `beta_state_occupancy`.\n")
        f.write("3. **Are dwell time, occupancy, entry rate, escape rate, and re-entry probability independently informative?** The previous analysis showed that `high_beta_power_trimmed95` had the highest marginal R2 (0.47), heavily contradicting the claim that 'suppression is primarily driven by state occupancy'.\n")
        f.write("4. **Does decomposition support mechanism or only measurement non-identifiability?** It primarily demonstrates non-identifiability: mean power conflates amplitude and occupancy, but amplitude remains the dominant empirical driver in this dataset.\n")
        f.write("5. **What wording is justified?** We can only claim that persistence metrics provide separable information, but we *cannot* claim that high-beta suppression is entirely or primarily a change in state dwell time. Amplitude reductions are a major factor.\n")

    # ---------------------------------------------------------
    # Audit 3: Negative Controls
    # ---------------------------------------------------------
    ctrl_df = pd.read_csv('outputs/tables/beta_escape_strengthen_negative_control_bands.csv')
    
    # Calculate stats for the table
    from scipy import stats
    audit3_table = []
    for band in ctrl_df['band'].unique():
        band_data = ctrl_df[ctrl_df['band'] == band]['dwell_time_s_change'].dropna()
        if len(band_data) > 0:
            t, p = stats.ttest_1samp(band_data, 0)
            audit3_table.append({
                'Band': band,
                'Mean_Dwell_Change': band_data.mean(),
                'p_value': p,
                'Significant': p < 0.05
            })
    pd.DataFrame(audit3_table).to_csv('outputs/tables/beta_escape_strengthen_audit_band_specificity.csv', index=False)
    
    with open('outputs/reports/beta_escape_strengthen_audit_negative_controls.md', 'w') as f:
        f.write("# Audit 3: Negative-Control Band Validity\n\n")
        f.write("1. **Are thresholds comparable across bands?** Yes, p75 was used uniformly.\n")
        f.write("2. **Does percentile thresholding artificially equalize occupancy across bands?** Yes, forcing the threshold at the 75th percentile normalizes the baseline occupancy to ~25% for all bands, heavily constraining variance.\n")
        f.write("3. **Is high-beta specificity present?** The mean dwell time change for high beta was 0.0004s (p=0.79). The effect is completely absent at the group level across all bands.\n")
        f.write("4. **Does the 35–45 Hz control rule out broadband/EMG?** Since neither high beta nor the control showed significant group-level persistence changes, we cannot conclusively rule out anything.\n")
        f.write("5. **Does low beta show similar effects?** Low beta also showed non-significant changes (p=0.16).\n")
        f.write("6. **Is the effect truly high-beta-specific, beta-family-specific, or generic?** The effect is statistically non-existent at the group level when parameterized this way, implying extreme individual variability or a generic null result.\n")

    # ---------------------------------------------------------
    # Audit 4: State Validation
    # ---------------------------------------------------------
    val_df = pd.read_csv('outputs/tables/beta_escape_strengthen_state_model_agreement.csv')
    
    audit4_table = val_df[['subject', 'phase', 'dice_coefficient']].copy()
    audit4_table['Agreement_Level'] = audit4_table['dice_coefficient'].apply(lambda x: 'Strong' if x > 0.6 else 'Weak')
    audit4_table.to_csv('outputs/tables/beta_escape_strengthen_audit_state_agreement.csv', index=False)
    
    with open('outputs/reports/beta_escape_strengthen_audit_state_validation.md', 'w') as f:
        f.write("# Audit 4: Threshold-Free State Validation\n\n")
        f.write("1. **What features were used in the GMM?** Log power of SMR, High-Beta, and Broadband envelopes.\n")
        f.write("2. **Was the number of states fixed or selected?** Fixed at 2 components (high beta vs low beta state).\n")
        f.write("3. **Was the high-beta state identified without using the threshold labels?** Yes, by selecting the component with the highest mean log beta power.\n")
        f.write("4. **Is Dice > 0.6 compared against chance?** No. The mean Dice coefficient was ~0.449, which is very weak agreement.\n")
        f.write("5. **Is agreement consistent across subjects and sessions?** It is consistently weak across all subjects.\n")
        f.write("6. **Does the GMM state reproduce dwell/transition findings?** Since the GMM states disagree with the threshold states >50% of the time, they are defining fundamentally different dynamical regimes.\n")

    # ---------------------------------------------------------
    # Audit 5: Robustness
    # ---------------------------------------------------------
    rob_df = pd.read_csv('outputs/tables/beta_escape_strengthen_subject_influence.csv')
    rob_df.to_csv('outputs/tables/beta_escape_strengthen_audit_subject_channel_robustness.csv', index=False)
    
    with open('outputs/reports/beta_escape_strengthen_audit_robustness.md', 'w') as f:
        f.write("# Audit 5: Robustness Validity\n\n")
        f.write("1. **Does leave-one-subject-out preserve direction and model ranking?** The LOO coefficients for Dwell Time vs Power Change ranged heavily (from 9.3 to 18.4).\n")
        f.write("2. **Do bootstrap CIs exclude zero for the key effects?** NO. The bootstrap 95% CI was [-2.075, 28.775], crossing zero.\n")
        f.write("3. **Does Huber/robust regression agree with ordinary regression?** Huber coefficient (9.18) was substantially lower than OLS (13.84), indicating outlier inflation in the OLS estimate.\n")
        f.write("4. **Are E36, E104, and E128 individually consistent?** Channel sensitivity showed broad variance.\n")
        f.write("5. **Are effects stronger only in the combined channel average?** Spatial averaging often artificially smooths independent noise, making the state appear more coherent than it is at the single-sensor level.\n")
        f.write("6. **Are artifact-heavy subjects driving the result?** Given the Huber attenuation and the wide bootstrap CI crossing zero, outliers/artifacts likely inflate the baseline effect.\n")

    # ---------------------------------------------------------
    # Audit 6: Final Claims and Labels
    # ---------------------------------------------------------
    with open('outputs/reports/beta_escape_strengthen_final_audit.md', 'w') as f:
        f.write("# Final Audit Summary\n\n")
        f.write("The previous analyses claimed strong empirical support, but a strict audit reveals severe vulnerabilities:\n")
        f.write("- **Model Comparison**: Binary prediction failed; continuous R2 was exceptionally weak (0.13).\n")
        f.write("- **Decomposition**: Amplitude changes drove mean power more than occupancy, contradicting the 'state-persistence-only' narrative.\n")
        f.write("- **Negative Controls**: No significant group-level persistence changes were found in any band.\n")
        f.write("- **State Validation**: Data-driven GMM states failed to align with predefined thresholds (Dice = 0.449).\n")
        f.write("- **Robustness**: Bootstrap confidence intervals crossed zero, indicating the central predictive effect is not statistically robust.\n")

    with open('outputs/reports/beta_escape_strengthen_final_claims.md', 'w') as f:
        f.write("# Defensible Claims\n\n")
        f.write("- Mean high-beta power conflates amplitude, occupancy, and persistence (measurement non-identifiability).\n")
        f.write("- Beta-state persistence metrics are mathematically separable from mean power.\n")
        f.write("- SMR neurofeedback learning is subject to extreme inter-individual dynamical variability.\n\n")
        f.write("*Excluded claims*: We cannot claim that beta escape (persistence change) is the primary driver of high-beta suppression, nor can we claim it strongly or universally predicts SMR acquisition in this dataset.\n")

    with open('outputs/reports/beta_escape_strengthen_final_submission_label.md', 'w') as f:
        f.write("# Final Submission Label\n\n")
        f.write("**No-go**\n\n")
        f.write("The strengthened results are inflated by overfitting, threshold artifacts (e.g. fixed percentile equalizing baseline occupancy), and failure to survive strict bootstrap and data-driven validation tests. The central strong claim—that beta-state persistence robustly and specifically exposes the mechanism of SMR learning better than mean power—cannot be defended against peer review given these audited results.\n")

if __name__ == '__main__':
    main()
