# NCTRL1 Results: Stochastic Active-Damping Model

Generated: 2026-07-01T19:04:33.486300+00:00

## Model

SDE closed-loop model with three variables:
- x(t): SMR target variable (slow regulation)
- eta(t): high-beta noise / fast stochastic fluctuation
- z(t): broadband contamination artifact

Active damping: deta = [-lambda_eta*eta - k_damp*I(|eta|>eta_thr)*eta]*dt + sigma_eta*dW_eta
Coupling: dx includes +c_xeta*eta*dt (noise injection into target)

## Prototype regimes

             name  smr_acquired  noise_damped    x_mean  eta_std  hb_burst_occupancy
     R1_damp_only         False         False  0.429188 0.695643            0.154111
      R2_acq_only          True         False  0.998675 2.192400            0.692556
          R3_both          True         False  0.973563 0.695643            0.154111
       R4_neither         False         False -2.833760 4.065895            0.801704
  R5_false_reward          True          True  0.986376 0.318823            0.000000
R6_noise_disturbs         False         False -3.888290 5.421194            0.842963

## Parameter grid (81 combinations)

Quadrant counts:
  A_both: 37 (45.7%)
  B_acq_only: 26 (32.1%)
  D_neither: 10 (12.3%)
  C_damp_only: 8 (9.9%)

Separability confirmed: True
- Regime B (SMR acquisition without noise damping): 26 cases
- Regime C (noise damping without SMR acquisition): 8 cases

## Interpretation

Active damping (k_damp) reduces high-frequency variance and burst occupancy WITHOUT necessarily
producing SMR acquisition (quadrant C exists). Conversely, SMR acquisition occurs with k_damp=0
when a_x is large (quadrant B). This confirms mechanistic separability.

The c_xeta coupling parameter controls how much uncontrolled high-frequency noise degrades x.
When c_xeta > 0 and k_damp = 0, high eta noise increases x diffusion and impairs SMR acquisition.
When k_damp > 0, eta is attenuated, reducing its disruptive coupling into x.

This is consistent with the central hypothesis: high-beta inhibition (k_damp) functions as
noise control that can improve SMR feedback quality without directly producing SMR acquisition.

Generated: 2026-07-01T19:04:33.491603+00:00
