# Audit 2: Decomposition Validity

1. **Is the conclusion that occupancy/dwell drives mean power partly algebraic?** Mean power is mathematically the integral of (amplitude^2 * time). If amplitude is constant, occupancy drives power. 
2. **Does the decomposition distinguish amplitude within S1 from time spent in S1?** Yes, via `high_beta_power_trimmed95` vs `beta_state_occupancy`.
3. **Are dwell time, occupancy, entry rate, escape rate, and re-entry probability independently informative?** The previous analysis showed that `high_beta_power_trimmed95` had the highest marginal R2 (0.47), heavily contradicting the claim that 'suppression is primarily driven by state occupancy'.
4. **Does decomposition support mechanism or only measurement non-identifiability?** It primarily demonstrates non-identifiability: mean power conflates amplitude and occupancy, but amplitude remains the dominant empirical driver in this dataset.
5. **What wording is justified?** We can only claim that persistence metrics provide separable information, but we *cannot* claim that high-beta suppression is entirely or primarily a change in state dwell time. Amplitude reductions are a major factor.
