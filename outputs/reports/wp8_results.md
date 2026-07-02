# WP8 Results: Empirical Anchoring in Real SMR-BCI EEG

Dataset analyzed: `ds004446` OpenNeuro high-density SMR-BCI subset.

Scope:

- Real EDF files were downloaded, inventoried, loaded, and analyzed.
- Subset: 5 subjects, sessions `ses-01;ses-08`, condition labels `interval;rest;task`.
- Sensorimotor channels: `E36;E104;E128` based on the official helper code identifying `[36,104,128]` as C3/C4/Cz.
- Results are descriptive empirical anchoring, not proof of mechanism.

Primary rest-condition pre/post changes:

- SMR power fractional change: -0.006.
- High-beta power fractional change: 0.052.
- Broadband non-target power fractional change: 0.266.
- Beta-burst rate fractional change: -0.079.
- Beta-burst duration fractional change: 0.056.

Regime classification:

- Inside validity-regime count: 5.
- Outside validity-regime count: 0.
- Signature-supported subjects: 0 / 5.
- Empirical interpretation label: non-support for the full joint signature.

Interpretation:

This subset provides a proof-of-pipeline empirical anchor. It does not provide strong empirical support for the predicted joint signature because mean high-beta power did not decrease, although beta-burst rate decreased and SMR power was approximately unchanged. No universal or mechanistic claim is made from this five-subject subset.
