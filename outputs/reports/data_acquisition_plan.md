# Data Acquisition Plan

Created: 2026-07-01T16:17:49.539465+00:00

Approved candidate datasets are listed in `data/manifests/candidate_datasets.csv`.

Acquisition sequence:

1. Verify public terms and license on the official source page.
2. Download only metadata or small file indexes first.
3. Estimate full size before any EEG download.
4. If full data are too large, download a documented representative subset only after license and size checks.
5. Inventory local files before any empirical analysis.

Current metadata status:

- Figshare metadata status: metadata_url_resolved_no_content; total size from available file metadata: not_estimated_no_file_index bytes; license field: must_verify_from_figshare_landing_page.
- OpenNeuro metadata pages: {'metadata_page_fetched': 4}.

Decision for this first pass:

No full EEG dataset was downloaded. This avoids large transfers before a clean size estimate and license verification are recorded.
