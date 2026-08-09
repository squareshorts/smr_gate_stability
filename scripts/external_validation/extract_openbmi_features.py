import sys
from pathlib import Path
import os
import glob
import numpy as np
import pandas as pd
import scipy.io as sio
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from empirical.nf_sqi_realtime import extract_realtime_features
from scripts.hybrid_gate_extension.hard_interlocks import compute_hard_interlocks

DATA_DIR = Path(r"C:\work\external_eeg\openbmi")
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FS = 1000
WINDOW_S = 1.0
HOP_S = 0.5
WINDOW_SAMPLES = int(WINDOW_S * FS)
HOP_SAMPLES = int(HOP_S * FS)

# Mapped strictly to C3(12), Cz(13), C4(14)
CHANNEL_INDICES = [12, 13, 14] 

def extract_windows(data_array, fs, window_samples, hop_samples):
    n_channels, n_samples = data_array.shape
    starts = np.arange(0, n_samples - window_samples + 1, hop_samples)
    return starts, [data_array[:, s:s+window_samples] for s in starts]

def process_file(mat_path):
    fname = mat_path.name
    cache_path = CACHE_DIR / fname.replace('.mat', '.parquet')
    if cache_path.exists():
        return
        
    print(f"Processing {fname}...")
    try:
        data = sio.loadmat(str(mat_path), simplify_cells=True)
    except Exception as e:
        print(f"Failed to load {fname}: {e}")
        return

    records = []
    
    for block_name, condition_label in [('EEG_MI_train', 'train'), ('EEG_MI_test', 'test')]:
        if block_name not in data: continue
        block = data[block_name]
        
        # 1. pre_rest processing (calibration data)
        # 60s max allowed
        pre_rest_raw = block.get('pre_rest')
        if pre_rest_raw is not None:
            pre_rest_raw = pre_rest_raw.T # shape: (channels, samples)
            n_rest = min(pre_rest_raw.shape[1], int(60 * FS))
            pre_rest = pre_rest_raw[CHANNEL_INDICES, :n_rest]
            
            # Use non-overlapping 1.0s windows for rest (as per greedy_nonoverlap frozen design)
            starts, windows = extract_windows(pre_rest, FS, WINDOW_SAMPLES, WINDOW_SAMPLES)
            for s, w in zip(starts, windows):
                features = extract_realtime_features(w, FS, previous_smr_power=None, channel_baseline=None)
                interlocks = compute_hard_interlocks(w, FS, expected_shape=(3, WINDOW_SAMPLES))
                rec = {
                    'session_file': fname,
                    'block': block_name,
                    'condition': 'rest',
                    'window_start_s': s / FS,
                    'high_beta_power': features.high_beta_power,
                    'broadband_power': features.broadband_power,
                    'noise_floor_power': features.noise_floor_power,
                    'transient_score': features.transient_score,
                    'raw_feature_valid': features.valid
                }
                for i, band in enumerate(["smr", "beta", "broadband", "noise"]):
                    for ch in range(3):
                        rec[f'channel_{band}_{ch}'] = features.channel_bandpowers[band][ch] if features.channel_bandpowers else np.nan
                rec.update(interlocks)
                records.append(rec)
                
        # 2. task processing
        x_raw = block.get('x')
        if x_raw is not None:
            x_raw = x_raw.T
            x = x_raw[CHANNEL_INDICES, :]
            starts, windows = extract_windows(x, FS, WINDOW_SAMPLES, HOP_SAMPLES)
            
            for s, w in zip(starts, windows):
                features = extract_realtime_features(w, FS, previous_smr_power=None, channel_baseline=None)
                interlocks = compute_hard_interlocks(w, FS, expected_shape=(3, WINDOW_SAMPLES))
                rec = {
                    'session_file': fname,
                    'block': block_name,
                    'condition': 'task',
                    'window_start_s': s / FS,
                    'high_beta_power': features.high_beta_power,
                    'broadband_power': features.broadband_power,
                    'noise_floor_power': features.noise_floor_power,
                    'transient_score': features.transient_score,
                    'raw_feature_valid': features.valid
                }
                for i, band in enumerate(["smr", "beta", "broadband", "noise"]):
                    for ch in range(3):
                        rec[f'channel_{band}_{ch}'] = features.channel_bandpowers[band][ch] if features.channel_bandpowers else np.nan
                rec.update(interlocks)
                records.append(rec)
                
    if records:
        df = pd.DataFrame(records)
        df.to_parquet(cache_path, index=False)

if __name__ == "__main__":
    mat_files = list(DATA_DIR.glob("*_EEG_MI.mat"))
    print(f"Found {len(mat_files)} MAT files.")
    from joblib import Parallel, delayed
    Parallel(n_jobs=-1)(delayed(process_file)(f) for f in tqdm(mat_files))

