import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import mne
from sklearn.mixture import GaussianMixture
from sklearn.metrics import jaccard_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')
mne.set_log_level('WARNING')

ROOT = Path('C:/work/smr_cn_revision')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from empirical.beta_escape_pipeline import (
    band_envelope, event_segments, concat_segments, threshold_values,
    read_events_for_edf, SENSORIMOTOR_CHANNELS, PRIMARY_CONDITION, STATE_FS, SMR_BAND, HIGH_BETA_BAND, BROADBAND_RANGE
)

def dice_coefficient(y_true, y_pred):
    intersection = np.sum((y_true == 1) & (y_pred == 1))
    return 2.0 * intersection / (np.sum(y_true == 1) + np.sum(y_pred == 1) + 1e-10)

def main():
    os.makedirs('outputs/tables', exist_ok=True)
    os.makedirs('outputs/figures', exist_ok=True)
    os.makedirs('outputs/reports', exist_ok=True)
    
    df = pd.read_csv('outputs/tables/beta_escape_primary_features.csv')
    df = df[(df['dataset_id'] == 'ds004447') & (df['threshold_def'] == 'p75')].copy()
    if len(df) == 0:
        df = pd.read_csv('outputs/tables/beta_escape_primary_features.csv')
        df = df[df['dataset_id'] == 'ds004447'].copy()
        thresh = df['threshold_def'].iloc[0]
        df = df[df['threshold_def'] == thresh].copy()
        
    df = df.drop_duplicates(subset=['subject', 'phase']).copy()
    
    results = []
    state_metrics = []
    
    # Process a subset to keep it lightweight, or all if feasible
    subjects_to_process = df['subject'].unique()
    
    for subject in subjects_to_process:
        for phase in ['early', 'late']:
            sub_df = df[(df['subject'] == subject) & (df['phase'] == phase)]
            if len(sub_df) == 0:
                continue
                
            row = sub_df.iloc[0]
            edf_path = ROOT / row['file_path']
            
            if not edf_path.exists():
                continue
                
            print(f"GMM modeling for {subject} {phase}")
            
            try:
                raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
                channels = [c for c in SENSORIMOTOR_CHANNELS if c in raw.ch_names]
                if not channels:
                    continue
                raw.pick_channels(channels)
                
                raw_duration_s = raw.times[-1]
                fs = raw.info['sfreq']
                events = read_events_for_edf(edf_path, raw_duration_s)
                segments = event_segments(events, PRIMARY_CONDITION, fs, raw.n_times)
                
                if not segments:
                    continue
                    
                x_data = raw.get_data()
                x = np.mean(x_data, axis=0)
                
                smr_env = band_envelope(x, fs, SMR_BAND)
                beta_env = band_envelope(x, fs, HIGH_BETA_BAND)
                broad_env = band_envelope(x, fs, BROADBAND_RANGE)
                
                c_smr = concat_segments(smr_env, segments)
                c_beta = concat_segments(beta_env, segments)
                c_broad = concat_segments(broad_env, segments)
                
                # Subsample to STATE_FS
                step = int(fs / STATE_FS)
                c_smr = c_smr[::step]
                c_beta = c_beta[::step]
                c_broad = c_broad[::step]
                
                # Threshold states
                beta_thr = threshold_values(c_beta)['p75']
                broad_thr = threshold_values(c_broad)['p75']
                amp_thr = np.percentile(np.abs(x), 99.5) # Approximate
                
                # Simpler thresholding for comparison: just high beta > thr
                s1_thr = (c_beta > beta_thr).astype(int)
                
                # Prepare features for GMM
                X_gmm = np.column_stack([
                    np.log10(c_beta + 1e-10),
                    np.log10(c_smr + 1e-10),
                    np.log10(c_broad + 1e-10)
                ])
                
                gmm = GaussianMixture(n_components=2, covariance_type='full', random_state=42)
                preds = gmm.fit_predict(X_gmm)
                
                # Align GMM components: the component with higher mean log beta is the 'high beta' state
                means = gmm.means_[:, 0] # 0 is log beta
                high_beta_comp = np.argmax(means)
                
                s1_gmm = (preds == high_beta_comp).astype(int)
                
                jac = jaccard_score(s1_thr, s1_gmm)
                dice = dice_coefficient(s1_thr, s1_gmm)
                acc = np.mean(s1_thr == s1_gmm)
                
                results.append({
                    'subject': subject,
                    'phase': phase,
                    'jaccard_index': jac,
                    'dice_coefficient': dice,
                    'accuracy': acc
                })
                
                # Compute state metrics on GMM states
                gmm_occupancy = np.mean(s1_gmm)
                # Dwell time
                changes = np.diff(np.concatenate(([0], s1_gmm, [0])))
                starts = np.where(changes == 1)[0]
                ends = np.where(changes == -1)[0]
                durations = (ends - starts) / STATE_FS
                
                mean_dwell = np.mean(durations) if len(durations) > 0 else 0
                long_burst = np.sum(durations > 0.5) / len(durations) if len(durations) > 0 else 0
                
                state_metrics.append({
                    'subject': subject,
                    'phase': phase,
                    'gmm_occupancy': gmm_occupancy,
                    'gmm_mean_dwell_s': mean_dwell,
                    'gmm_long_burst_fraction': long_burst,
                    'thr_occupancy': np.mean(s1_thr)
                })
                
            except Exception as e:
                print(f"Error {subject} {phase}: {e}")
                
    res_df = pd.DataFrame(results)
    res_df.to_csv('outputs/tables/beta_escape_strengthen_state_model_agreement.csv', index=False)
    
    metrics_df = pd.DataFrame(state_metrics)
    metrics_df.to_csv('outputs/tables/beta_escape_strengthen_data_driven_state_metrics.csv', index=False)
    
    # Plotting
    sns.set_theme(style="whitegrid")
    
    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    sns.boxplot(data=res_df, y='dice_coefficient')
    sns.stripplot(data=res_df, y='dice_coefficient', color='black', alpha=0.5)
    plt.title('GMM vs Threshold Dice Coefficient')
    plt.ylabel('Dice Coefficient')
    
    plt.subplot(1, 2, 2)
    sns.scatterplot(data=metrics_df, x='thr_occupancy', y='gmm_occupancy')
    plt.plot([0, 1], [0, 1], ls='--', color='gray')
    plt.title('Threshold vs GMM Occupancy')
    plt.xlabel('Threshold Occupancy')
    plt.ylabel('GMM Occupancy')
    
    plt.tight_layout()
    plt.savefig('outputs/figures/beta_escape_strengthen_state_model_agreement.png', dpi=300)
    plt.savefig('outputs/figures/beta_escape_strengthen_state_model_agreement.pdf')
    plt.savefig('outputs/figures/beta_escape_strengthen_state_model_agreement.svg')
    
    # Report
    with open('outputs/reports/beta_escape_strengthen_threshold_free_state_validation.md', 'w') as f:
        f.write("# Task 4: Threshold-Free State Validation\n\n")
        f.write("## Does a data-driven state model support the threshold-defined S1 state?\n\n")
        
        mean_dice = res_df['dice_coefficient'].mean()
        f.write(f"The mean Dice coefficient between the threshold-defined S1 state and the data-driven GMM state is **{mean_dice:.3f}**.\n\n")
        
        if mean_dice > 0.6:
            f.write("Yes. The data-driven state model shows strong agreement with the predeclared threshold-defined S1 state, indicating that the threshold captures a robust underlying state dynamic.\n\n")
        else:
            f.write("Weak agreement. The data-driven model isolates states differently than the predefined threshold.\n\n")
            
        # Manual markdown formatting
        headers = res_df.columns.tolist()
        f.write("### Model Agreement Results\n\n")
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for _, row in res_df.head(10).iterrows(): # Show top 10 rows
            f.write("| " + " | ".join([f"{x:.4f}" if isinstance(x, float) else str(x) for x in row]) + " |\n")

if __name__ == '__main__':
    main()
