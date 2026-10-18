# Benchmark-session phase-geometry audit

## Stop-rule result

This document reports the numerical Benchmark-session results before any manuscript edit. No resting-state analysis, resting-state result table, or manuscript file was modified.

**Classification: no detectable Benchmark-session phase-geometry difference.**

**The prespecified early-session Gini contrast was large but did not reach significance under exact participant-level randomization inference.**

The single primary endpoint was the trained-minus-control difference in participant-level slopes of Gini phase sensitivity over the identical first 15 minutes. The estimate was -0.00195891 per minute (95% participant-bootstrap CI [-0.00673369, 0.00211388]); exact two-sided p = 0.420202 from all 495 allocations.

## 1. Data and provenance audit

- Ingested archive `Benchmark_Treinado.zip`: SHA256 E2ED5749B90E29CCA0E3DE9B8288342C95CD1B56E0EAC3946E50BD588C46C81C.
- Ingested archive `Benchmark_controle.zip`: SHA256 2E875ADDCDC4757F9423879746E92B70EC2E6573ED11B61C81FBD8DF297CA17D.
- Inventory: 8 trained and 5 control EDFs; all are 300 Hz with C3 and C4 available.
- The Trigger channel is identically zero in every EDF and no EDF contains annotations.
- DMS is 3.075 minutes and is excluded from all participant-slope trajectory inference. The other 12 recordings meet the 15-minute primary threshold (trained n=8, control n=4).

### Meaning of `Benchmark`, `Benchmark1`, and `Bench_OA`

The exact meaning remains unresolved. The legacy repository at `C:/Users/mirro/nf_reanalysis` contains no occurrence of any of the three labels. The official BrainAvatar 2.2 manual also contains no occurrence of those strings. It documents that changing the software's recording-condition control creates a new EDF, but it does not map these study-specific filename tokens to a session type or establish that feedback was active. Accordingly, this analysis uses the neutral term **benchmark-session recordings**.

Official manual consulted: https://brainmaster.com/wp-content/uploads/2023/07/531-322_BrainAvatarUserManual_v2.2_1-23-23.pdf

### Trained identity mapping for exploratory transfer analysis

`ScoresBrainAvatar.xlsx` contains the complete trained roster ARN, RCB, FFS, JDS, EFS, JBS, IBJ, JAM aligned to experimental subjects 1-8. Seven initials map exactly. Benchmark `IBJ` to resting `IBP` is recorded as `inferred_high_confidence`, not documentary certainty: it is the unique unmatched trained-cohort pair and the age is identical. The main transfer analysis includes all eight; a prespecified sensitivity excludes IBJ/IBP. JBS remains included because legacy MAT files independently demonstrate that age 48 versus 50 is an existing metadata inconsistency for the same participant.

## 2. Frozen preprocessing and time coordinates

The validated pipeline was reused: channel-role classification and robust channel QC from `scripts/02_preprocess_eeg.py`; 500-uV jump annotations; 0.5-45 Hz analysis filtering; extended-Infomax ICA fit to the 1-100 Hz, 60-Hz-notched, average-referenced copy with random state 97; automatic exclusion only when summed artifact probability was at least 0.90 and brain probability at most 0.05; bad-channel interpolation; and scalp average reference with mastoids excluded. Artifact intervals remain annotations on the original elapsed timeline; they are not concatenated away.

| Group   |   Recordings |   Median duration (min) |   Minimum duration (min) |   Median continuous retention (%) |   ICA components excluded |
|:--------|-------------:|------------------------:|-------------------------:|----------------------------------:|--------------------------:|
| control |            5 |                 60.1    |                   3.075  |                           99.9731 |                         8 |
| trained |            8 |                 60.1833 |                  19.4417 |                           99.923  |                        10 |

Two-second epochs with 50% overlap were aligned to continuous elapsed time inside fixed 3-minute windows. Epochs overlapping annotations or exceeding the frozen 150-uV peak-to-peak/0.01-uV flat criteria were excluded. The first and last 10 seconds of each physical recording were guarded against filter-edge effects.

Across 212 unique physical windows, 14 had no valid strict 12-15 Hz mode after frozen QC and were retained as missing rather than imputed (ARN: 7, JBS: 7). In the primary interval, the JBS 12-15-minute window had no retained epochs; JBS therefore contributed four valid window estimates, while the other 11 participants contributed five. Every participant-level slope remained estimable.

## 3. Frozen phase geometry

The real-data choices were not retuned: sfreq 300 Hz; 12-15 Hz Koopman mode; tau=10 samples; m=5; local gradient k=10. Window descriptors are means across retained 2-second epochs. The phase-coherence radius is the validated `rc_norm_95` implementation (high-gradient threshold 3x the median gradient). The decay metric is called **DMD modal decay per cycle** throughout; no Floquet or transverse-contraction interpretation is used.

## 4. Primary first-15-minute inference

