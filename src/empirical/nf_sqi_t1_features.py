import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import mne
import warnings
from scipy import signal
from scipy.stats import median_abs_deviation

warnings.filterwarnings('ignore')
mne.set_log_level('WARNING')

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from empirical.nf_sqi_common import (
    SENSORIMOTOR_CHANNELS, SMR_BAND, HIGH_BETA_BAND, BROADBAND_RANGE, NOISE_FLOOR_BAND,
    read_events_for_edf, welch_psd, bandpower_from_psd
)

WINDOW_CONFIGS = [
    {'len_s': 1.0, 'step_s': 0.5},
    {'len_s': 0.5, 'step_s': 0.25},
    {'len_s': 2.0, 'step_s': 1.0}
]

def extract_window_features(x_channels, fs):
    """
    x_channels: array of shape (n_channels, n_samples)
    fs: sampling frequency
    """
    n_channels = x_channels.shape[0]

    # Transient score: max absolute amplitude across all samples and channels in the window
    transient_score = np.max(np.abs(x_channels))

    # Average across channels for spectral features
    x = np.mean(x_channels, axis=0)

    # Spectral metrics (average channel)
    freqs, psd = welch_psd(x, fs)
    if len(freqs) == 0:
        return {'valid': False}

    smr_power = bandpower_from_psd(freqs, psd, SMR_BAND)
    beta_power = bandpower_from_psd(freqs, psd, HIGH_BETA_BAND)
    noise_power = bandpower_from_psd(freqs, psd, NOISE_FLOOR_BAND)

    broadband_mask = (freqs >= BROADBAND_RANGE[0]) & (freqs <= BROADBAND_RANGE[1]) & \
                     ~((freqs >= SMR_BAND[0]) & (freqs <= SMR_BAND[1])) & \
                     ~((freqs >= HIGH_BETA_BAND[0]) & (freqs <= HIGH_BETA_BAND[1]))
    broadband_power = float(np.trapz(psd[broadband_mask], freqs[broadband_mask])) if broadband_mask.sum() >= 2 else np.nan

    smr_snr = smr_power / (broadband_power + 1e-9)

    slope_mask = broadband_mask & (psd > 0) & (freqs > 0)
    slope = np.nan
    if slope_mask.sum() >= 5:
        xx = np.log10(freqs[slope_mask])
        yy = np.log10(psd[slope_mask])
        slope, _ = np.polyfit(xx, yy, deg=1)

    # Channel-specific powers for channel inconsistency calculation later
    ch_feats = {}
    for i in range(n_channels):
        f_i, p_i = welch_psd(x_channels[i, :], fs)
        ch_feats[f'ch_{i}_smr'] = bandpower_from_psd(f_i, p_i, SMR_BAND)
        ch_feats[f'ch_{i}_beta'] = bandpower_from_psd(f_i, p_i, HIGH_BETA_BAND)
        ch_feats[f'ch_{i}_broadband'] = bandpower_from_psd(f_i, p_i, BROADBAND_RANGE) # Using full broadband for this
        ch_feats[f'ch_{i}_noise'] = bandpower_from_psd(f_i, p_i, NOISE_FLOOR_BAND)

    res = {
        'valid': True,
        'smr_power': smr_power,
        'smr_snr': smr_snr,
        'high_beta_power': beta_power,
        'noise_floor_power': noise_power,
        'broadband_power': broadband_power,
        'spectral_slope': slope,
        'transient_score': transient_score,
    }
    res.update(ch_feats)
    return res

