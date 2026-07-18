# Theorem statement

Two independent baseline calibration replicates evaluate a conjunctive gate on task windows.
P1=P(G1=1), P2=P(G2=1), Q=P(G1=1 and G2=1). Accepted-set Jaccard J_old = Q/(P1+P2-Q).
Add one criterion with replicate pass probabilities a, b and joint c; under independence between the
new criterion and the existing gate, J_new = Qc/(P1a+P2b-Qc).

Composition theorem: with Q>0 and positive denominators,
  J_new <= J_old  iff  c(P1+P2) <= P1a + P2b  iff  P1(a-c) + P2(b-c) >= 0.

Assumptions: independence of the added criterion and the gate; accepted-set Jaccard between
replicates is the target.
Exact inequality: as above.
Equality condition: a=c and b=c (added criterion perfectly reproducible).
Symmetric corollary (a=b=p): condition reduces to c<=p; since c<=min(a,b) always, Jaccard is
monotonically non-increasing under independence.
Dependence limitation: the closed form is exact only under independence; with positively dependent
criteria the factorized prediction is a conservative approximation, and an empirical increase can
occur only through dependence.
Extension to K criteria: J_S = prod(q_j)/(prod(p_j1)+prod(p_j2)-prod(q_j)); the one-step condition
applies recursively; predicted Jaccard decays multiplicatively as prod(r_j), r_j=q_j/max(p_j1,p_j2).
