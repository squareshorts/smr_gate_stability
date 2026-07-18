# OpenNeuro selective-download preflight

Date: 2026-07-15. Local searches of `C:\work`, `C:\data`, `C:\datasets`, `C:\Users\mirro\Downloads`, and `C:\Users\mirro\Documents` found no local copy of ds004447, ds004444, ds004446, the canonical `nf_sqi_window_features.csv`, or an equivalent cache.

The official OpenNeuro GraphQL snapshot API was queried at the fixed `1.0.1` tags. The release's raw replay outputs identify the exact session sets needed for count reproduction: first/last available session for all 22 ds004447 participants (44 EDFs), first/last available session for all 30 ds004444 participants (60 EDFs), and the released five-participant ds004446 subset (`sub-004`, `sub-005`, `sub-012`, `sub-013`, `sub-018`; sessions `ses-01` and `ses-08`; 10 EDFs).

| Dataset | EDFs | Required download | Selective size (GiB) |
|---|---:|---:|---:|
| ds004447 | 44 | EDFs plus event/channel/electrode/EEG sidecars and top-level metadata | 1.870 |
| ds004444 | 60 | EDFs plus event/channel/electrode/EEG sidecars and top-level metadata | 6.260 |
| ds004446 | 10 | EDFs plus event/channel/electrode/EEG sidecars and top-level metadata | 0.998 |
| Total | 114 | Exact selective input set | 9.128 |

Available space on `C:` before acquisition: 85.613 GiB. The selective download is therefore permitted; raw data will be written only under the already ignored `data/raw/openneuro/` tree. Full snapshot manifests will be stored under the also ignored `data/manifests/` tree so the released dataset helper can resolve them without committing machine-local inputs.