def main():
    os.makedirs('outputs/tables', exist_ok=True)
    os.makedirs('outputs/reports', exist_ok=True)

    dataset_dir = ROOT / "data" / "raw" / "openneuro" / "ds004447"
    edf_files = list(dataset_dir.rglob("sub-*/ses-*/eeg/*.edf"))

    all_features = []
    subject_sessions = []

    total_windows = 0
    missing_data_files = 0

    for edf_path in edf_files:
        subject = edf_path.parts[-4]
        session = edf_path.parts[-3]

        print(f"Processing {subject} {session}...")

        try:
            raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
            channels = [c for c in SENSORIMOTOR_CHANNELS if c in raw.ch_names]
            if not channels:
                missing_data_files += 1
                continue

            raw.pick_channels(channels)
            fs = raw.info['sfreq']

            raw_duration_s = raw.times[-1]
            events = read_events_for_edf(edf_path, raw_duration_s)

            # Map samples to condition
            event_arr = np.zeros(raw.n_times, dtype=int)
            for _, row in events[events["instruction"].astype(str) == "task"].iterrows():
                start = int(round(float(row["onset_s"]) * fs))
                stop = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
                start = max(0, min(start, raw.n_times))
                stop = max(start, min(stop, raw.n_times))
                event_arr[start:stop] = 1

            data = raw.get_data() # (n_channels, n_samples)
            n_samples = data.shape[1]

            for config in WINDOW_CONFIGS:
                win_len_s = config['len_s']
                win_step_s = config['step_s']

                win_len_samples = int(win_len_s * fs)
                win_step_samples = int(win_step_s * fs)

                starts = np.arange(0, n_samples - win_len_samples, win_step_samples)

                prev_smr = np.nan
                session_windows = []

                for start in starts:
                    stop = start + win_len_samples
                    win_data = data[:, start:stop]
                    condition_val = np.mean(event_arr[start:stop])
                    condition = 'task' if condition_val > 0.5 else 'rest'

                    feats = extract_window_features(win_data, fs)
                    if not feats['valid']:
                        continue

                    del feats['valid']

                    nonstationarity = np.abs(feats['smr_power'] - prev_smr) if not np.isnan(prev_smr) else 0.0
                    prev_smr = feats['smr_power']

                    feats['subject'] = subject
                    feats['session'] = session
                    feats['time_s'] = start / fs
                    feats['condition'] = condition
                    feats['nonstationarity'] = nonstationarity
                    feats['window_size'] = win_len_s

                    session_windows.append(feats)

                # Compute channel inconsistency for this session and window size
                if len(session_windows) > 0:
                    sw_df = pd.DataFrame(session_windows)
                    rest_mask = sw_df['condition'] == 'rest'

                    bands = ['smr', 'beta', 'broadband', 'noise']
                    for band in bands:
                        cols = [f'ch_{i}_{band}' for i in range(len(channels))]

                        # Calculate rest stats for standardization
                        means = sw_df.loc[rest_mask, cols].mean()
                        stds = sw_df.loc[rest_mask, cols].std()
                        stds[stds == 0] = 1e-9

                        # Standardize all windows
                        std_vals = (sw_df[cols] - means) / stds

                        # SD and MAD across channels
                        sw_df[f'ch_inc_{band}_sd'] = std_vals.std(axis=1)
                        sw_df[f'ch_inc_{band}_mad'] = std_vals.apply(lambda row: median_abs_deviation(row.dropna()), axis=1)

                    # Primary channel inconsistency score (Mean of SDs)
                    sw_df['channel_inconsistency'] = sw_df[[f'ch_inc_{b}_sd' for b in bands]].mean(axis=1)
                    sw_df['channel_inconsistency_mad'] = sw_df[[f'ch_inc_{b}_mad' for b in bands]].mean(axis=1)

                    # Drop raw channel columns to save space
                    cols_to_drop = [c for c in sw_df.columns if c.startswith('ch_') and not c.startswith('ch_inc')]
                    sw_df = sw_df.drop(columns=cols_to_drop)

                    all_features.append(sw_df)

                    n_win = len(sw_df)
                    n_task = rest_mask.sum()
                    n_rest = n_win - n_task
                    total_windows += n_win

                    subject_sessions.append({
                        'subject': subject,
                        'session': session,
                        'window_size': win_len_s,
                        'total_windows': n_win,
                        'task_windows': n_task,
                        'rest_windows': n_rest
                    })

        except Exception as e:
            print(f"Error on {subject} {session}: {e}")
            missing_data_files += 1

    df_feats = pd.concat(all_features, ignore_index=True)
    df_feats.to_csv('outputs/tables/nf_sqi_window_features.csv', index=False)

    df_summ = pd.DataFrame(subject_sessions)
    df_summ.to_csv('outputs/tables/nf_sqi_subject_session_summary.csv', index=False)

    with open('outputs/reports/nf_sqi_feature_extraction.md', 'w') as f:
        f.write("# Task 1: NF-SQI Feature Extraction\n\n")
        f.write(f"- **Subjects processed:** {df_summ['subject'].nunique()}\n")
        f.write(f"- **Sessions processed:** {df_summ['session'].nunique()}\n")
        f.write(f"- **Total windows:** {total_windows}\n")
        f.write(f"- **Channels used:** {SENSORIMOTOR_CHANNELS}\n")
        f.write(f"- **Missing data files:** {missing_data_files}\n\n")
        f.write("## Extracted Features\n")
        f.write("1. `smr_power`: Welch PSD (12-15 Hz) averaged across channels.\n")
        f.write("2. `smr_snr`: `smr_power` / `broadband_power`.\n")
        f.write("3. `high_beta_power`: Welch PSD (20-30 Hz).\n")
        f.write("4. `noise_floor_power`: Welch PSD (35-45 Hz).\n")
        f.write("5. `broadband_power`: Welch PSD (4-45 Hz, excluding SMR and high beta).\n")
        f.write("6. `spectral_slope`: Linear fit of log(PSD) vs log(freq) in the broadband range.\n")
        f.write("7. `transient_score`: Maximum absolute amplitude across channels in the window.\n")
        f.write("8. `channel_inconsistency`: Mean across-channel standard deviation of standardized power for SMR, High Beta, Broadband, and Noise Floor.\n")
        f.write("9. `channel_inconsistency_mad`: Robust median absolute deviation version.\n")
        f.write("10. `nonstationarity`: Absolute difference in `smr_power` from the previous window.\n")

if __name__ == '__main__':
    main()
