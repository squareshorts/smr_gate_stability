# Analysis dependency graph

```
raw EDF (data/raw/openneuro)               reusable feature cache
        |                                  (runtime_assurance_remediation/.../feature_cache)
        v                                          |
canonical per-window cache  <----------------------+
(baseline_gate_stability/checkpoints/features)
        |
        +--> 31-subset law study (conjunctive_gate_instability/)
        |         |
        |         +--> composition theorem (stage1) + validation/blinding (stage2)
        |         +--> cardinality / lattice / LODO / scorecard
        |
        +--> single-score remedy (conjunctive_law_remedy/)
        |         +--> calibration stability, transport, operational (stage3_6)
        |         +--> downstream decoder (stage6_downstream, reuses decoder features + folds)
        |         +--> 12-criterion scorecard (stage8_finalize)
        |
        +--> controlled degradation (conjunctive_gate_final/degradation)
                  (raw windows re-extracted, D0-D9 transforms, R0/R1/R2)
                  |
                  v
        figure_data (conjunctive_gate_final/figure_data) --> figures_r/*.R --> figures/*.{pdf,png}
                  |
                  v
        author_package (conjunctive_gate_final/author_package)
```

Downstream decoder reuses verified M0/M4 fold results; the law lattice, Potato, and broad decoder
study are NOT rerun.
