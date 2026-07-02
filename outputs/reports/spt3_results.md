# SPT3 Results: Control-barrier Interpretation

## Model

High-beta inhibition is formalized as a control barrier function (CBF):

  h_beta(y) = y_barrier - y
  Admissible training state: h_beta(y) >= 0  <=>  y < y_barrier

The controller applies a barrier inhibit force proportional to violation:
  u_beta = -K_beta * max(y - y_barrier, 0)

## Parameter sweep

- epsilon: [0.02, 0.1, 0.5]
- K_beta: [0.0, 0.5, 1.5, 3.0, 5.0]
- sigma_y: [0.05, 0.15, 0.30]
- Total simulations: 135

## Barrier violation metrics (mean over sigma_y and seed)

K_beta | Violation rate | SMR after violation | SMR after admissible
-------|----------------|---------------------|---------------------
0.0    | 0.869          | 0.0420              | 0.1039
0.5    | 0.869          | 0.0418              | 0.1052
1.5    | 0.725          | 0.0415              | 0.1065
3.0    | 0.725          | 0.0416              | 0.1063
5.0    | 0.725          | 0.0413              | 0.1081

## Interpretation

**SMR change after admissible state minus after violation: 0.0644**

SMR state improves MORE after admissible-state blocks than after barrier-violation blocks. This is consistent with the barrier stabilization hypothesis: high-beta violations suppress subsequent SMR acquisition probability.

**Conclusion:** High-beta behavior in the fast–slow model acts like a stabilization
constraint variable rather than a target-learning variable. The barrier K_beta reduces
violation rate, increases admissible-state occupancy, and modulates (but does not
determine) subsequent SMR improvement.

Generated: 2026-07-01T18:15:46.025921+00:00
