# Task 1: Incremental Model Comparison

## Does beta-state persistence add explanatory value beyond mean high-beta power?

Yes. Beta-state persistence metrics improve prediction of SMR outcomes beyond what mean high-beta power provides alone.

## Summary of Predictive Performance

| Outcome | Outcome_Type | Model | Metric1_Name | Metric1_Value | Metric2_Name | Metric2_Value |
|---|---|---|---|---|---|---|
| smr_snr_change | Continuous | Model A: Mean Power | R2 (LOOCV) | -0.23120456250172805 | Pearson r (LOOCV) | -0.3904720900571865 |
| smr_snr_change | Continuous | Model B: Mean Power + Controls | R2 (LOOCV) | -0.1404138885093844 | Pearson r (LOOCV) | 0.02467647061450514 |
| smr_snr_change | Continuous | Model C: Persistence | R2 (LOOCV) | 0.1315498343585323 | Pearson r (LOOCV) | 0.39532271088449067 |
| smr_snr_change | Continuous | Model D: Persistence + Controls | R2 (LOOCV) | 0.2319412752905764 | Pearson r (LOOCV) | 0.5239472362163586 |
| smr_snr_change | Continuous | Model E: Combined | R2 (LOOCV) | 0.10078063087591116 | Pearson r (LOOCV) | 0.47561517074472365 |
| clean_smr_occupancy_change | Continuous | Model A: Mean Power | R2 (LOOCV) | -0.1891501988748001 | Pearson r (LOOCV) | -0.1822480774878955 |
| clean_smr_occupancy_change | Continuous | Model B: Mean Power + Controls | R2 (LOOCV) | -0.006102321732189608 | Pearson r (LOOCV) | 0.1671845638104583 |
| clean_smr_occupancy_change | Continuous | Model C: Persistence | R2 (LOOCV) | 0.528914491509462 | Pearson r (LOOCV) | 0.7306890269209103 |
| clean_smr_occupancy_change | Continuous | Model D: Persistence + Controls | R2 (LOOCV) | 0.6075366646882117 | Pearson r (LOOCV) | 0.779497728641936 |
| clean_smr_occupancy_change | Continuous | Model E: Combined | R2 (LOOCV) | 0.5717484373979789 | Pearson r (LOOCV) | 0.7575975544879877 |
| smr_acquisition | Binary | Model A: Mean Power | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| smr_acquisition | Binary | Model B: Mean Power + Controls | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| smr_acquisition | Binary | Model C: Persistence | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| smr_acquisition | Binary | Model D: Persistence + Controls | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| smr_acquisition | Binary | Model E: Combined | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| beta_escape | Binary | Model A: Mean Power | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| beta_escape | Binary | Model B: Mean Power + Controls | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| beta_escape | Binary | Model C: Persistence | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| beta_escape | Binary | Model D: Persistence + Controls | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
| beta_escape | Binary | Model E: Combined | AUC (LOOCV) | 0.0 | Accuracy (LOOCV) | 0.0 |
