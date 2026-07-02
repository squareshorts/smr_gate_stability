# Task 2: Amplitude-Occupancy-Persistence Decomposition

## What does 'high-beta suppression' mean empirically?

The variance in mean high-beta power change is primarily driven by: **high_beta_power_trimmed95**.

### Multiple Regression (Standardized Coefficients)

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:                      y   R-squared:                       0.568
Model:                            OLS   Adj. R-squared:                  0.303
Method:                 Least Squares   F-statistic:                     2.140
Date:                Thu, 02 Jul 2026   Prob (F-statistic):              0.107
Time:                        09:56:06   Log-Likelihood:                -21.973
No. Observations:                  22   AIC:                             61.95
Df Residuals:                      13   BIC:                             71.77
Df Model:                           8                                         
Covariance Type:            nonrobust                                         
========================================================================================================
                                           coef    std err          t      P>|t|      [0.025      0.975]
--------------------------------------------------------------------------------------------------------
const                                 2.776e-17      0.182   1.52e-16      1.000      -0.394       0.394
high_beta_power_trimmed95_change         0.4861      0.529      0.919      0.375      -0.656       1.628
beta_state_occupancy_change              0.8916      2.238      0.398      0.697      -3.942       5.725
s1_episode_rate_per_min_change          -0.5276      1.011     -0.522      0.611      -2.713       1.658
mean_s1_dwell_time_s_change             -0.1055      1.636     -0.064      0.950      -3.639       3.429
long_high_beta_burst_fraction_change    -0.3342      0.533     -0.627      0.541      -1.485       0.817
s1_escape_rate_per_s_change             -0.3245      1.283     -0.253      0.804      -3.097       2.448
s1_reentry_probability_change           -0.5636      1.181     -0.477      0.641      -3.115       1.988
broadband_non_target_power_change        0.2277      0.514      0.443      0.665      -0.883       1.338
==============================================================================
Omnibus:                       36.249   Durbin-Watson:                   2.275
Prob(Omnibus):                  0.000   Jarque-Bera (JB):              103.463
Skew:                          -2.765   Prob(JB):                     3.41e-23
Kurtosis:                      12.072   Cond. No.                         35.1
==============================================================================

Notes:
[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.
```

### Bivariate Relationships

| Predictor | Pearson_r_with_Mean_Power_Change | R2_Marginal |
|---|---|---|
| high_beta_power_trimmed95 | 0.6910 | 0.4774 |
| broadband_non_target_power | 0.6217 | 0.3865 |
| s1_episode_rate_per_min | -0.3913 | 0.1531 |
| beta_state_occupancy | -0.3624 | 0.1313 |
| long_high_beta_burst_fraction | -0.3537 | 0.1251 |
| s1_escape_rate_per_s | 0.2853 | 0.0814 |
| s1_reentry_probability | -0.2721 | 0.0741 |
| mean_s1_dwell_time_s | -0.2707 | 0.0733 |
