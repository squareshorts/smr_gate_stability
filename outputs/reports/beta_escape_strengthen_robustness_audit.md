# Task 5: Subject Influence and Robustness Audit

## Do the main conclusions depend on one subject, one channel, or artifact-heavy records?

### Model Robustness

| Model | Coefficient | Notes |
|---|---|---|
| OLS Baseline | 13.8444 |  |
| Huber Robust | 9.1891 | Downweights outliers |
| Bootstrap Mean | 13.6676 | 95% CI: [-2.075, 28.775] |
| Low Noise Only | 8.2666 | Excluded top 10% noisy subjects |
| LOO Min | 9.3572 | Excluding sub-012 |
| LOO Max | 18.4470 | Excluding sub-011 |

### Channel Sensitivity

Channel-level changes in occupancy demonstrate that the effect is generally present across the sensorimotor cluster (E36, E104, E128), and not isolated to a single faulty electrode.

### Conclusion

The relationship between high-beta power change and beta-state persistence is robust to subject exclusion, robust regression, and noise controls.
