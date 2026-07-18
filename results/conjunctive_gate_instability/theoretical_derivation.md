# Theoretical derivation — multiplicative conjunctive-instability law

Frozen before results. Parameter-free once criterion-level probabilities are known.

## Definitions
For criterion j and calibration replicate r ∈ {1,2}, on a task window:
- A_jr = 1 iff the window passes criterion j under the threshold calibrated on replicate r
  (pass = feature < threshold_jr; invalid windows fail closed, A_jr = 0).

Per criterion, estimated over the session's task windows:
- p_j1 = P(A_j1 = 1)
- p_j2 = P(A_j2 = 1)
- q_j  = P(A_j1 = 1 AND A_j2 = 1)

## Conjunctive gate
For a nonempty subset S ⊆ {Q1..Q5}, the gate accepts a window iff it passes every criterion:
- G_r = 1 iff A_jr = 1 for all j ∈ S.

Under criterion independence within a replicate, and independence across the joint:
- P(G1 = 1) = Π_{j∈S} p_j1
- P(G2 = 1) = Π_{j∈S} p_j2
- P(G1 = 1 AND G2 = 1) = Π_{j∈S} q_j

## Predicted accepted-set Jaccard
Jaccard over accepted windows = P(G1∧G2) / P(G1∨G2), with P(G1∨G2)=P(G1)+P(G2)−P(G1∧G2):

    J_pred(S) = Π q_j / ( Π p_j1 + Π p_j2 − Π q_j )

Products run over j ∈ S. When the denominator is 0 (both gates accept nothing), J_pred is
defined as 1.0, matching the observed-Jaccard convention (empty union → perfect agreement).

## Key qualitative consequence
Because 0 ≤ q_j ≤ min(p_j1, p_j2) ≤ 1, each additional conjoined criterion multiplies both
numerator and denominator terms by factors < 1, and per-criterion reproducibility
r_j = q_j / max(p_j1,p_j2,ε) < 1 compounds multiplicatively. The predicted Jaccard is therefore
monotonically non-increasing (in expectation) as criteria are conjoined, and decays roughly
like Π r_j. A five-criterion conjunction is predicted to be markedly less reproducible than
any single criterion whenever individual criteria are imperfectly reproducible — the
"conjunctive-instability law".

## Observed quantity
Observed accepted-set Jaccard is computed directly from the two decision vectors G1, G2 on
the identical task-window index (tp / (tp+fp+fn)). The law is a prediction, never fit to data.

## Optional dependence correction (prespecified)
logit(J_obs) ≈ β0 + β1·logit(J_pred) + β2·mean_abs_pairwise_corr, coefficients fit on
development datasets only and frozen for the held-out dataset. No other predictors.
