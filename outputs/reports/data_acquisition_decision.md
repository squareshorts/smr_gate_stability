# Data Acquisition Decision

Created: 2026-07-01T17:06:00.854349+00:00

Selected first dataset: `ds004446` (`The BMI-HDEEG dataset 2`, OpenNeuro snapshot `1.0.1`).

Why selected:

- It is part of the 2023 Scientific Data high-density SMR-BCI/neurofeedback collection.
- The official OpenNeuro metadata reports `CC0` license and public access.
- It is smaller than several sibling high-density snapshots but still has 30 subjects and 8-session structure for most subjects.
- A five-subject pre/post subset is sufficient for proof-of-pipeline empirical anchoring while avoiding a 31 GB full download.

Expected size:

- Full snapshot estimate: 31.383 GB.
- Selected subset estimate: 1.071 GB (1071128672 bytes).

License/terms status:

- OpenNeuro `dataset_description.json` license field: `CC0`.
- Terms decision: `acceptable_for_secondary_analysis`.

Download decision:

- Full download will not be used in this pass.
- Subset download will be used: subjects `sub-013,sub-018,sub-004,sub-005,sub-012`, sessions `ses-01,ses-08`.
- Proceed with EEG download: `True`.

Exact API/command used:

- Metadata and file URLs are obtained with `POST https://openneuro.org/crn/graphql` using the `snapshot(datasetId, tag) { files(recursive: true) { filename size annexed urls } }` query.
- Files are downloaded with HTTPS `GET` from the official `DatasetFile.urls[0]` values returned by OpenNeuro.
- Local command: `python empirical\wp7_dataset_plan_inventory.py --download`.

Priority-2 dataset status:

- The 2021 longitudinal SMR-BCI figshare DOI was resolved, but file-size and license metadata were not exposed through the attempted official endpoint in this environment. It was therefore not downloaded.
