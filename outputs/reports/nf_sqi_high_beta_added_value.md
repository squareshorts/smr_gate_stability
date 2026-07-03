# Task 4: Added Value of High Beta

Cross-validated logistic regression models were trained to detect contaminated windows (broadband/noise/transient contamination).

## Model Performance

| Model | AUC | Balanced_Accuracy | F1 | Precision | Recall |
|---|---|---|---|---|---|
| Model A: Broadband/Noise | 0.7136 | 0.6616 | 0.5256 | 0.5021 | 0.5514 |
| Model B: High Beta Only | 0.5577 | 0.5444 | 0.3592 | 0.3559 | 0.3626 |
| Model C: Broadband/Noise + High Beta | 0.7000 | 0.6603 | 0.5241 | 0.4982 | 0.5527 |
| Model D: Full NF-SQI | 0.7024 | 0.6562 | 0.5208 | 0.4815 | 0.5671 |

**Conclusion**: In this model comparison, high beta alone performs below broadband/noise-floor predictors, and adding high beta to broadband/noise-floor predictors does not improve AUC (Model A AUC=0.7136; Model B AUC=0.5577; Model C AUC=0.7000). High beta is therefore supported here as a gate-level safeguard for a subset of candidate windows, not as an incremental predictive feature beyond broadband/noise-floor metrics.
