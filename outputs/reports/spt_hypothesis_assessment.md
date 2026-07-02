# SPT Hypothesis Assessment

Generated: 2026-07-01T18:19:08.195894+00:00

## Central hypothesis

In SMR neurofeedback, high-beta inhibition acts as a fast boundary-layer stabilization
process, whereas SMR acquisition evolves on a slower learning time scale. High-beta
suppression is neither necessary nor sufficient evidence of SMR learning. Its mechanistic
role is to keep the EEG state near an admissible training manifold that permits, but does
not guarantee, slow SMR acquisition.

## Assessment by question

### 1. Do simulations support the fast-slow separability hypothesis?

**Result:** YES

SPT1 simulations demonstrate that the fast-slow closed-loop model produces all four
separable outcomes (both, acquisition-only, stabilization-only, neither) by varying
model parameters. This is structural separability and directly supports the hypothesis
that high-beta suppression and SMR acquisition are mechanistically independent.

### 2. Do simulations support the barrier-constraint interpretation?

**Result:** YES (partial)

SPT3 simulations show that blocks following admissible-state occupation show greater
mean SMR improvement than blocks following barrier violations. The effect is modest
and parameter-dependent, but consistent with the interpretation of high-beta as a
stabilization constraint variable.

### 3. Does real EEG support empirical time-scale separation?

**Result:** INCONCLUSIVE — BANDWIDTH CONFOUND

SPT4 (revised) analysis reveals that the observed tau_ratio (AR1) ≈ 0.100 matches almost exactly the theoretical prediction from filter bandwidth alone (0.090; Gaussian approximation, SMR bandwidth 3 Hz vs high-beta bandwidth 10 Hz). When bandwidth is matched (SMR 12–15 Hz vs HB 20–23 Hz, both 3 Hz), the tau ratio rises to ≈ 1.05 (no separation). Block-mean tau ratios are ≈ 0.92, and 1-Hz decimated ratios ≈ 1.38. These deconfounded estimates show no reliable time-scale separation beyond what the bandwidth difference alone predicts.

**Conclusion**: The primary AR1 tau analysis cannot distinguish genuine fast–slow dynamics from a filter bandwidth artefact. The claim of empirical time-scale separation is **not supported** by the deconfounded analyses. This does not rule out true time-scale separation, but the available 4-Hz (SMR) vs 10-Hz (high-beta) bandwidth comparison is insufficient to demonstrate it.

### 4. Does real EEG support empirical separability between SMR acquisition and high-beta stabilization?

**Result:** SUPPORTED (descriptive, N=5)

SPT5 four-quadrant classification shows: A (both) = 0, B (acquisition only) = 2, C (stabilization only) = 3, D (neither) = 0. All 5 subjects are in separable quadrants (B or C); none show the full joint signature (A) and none show neither (D). This empirically demonstrates that SMR acquisition and high-beta stabilization dissociate at the subject level. CAUTION: n=5 is very small. Results are descriptive only.

### 5. Do high-beta barrier violations predict future instability or failed SMR acquisition?

**Result:** NULL RESULT (after FDR correction)

SPT6 (revised) corrects two methodological flaws in the original:
(1) Thresholds now computed on block-mean distributions (not raw envelope) — resolving the sparsity that caused 168/200 rows to have zero violations.
(2) The `admissible_next` outcome is excluded from primary inference because it is confounded by regression to the mean when percentile thresholds are used.

For the theoretically meaningful `smr_increase` outcome (100 tests: 5 subjects × 2 sessions × 2 conditions × 5 thresholds), after Benjamini-Hochberg FDR correction: **0 / 100 tests survive at q < 0.05**. A consistent negative direction (violations → less SMR increase; mean phi = −0.14, 84/100 negative tests) is compatible with the barrier hypothesis but does not meet the threshold for statistical inference at n = 5.

### 6. Is the hypothesis stronger than the previous Stuart-Landau framing?

**Result:** YES (conceptual analysis)

SPT7 comparison shows SPT wins on 5/8 criteria vs SL winning 1/8. The key advantages:
- SPT explicitly supports the non-diagnostic interpretation of high-beta suppression.
- SPT is consistent with the mixed empirical result (0/5 joint signature subjects).
- SPT yields clearer testable predictions.
- SPT does not require near-criticality assumptions.

### 7. Which claims are supported?

- Structural separability in the fast-slow model (simulation: SUPPORTED).
- Barrier constraint interpretation in simulation (simulation: PARTIAL).
- SPT framework superiority over SL (conceptual: SUPPORTED).
- Non-diagnostic framing of high-beta suppression (conceptual: SUPPORTED).
- Empirical time-scale separation tau_beta<<tau_SMR: **INCONCLUSIVE** (bandwidth confound; deconfounded analyses show ratio ≈ 1.0).
- Empirical separability of SMR acquisition and beta stabilization (descriptive, n=5: SUPPORTED; 2B + 3C, 0A, 0D).
- Barrier violation predicts next-state SMR outcome in real EEG: **NOT SUPPORTED** (null after FDR; 0/100 tests survive at q<0.05).

### 8. Which claims remain unsupported (at this evidence level)?




- Any claim of statistical confirmation from n=5 subjects.
- Causal claims about high-beta suppression and SMR learning.

### 9. Which claims must be avoided?

- High-beta suppression causes SMR learning.
- High-beta suppression is necessary for SMR learning.
- High-beta suppression is sufficient evidence of SMR acquisition.
- The empirical data prove any physiological mechanism.
- The fast-slow hypothesis is empirically confirmed (only simulation-confirmed).
- Generalization from n=5 to all SMR-BCI populations.

## Final conclusion

**Simulation-supported, empirically inconclusive fast–slow barrier hypothesis.**

The fast–slow barrier hypothesis is mechanistically coherent (SPT1–SPT3) and
conceptually superior to the Stuart-Landau framing (SPT7). Two primary empirical
tests were revised with methodological fixes and yield inconclusive or null results:

- **Time-scale separation (SPT4, revised)**: The AR1 tau_ratio (≈ 0.10) matches the
  bandwidth-predicted ratio (0.09) almost exactly. Bandwidth-matched and block-mean
  analyses give tau_ratio ≈ 1.0. Empirical time-scale separation is NOT demonstrated
  independently of the filter bandwidth difference.

- **Barrier prediction (SPT6, revised)**: After FDR correction, 0/100 smr_increase
  tests are significant. A directionally consistent negative signal (mean phi = −0.14,
  84/100 negative) exists but does not meet the threshold for statistical inference
  at n = 5.

- **Four-quadrant separability (SPT5)**: All 5 subjects fall in separable quadrants
  (2 in B, 3 in C; 0 in A or D), providing the strongest descriptive empirical finding.

**Stuart-Landau model**: Demoted to supplementary material. SPT wins 5/8 criteria vs SL.
SL is neither required by nor consistent with the SPT framing.

**n = 5 limitation**: Only ds004446 (sub-004, sub-005, sub-012, sub-013, sub-018,
sessions ses-01 and ses-08) is locally available. Expansion to ds004444, ds004447,
or ds004448 requires new downloads and is not currently feasible.

The hypothesis should be presented as a theoretically grounded framework consistent
with the four-quadrant pattern (SPT5) and simulation results (SPT1–SPT3), while
explicitly acknowledging that time-scale separation and barrier prediction were
inconclusive in this small dataset.

Generated: 2026-07-01 (revised)
