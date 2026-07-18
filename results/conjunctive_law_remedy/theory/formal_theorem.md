# Composition theorem for accepted-set stability of conjunctive gates

Mathematical notes (not manuscript prose). Verified symbolically (sympy) in
`algebra_verification.txt` and numerically in `simulated_sanity_checks.csv`.

## Setup
A gate G accepts a task window iff every criterion in it passes. Two independent
baseline calibration replicates r=1,2 produce decision vectors G1, G2 over the same
task windows. Marginals and joint:

    P1 = P(G1=1),  P2 = P(G2=1),  Q = P(G1=1 ∧ G2=1).

Accepted-set (positive) Jaccard between replicates:

    J_old = Q / (P1 + P2 − Q).

Add one more criterion A with replicate indicators A1, A2:

    a = P(A1=1),  b = P(A2=1),  c = P(A1=1 ∧ A2=1).

The composed gate is H_r = G_r ∧ A_r. **Under independence between the new criterion
and the existing gate within each replicate and in the joint**,

    P(H1=1)=P1·a,  P(H2=1)=P2·b,  P(H1∧H2)=Q·c,

so

    J_new = Q·c / (P1·a + P2·b − Q·c).

## Theorem (conjunctive-instability / composition theorem)
With Q>0 and both denominators positive,

    J_new ≤ J_old   ⇔   c·(P1 + P2) ≤ P1·a + P2·b   ⇔   P1·(a − c) + P2·(b − c) ≥ 0.

### 1. Proof
J = x/(y−x) is strictly increasing in the joint x and strictly decreasing in the
marginal sum y (∂J/∂x = y/(y−x)² > 0, ∂J/∂y = −x/(y−x)² < 0). Cross-multiplying the
inequality J_new ≤ J_old by the two positive denominators and expanding gives, exactly,

    (J_old − J_new)·(P1+P2−Q)·(P1·a+P2·b−Q·c) = Q·( P1·a + P2·b − c·(P1+P2) ).

The Q² c cross-terms cancel. Since Q>0 and both denominators are >0, the sign of
J_old − J_new equals the sign of P1·a + P2·b − c·(P1+P2). Hence the stated equivalence. ∎

### 2. Symmetric-calibration corollary (a=b=p)
Then P1·a+P2·b = p·(P1+P2), and the condition reduces to **c ≤ p**.

### 3. c ≤ p ⇒ non-increasing (symmetric case)
Because c = P(A1∧A2) ≤ min(a,b) = p always holds for genuine probabilities, the
symmetric condition c ≤ p is automatically satisfied, so J_new ≤ J_old whenever the
new criterion is added — accepted-set Jaccard is monotonically non-increasing.

### 4. Equality conditions
J_new = J_old ⇔ P1·(a−c) + P2·(b−c) = 0. With a−c ≥ 0 and b−c ≥ 0 this forces
a = c and b = c (the added criterion is perfectly reproducible: A1 = A2 a.s.), or the
degenerate P1 = P2 = 0.

### 5. Conditions allowing an increase
An increase (J_new > J_old) requires c·(P1+P2) > P1·a + P2·b, i.e. P1·(a−c)+P2·(b−c) < 0.
Since a−c ≥ 0 and b−c ≥ 0 under independence, **this is impossible under the independence
assumption**. An empirical increase can occur only when the new criterion is *dependent*
on the existing gate — specifically when it preferentially rejects windows where the two
replicate gates disagree (removing fp/fn). Monte-Carlo: 0/10000 independence-regime
increases beyond finite-sample boundary noise; 9693/10000 engineered-dependence increases.

### 6. Extension to K conjunctive criteria
For a subset S of criteria with per-criterion (p_j1, p_j2, q_j),

    J_S = Π_{j∈S} q_j / ( Π p_j1 + Π p_j2 − Π q_j ).

Adding criterion j multiplies the numerator by q_j and the two marginal products by
p_j1, p_j2; applying the one-step theorem recursively shows each addition is
non-increasing under independence. Writing r_j = q_j / max(p_j1,p_j2) ∈ (0,1], the
predicted Jaccard decays multiplicatively, ≈ Π_j r_j — the **multiplicative stability law**.

### 7. Relation to positive/negative agreement
With counts tp (both accept), tn (both withhold), fp, fn:
positive agreement = 2tp/(2tp+fp+fn) is monotone in accepted-set Jaccard = tp/(tp+fp+fn)
(both fall as criteria conjoin); negative agreement = 2tn/(2tn+fp+fn) rises as tn grows.

### 8. Why overall agreement can rise while accepted-set Jaccard falls
Overall agreement = (tp+tn)/n. Conjoining criteria drives tp→0 and tn→n (most windows
withheld by both replicates), so (tp+tn)/n is dominated by tn and can increase, even as
tp/(tp+fp+fn) decreases. High global agreement therefore masks low accepted-set agreement.

### 9. Dependence limitations
The equality J_new = Q·c/(P1·a+P2·b−Q·c) is exact only under independence of the added
criterion and the existing gate. Empirically the five EEG criteria are positively
associated, so the independence prediction is a slightly conservative approximation
(observed Jaccard tends to sit modestly above the factorized prediction; see validation
calibration slope < 1, intercept > 0). The theorem is a statement about the *composition
of marginals*, not an exact model of the dependent empirical gate.

### 10. Exact theorem vs empirical approximation
- **Exact (independence):** J_new ≤ J_old always; governed precisely by
  c·(P1+P2) ≤ P1·a+P2·b (identity match fraction 1.0 over 20000 random tuples).
- **Empirical (dependent criteria):** the factorized prediction closely tracks but does
  not equal the observed Jaccard; increases are possible only through dependence.

This is a **composition theorem / conjunctive-instability theorem** about **accepted-set
stability** under a **multiplicative stability law**. It is not claimed as a universal
biological law.
