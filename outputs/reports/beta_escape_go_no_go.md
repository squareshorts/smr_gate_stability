# Go / No-Go

1. Was a larger dataset obtained?
   - True. `ds004447` contributed 22 early/late task contrasts.

2. Is there empirical evidence that dwell-time/escape metrics outperform mean high-beta power?
   - Mixed. Directional dwell/persistence improvement: True. Mean power decrease: True. Discordance present: True. Strong survival/hazard inferential support: False (Cox p=0.81574, dwell sign-flip p=0.521974, best tail p=0.285636).

3. Is there evidence that SMR acquisition and beta escape are separable?
   - True.

4. Do results survive broadband/artifact controls?
   - True. See `beta_escape_broadband_controls.csv` and `beta_escape_spectral_slope_controls.csv`.

5. Are results robust across definitions?
   - True. See `beta_escape_definition_robustness.csv`.

6. Are results driven by one subject or dataset?
   - Single-subject risk flag: False. Only one larger dataset was analyzed in this run.

7. Is the manuscript viable as a conceptually novel empirical paper with mathematical support?
   - Viability is conditional. The larger dataset supports feasibility, discordance, and separability tests, but the primary survival/hazard evidence is mixed rather than strong.

8. Should the manuscript proceed, require more data, or stop?
   - Conditional go: promising empirical support but needs cautious framing.

Final label: Conditional go: promising empirical support but needs cautious framing.
