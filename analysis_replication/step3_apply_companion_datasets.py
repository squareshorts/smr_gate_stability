import os
import sys
import pandas as pd
import numpy as np
import mne
import warnings
from pathlib import Path
from scipy.stats import median_abs_deviation

warnings.filterwarnings('ignore')
mne.set_log_level('WARNING')

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from empirical.nf_sqi_common import (
    SMR_BAND, HIGH_BETA_BAND, BROADBAND_RANGE, NOISE_FLOOR_BAND,
    read_events_for_edf, welch_psd, bandpower_from_psd
)
from empirical.nf_sqi_t1_features import extract_window_features
from sklearn.metrics import roc_auc_score, balanced_accuracy_score

# Primary channels for ds004447
SENSORIMOTOR_CHANNELS = ["E36", "E104", "E128"]
# Fallback channels if E36/104/128 are not present (Standard 10-20 mapping for C3, Cz, C4)
FALLBACK_CHANNELS = ["C3", "Cz", "C4"]

def identify_sensorimotor_channels(ch_names):
    if all(c in ch_names for c in SENSORIMOTOR_CHANNELS):
        return SENSORIMOTOR_CHANNELS
    elif all(c in ch_names for c in FALLBACK_CHANNELS):
        return FALLBACK_CHANNELS
    else:
        # Check for any valid mapping if possible
        c3 = [c for c in ch_names if c.upper() == 'C3']
        cz = [c for c in ch_names if c.upper() == 'CZ']
        c4 = [c for c in ch_names if c.upper() == 'C4']
        if c3 and cz and c4:
            return [c3[0], cz[0], c4[0]]
        return None

def extract_dataset_features(dataset_id):
    dataset_dir = ROOT / "data" / "raw" / "openneuro" / dataset_id
    edf_files = list(dataset_dir.rglob("sub-*/ses-*/eeg/*.edf"))

    if not edf_files:
        print(f"[{dataset_id}] No EDF files found. Skipping.")
        return None, None

    all_features = []

    for edf_path in edf_files:
        subject = edf_path.parts[-4]
        session = edf_path.parts[-3]

        try:
            raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
            channels = identify_sensorimotor_channels(raw.ch_names)

            if not channels:
                print(f"[{dataset_id}] {subject} {session} missing sensorimotor channels. Skipping.")
                continue

            raw.pick_channels(channels)
            fs = raw.info['sfreq']

            raw_duration_s = raw.times[-1]
            try:
                events = read_events_for_edf(edf_path, raw_duration_s)
                # Map samples to condition
                event_arr = np.zeros(raw.n_times, dtype=int)
                for _, row in events[events["instruction"].astype(str) == "task"].iterrows():
                    start = int(round(float(row["onset_s"]) * fs))
                    stop = int(round((float(row["onset_s"]) + float(row["duration_s"])) * fs))
                    start = max(0, min(start, raw.n_times))
                    stop = max(start, min(stop, raw.n_times))
                    event_arr[start:stop] = 1
            except Exception as e:
                # If events missing, skip
                print(f"[{dataset_id}] {subject} {session} missing events. {e}")
                continue

            data = raw.get_data() # (n_channels, n_samples)
            n_samples = data.shape[1]

            # Using only the 1.0s window for primary analysis to save time across datasets
            win_len_s = 1.0
            win_step_s = 0.5

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

            # Compute channel inconsistency for this session
            if len(session_windows) > 0:
                sw_df = pd.DataFrame(session_windows)
                rest_mask = sw_df['condition'] == 'rest'

                if rest_mask.sum() == 0:
                    print(f"[{dataset_id}] {subject} {session} has no rest baseline. Skipping.")
                    continue

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

        except Exception as e:
            print(f"[{dataset_id}] Error on {subject} {session}: {e}")

    if not all_features:
        print(f"[{dataset_id}] No usable features generated. Check logs.")
        return None, None

    df_feats = pd.concat(all_features, ignore_index=True)
    df_feats.to_csv(ROOT / f'outputs/replication_tables/{dataset_id}_window_features.csv', index=False)

    return df_feats, channels

