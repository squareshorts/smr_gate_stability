import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import mne
import warnings
from scipy.stats import median_abs_deviation

warnings.filterwarnings('ignore')
mne.set_log_level('WARNING')

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

from empirical.nf_sqi_common import (
    SENSORIMOTOR_CHANNELS, SMR_BAND, HIGH_BETA_BAND, BROADBAND_RANGE, NOISE_FLOOR_BAND,
    read_events_for_edf, welch_psd, bandpower_from_psd
)

EXPANDED_ROI = ['C3', 'C4', 'Cz', 'FC1', 'FC2', 'CP1', 'CP2', 'FC3', 'FC4', 'CP3', 'CP4']
DATASETS = ['ds004447', 'ds004444', 'ds004446']

def extract_window_features(x_channels, fs, channels):
    n_channels = x_channels.shape[0]
    transient_score = np.max(np.abs(x_channels))
    # Artifact baseline: MNE peak-to-peak amplitude > 150uV is a standard threshold
    ptp_amp = np.max(np.ptp(x_channels, axis=1))

    x = np.mean(x_channels, axis=0)
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

    ch_feats = {}
    for i, ch in enumerate(channels):
        cf, cpsd = welch_psd(x_channels[i], fs)
        ch_feats[f'ch_{ch}_smr'] = bandpower_from_psd(cf, cpsd, SMR_BAND)
        ch_feats[f'ch_{ch}_beta'] = bandpower_from_psd(cf, cpsd, HIGH_BETA_BAND)
        ch_feats[f'ch_{ch}_broadband'] = float(np.trapz(cpsd[broadband_mask], cf[broadband_mask])) if broadband_mask.sum() >= 2 else np.nan
        ch_feats[f'ch_{ch}_noise'] = bandpower_from_psd(cf, cpsd, NOISE_FLOOR_BAND)

    res = {
        'valid': True,
        'smr_power': smr_power,
        'high_beta_power': beta_power,
        'noise_floor_power': noise_power,
        'broadband_power': broadband_power,
        'smr_snr': smr_power / (broadband_power + 1e-9),
        'transient_score': transient_score,
        'ptp_amp': ptp_amp,
    }
    res.update(ch_feats)
    return res

def compute_ch_inc(sw_df, channels, suffix=''):
    rest_mask = sw_df['condition'] == 'rest'
    bands = ['smr', 'beta', 'broadband', 'noise']
    for band in bands:
        cols = [f'ch_{ch}_{band}' for ch in channels]
        means = sw_df.loc[rest_mask, cols].mean()
        stds = sw_df.loc[rest_mask, cols].std()
        stds[stds == 0] = 1e-9
        std_vals = (sw_df[cols] - means) / stds
        sw_df[f'ch_inc_{band}_sd'] = std_vals.std(axis=1)

    return sw_df[[f'ch_inc_{b}_sd' for b in bands]].mean(axis=1)

