# Final Audit Summary

The previous analyses claimed strong empirical support, but a strict audit reveals severe vulnerabilities:
- **Model Comparison**: Binary prediction failed; continuous R2 was exceptionally weak (0.13).
- **Decomposition**: Amplitude changes drove mean power more than occupancy, contradicting the 'state-persistence-only' narrative.
- **Negative Controls**: No significant group-level persistence changes were found in any band.
- **State Validation**: Data-driven GMM states failed to align with predefined thresholds (Dice = 0.449).
- **Robustness**: Bootstrap confidence intervals crossed zero, indicating the central predictive effect is not statistically robust.
