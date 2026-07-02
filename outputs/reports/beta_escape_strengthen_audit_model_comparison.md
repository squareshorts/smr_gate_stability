# Audit 1: Incremental Model Comparison

1. **What exact outcomes were predicted?** SNR change and clean SMR occupancy change (continuous), SMR acquisition and Beta escape (binary).
2. **Which predictors were used in each model?** Model A (mean power), Model B (+ controls), Model C (persistence: dwell, burst frac, escape, reentry, occupancy), Model D (+ controls), Model E (all).
3. **Was LOOCV used correctly?** Yes, but continuous predictions yielded negative R2 for Model A, indicating extreme overfitting or poor signal. Binary prediction failed entirely due to label mismatch.
4. **Was all scaling/tuning inside training folds?** Yes, StandardScaler was inside the LOOCV loop.
5. **Were predictors independent of the outcome definition?** Yes, mostly, though SNR change and power change can be mathematically coupled if bands overlap.
6. **Did Model C outperform Model A by a meaningful margin?** Yes, but Model C's R2 was only ~0.13, which is very weak absolute performance.
7. **Did Model C outperform Model B?** Model C (0.13) > Model B (-0.14).
8. **Are performance gains stable under permutation/bootstrap?** We didn't run permutation tests on the LOOCV predictions, which is a weakness.
9. **Are results driven by one subject?** The overall R2 is so low that it's sensitive to outliers.
10. **Are p-values/CIs reported?** No permutation probabilities were reported for the R2 values.
