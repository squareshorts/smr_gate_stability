# Mathematical/Engineering Signal-Quality Framework (NF-SQI)

## 1. Observation Model
The observed EEG signal during neurofeedback is modeled as:
`y(t) = s(t) + c_hb(t) + c_bb(t) + n(t)`
Where `s(t)` is the target neural component (SMR), `c_hb(t)` is high-beta contamination (e.g. motor tension), `c_bb(t)` is broadband non-target physiological activity, and `n(t)` is the high-frequency noise floor and transients.

## 2. Admissible Feedback State
A window is *clean admissible* if `s(t)` dominates the signal space while `c_hb(t)`, `c_bb(t)`, and `n(t)` are below dynamically defined baseline thresholds.

## 3. False-Admissible State
A window is *false-admissible* if standard SMR-only gates (SMR power/SNR > threshold) pass, but the signal space is actually contaminated by `c_bb(t)` or `n(t)`.

## 4. Role of High-Beta Inhibit Channel
Rather than representing a fundamental neural state (e.g. idle motor cortex), the high-beta inhibit channel serves as an *admissibility safeguard*. It intercepts windows where SMR power is artificially inflated by broadband shifts or motor artifacts.

## 5. Gate Logic
- **Gate A**: Passes if `s(t) > threshold`.
- **Gate B**: Passes if `Gate A` and `c_hb(t) < threshold`.
- **Gate C**: Passes if `Gate B` and `c_bb(t), n(t) < threshold`.