def process_dataset(ds):
    dataset_dir = ROOT / "archive/stale_pending_delete/data/data/raw/openneuro" / ds
    edf_files = list(dataset_dir.rglob("sub-*/ses-*/eeg/*.edf"))
    
    all_features = []
    
    for edf_path in edf_files:
        subject = edf_path.parts[-4]
        session = edf_path.parts[-3]
        
        try:
            raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
            
            # Identify standard central and expanded channels
            std_channels = [c for c in SENSORIMOTOR_CHANNELS if c in raw.ch_names]
            exp_channels = [c for c in EXPANDED_ROI if c in raw.ch_names]
            use_exp = len(exp_channels) >= 5 # only do expanded if we have enough
            
            all_chans = list(set(std_channels + (exp_channels if use_exp else [])))
            if not std_channels: continue
            
            raw.pick_channels(all_chans)
            fs = raw.info['sfreq']
            
            events = read_events_for_edf(edf_path, raw.times[-1])
            event_arr = np.zeros(raw.n_times, dtype=int)
            for _, row in events[events["instruction"].astype(str) == "task"].iterrows():
                start = int(round(float(row["onset_s"]) * fs))
                stop = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
                start = max(0, min(start, raw.n_times))
                stop = max(start, min(stop, raw.n_times))
                event_arr[start:stop] = 1

            data = raw.get_data()
            n_samples = data.shape[1]
            
            win_len_samples = int(1.0 * fs)
            win_step_samples = int(0.5 * fs)
            starts = np.arange(0, n_samples - win_len_samples, win_step_samples)
            
            session_windows = []
            
            # Map channel indices
            std_idx = [raw.ch_names.index(c) for c in std_channels]
            exp_idx = [raw.ch_names.index(c) for c in exp_channels] if use_exp else []
            
            for start in starts:
                stop = start + win_len_samples
                condition = 'task' if np.mean(event_arr[start:stop]) > 0.5 else 'rest'
                
                # Standard features
                feats_std = extract_window_features(data[std_idx, start:stop], fs, std_channels)
                if not feats_std['valid']: continue
                
                # Expanded features
                if use_exp:
                    feats_exp = extract_window_features(data[exp_idx, start:stop], fs, exp_channels)
                    for k, v in feats_exp.items():
                        if k.startswith('ch_'): feats_std[k] = v
                
                feats_std['subject'] = subject
                feats_std['session'] = session
                feats_std['condition'] = condition
                feats_std['has_exp'] = use_exp
                session_windows.append(feats_std)
                
            if len(session_windows) > 0:
                sw_df = pd.DataFrame(session_windows)
                sw_df['channel_inconsistency'] = compute_ch_inc(sw_df, std_channels)
                if use_exp:
                    sw_df['channel_inconsistency_exp'] = compute_ch_inc(sw_df, exp_channels)
                else:
                    sw_df['channel_inconsistency_exp'] = np.nan
                    
                cols_to_drop = [c for c in sw_df.columns if c.startswith('ch_') and not c.startswith('ch_inc')]
                sw_df = sw_df.drop(columns=cols_to_drop)
                all_features.append(sw_df)
                
        except Exception as e:
            pass
            
    if all_features:
        return pd.concat(all_features, ignore_index=True)
    return None

def analyze_tradeoff_and_baseline(df, ds):
    # Recompute thresholds from rest
    task_df = df[df['condition'] == 'task'].copy()
    rest_df = df[df['condition'] == 'rest'].copy()
    
    percs = [50, 60, 70, 75, 80, 85, 90, 95]
    res_tradeoff = []
    
    # Artifact Baseline (MNE ptp > 150uV)
    task_df['baseline_flag'] = task_df['ptp_amp'] > 150e-6
    
    for p in percs:
        # compute thresholds
        thrs = {}
        for metric in ['smr_snr', 'high_beta_power', 'broadband_power', 'noise_floor_power', 'transient_score', 'channel_inconsistency']:
            val = rest_df.groupby(['subject', 'session'])[metric].transform(lambda x: np.nanpercentile(x, p))
            task_df[f'{metric}_thr'] = task_df.set_index(['subject', 'session']).index.map(rest_df.groupby(['subject', 'session'])[metric].apply(lambda x: np.nanpercentile(x, p)))
            
        # evaluate gates
        gate_A = task_df['smr_snr'] > task_df['smr_snr_thr']
        gate_B = gate_A & (task_df['high_beta_power'] < task_df['high_beta_power_thr'])
        is_contam = (task_df['broadband_power'] > task_df['broadband_power_thr']) | \
                    (task_df['noise_floor_power'] > task_df['noise_floor_power_thr']) | \
                    (task_df['transient_score'] > task_df['transient_score_thr']) | \
                    (task_df['channel_inconsistency'] > task_df['channel_inconsistency_thr'])
        gate_C = gate_B & ~is_contam
        
        n_task = len(task_df)
        res_tradeoff.append({
            'dataset': ds,
            'percentile': p,
            'gate_a_yield_pct': gate_A.sum() / n_task * 100,
            'gate_b_yield_pct': gate_B.sum() / n_task * 100,
            'gate_c_yield_pct': gate_C.sum() / n_task * 100,
            'quality_flagged_pct': is_contam.sum() / n_task * 100,
            'clean_gate_a_pct': (gate_A & ~is_contam).sum() / gate_A.sum() * 100 if gate_A.sum() > 0 else 0,
            'retained_windows_per_min': (gate_C.sum() / n_task) * 120 # 120 windows/min approx
        })
        
        if p == 75:
            # Baseline analysis
            baseline_flagged = task_df['baseline_flag'].sum()
            nfsqi_flagged = is_contam.sum()
            overlap = (task_df['baseline_flag'] & is_contam).sum()
            baseline_res = {
                'dataset': ds,
                'baseline_flagged_pct': baseline_flagged / n_task * 100,
                'nfsqi_flagged_pct': nfsqi_flagged / n_task * 100,
                'overlap_pct': overlap / baseline_flagged * 100 if baseline_flagged > 0 else 0,
                'clean_retention_pct': (~task_df['baseline_flag']).sum() / n_task * 100
            }
            
            # Montage Sensitivity
            if 'channel_inconsistency_exp' in task_df.columns:
                task_df['exp_thr'] = task_df.set_index(['subject', 'session']).index.map(rest_df.groupby(['subject', 'session'])['channel_inconsistency_exp'].apply(lambda x: np.nanpercentile(x, p)))
                is_contam_exp = (task_df['broadband_power'] > task_df['broadband_power_thr']) | \
                                (task_df['noise_floor_power'] > task_df['noise_floor_power_thr']) | \
                                (task_df['transient_score'] > task_df['transient_score_thr']) | \
                                (task_df['channel_inconsistency_exp'] > task_df['exp_thr'])
                montage_res = {
                    'dataset': ds,
                    'std_roi_quality_flagged_pct': is_contam.sum() / n_task * 100,
                    'exp_roi_quality_flagged_pct': is_contam_exp.sum() / n_task * 100,
                    'gate_c_yield_std': gate_C.sum() / n_task * 100,
                    'gate_c_yield_exp': (gate_B & ~is_contam_exp).sum() / n_task * 100
                }
            else:
                montage_res = {}

    return pd.DataFrame(res_tradeoff), baseline_res, montage_res

