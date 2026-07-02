# NCTRL Revised Hypothesis Label

Generated: 2026-07-01T19:48:51.545255+00:00

## Label change

| | |
|---|---|
| Original label | **Strong support for active-damping noise-control hypothesis.** |
| Revised label | **Simulation support only; empirical support insufficient.** |

## Reason for downgrade

The original "Strong support" label was inflated by:

1. **Simulation success counted as empirical evidence** (Q1, Q2 in original scoring)
2. **HB band-specificity misclassified** (Q3: "BAND-SPECIFIC" based on max of 1 session, not mean; actual mean HB residual = -0.0442 < 0)
3. **Reward analysis treated as valid evidence** (Q6 in original scoring, but NCTRL6 uses circular proxy)
4. **Framework comparison circularity ignored** (NCTRL7 perfect score = criteria designed to favour NCTRL)
5. **Quadrant robustness not tested** (definition-sensitive; each key quadrant driven by 1 subject)
6. **HB-SMR direction ignored** (positive correlation contradicts suppression narrative)

## Conservative criteria summary

| Criterion | Result | Key finding |
|---|---|---|
| C1: Empirical noise-floor support | FAIL | HB resid mean -0.044; SNR improves 1/5 |
| C2: Quadrant robust across definitions | FAIL | Agreement 0.65; 2.4 unique quads/subject |
| C3: Not single-subject driven | PASS | 2 subjects ever in A_both |
| C4: Reward analysis valid | FAIL | total_reward_frac = 0.50 by construction |
| C5: Framework comparison not circular | FAIL | NCTRL scores 16/16 = perfect |
| C6: Simulation supports mechanism | PASS | B=26, C=8 separable quadrants |
| C7: HB-SMR direction consistent | FAIL | Mean HB-SMR corr = 0.264 (positive = wrong direction) |

**Criteria passed: 2/7**

## Approved claims

- Simulation demonstrates that noise damping (high-beta suppression) and SMR acquisition can be mechanistically
  separable within the active-damping SDE model.
- High-beta changes in this dataset are predominantly broadband in character (HB residual above 1/f is near zero
  or negative for 3/5 subjects).
- Four-quadrant subject classification is possible but highly dependent on the metric used. No subject shows
  consistent A_both classification across definitions.
- The NCTRL framework generates testable predictions that are more directly applicable to EEG data than
  Stuart-Landau or singular perturbation (conceptual argument only).

## Claims that must be removed or qualified

- **REMOVE**: "Strong support for active-damping noise-control hypothesis" as a label.
- **REMOVE**: Any statement that NCTRL6 provides evidence about reward quality (it is a circular proxy).
- **REMOVE**: Any use of NCTRL7 as empirical evidence (it is illustrative/conceptual).
- **QUALIFY**: "HB is band-specific" — data show it is mostly broadband.
- **QUALIFY**: "HB suppression improves SMR SNR" — empirically supported in only 1/5 subjects.
- **QUALIFY**: "Subjects are separable into four quadrants" — true under some definitions, false under others.
- **QUALIFY**: Simulation separability — note the noise_damped flag inconsistency in the regime summary.

Generated: 2026-07-01T19:48:51.545255+00:00
