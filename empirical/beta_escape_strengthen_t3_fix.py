import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

BANDS = ['theta', 'alpha', 'SMR', 'low_beta', 'high_beta', 'high_freq']

def main():
    change_df = pd.read_csv('outputs/tables/beta_escape_strengthen_negative_control_bands.csv')
    
    # Merge with SMR acquisition
    quad_df = pd.read_csv('outputs/tables/beta_escape_smr_beta_quadrants.csv')
    smr_acq_df = quad_df[['subject', 'smr_acquisition_primary']].drop_duplicates()
    change_df = change_df.merge(smr_acq_df, on='subject')
    
    # Plotting
    sns.set_theme(style="whitegrid")
    metrics_to_plot = ['dwell_time_s_change', 'escape_rate_per_s_change', 'reentry_probability_change', 'occupancy_change']
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    axes = axes.flatten()
    
    for i, metric in enumerate(metrics_to_plot):
        sns.boxplot(data=change_df, x='band', y=metric, ax=axes[i], order=BANDS)
        sns.stripplot(data=change_df, x='band', y=metric, ax=axes[i], color='black', alpha=0.5, order=BANDS)
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
        
        stats_results = []
        for band in BANDS:
            band_data = change_df[change_df['band'] == band]
            t_val, p_val = stats.ttest_1samp(band_data['dwell_time_s_change'].dropna(), 0)
            stats_results.append({
                'Band': band,
                'Mean Dwell Change': band_data['dwell_time_s_change'].mean(),
                'p-value (vs 0)': p_val
            })
            
        stats_df = pd.DataFrame(stats_results)
        
        headers = stats_df.columns.tolist()
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for _, row in stats_df.iterrows():
            f.write("| " + " | ".join([f"{x:.4f}" if isinstance(x, float) else str(x) for x in row]) + " |\n")

        f.write("\n\nInterpretation: The results indicate whether the state dynamics changes are isolated to high beta or represent a broader broadband shift.\n")

if __name__ == '__main__':
    main()