def compute_dataset_gates(df, dataset_id):
    # Re-apply threshold logic for Gates A, B, C exactly as in ds004447

    thresholds_list = []

    df_rest = df[df['condition'] == 'rest']

    for (sub, ses), group in df_rest.groupby(['subject', 'session']):
        p75 = group[['smr_power', 'high_beta_power', 'noise_floor_power', 'broadband_power', 'transient_score', 'channel_inconsistency', 'channel_inconsistency_mad']].quantile(0.75)
        p70 = group[['smr_power', 'high_beta_power', 'noise_floor_power', 'broadband_power', 'transient_score', 'channel_inconsistency', 'channel_inconsistency_mad']].quantile(0.70)
        p80 = group[['smr_power', 'high_beta_power', 'noise_floor_power', 'broadband_power', 'transient_score', 'channel_inconsistency', 'channel_inconsistency_mad']].quantile(0.80)
        p90 = group[['smr_power', 'high_beta_power', 'noise_floor_power', 'broadband_power', 'transient_score', 'channel_inconsistency', 'channel_inconsistency_mad']].quantile(0.90)

        # MAD
        def mad_thr(x):
            med = x.median()
            mad = median_abs_deviation(x.dropna())
            return med + 1.4826 * mad

        mad = group[['smr_power', 'high_beta_power', 'noise_floor_power', 'broadband_power', 'transient_score', 'channel_inconsistency', 'channel_inconsistency_mad']].apply(mad_thr)

        thresholds_list.append({
            'subject': sub,
            'session': ses,
            'smr_p75': p75['smr_power'],
            'beta_p75': p75['high_beta_power'],
            'noise_p75': p75['noise_floor_power'],
            'broadband_p75': p75['broadband_power'],
            'transient_p90': p90['transient_score'], # Transient uses 90th
            'ch_inc_p75': p75['channel_inconsistency'],

            # Sensitivity thresholds for later
            'beta_p70': p70['high_beta_power'],
            'beta_p80': p80['high_beta_power'],
            'beta_p90': p90['high_beta_power'],
            'beta_mad': mad['high_beta_power']
        })

    df_thr = pd.DataFrame(thresholds_list)
    df_task = df[df['condition'] == 'task'].copy()
    df_task = df_task.merge(df_thr, on=['subject', 'session'], how='left')

    # Primary gate configuration
    df_task['gate_A'] = df_task['smr_power'] > df_task['smr_p75']
    df_task['gate_B'] = df_task['gate_A'] & (df_task['high_beta_power'] <= df_task['beta_p75'])

    # Contamination triggers for full gate (C) and analysis
    df_task['is_hb_contam'] = df_task['high_beta_power'] > df_task['beta_p75']
    df_task['is_noise_contam'] = df_task['noise_floor_power'] > df_task['noise_p75']
    df_task['is_bb_contam'] = df_task['broadband_power'] > df_task['broadband_p75']
    df_task['is_transient_contam'] = df_task['transient_score'] > df_task['transient_p90']
    df_task['is_ch_inc_contam'] = df_task['channel_inconsistency'] > df_task['ch_inc_p75']

    # A candidate is contaminated if ANY of the robust safeguards trigger (bb, noise, transient, ch_inc)
    # Note: the paper defines "is_contaminated" by broadband, noise floor, transient, or channel inconsistency.
    df_task['is_contaminated'] = df_task['is_bb_contam'] | df_task['is_noise_contam'] | df_task['is_transient_contam'] | df_task['is_ch_inc_contam']

    df_task['gate_C'] = df_task['gate_B'] & (~df_task['is_contaminated'])

    # False-admissible analysis (within Gate A candidates)
    cands = df_task[df_task['gate_A'] == True].copy()

    overlap_results = []

    for (sub, ses), group in cands.groupby(['subject', 'session']):
        total = len(group)
        if total == 0:
            continue

        # Contamination composition
        clean = group[~group['is_contaminated'] & ~group['is_hb_contam']]
        hb_only = group[group['is_hb_contam'] & ~group['is_contaminated']]
        bbnf = group['is_bb_contam'] | group['is_noise_contam']
        bb_only = group[bbnf & ~group['is_hb_contam'] & ~group['is_transient_contam'] & ~group['is_ch_inc_contam']]
        ch_only = group[group['is_ch_inc_contam'] & ~group['is_hb_contam'] & ~bbnf & ~group['is_transient_contam']]
        tr_only = group[group['is_transient_contam'] & ~group['is_hb_contam'] & ~bbnf & ~group['is_ch_inc_contam']]

        multi = group[(group['is_hb_contam'].astype(int) + bbnf.astype(int) + group['is_ch_inc_contam'].astype(int) + group['is_transient_contam'].astype(int)) > 1]

        # False admissible counts
        false_admissible = group[group['is_contaminated'] | group['is_hb_contam']]
        fa_total = len(false_admissible)

        if fa_total > 0:
            blk_hb = false_admissible['is_hb_contam'].sum()
            blk_bbnf = bbnf[false_admissible.index].sum()
            blk_tr = false_admissible['is_transient_contam'].sum()
            blk_ch = false_admissible['is_ch_inc_contam'].sum()
            blk_full = fa_total # Full NF-SQI by definition blocks all identified contamination
        else:
            blk_hb = blk_bbnf = blk_tr = blk_ch = blk_full = 0

        overlap_results.append({
            'subject': sub,
            'session': ses,
            'total_candidates': total,
            'clean': len(clean),
            'high_beta_excl': len(hb_only),
            'broadband_noise_excl': len(bb_only),
            'channel_inc_excl': len(ch_only),
            'transient_excl': len(tr_only),
            'multi_contam': len(multi),
            'contaminated': fa_total,
            'blocked_by_hb_single': blk_hb,
            'blocked_by_bbnf_single': blk_bbnf,
            'blocked_by_tr_single': blk_tr,
            'blocked_by_ch_single': blk_ch,
            'blocked_by_full': blk_full
        })

    df_overlap = pd.DataFrame(overlap_results)
    df_overlap.to_csv(ROOT / f'outputs/replication_tables/{dataset_id}_contamination_overlap.csv', index=False)

    # Save the labeled windows as well
    df_task.to_csv(ROOT / f'outputs/replication_tables/{dataset_id}_task_labeled_windows.csv', index=False)

    return df_task, df_overlap

