# Audit 5: Robustness Validity

1. **Does leave-one-subject-out preserve direction and model ranking?** The LOO coefficients for Dwell Time vs Power Change ranged heavily (from 9.3 to 18.4).
2. **Do bootstrap CIs exclude zero for the key effects?** NO. The bootstrap 95% CI was [-2.075, 28.775], crossing zero.
3. **Does Huber/robust regression agree with ordinary regression?** Huber coefficient (9.18) was substantially lower than OLS (13.84), indicating outlier inflation in the OLS estimate.
4. **Are E36, E104, and E128 individually consistent?** Channel sensitivity showed broad variance.
5. **Are effects stronger only in the combined channel average?** Spatial averaging often artificially smooths independent noise, making the state appear more coherent than it is at the single-sensor level.
6. **Are artifact-heavy subjects driving the result?** Given the Huber attenuation and the wide bootstrap CI crossing zero, outliers/artifacts likely inflate the baseline effect.
