# Data Acquisition Plan

Created: 2026-07-02T12:33:13.451129+00:00

Local data status:

- The pre-download local inventory showed `ds004446` as the only usable raw OpenNeuro EEG dataset if `ds004447` was not already present.
- The previous local subset is not sufficient for a conceptually novel empirical validation because it contains fewer than 20 subjects.

Candidate decision:

- OpenNeuro `ds004447` was selected because it is a sibling BMI-HDEEG SMR-BCI dataset with 22 indexed subjects and up to 20 sessions.
- Official metadata/index fields record public access and `CC0` license for `ds004447`.
- Full snapshot size is 22.254 GB. The controlled subset selects first and last available sessions for every subject, estimated at 2.008 GB.
- The selected subset meets the minimum target of at least 20 subjects and preserves early/late longitudinal contrast.

Download rule:

- Download full EEG only if feasible; otherwise use the predeclared first/last-session subset.
- For this run, the subset is feasible and was selected.
- Proceed with download: `True`.

Non-selected candidates:

- `ds004446` already existed locally but was too small in its local subset.
- `ds004444` and `ds004448` are larger full snapshots; they remain backup candidates.
- The Figshare/Scientific Data longitudinal dataset was not selected because a feasible CC0 OpenNeuro subset with 22 subjects was available and local file-index/license metadata for Figshare were not verified here.