Each participant contributed one OLS slope across up to five fixed 3-minute windows. Participants, not windows, formed the exact allocation distribution.

| Endpoint                                    |   n trained |   n control |   Trained mean slope/min |   Trained median slope/min |   Control mean slope/min |   Control median slope/min |   Difference |   95% CI low |   95% CI high |   Hedges g |   g 95% CI low |   g 95% CI high |   Exact p | Holm p (secondary only)   |
|:--------------------------------------------|------------:|------------:|-------------------------:|---------------------------:|-------------------------:|---------------------------:|-------------:|-------------:|--------------:|-----------:|---------------:|----------------:|----------:|:--------------------------|
| Gini of phase sensitivity G(|grad phi_hat|) |           8 |           4 |             -0.000120429 |               -0.000121573 |               0.00183848 |                0.000628862 |  -0.00195891 |  -0.00673369 |    0.00211388 |  -0.471244 |      -1.80902  |        0.795113 | 0.420202  | NA                        |
| Phase-coherence radius r_c/D                |           8 |           4 |              0.000433151 |                0.00179809  |              -0.00370204 |               -0.00172242  |   0.00413519 |  -0.00100821 |    0.00964635 |   0.712747 |      -0.180669 |        2.56409  | 0.242424  | 0.242424                  |
| DMD modal decay per cycle                   |           8 |           4 |             -0.00273473  |               -0.00311826  |               0.0056053  |                0.00458599  |  -0.00834004 |  -0.014011   |   -0.00289304 |  -1.5539   |      -3.50871  |       -0.688507 | 0.0161616 | 0.0323232                 |

### Window-level participant-fixed-effect sensitivity

The first-15-minute window values were also fit with participant fixed effects, elapsed time, and the group-by-elapsed-time interaction. Participant identity absorbed subject intercepts; group labels were permuted only at the participant level and the model was refit for all 495 allocations. This did not replace the primary subject-slope analysis.

| Statistic                                                |   Window observations |   Coefficient/min |   Exact p |   Allocations |
|:---------------------------------------------------------|----------------------:|------------------:|----------:|--------------:|
| group x elapsed_time coefficient (trained minus control) |                    59 |       -0.00228952 |  0.355556 |           495 |

## 5. Duration sensitivity for the primary descriptor

No phase, embedding, QC, or window parameter changed. The approximately full-duration subset is the natural 60-minute cluster (trained n=6, control n=3), analyzed over the common first 60 minutes.

| Analysis                        |   n trained |   n control |   Trained mean slope/min |   Control mean slope/min |   Difference |   95% CI low |   95% CI high |   Exact p |   Allocations |
|:--------------------------------|------------:|------------:|-------------------------:|-------------------------:|-------------:|-------------:|--------------:|----------:|--------------:|
| all_available_ge15_min          |           8 |           4 |             -3.01618e-05 |              0.000480328 | -0.00051049  |  -0.00120611 |   9.51592e-05 |  0.167677 |           495 |
| common_first_30_min             |           7 |           4 |              0.00088867  |              0.00138451  | -0.000495836 |  -0.00190437 |   0.000768474 |  0.49697  |           330 |
| common_first_45_min             |           7 |           3 |              0.000438859 |              0.000844938 | -0.000406079 |  -0.00169728 |   0.000768942 |  0.608333 |           120 |
| common_first_60_min_approx_full |           6 |           3 |              1.99147e-05 |              0.000581754 | -0.000561839 |  -0.00141919 |   0.000224208 |  0.25     |            84 |

The sensitivity differences had the primary direction in 4 of 4 prespecified analyses and ranged from -0.000561839 to -0.000406079 per minute. Direction was stable, but magnitude was not: the absolute sensitivity estimates were only 20.73% to 28.68% of the primary 15-minute estimate.

The inference CSV contains the identically specified secondary-metric sensitivities and their within-set two-endpoint Holm adjustments. Phase-coherence radius r_c/D preserved its primary direction in 3/4 sensitivities; DMD modal decay per cycle preserved its primary direction in 0/4 sensitivities.

## 6. Protocol-concordance manipulation checks (first 15 minutes)

| Check                                    |   Trained mean slope/min |   Control mean slope/min |   Difference |   95% CI low |   95% CI high |   Exact p |
|:-----------------------------------------|-------------------------:|-------------------------:|-------------:|-------------:|--------------:|----------:|
| C3 SMR 12-15 Hz log10 power (uV^2)       |             -0.000517725 |               0.00285217 |  -0.00336989 |  -0.0105073  |    0.00233743 |  0.345455 |
| C3 high-beta 20-30 Hz log10 power (uV^2) |             -0.00438307  |              -0.00110306 |  -0.00328001 |  -0.00969375 |    0.00269358 |  0.490909 |

These checks are C3 SMR 12-15 Hz and C3 high-beta 20-30 Hz only; they are not a discovery family.

## 7. Exploratory acute-versus-transfer analysis