def main():
    out_dir = ROOT / 'results/final'
    out_dir.mkdir(parents=True, exist_ok=True)
    
    all_tradeoffs = []
    all_baselines = []
    all_montages = []
    
    for ds in DATASETS:
        print(f"Processing dataset {ds}...")
        df = process_dataset(ds)
        if df is not None:
            trade, base, mont = analyze_tradeoff_and_baseline(df, ds)
            all_tradeoffs.append(trade)
            all_baselines.append(base)
            if mont: all_montages.append(mont)
            
    if all_tradeoffs:
        trade_df = pd.concat(all_tradeoffs, ignore_index=True)
        trade_df.to_csv(out_dir / 'nfsqi_operating_tradeoff.csv', index=False)
        trade_df.to_markdown(out_dir / 'nfsqi_operating_tradeoff.md', index=False)
        
        # density
        dens = trade_df[trade_df['percentile'] == 75][['dataset', 'gate_a_yield_pct', 'gate_b_yield_pct', 'gate_c_yield_pct', 'retained_windows_per_min']]
        dens.to_csv(out_dir / 'nfsqi_feedback_density.csv', index=False)
        dens.to_markdown(out_dir / 'nfsqi_feedback_density.md', index=False)
        
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 6))
        for ds in DATASETS:
            ds_df = trade_df[trade_df['dataset'] == ds]
            if not ds_df.empty:
                plt.plot(ds_df['retained_windows_per_min'], ds_df['quality_flagged_pct'], marker='o', label=ds)
                
                # Default point
                default = ds_df[ds_df['percentile'] == 75]
                plt.scatter(default['retained_windows_per_min'], default['quality_flagged_pct'], s=100, edgecolors='k', zorder=5)
                
        plt.xlabel('Retained Windows / Minute')
        plt.ylabel('Quality Flagged (%)')
        # plt.title('Operating Tradeoff: Yield vs. Blocking')
        plt.legend()
        plt.grid(True)
        (ROOT / 'manuscript/figures').mkdir(parents=True, exist_ok=True)
        plt.savefig(ROOT / 'manuscript/figures/nfsqi_operating_tradeoff.pdf')
        
    if all_baselines:
        pd.DataFrame(all_baselines).to_csv(out_dir / 'nfsqi_artifact_baseline_comparison.csv', index=False)
        pd.DataFrame(all_baselines).to_markdown(out_dir / 'nfsqi_artifact_baseline_comparison.md', index=False)
        
    if all_montages:
        pd.DataFrame(all_montages).to_csv(out_dir / 'nfsqi_montage_sensitivity.csv', index=False)
        pd.DataFrame(all_montages).to_markdown(out_dir / 'nfsqi_montage_sensitivity.md', index=False)
        
if __name__ == '__main__':
    main()
