import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    os.makedirs('outputs/tables', exist_ok=True)
    os.makedirs('outputs/figures', exist_ok=True)
    os.makedirs('outputs/reports', exist_ok=True)
    
    df = pd.read_csv('outputs/tables/nf_sqi_task_labeled_windows.csv')
    df_1s = df[df['window_size'] == 1.0].copy()
    
    cands = df_1s[df_1s['gate_A'] == True].copy()
    
    full_df = pd.read_csv('outputs/tables/nf_sqi_window_features.csv')
    full_df_1s = full_df[full_df['window_size'] == 1.0].copy()
    
    decomp_results = []
    
    for (sub, ses), group in cands.groupby(['subject', 'session']):
        sub_rest = full_df_1s[(full_df_1s['subject'] == sub) & (full_df_1s['session'] == ses) & (full_df_1s['condition'] == 'rest')]
        if len(sub_rest) == 0:
            continue
            
        hb_thr = np.percentile(sub_rest['high_beta_power'].dropna(), 75)
        bb_thr = np.percentile(sub_rest['broadband_power'].dropna(), 75)
        nf_thr = np.percentile(sub_rest['noise_floor_power'].dropna(), 75)
        tr_thr = np.percentile(sub_rest['transient_score'].dropna(), 90)
        ch_thr = np.percentile(sub_rest['channel_inconsistency'].dropna(), 75)
        
        hb_contam = group['high_beta_power'] > hb_thr
        bb_nf_contam = (group['broadband_power'] > bb_thr) | (group['noise_floor_power'] > nf_thr)
        tr_contam = group['transient_score'] > tr_thr
        ch_contam = group['channel_inconsistency'] > ch_thr
        
        # Determine exclusivity
        sum_contam = hb_contam.astype(int) + bb_nf_contam.astype(int) + tr_contam.astype(int) + ch_contam.astype(int)
        
        clean = sum_contam == 0
        multi = sum_contam > 1
        
        only_hb = (sum_contam == 1) & hb_contam
        only_bb_nf = (sum_contam == 1) & bb_nf_contam
        only_tr = (sum_contam == 1) & tr_contam
        only_ch = (sum_contam == 1) & ch_contam
        
        n_cands = len(group)
        if n_cands == 0: continue
        
        # Calculate early vs late? The session strings might be 'ses-01' and 'ses-19' etc.
        # We can extract the session number to determine early vs late later.
        
        # Gate blocking (False-Admissible blocking)
        # False admissible = passed Gate A but is contaminated by anything
        # A false-admissible window is blocked by a specific gate if that gate flags it.
        # "Blocked by high beta alone" might mean blocked by high beta (regardless of others) OR only blocked by high beta?
        # The prompt asks for "how many false-admissible Gate A windows are blocked by: high beta alone, etc"
        # "alone" could mean the single-gate approach block rate, e.g., if we only had the HB gate, how many would it block?
        
        fa_mask = sum_contam > 0
        n_fa = fa_mask.sum()
        
        if n_fa > 0:
            blocked_hb = hb_contam[fa_mask].sum() / n_fa
            blocked_bb_nf = bb_nf_contam[fa_mask].sum() / n_fa
            blocked_tr = tr_contam[fa_mask].sum() / n_fa
            blocked_ch = ch_contam[fa_mask].sum() / n_fa
            blocked_full = (sum_contam[fa_mask] > 0).sum() / n_fa # By definition 1.0 since it's the FA mask itself
        else:
            blocked_hb = blocked_bb_nf = blocked_tr = blocked_ch = blocked_full = 0.0
        
        decomp_results.append({
            'subject': sub,
            'session': ses,
            'total_candidates': n_cands,
            'clean': clean.sum() / n_cands,
            'high_beta_excl': only_hb.sum() / n_cands,
            'broadband_noise_excl': only_bb_nf.sum() / n_cands,
            'transient_excl': only_tr.sum() / n_cands,
            'channel_inc_excl': only_ch.sum() / n_cands,
            'multi_contam': multi.sum() / n_cands,
            
            'fa_total': n_fa,
            'blocked_by_hb_single': blocked_hb,
            'blocked_by_bbnf_single': blocked_bb_nf,
            'blocked_by_tr_single': blocked_tr,
            'blocked_by_ch_single': blocked_ch,
            'blocked_by_full': blocked_full
        })
        
    decomp_df = pd.DataFrame(decomp_results)
    
    # Parse early/late
    # Usually ses-01 is early, and max ses is late.
    decomp_df['ses_num'] = decomp_df['session'].str.extract('(\d+)').astype(float)
    
    early_late_res = []
    for sub, group in decomp_df.groupby('subject'):
        if len(group) == 0: continue
        early_idx = group['ses_num'].idxmin()
        late_idx = group['ses_num'].idxmax()
        
        early_row = group.loc[early_idx]
        late_row = group.loc[late_idx]
        
        early_late_res.append(early_row.to_dict())
        if early_idx != late_idx:
            early_late_res.append(late_row.to_dict())
            
    # Simplify early vs late by marking them
    for i, row in decomp_df.iterrows():
        sub_df = decomp_df[decomp_df['subject'] == row['subject']]
        if row['ses_num'] == sub_df['ses_num'].min():
            decomp_df.at[i, 'phase'] = 'early'
        elif row['ses_num'] == sub_df['ses_num'].max():
            decomp_df.at[i, 'phase'] = 'late'
        else:
            decomp_df.at[i, 'phase'] = 'mid'
            
    decomp_df.to_csv('outputs/tables/nf_sqi_contamination_overlap.csv', index=False)
    
    # Output blocking rates
    block_df = decomp_df[['subject', 'session', 'phase', 'blocked_by_hb_single', 'blocked_by_bbnf_single', 'blocked_by_tr_single', 'blocked_by_ch_single', 'blocked_by_full']]
    block_df.to_csv('outputs/tables/nf_sqi_gate_blocking_decomposition.csv', index=False)
    
    # Global Proportions
    cols = ['clean', 'high_beta_excl', 'broadband_noise_excl', 'transient_excl', 'channel_inc_excl', 'multi_contam']
    mean_props = decomp_df[cols].mean()
    
    # Replace variable names with publication labels
    mean_props = mean_props.rename({
        'clean': 'Clean',
        'high_beta_excl': 'High beta only',
        'broadband_noise_excl': 'Broadband/noise only',
        'transient_excl': 'Transient amplitude only',
        'channel_inc_excl': 'Channel inconsistency only',
        'multi_contam': 'Multi-contaminated'
    })
    
    mean_blocks = block_df[['blocked_by_hb_single', 'blocked_by_bbnf_single', 'blocked_by_tr_single', 'blocked_by_ch_single', 'blocked_by_full']].mean()
    mean_blocks = mean_blocks.rename({
        'blocked_by_hb_single': 'High beta',
        'blocked_by_bbnf_single': 'Broadband/noise floor',
        'blocked_by_tr_single': 'Transient amplitude',
        'blocked_by_ch_single': 'Channel inconsistency',
        'blocked_by_full': 'Full NF-SQI'
    })
    
    # Assertion check for Task 1 & 2
    assert np.allclose(mean_props.sum(), 1.0, atol=1e-3), "Values do not sum to 100%"
    
    # Task 1: 100% stacked horizontal bar (or just a regular horizontal bar chart, the user said "100% stacked horizontal bar or horizontal bar chart")
    # Let's use a standard horizontal bar chart sorted by value.
    plt.rcParams.update({'font.size': 14})
    
    mean_props_pct = mean_props * 100
    mean_props_sorted = mean_props_pct.sort_values(ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(mean_props_sorted.index, mean_props_sorted.values, color='steelblue')
    ax.set_xlabel('Proportion of candidate windows (%)', fontsize=16)
    
    for bar in bars:
        width = bar.get_width()
        ax.annotate(f'{width:.1f}%',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(3, 0),  # 3 points horizontal offset
                    textcoords="offset points",
                    ha='left', va='center', fontsize=12)
    
    # Despine and remove unwanted labels
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig('outputs/figures/nf_sqi_contamination_overlap_pie.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/figures/nf_sqi_contamination_overlap_pie.pdf', bbox_inches='tight')
    
    # Task 2: Sorted horizontal bar for blocking rates
    mean_blocks_pct = mean_blocks * 100
    mean_blocks_sorted = mean_blocks_pct.sort_values(ascending=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(mean_blocks_sorted.index, mean_blocks_sorted.values, color='indianred')
    ax.set_xlabel('False-admissible windows blocked (%)', fontsize=16)
    
    for bar in bars:
        width = bar.get_width()
        ax.annotate(f'{width:.1f}%',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(3, 0),
                    textcoords="offset points",
                    ha='left', va='center', fontsize=12)
                    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig('outputs/figures/nf_sqi_contamination_overlap_bar.png', dpi=300, bbox_inches='tight')
    plt.savefig('outputs/figures/nf_sqi_contamination_overlap_bar.pdf', bbox_inches='tight')
    
    with open('outputs/reports/nf_sqi_contamination_overlap_report.md', 'w') as f:
        f.write("# SMR Candidate Contamination Decomposition\n\n")
        f.write("## Overall Proportions\n")
        for k, v in mean_props.items():
            f.write(f"- {k}: {v*100:.2f}%\n")
            
        f.write("\n## Block Rates of False-Admissible Windows (Single Gate Evaluation)\n")
        for k, v in mean_blocks.items():
            f.write(f"- {k}: {v*100:.2f}%\n")
            
        f.write("\n## Final Interpretation\n")
        redundancy_check = mean_props['High beta only'] > 0.05
        if redundancy_check:
            f.write("The high-beta gate has a **distinct safeguard role**. A meaningful portion of candidate windows are exclusively contaminated by high-beta activity (not flagged by broadband, noise, transient, or channel inconsistency checks). It is not completely redundant.\n")
        else:
            f.write("The high-beta gate is **mostly redundant**. The majority of high-beta contaminated windows are also captured by broadband, noise-floor, transient, or channel-inconsistency checks, as evidenced by a low exclusive high-beta proportion.\n")

if __name__ == '__main__':
    main()