| Analysis                  | Resting transfer target                    |   n |   Spearman rho |   95% bootstrap CI low |   95% bootstrap CI high |   Exact p |   Holm p |   Permutations |
|:--------------------------|:-------------------------------------------|----:|---------------:|-----------------------:|------------------------:|----------:|---------:|---------------:|
| all_8_trained             | Resting pre-post C3 SMR log10 power change |   8 |     -0.47619   |              -1        |                0.4      |  0.243056 | 0.486111 |          40320 |
| all_8_trained             | Resting pre-post validated PAC change      |   8 |     -0.0952381 |              -0.822785 |                0.684211 |  0.840129 | 0.840129 |          40320 |
| exclude_ibj_ibp_crosswalk | Resting pre-post C3 SMR log10 power change |   7 |     -0.357143  |              -1        |                0.764706 |  0.444444 | 0.888889 |           5040 |
| exclude_ibj_ibp_crosswalk | Resting pre-post validated PAC change      |   7 |     -0.142857  |              -0.944444 |                0.653846 |  0.78254  | 0.888889 |           5040 |

The main exact Spearman tests enumerate all 8! = 40,320 permutations; the crosswalk sensitivity enumerates all 7! = 5,040 permutations. These tests are exploratory. They address whether within-session Gini reorganization covaries with durable resting C3 SMR or validated PAC change; they do not establish that the benchmark-session recordings contained active feedback.

For all eight trained participants, the inverse Gini-PAC association had raw exact p=0.840129 and Holm p=0.840129 across the two prespecified transfer outcomes. It therefore did not survive the two-test multiplicity correction.

Excluding IBJ/IBP did not materially change the PAC conclusion: rho changed from -0.0952381 (exact p=0.840129) to -0.142857 (exact p=0.78254).

### Leave-one-participant-out Gini-PAC diagnostic

| Participant omitted   |   n |   Spearman rho |   Raw exact p |   Permutations |
|:----------------------|----:|---------------:|--------------:|---------------:|
| ARN                   |   7 |     -0.321429  |      0.497619 |           5040 |
| EFS                   |   7 |     -0.0357143 |      0.963492 |           5040 |
| FFS                   |   7 |     -0.0714286 |      0.906349 |           5040 |
| IBJ/IBP               |   7 |     -0.142857  |      0.78254  |           5040 |
| JAM                   |   7 |      0.0714286 |      0.906349 |           5040 |
| JBS                   |   7 |      0.0357143 |      0.963492 |           5040 |
| JDS                   |   7 |      0.0714286 |      0.906349 |           5040 |
| RCB                   |   7 |     -0.357143  |      0.444444 |           5040 |

All eight Gini-PAC leave-one-out estimates were negative, ranging from -0.357143 to 0.0714286. No single participant was necessary for the negative direction, although raw exact p-values varied across omissions.

### Leave-one-participant-out Gini-SMR diagnostic

| Participant omitted   |   n |   Spearman rho |   Raw exact p |   Permutations |
|:----------------------|----:|---------------:|--------------:|---------------:|
| ARN                   |   7 |      -0.357143 |      0.444444 |           5040 |
| EFS                   |   7 |      -0.571429 |      0.2      |           5040 |
| FFS                   |   7 |      -0.642857 |      0.138889 |           5040 |
| IBJ/IBP               |   7 |      -0.357143 |      0.444444 |           5040 |
| JAM                   |   7 |      -0.678571 |      0.109524 |           5040 |
| JBS                   |   7 |      -0.214286 |      0.661508 |           5040 |
| JDS                   |   7 |      -0.5      |      0.266667 |           5040 |
| RCB                   |   7 |      -0.428571 |      0.353571 |           5040 |

The Gini-SMR leave-one-out rho range was -0.678571 to -0.214286; all raw exact p-values exceeded 0.05.

## 8. Output map and locked confirmation rule

- `results/tables/benchmark_inventory.csv`: archive/EDF provenance, duration, channels, trigger/annotation audit, identity mapping, and preprocessing QC.
- `results/tables/benchmark_phase_geometry_trajectories.csv`: window values plus the participant slope repeated within each prespecified analysis set.
- `results/tables/benchmark_phase_geometry_inference.csv`: primary, secondary, duration/manipulation inference, plus the fixed-effect sensitivity row.
- `results/tables/benchmark_rest_transfer.csv`: two-outcome Holm correction, crosswalk sensitivity, and leave-one-participant-out diagnostics.
- `docs/benchmark_phase_geometry_manuscript_ready_results.md`: manuscript-ready numerical results text; no manuscript file was edited.
- `results/figures/benchmark_*_timecourses.png`: individual and group time courses for the five requested measures.

If missing control EDFs are recovered, rerun this identical script without changing parameters or windows as a locked-method confirmation.

No entropy, connectivity, classifier, extra band, or additional nonlinear descriptor was computed.
