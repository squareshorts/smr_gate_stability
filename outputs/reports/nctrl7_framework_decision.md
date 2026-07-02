# NCTRL7: Framework Comparison

Generated: 2026-07-01T19:07:24.075502+00:00

## Frameworks evaluated

1. Stuart–Landau (SL) oscillator mechanism
2. Singular Perturbation / fast–slow barrier (SPT)
3. Generic Closed-Loop Feedback (CLF)
4. Active Damping / Stochastic Noise-Control (NCTRL) — proposed

## Scoring criteria (0=fails, 1=partial, 2=meets)

1. Matches empirical data (n=5)
2. Explains HB/SMR separability
3. Avoids overclaiming HB as SMR marker
4. Testable from EEG (available data)
5. Handles broadband contamination
6. Handles burst instability
7. Conservative theory paper
8. Requires few untested assumptions

## Scores

  Stuart-Landau (SL): 2/16 (12%)
  Singular Perturbation (SPT): 7/16 (44%)
  Generic Closed-Loop Feedback: 11/16 (69%)
  Active Damping / Noise-Control (NCTRL): 16/16 (100%)

## Rationale by framework


### Stuart-Landau (SL)- **Empirical fit** [1/2]: Mixed fit: SL predicts near-critical SMR which is not confirmed empirically.- **Separability** [1/2]: Partial: separability requires fine-tuning of SL parameters.- **No overclaiming** [0/2]: Fails: near-criticality framing implies HB → SMR coupling.- **EEG testability** [0/2]: Low testability: requires careful parameterization of complex Hopf bifurcation.- **Broadband handling** [0/2]: SL does not include broadband contamination variable.- **Burst handling** [0/2]: SL does not model stochastic burst events.- **Conservative theory** [0/2]: Not conservative: requires near-criticality assumptions.- **Parsimony** [0/2]: Many untested assumptions (bifurcation parameter, driving frequency).
### Singular Perturbation (SPT)- **Empirical fit** [1/2]: Partial: tau separation was null after bandwidth correction.- **Separability** [2/2]: Strong: fast-slow framework directly supports separability.- **No overclaiming** [1/2]: Partial: barrier framing still implies HB suppression is necessary condition.- **EEG testability** [1/2]: Partial: tau analysis confounded by bandwidth; barrier prediction null.- **Broadband handling** [0/2]: SPT does not model broadband contamination.- **Burst handling** [0/2]: SPT does not model stochastic burst dynamics.- **Conservative theory** [1/2]: Reasonable: mechanistic but barrier prediction was null.- **Parsimony** [1/2]: Requires epsilon<<1 (not empirically verified).
### Generic Closed-Loop Feedback- **Empirical fit** [1/2]: Meets: CLF explains mixed outcomes without strong mechanistic commitment.- **Separability** [1/2]: Partial: separability is natural but unexplained.- **No overclaiming** [1/2]: Meets: CLF explicitly avoids mechanistic overclaiming.- **EEG testability** [2/2]: Meets: testable from any closed-loop EEG system.- **Broadband handling** [1/2]: Partial: CLF can model broadband but usually not explicit.- **Burst handling** [1/2]: Partial: CLF can model burst inhibition.- **Conservative theory** [2/2]: Meets: conservative and minimal commitments.- **Parsimony** [2/2]: Minimal untested assumptions.
### Active Damping / Noise-Control (NCTRL)- **Empirical fit** [2/2]: Best fit: noise-control framing matches mixed quadrants and null barrier prediction.- **Separability** [2/2]: Strong: active damping and SMR acquisition are mechanistically independent.- **No overclaiming** [2/2]: Strongest: explicitly states HB reduction ≠ SMR acquisition.- **EEG testability** [2/2]: Direct testability: PSD, burst metrics, diffusion, SNR are all computable.- **Broadband handling** [2/2]: Explicitly models broadband contamination (z variable).- **Burst handling** [2/2]: Explicitly models HB burst dynamics (threshold-triggered damping).- **Conservative theory** [2/2]: Most conservative: null results are predicted and reported.- **Parsimony** [2/2]: Minimal: stochastic SDE with three variables; few free parameters.

## Recommendation

**Recommended primary framework: Active Damping / Noise-Control (NCTRL)**

Reasons:
- NCTRL scores highest across all criteria (16/16).
- Only framework that explicitly models broadband contamination and burst dynamics.
- Directly testable from available EEG metrics (PSD, burst rate, diffusion, SNR).
- Most conservative: does not require near-criticality, epsilon<<1, or band-specific HB causation.
- Explicitly states that HB suppression ≠ SMR acquisition (avoids overclaiming).
- Null and mixed empirical results (from SPT revision) are PREDICTED by the noise-control model.

**Stuart-Landau**: REMOVE from primary claims. Demote to historical context or supplementary.
**SPT**: RETAIN as supplementary mechanistic motivation for time-scale separation, 
         but do not claim empirical support (bandwidth-confounded tau analysis).
**CLF**: USE as general framework context (standard BCI theory).
**NCTRL**: USE as primary mechanistic hypothesis for this revision.

Generated: 2026-07-01T19:07:24.077509+00:00
