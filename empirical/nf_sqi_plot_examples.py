import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import mne
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

mne.set_log_level('WARNING')

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from empirical.nf_sqi_common import (
    SENSORIMOTOR_CHANNELS, SMR_BAND, HIGH_BETA_BAND, BROADBAND_RANGE, NOISE_FLOOR_BAND,
    welch_psd
)

def main():
    os.makedirs('outputs/figures', exist_ok=True)

    # Load labeled windows
    df = pd.read_csv('outputs/tables/nf_sqi_task_labeled_windows.csv')
    df_1s = df[df['window_size'] == 1.0].copy()

    # Load all window features to get rest data for thresholds
    full_df = pd.read_csv('outputs/tables/nf_sqi_window_features.csv')
    full_df_1s = full_df[full_df['window_size'] == 1.0].copy()

    cands = df_1s[df_1s['gate_A'] == True]
    clean_cands = cands[cands['is_contaminated'] == False]
    contam_cands = cands[cands['is_contaminated'] == True]

    # We want a contaminated candidate with visible spectral contamination.
    # To do this robustly, we compute thresholds for all subjects and pick one with high noise-floor or high-beta contamination.

    # Let's find one with high noise floor power
    contam_cands = contam_cands.sort_values('noise_floor_power', ascending=False)

    if len(clean_cands) == 0 or len(contam_cands) == 0:
        print("Not enough examples to plot.")
        return

    # Pick a clean candidate with good SMR power
    clean_cands = clean_cands.sort_values('smr_power', ascending=False)
    ex_clean = clean_cands.iloc[10] # arbitrary but solid SMR

    # Pick a contaminated one that is highly contaminated in noise floor
    ex_contam = contam_cands.iloc[5] # Top 5 to avoid potential extreme outliers/artifacts

    dataset_dir = ROOT / "data" / "raw" / "openneuro" / "ds004447"

    # Calculate exact contamination flags for the validation message
    def get_flags(row):
        sub = row['subject']
        ses = row['session']
        sub_rest = full_df_1s[(full_df_1s['subject'] == sub) & (full_df_1s['session'] == ses) & (full_df_1s['condition'] == 'rest')]

        hb_thr = np.percentile(sub_rest['high_beta_power'].dropna(), 75)
        bb_thr = np.percentile(sub_rest['broadband_power'].dropna(), 75)
        nf_thr = np.percentile(sub_rest['noise_floor_power'].dropna(), 75)
        tr_thr = np.percentile(sub_rest['transient_score'].dropna(), 90)

        flags = []
        if row['high_beta_power'] > hb_thr: flags.append('high-beta')
        if row['broadband_power'] > bb_thr: flags.append('broadband')
        if row['noise_floor_power'] > nf_thr: flags.append('noise-floor')
        if row['transient_score'] > tr_thr: flags.append('transient')

        if not flags:
            return "None (Clean)"
        elif len(flags) > 1:
            return f"multi-contaminated ({', '.join(flags)})"
        else:
            return f"{flags[0]} only"

    clean_flags = get_flags(ex_clean)
    contam_flags = get_flags(ex_contam)

    examples = [
        ('Clean candidate', ex_clean),
        ('Contaminated candidate', ex_contam)
    ]

    plt.rcParams.update({'font.size': 14, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))

    # Store extracted data for common axis scaling
    all_time_data = []
    all_psd_data = []

    # First pass: load data
    for i, (label_txt, row) in enumerate(examples):
        sub = row['subject']
        ses = row['session']
        t_start = row['time_s']

        # Output validation message
        if i == 0:
            print(f"Example 1 ({label_txt}):")
            print(f"  Subject: {sub}, Session: {ses}, Window: {t_start:.1f}s")
            print(f"  Contamination flags: {clean_flags}")
        else:
            print(f"Example 2 ({label_txt}):")
            print(f"  Subject: {sub}, Session: {ses}, Window: {t_start:.1f}s")
            print(f"  Contamination flags: {contam_flags}")

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

        mean_data = np.mean(data, axis=0) * 1e6 # Convert to uV
        freqs, psd = welch_psd(np.mean(data, axis=0), fs)
        log_psd = np.log10(psd)

        all_time_data.append((times, mean_data))
        all_psd_data.append((freqs, log_psd))

    if len(all_time_data) < 2:
        return

    # Get common limits
    y_min_time = min([np.min(d[1]) for d in all_time_data])
    y_max_time = max([np.max(d[1]) for d in all_time_data])
    y_min_psd = min([np.min(d[1][d[0] <= 50]) for d in all_psd_data])
    y_max_psd = max([np.max(d[1][d[0] <= 50]) for d in all_psd_data])

    panel_labels = [['A', 'B'], ['C', 'D']]

    for i in range(2):
        label_txt = examples[i][0]
        times, mean_data = all_time_data[i]
        freqs, log_psd = all_psd_data[i]

        # Plot Time Domain
        ax_time = axes[i, 0]
        ax_time.plot(times, mean_data, color='k', linewidth=1.5)
        ax_time.set_ylabel('Amplitude (µV)')
        ax_time.set_xlim(0, 1)
        ax_time.set_ylim(y_min_time - 5, y_max_time + 5)
        if i == 1:
            ax_time.set_xlabel('Time (s)')
        else:
            ax_time.set_xticklabels([])

        ax_time.text(-0.15, 1.05, panel_labels[i][0], transform=ax_time.transAxes,
                     fontsize=18, fontweight='bold', va='top')

        ax_time.text(0.02, 0.95, label_txt, transform=ax_time.transAxes,
                     fontsize=14, va='top', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

        # Plot PSD
        ax_psd = axes[i, 1]
        ax_psd.plot(freqs, log_psd, color='k', linewidth=1.5)

        # Shading
        ax_psd.axvspan(SMR_BAND[0], SMR_BAND[1], color='mediumseagreen', alpha=0.25, label='SMR (12-15 Hz)' if i==0 else "")
        ax_psd.axvspan(HIGH_BETA_BAND[0], HIGH_BETA_BAND[1], color='indianred', alpha=0.25, label='High beta (20-30 Hz)' if i==0 else "")
        ax_psd.axvspan(NOISE_FLOOR_BAND[0], NOISE_FLOOR_BAND[1], color='gray', alpha=0.25, label='Noise floor (35-45 Hz)' if i==0 else "")

        ax_psd.set_xlim(0, 50)
        ax_psd.set_ylim(y_min_psd - 0.5, y_max_psd + 0.5)
        ax_psd.set_ylabel('Log PSD')

        if i == 1:
            ax_psd.set_xlabel('Frequency (Hz)')
        else:
            ax_psd.set_xticklabels([])

        ax_psd.text(-0.15, 1.05, panel_labels[i][1], transform=ax_psd.transAxes,
                     fontsize=18, fontweight='bold', va='top')

        if i == 0:
            fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=3, frameon=False, fontsize=11)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    plt.savefig('outputs/figures/nf_sqi_example_windows_psd.pdf', bbox_inches='tight')
    plt.savefig('outputs/figures/nf_sqi_example_windows_psd.png', dpi=300, bbox_inches='tight')

if __name__ == '__main__':
    main()
