import pandas as pd
import numpy as np
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results" / "external_validation"
CACHE_DIR = Path(__file__).parent / "cache"

def grouped_bootstrap_median(df, group_col, value_col, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    groups = df[group_col].unique()
    n_groups = len(groups)
    medians = []
    
    # Pre-group data for faster access
    grouped = dict(tuple(df.groupby(group_col)))
    
    for _ in range(n_boot):
        sample_groups = rng.choice(groups, size=n_groups, replace=True)
        # Flatten values from sampled groups
        sampled_vals = np.concatenate([grouped[g][value_col].to_numpy() for g in sample_groups if g in grouped])
        if len(sampled_vals) > 0:
            medians.append(np.nanmedian(sampled_vals))
    
    if not medians:
        return np.nan, np.nan, np.nan
        
    actual = df[value_col].median()
    return actual, np.percentile(medians, 2.5), np.percentile(medians, 97.5)

def aggregate_all():
    res = {}
    
    # Data Integrity
    files = list(CACHE_DIR.glob("*.parquet"))
    res['data_integrity'] = {
        'total_files_processed': len(files)
    }
    
    # Q1
    q1 = pd.read_csv(OUT_DIR / "q1_cardinality.csv")
    q1_agg = {}
    for c in q1['cardinality'].unique():
        sub = q1[q1['cardinality'] == c]
        med, p2, p97 = grouped_bootstrap_median(sub, 'participant', 'observed_jaccard')
        q1_agg[str(c)] = {'median': med, 'ci_low': p2, 'ci_high': p97}
    res['q1_cardinality'] = q1_agg
    
    # Q2
    q2 = pd.read_csv(OUT_DIR / "q2_composition.csv")
    re_err = np.abs(q2['reconstructed_delta'] - q2['observed_delta'])
    res['q2_composition'] = {
        'total_edges': len(q2),
        'max_abs_error': float(re_err.max()),
        'median_abs_error': float(re_err.median()),
        'sign_agreement': float((np.sign(q2['reconstructed_delta']) == np.sign(q2['observed_delta'])).mean()),
        'obs_increases': float((q2['observed_delta'] > 0).mean()),
        'obs_decreases': float((q2['observed_delta'] < 0).mean()),
        'obs_unchanged': float((q2['observed_delta'] == 0).mean())
    }
    
    # Q3
    q3 = pd.read_csv(OUT_DIR / "q3_aggregation.csv")
    m_conj, c_low, c_high = grouped_bootstrap_median(q3, 'participant', 'jaccard_conj')
    m_mean, m_low, m_high = grouped_bootstrap_median(q3, 'participant', 'jaccard_mean')
    m_rms, r_low, r_high = grouped_bootstrap_median(q3, 'participant', 'jaccard_rms')
    
    res['q3_aggregation'] = {
        'jaccard_conj': {'median': m_conj, 'ci_low': c_low, 'ci_high': c_high},
        'jaccard_mean': {'median': m_mean, 'ci_low': m_low, 'ci_high': m_high},
        'jaccard_rms': {'median': m_rms, 'ci_low': r_low, 'ci_high': r_high},
        'accept_conj': float(q3['accept_conj'].mean()),
        'accept_mean': float(q3['accept_mean'].mean()),
        'accept_rms': float(q3['accept_rms'].mean()),
        'pct_geq_80_conj': float((q3['jaccard_conj'] >= 0.8).mean() * 100),
        'pct_geq_80_mean': float((q3['jaccard_mean'] >= 0.8).mean() * 100),
        'pct_geq_80_rms': float((q3['jaccard_rms'] >= 0.8).mean() * 100),
    }
    
    # Q4
    q4 = pd.read_csv(OUT_DIR / "q4_h1.csv")
    m_h1, h1_low, h1_high = grouped_bootstrap_median(q4, 'participant', 'jaccard_h1')
    res['q4_h1'] = {
        'jaccard_h1': {'median': m_h1, 'ci_low': h1_low, 'ci_high': h1_high},
        'accept_h1': float(q4['accept_h1'].mean()),
        'pct_geq_80_h1': float((q4['jaccard_h1'] >= 0.8).mean() * 100),
        'il_A_rate': float(q4['il_A_rate'].mean()),
        'il_B_rate': float(q4['il_B_rate'].mean()),
        'il_C_rate': float(q4['il_C_rate'].mean()),
        'il_D_rate': float(q4['il_D_rate'].mean()),
        'any_il_rate': float(q4['any_il_rate'].mean())
    }
    
    # Q5
    q5 = pd.read_csv(OUT_DIR / "q5_duration.csv")
    q5_agg = {}
    for dur in q5['duration'].unique():
        sub = q5[q5['duration'] == dur]
        # Just mean accepts to see the dependence
        q5_agg[str(dur)] = {
            'accept_conj': float(sub['accept_conj'].mean()),
            'accept_mean': float(sub['accept_mean'].mean()),
            'accept_rms': float(sub['accept_rms'].mean()),
            'accept_h1': float(sub['accept_h1'].mean())
        }
    res['q5_duration'] = q5_agg
    
    # Q6
    if (OUT_DIR / "q6_transport.csv").exists():
        q6 = pd.read_csv(OUT_DIR / "q6_transport.csv")
        res['q6_transport'] = {
            'jaccard_conj': float(q6['jaccard_conj'].median()),
            'jaccard_mean': float(q6['jaccard_mean'].median()),
            'jaccard_rms': float(q6['jaccard_rms'].median()),
            'jaccard_h1': float(q6['jaccard_h1'].median()),
            'accept_h1_1': float(q6['accept_h1_1'].mean()),
            'accept_h1_2': float(q6['accept_h1_2'].mean())
        }
        
    with open(OUT_DIR / "summary_stats.json", "w") as f:
        json.dump(res, f, indent=2)
    print("Aggregated statistics written to summary_stats.json")

if __name__ == "__main__":
    aggregate_all()
