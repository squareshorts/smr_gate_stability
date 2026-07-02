import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import mne
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

mne.set_log_level('WARNING')

ROOT = Path('C:/work/smr_cn_revision')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from empirical.beta_escape_pipeline import (
    SENSORIMOTOR_CHANNELS, SMR_BAND, HIGH_BETA_BAND, BROADBAND_RANGE, NOISE_FLOOR_BAND,
    welch_psd
)

def main():
    os.makedirs('outputs/figures', exist_ok=True)
    
    # Load labeled windows
    df = pd.read_csv('outputs/tables/nf_sqi_task_labeled_windows.csv')
    df_1s = df[df['window_size'] == 1.0].copy()
    
    cands = df_1s[df_1s['gate_A'] == True]
    clean_cands = cands[cands['is_contaminated'] == False]
    contam_cands = cands[cands['is_contaminated'] == True]
    
    # Pick one of each
    # For a good visualization, let's pick a contaminated one with high beta and broadband issues.
    # Just sort by some power to get a clear example.
    contam_cands = contam_cands.sort_values('high_beta_power', ascending=False)
    
    if len(clean_cands) == 0 or len(contam_cands) == 0:
        print("Not enough examples to plot.")
        return
        
    ex_clean = clean_cands.iloc[10] # just an arbitrary index to avoid edges
    ex_contam = contam_cands.iloc[10]
    
    dataset_dir = ROOT / "data" / "raw" / "openneuro" / "ds004447"
    
    examples = [
        ('Clean SMR-Candidate Window', ex_clean),
        ('Contaminated SMR-Candidate Window', ex_contam)
    ]
    
    plt.rcParams.update({'font.size': 14})
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    
    for i, (title, row) in enumerate(examples):
        sub = row['subject']
        ses = row['session']
        t_start = row['time_s']
        
        # Find EDF
        edf_matches = list(dataset_dir.rglob(f"{sub}/{ses}/eeg/*.edf"))
        if not edf_matches:
            print(f"EDF not found for {sub} {ses}")
            continue
            
        edf_path = edf_matches[0]
        raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
        channels = [c for c in SENSORIMOTOR_CHANNELS if c in raw.ch_names]
        raw.pick_channels(channels)
        
        fs = raw.info['sfreq']
        start_samp = int(t_start * fs)
        stop_samp = int((t_start + 1.0) * fs)
        
        data = raw.get_data()[:, start_samp:stop_samp]
        times = np.arange(data.shape[1]) / fs
        
        # Plot Time Domain (Average across channels)
        ax_time = axes[i, 0]
        mean_data = np.mean(data, axis=0) * 1e6 # Convert to uV
        ax_time.plot(times, mean_data, color='k')
        ax_time.set_ylabel('Amplitude (uV)')
        ax_time.set_xlabel('Time (s)')
        # Add a text box instead of title to respect formatting rules
        ax_time.text(0.05, 0.95, title + ' (Time)', transform=ax_time.transAxes, 
                     fontsize=14, fontweight='bold', va='top', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
        ax_time.spines['top'].set_visible(False)
        ax_time.spines['right'].set_visible(False)
        
        # Plot PSD
        ax_psd = axes[i, 1]
        freqs, psd = welch_psd(np.mean(data, axis=0), fs)
        # Convert PSD to log scale for plotting
        ax_psd.plot(freqs, np.log10(psd), color='k')
        
        # Shading
        ax_psd.axvspan(SMR_BAND[0], SMR_BAND[1], color='mediumseagreen', alpha=0.3, label='SMR (12-15 Hz)')
        ax_psd.axvspan(HIGH_BETA_BAND[0], HIGH_BETA_BAND[1], color='indianred', alpha=0.3, label='High beta (20-30 Hz)')
        ax_psd.axvspan(NOISE_FLOOR_BAND[0], NOISE_FLOOR_BAND[1], color='gray', alpha=0.3, label='Noise floor (35-45 Hz)')
        
        ax_psd.set_xlim(0, 50)
        ax_psd.set_ylabel('Log PSD')
        ax_psd.set_xlabel('Frequency (Hz)')
        ax_psd.text(0.05, 0.95, title + ' (Spectrum)', transform=ax_psd.transAxes, 
                     fontsize=14, fontweight='bold', va='top', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
        
        if i == 0:
            ax_psd.legend(loc='upper right', fontsize=10, frameon=False)
            
        ax_psd.spines['top'].set_visible(False)
        ax_psd.spines['right'].set_visible(False)
        
    plt.tight_layout()
    plt.savefig('outputs/figures/nf_sqi_example_windows_psd.pdf', bbox_inches='tight')
    plt.savefig('outputs/figures/nf_sqi_example_windows_psd.png', dpi=300, bbox_inches='tight')

if __name__ == '__main__':
    main()