def run_model_comparison(df_task, dataset_id):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    cands = df_task[df_task['gate_A'] == True].copy()
    cands['target'] = cands['is_contaminated'].astype(int)

    subjects = cands['subject'].unique()

    models = {
        'Broadband/Noise Floor Only': ['broadband_power', 'noise_floor_power'],
        'High Beta Only': ['high_beta_power'],
        'Broadband/Noise Floor + High Beta': ['broadband_power', 'noise_floor_power', 'high_beta_power'],
        'Full NF-SQI': ['broadband_power', 'noise_floor_power', 'high_beta_power', 'transient_score', 'channel_inconsistency']
    }

    results = []

    for name, features in models.items():
        y_true = []
        y_pred_proba = []
        test_sub_col = []

        for test_sub in subjects:
            train_df = cands[cands['subject'] != test_sub]
            test_df = cands[cands['subject'] == test_sub]

            if len(train_df) == 0 or len(test_df) == 0 or train_df['target'].nunique() < 2:
                continue

            scaler = StandardScaler()
            X_train = scaler.fit_transform(train_df[features])
            X_test = scaler.transform(test_df[features])

            clf = LogisticRegression(class_weight='balanced', random_state=20260702, solver='lbfgs')
            clf.fit(X_train, train_df['target'])

            y_true.extend(test_df['target'].values)
            y_pred_proba.extend(clf.predict_proba(X_test)[:, 1])
            test_sub_col.extend([test_sub] * len(test_df))

        if len(y_true) > 0 and len(np.unique(y_true)) > 1:
            auc = roc_auc_score(y_true, y_pred_proba)
            preds = np.array(y_pred_proba) > 0.5
            bacc = balanced_accuracy_score(y_true, preds)

            results.append({
                'Dataset': dataset_id,
                'Model': name,
                'AUC': auc,
                'Balanced_Accuracy': bacc
            })

            # Save predictions for bootstrap
            df_preds = pd.DataFrame({
                'subject': test_sub_col,
                'y_true': y_true,
                'y_pred_proba': y_pred_proba
            })
            df_preds.to_csv(ROOT / f'outputs/replication_tables/{dataset_id}_{name.replace("/", "_").replace(" ", "_")}_predictions.csv', index=False)

    df_models = pd.DataFrame(results)
    if not df_models.empty:
        df_models.to_csv(ROOT / f'outputs/replication_tables/{dataset_id}_model_comparison.csv', index=False)

    return df_models

def main():
    datasets = ['ds004444', 'ds004446', 'ds004448']

    for d_id in datasets:
        print(f"--- Processing companion dataset: {d_id} ---")
        df_feats, channels = extract_dataset_features(d_id)

        if df_feats is not None:
            print(f"[{d_id}] Channels mapped: {channels}")
            df_task, df_overlap = compute_dataset_gates(df_feats, d_id)
            if df_task is not None and len(df_task) > 0:
                df_models = run_model_comparison(df_task, d_id)
                print(f"[{d_id}] Processing complete. Generated {len(df_overlap)} session overlap records and {len(df_models) if df_models is not None else 0} model evaluation rows.")
            else:
                print(f"[{d_id}] No valid task windows found.")

if __name__ == '__main__':
    main()
