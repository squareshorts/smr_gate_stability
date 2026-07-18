# Data inventory and reconciliation gate

The exact OpenNeuro `1.0.1` snapshots were selectively acquired into the ignored `data/raw/openneuro/` tree. Their full fixed-snapshot indexes are in ignored `data/manifests/`. No raw EEG is tracked by Git.

| Dataset | EDFs | event sidecars | selected files | size (GiB) | count reproduction |
|---|---:|---:|---:|---:|---|
| ds004447 | 44 | 44 | 225 | 1.870 | PASS |
| ds004444 | 60 | 60 | 307 | 6.260 | PASS |
| ds004446 | 10 | 10 | 57 | 0.998 | PASS |

The selection matches the released replay tables: all first/last sessions for ds004447 and ds004444; the release-defined five-subject, ten-session ds004446 subset. The canonical feature function was applied in memory by the isolated wrapper, so no untracked multi-gigabyte feature cache was created. See `data_acquisition_manifest.csv`, `canonical_pipeline_map.md`, and `count_reproduction.csv`.
