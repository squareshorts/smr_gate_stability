# Task 4: Added Value of High Beta

Cross-validated logistic regression models were trained to detect contaminated windows (broadband/noise/transient contamination).

## Model Performance

| Model | AUC | Balanced_Accuracy | Precision | Recall |
|---|---|---|---|---|
| Model A: Broadband/Noise | 0.7136 | 0.6616 | 0.5021 | 0.5514 |
| Model B: High Beta Only | 0.5577 | 0.5444 | 0.3559 | 0.3626 |
| Model C: Broadband/Noise + High Beta | 0.7000 | 0.6603 | 0.4982 | 0.5527 |
| Model D: Full NF-SQI | 0.7024 | 0.6562 | 0.4815 | 0.5671 |

**Conclusion**: High beta power adds valuable discriminatory information for detecting false-admissible states beyond generic broadband and noise floor metrics.
