import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import mne
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
    analyze_state_segments, read_events_for_edf, SENSORIMOTOR_CHANNELS, PRIMARY_CONDITION, STATE_FS, MIN_EPISODE_S
)

BANDS = {
    'theta': (4.0, 8.0),
    'alpha': (8.0, 11.0),
    'SMR': (12.0, 15.0),
    'low_beta': (15.0, 20.0),
    'high_beta': (20.0, 30.0),
    'high_freq': (35.0, 45.0)
}

BROADBAND = (4.0, 45.0)

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
    
    # Process each EDF
    for _, row in df.iterrows():
        subject = row['subject']
        phase = row['phase']
        edf_path = ROOT / row['file_path']
        
        if not edf_path.exists():
            print(f"Skipping {edf_path}, file not found.")
            continue
            
        print(f"Processing {subject} {phase}")
        
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
            x = np.mean(x_data, axis=0) # average over sensorimotor channels
            
            # Broadband envelope (for artifact control)
            broad_env = band_envelope(x, fs, BROADBAND)
            concat_broad = concat_segments(broad_env, segments)
            broad_thr = threshold_values(concat_broad)['p75']
            
            # Amplitude for S2
            amp_abs = np.abs(x)
            concat_amp = concat_segments(amp_abs, segments)
            amp_thr = np.percentile(concat_amp, 99.5)
            
            # SMR env (needed for SMR-compatible occupancy calculation)
            smr_env = band_envelope(x, fs, (12.0, 15.0))
            concat_smr = concat_segments(smr_env, segments)
            smr_thr = threshold_values(concat_smr)['p75']
            
            # Loop over bands
            for band_name, band_range in BANDS.items():
                band_env = band_envelope(x, fs, band_range)
                concat_band = concat_segments(band_env, segments)
                
                band_thresholds = threshold_values(concat_band)
                target_thr = band_thresholds['p75'] # using p75 as primary
                
                step = int(fs / STATE_FS)
                metrics = analyze_state_segments(
                    band_env, smr_env, broad_env, amp_abs, segments, step, target_thr, broad_thr, amp_thr, smr_thr
                )
                
                res = {
                    'subject': subject,
                    'phase': phase,
                    'band': band_name,
                    'mean_power': np.mean(concat_band**2),
                    'occupancy': metrics['s1_occupancy'],
                    'dwell_time_s': metrics['mean_s1_dwell_time_s'],
                    'escape_rate_per_s': metrics['s1_escape_rate_per_s'],
                    'reentry_probability': metrics['s1_reentry_probability'],
                    'n_episodes': metrics['n_beta_episodes'],
                    'long_burst_fraction': 0.0 # Calculate later if needed
                }
                
                durations = np.array(metrics['episode_durations_s'])
                if len(durations) > 0:
                    res['long_burst_fraction'] = np.sum(durations > 0.5) / len(durations)
                
                results.append(res)
                
        except Exception as e:
            print(f"Error processing {edf_path}: {e}")
            
    res_df = pd.DataFrame(results)
    
    # Calculate change scores
    change_records = []
    subjects = res_df['subject'].unique()
    for sub in subjects:
        sub_df = res_df[res_df['subject'] == sub]
        for band in BANDS.keys():
            band_df = sub_df[sub_df['band'] == band]
            if len(band_df) == 2:
                early = band_df[band_df['phase'] == 'early'].iloc[0]
                late = band_df[band_df['phase'] == 'late'].iloc[0]
                change_records.append({
                    'subject': sub,
                    'band': band,
                    'mean_power_change': late['mean_power'] - early['mean_power'],
                    'occupancy_change': late['occupancy'] - early['occupancy'],
                    'dwell_time_s_change': late['dwell_time_s'] - early['dwell_time_s'],
                    'escape_rate_per_s_change': late['escape_rate_per_s'] - early['escape_rate_per_s'],
                    'reentry_probability_change': late['reentry_probability'] - early['reentry_probability'],
                    'long_burst_fraction_change': late['long_burst_fraction'] - early['long_burst_fraction']
                })
                
    change_df = pd.DataFrame(change_records)
    change_df.to_csv('outputs/tables/beta_escape_strengthen_negative_control_bands.csv', index=False)
    
    # Relationship to SMR acquisition
    smr_acq_df = df[['subject', 'smr_acquisition_primary']].drop_duplicates()
    change_df = change_df.merge(smr_acq_df, on='subject')
    
    # Plotting
    sns.set_theme(style="whitegrid")
    
    metrics_to_plot = ['dwell_time_s_change', 'escape_rate_per_s_change', 'reentry_probability_change', 'occupancy_change']
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    axes = axes.flatten()
    
    for i, metric in enumerate(metrics_to_plot):
        sns.boxplot(data=change_df, x='band', y=metric, ax=axes[i], order=list(BANDS.keys()))
        sns.stripplot(data=change_df, x='band', y=metric, ax=axes[i], color='black', alpha=0.5, order=list(BANDS.keys()))
        axes[i].set_title(f'Band Specificity: {metric.replace("_change", " Change")}')
        axes[i].axhline(0, ls='--', color='gray')
        
    plt.tight_layout()
    plt.savefig('outputs/figures/beta_escape_strengthen_band_specificity_panel.png', dpi=300)
    plt.savefig('outputs/figures/beta_escape_strengthen_band_specificity_panel.pdf')
    plt.savefig('outputs/figures/beta_escape_strengthen_band_specificity_panel.svg')
    
    # Write report
    with open('outputs/reports/beta_escape_strengthen_negative_control_bands.md', 'w') as f:
        f.write("# Task 3: Negative-Control Band Analysis\n\n")
        f.write("## Is the persistence/dissociation effect high-beta-specific?\n\n")
        
        f.write("The persistence metrics were re-calculated across multiple bands to test for frequency-specificity.\n\n")
        
        # Calculate t-tests against zero
        from scipy import stats
        stats_results = []
        for band in BANDS.keys():
            band_data = change_df[change_df['band'] == band]
            t_val, p_val = stats.ttest_1samp(band_data['dwell_time_s_change'], 0)
            stats_results.append({
                'Band': band,
                'Mean Dwell Change': band_data['dwell_time_s_change'].mean(),
                'p-value (vs 0)': p_val
            })
            
        stats_df = pd.DataFrame(stats_results)
        
        # Manual markdown formatting
        headers = stats_df.columns.tolist()
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for _, row in stats_df.iterrows():
            f.write("| " + " | ".join([f"{x:.4f}" if isinstance(x, float) else str(x) for x in row]) + " |\n")

        f.write("\n\nInterpretation: The results indicate whether the state dynamics changes are isolated to high beta or represent a broader broadband shift.\n")
        
if __name__ == '__main__':
    main()
