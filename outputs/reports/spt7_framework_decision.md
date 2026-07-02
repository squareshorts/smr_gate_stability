# SPT7: Stuart-Landau vs Singular Perturbation Framework Decision

## Comparison summary

Criteria evaluated: 8
- SPT/fast-slow wins: 6
- Stuart-Landau wins: 1
- Draw: 1

## Criterion-by-criterion comparison

### Matches empirical mixed result (no joint signature)

**Stuart-Landau:** Weak: SL requires near-criticality regime with specific coupling. Mixed empirical result (SMR ~unchanged, beta increased) falls outside the joint-signature regime in most simulations.

**SPT/Fast-slow:** Better: SPT predicts that high-beta stabilization and SMR acquisition are independent processes. The observed mixed result (quadrant D or C) is a natural outcome when alpha_x is low, not a model failure.

**Assessment:** SPT  
**Notes:** WP8 showed 0/5 joint-signature subjects; SPT predicts separability explicitly.

---

### Supports non-diagnostic interpretation of high-beta suppression

**Stuart-Landau:** Weak: in SL, beta suppression emerges from the same oscillator dynamics that produce SMR changes, making separation between the two difficult to argue mechanistically.

**SPT/Fast-slow:** Strong: SPT explicitly separates high-beta (fast, stabilization variable) from SMR (slow, learning variable). High-beta suppression is a constraint, not a surrogate of learning. Non-diagnostic interpretation follows directly.

**Assessment:** SPT  
**Notes:** Central conceptual advantage of SPT framework.

---

### Clear testable predictions

**Stuart-Landau:** Moderate: SL predicts specific spectral signatures near bifurcation; hard to test without precise parameter estimation in vivo.

**SPT/Fast-slow:** Good: SPT predicts tau_beta << tau_SMR, four-quadrant separability, barrier violation -> instability. These are measurable in EEG data, though small sample size limits empirical verification.

**Assessment:** SPT  
**Notes:** SPT yields clearer empirically-testable predictions.

---

### Mechanistic richness / nonlinear detail

**Stuart-Landau:** Strong: SL provides a specific nonlinear oscillator mechanism, bifurcation structure, and analytic regime boundaries.

**SPT/Fast-slow:** Moderate: SPT provides a general separation-of-timescales argument without committing to a specific nonlinear oscillator. Less mechanistically specific, but more flexible.

**Assessment:** SL  
**Notes:** SL has richer mechanistic detail; SPT is more framework-level.

---

### Empirical support (ds004446, n=5)

**Stuart-Landau:** Unsupported: joint signature (SMR up + beta down) found in 0/5 subjects. SL-predicted regime not clearly observed.

**SPT/Fast-slow:** Partial: separability hypothesis consistent with mixed empirical result. No positive evidence of separability, but mixed result is not a failure of SPT as it would be for SL.

**Assessment:** SPT  
**Notes:** Neither framework is strongly supported; SPT is not falsified by mixed data.

---

### Simulation support for separability

**Stuart-Landau:** Partial: SL can show domains where beta suppression occurs without SMR acquisition, but the coupling structure makes full separability limited.

**SPT/Fast-slow:** Strong: SPT simulations directly demonstrate four separable regimes (both, acquisition only, stabilization only, neither). Separability is built into the model structure.

**Assessment:** SPT  
**Notes:** SPT1 simulations confirm four-regime separability.

---

### Validity domain requirements

**Stuart-Landau:** Specific: requires near-criticality, specific coupling strength, and feedback gain within narrow validity domain (WP1-WP6).

**SPT/Fast-slow:** General: valid when epsilon << 1 (tau_beta << tau_SMR). SPT2 shows validity for epsilon <= 0.03 in simulations. Whether real EEG satisfies this is uncertain (SPT4 weak/partial support).

**Assessment:** Draw  
**Notes:** Both require specific conditions; SPT conditions are simpler to state.

---

### Conservative causal claims

**Stuart-Landau:** Risk: SL can be interpreted as implying that beta suppression causes or is causally linked to SMR changes through the oscillator mechanism.

**SPT/Fast-slow:** Safe: SPT explicitly models high-beta as a constraint variable, not a target-learning variable. Framework explicitly prohibits causal claims about beta suppression -> SMR acquisition.

**Assessment:** SPT  
**Notes:** SPT is safer for conservative framing consistent with editorial requirements.

---


## Framework decision

### Recommendation: DEMOTE Stuart-Landau to supplementary material.

Rationale:

1. The singular perturbation / fast-slow barrier framework is conceptually better
   aligned with the core hypothesis: high-beta suppression as a stabilization
   constraint, not a target-learning surrogate.

2. Stuart-Landau provides mechanistic detail but this detail is not supported
   by the empirical data (0/5 subjects showed the joint signature) and requires
   unrealistically specific parameter assumptions.

3. Stuart-Landau adds interpretive risk: the coupling structure in SL makes it
   harder to argue that high-beta suppression and SMR acquisition are independent,
   which is the central scientific claim.

4. The SPT framework does not replace Stuart-Landau as a dynamic systems model;
   rather, it provides a higher-level framework within which SL could be seen as
   one specific nonlinear mechanism. Stuart-Landau can be mentioned as a concrete
   example of a fast-slow oscillator system in a supplementary section.

5. The fast-slow framework yields clearer testable predictions (tau_ratio,
   four-quadrant separability, barrier violation prediction) even if current
   empirical support is only partial.

### What to retain from Stuart-Landau analysis

- The finding that beta suppression can occur in generic feedback models without
  mechanistic specificity supports the SPT framing.
- The validity-domain analysis (WP1-WP6) demonstrated that the full SMR-beta
  joint signature is not universally generated by oscillator dynamics, which
  is consistent with the SPT separability argument.
- Stuart-Landau can be cited as showing that the problem is not specific to
  any one dynamical mechanism, motivating the more general SPT framework.

### What NOT to carry forward

- Claims that Stuart-Landau is the primary mechanistic model for SMR neurofeedback.
- Regime-specific SL predictions as the main analytic framework.
- The near-criticality interpretation as necessary for high-beta suppression.

Generated: 2026-07-01T18:12:19.132612+00:00
