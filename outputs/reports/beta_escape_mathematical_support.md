# Mathematical Support For Beta-State Persistence / Escape-Rate Control

This technical report supports the empirical analysis framework only. It is not manuscript prose.

## 1. Three-state metastable model

Let X_t in {S0, S1, S2}, where S0 is a clean SMR-compatible state, S1 is a high-beta occupied state, and S2 is a broadband/artifact-contaminated state. In discrete time with bin width Delta t, transitions are described by a stochastic matrix P with entries P_ij = P(X_{t+Delta t}=Sj | X_t=Si).

## 2. Beta episode definition

A beta episode is a maximal contiguous interval in which the high-beta envelope exceeds a predeclared subject/session baseline threshold and the bin is not classified as S2. Its duration is T_beta.

## 3. Survival function

The dwell-time survival function is S(t) = P(T_beta > t). Longer right tails imply more persistent S1 occupation even if mean high-beta power is unchanged.

## 4. Hazard / escape-rate formulation

The discrete escape hazard is h(t) = P(t <= T_beta < t + Delta t | T_beta >= t). A larger hazard means faster exit from S1. The reciprocal mean dwell time is a compact escape-rate summary when the distribution is not too heavy-tailed.

## 5. Transition matrix formulation

S1 persistence is encoded by P_11 and the distribution of consecutive S1 runs. Re-entry is encoded by P_01 and P_21 or by P(X_{t+Delta t}=S1 | X_t != S1). S0 occupancy and clean SMR-compatible occupancy are separable from S1 escape.

## 6. Mean power and dwell time are not identifiable from one another

Let high-beta power be A during S1 and B outside S1. The time average is mean_power = pi_1 A + (1 - pi_1) B, where pi_1 is S1 occupancy. Many combinations of A, B, and pi_1 give the same mean. Dwell times further depend on transition probability P_11, not just pi_1. Therefore equal mean high-beta power can arise from short frequent episodes, rare long episodes, or amplitude changes within episodes.

## 7. Prediction for high-beta inhibition

If high-beta inhibition acts through state persistence, the most direct empirical signature is reduced S1 dwell-time tail, reduced long-burst fraction, reduced occupancy/re-entry, and increased escape hazard. Mean power may move with those quantities but is not the mechanism by itself.

## 8. Prediction for separability

SMR acquisition and beta escape are distinct control objectives: SMR metrics depend on SMR-band enhancement and clean compatible occupancy, whereas beta escape depends on S1 dwell, hazard, and re-entry. The four-quadrant empirical classification tests whether those objectives dissociate.
