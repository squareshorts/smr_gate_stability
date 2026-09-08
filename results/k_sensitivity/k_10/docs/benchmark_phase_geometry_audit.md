# Benchmark-session phase-geometry audit

## Stop-rule result

This document reports the numerical Benchmark-session results before any manuscript edit. No resting-state analysis, resting-state result table, or manuscript file was modified.

**Classification: participant-sensitive/exploratory signal.**

**The prespecified early-session Gini contrast was large but did not reach significance under exact participant-level randomization inference.**

The single primary endpoint was the trained-minus-control difference in participant-level slopes of Gini phase sensitivity over the identical first 15 minutes. The estimate was -0.00262553 per minute (95% participant-bootstrap CI [-0.00487054, -0.000397308]); exact two-sided p = 0.0707071 from all 495 allocations.

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
| Gini of phase sensitivity G(|grad phi_hat|) |           8 |           4 |              -0.00107305 |               -0.000884992 |               0.00155248 |                 0.00174944 |  -0.00262553 |  -0.00487054 |  -0.000397308 |   -1.16757 |      -3.00569  |       -0.241963 | 0.0707071 | NA                        |
| Phase-coherence radius r_c/D                |           8 |           4 |               0.00044473 |                0.00230248  |              -0.00286994 |                -0.00133799 |   0.00331467 |  -0.00177231 |   0.00868239  |    0.58697 |      -0.316052 |        2.52637  | 0.337374  | 0.337374                  |
| DMD modal decay per cycle                   |           8 |           4 |              -0.00273473 |               -0.00311826  |               0.0056053  |                 0.00458599 |  -0.00834004 |  -0.014011   |  -0.00289304  |   -1.5539  |      -3.50871  |       -0.688507 | 0.0161616 | 0.0323232                 |

### Window-level participant-fixed-effect sensitivity

The first-15-minute window values were also fit with participant fixed effects, elapsed time, and the group-by-elapsed-time interaction. Participant identity absorbed subject intercepts; group labels were permuted only at the participant level and the model was refit for all 495 allocations. This did not replace the primary subject-slope analysis.

| Statistic                                                |   Window observations |   Coefficient/min |   Exact p |   Allocations |
|:---------------------------------------------------------|----------------------:|------------------:|----------:|--------------:|
| group x elapsed_time coefficient (trained minus control) |                    59 |        -0.0026456 | 0.0828283 |           495 |

## 5. Duration sensitivity for the primary descriptor

No phase, embedding, QC, or window parameter changed. The approximately full-duration subset is the natural 60-minute cluster (trained n=6, control n=3), analyzed over the common first 60 minutes.

| Analysis                        |   n trained |   n control |   Trained mean slope/min |   Control mean slope/min |   Difference |   95% CI low |   95% CI high |   Exact p |   Allocations |
|:--------------------------------|------------:|------------:|-------------------------:|-------------------------:|-------------:|-------------:|--------------:|----------:|--------------:|
| all_available_ge15_min          |           8 |           4 |              0.000188931 |              0.000293278 | -0.000104347 | -0.000573722 |   0.000303484 |  0.684848 |           495 |
| common_first_30_min             |           7 |           4 |              8.26184e-05 |              0.00113253  | -0.00104991  | -0.00246732  |   0.000450503 |  0.30303  |           330 |
| common_first_45_min             |           7 |           3 |             -1.63617e-05 |              0.000686451 | -0.000702812 | -0.00144482  |  -6.07602e-05 |  0.166667 |           120 |
| common_first_60_min_approx_full |           6 |           3 |              0.000203405 |              0.000400454 | -0.000197049 | -0.000738783 |   0.0002719   |  0.52381  |            84 |

The sensitivity differences had the primary direction in 4 of 4 prespecified analyses and ranged from -0.00104991 to -0.000104347 per minute. Direction was stable, but magnitude was not: the absolute sensitivity estimates were only 3.974% to 39.99% of the primary 15-minute estimate.

The inference CSV contains the identically specified secondary-metric sensitivities and their within-set two-endpoint Holm adjustments. Phase-coherence radius r_c/D preserved its primary direction in 3/4 sensitivities; DMD modal decay per cycle preserved its primary direction in 0/4 sensitivities.

## 6. Protocol-concordance manipulation checks (first 15 minutes)

| Check                                    |   Trained mean slope/min |   Control mean slope/min |   Difference |   95% CI low |   95% CI high |   Exact p |
|:-----------------------------------------|-------------------------:|-------------------------:|-------------:|-------------:|--------------:|----------:|
| C3 SMR 12-15 Hz log10 power (uV^2)       |             -0.000517725 |               0.00285217 |  -0.00336989 |  -0.0105073  |    0.00233743 |  0.345455 |
| C3 high-beta 20-30 Hz log10 power (uV^2) |             -0.00438307  |              -0.00110306 |  -0.00328001 |  -0.00969375 |    0.00269358 |  0.490909 |

These checks are C3 SMR 12-15 Hz and C3 high-beta 20-30 Hz only; they are not a discovery family.

## 7. Exploratory acute-versus-transfer analysis

| Analysis                  | Resting transfer target                    |   n |   Spearman rho |   95% bootstrap CI low |   95% bootstrap CI high |   Exact p |    Holm p |   Permutations |
|:--------------------------|:-------------------------------------------|----:|---------------:|-----------------------:|------------------------:|----------:|----------:|---------------:|
| all_8_trained             | Resting pre-post C3 SMR log10 power change |   8 |       0.5      |              -0.493671 |               0.974684  |  0.216171 | 0.216171  |          40320 |
| all_8_trained             | Resting pre-post validated PAC change      |   8 |      -0.761905 |              -1        |              -0.0886076 |  0.036756 | 0.0735119 |          40320 |
| exclude_ibj_ibp_crosswalk | Resting pre-post C3 SMR log10 power change |   7 |       0.464286 |              -0.764706 |               1         |  0.302381 | 0.302381  |           5040 |
| exclude_ibj_ibp_crosswalk | Resting pre-post validated PAC change      |   7 |      -0.821429 |              -1        |              -0.0588235 |  0.034127 | 0.068254  |           5040 |

The main exact Spearman tests enumerate all 8! = 40,320 permutations; the crosswalk sensitivity enumerates all 7! = 5,040 permutations. These tests are exploratory. They address whether within-session Gini reorganization covaries with durable resting C3 SMR or validated PAC change; they do not establish that the benchmark-session recordings contained active feedback.

For all eight trained participants, the inverse Gini-PAC association had raw exact p=0.036756 and Holm p=0.0735119 across the two prespecified transfer outcomes. It therefore did not survive the two-test multiplicity correction.

Excluding IBJ/IBP did not materially change the PAC conclusion: rho changed from -0.761905 (exact p=0.036756) to -0.821429 (exact p=0.034127).

### Leave-one-participant-out Gini-PAC diagnostic

| Participant omitted   |   n |   Spearman rho |   Raw exact p |   Permutations |
|:----------------------|----:|---------------:|--------------:|---------------:|
| ARN                   |   7 |      -0.714286 |    0.0880952  |           5040 |
| EFS                   |   7 |      -0.928571 |    0.00674603 |           5040 |
| FFS                   |   7 |      -0.642857 |    0.138889   |           5040 |
| IBJ/IBP               |   7 |      -0.821429 |    0.034127   |           5040 |
| JAM                   |   7 |      -0.821429 |    0.034127   |           5040 |
| JBS                   |   7 |      -0.714286 |    0.0880952  |           5040 |
| JDS                   |   7 |      -0.75     |    0.0662698  |           5040 |
| RCB                   |   7 |      -0.642857 |    0.138889   |           5040 |

All eight Gini-PAC leave-one-out estimates were negative, ranging from -0.928571 to -0.642857. No single participant was necessary for the negative direction, although raw exact p-values varied across omissions.

### Leave-one-participant-out Gini-SMR diagnostic

| Participant omitted   |   n |   Spearman rho |   Raw exact p |   Permutations |
|:----------------------|----:|---------------:|--------------:|---------------:|
| ARN                   |   7 |       0.464286 |      0.302381 |           5040 |
| EFS                   |   7 |       0.678571 |      0.109524 |           5040 |
| FFS                   |   7 |       0.25     |      0.594841 |           5040 |
| IBJ/IBP               |   7 |       0.464286 |      0.302381 |           5040 |
| JAM                   |   7 |       0.571429 |      0.2      |           5040 |
| JBS                   |   7 |       0.678571 |      0.109524 |           5040 |
| JDS                   |   7 |       0.571429 |      0.2      |           5040 |
| RCB                   |   7 |       0.25     |      0.594841 |           5040 |

The Gini-SMR leave-one-out rho range was 0.25 to 0.678571; all raw exact p-values exceeded 0.05.

## 8. Output map and locked confirmation rule

- `results/tables/benchmark_inventory.csv`: archive/EDF provenance, duration, channels, trigger/annotation audit, identity mapping, and preprocessing QC.
- `results/tables/benchmark_phase_geometry_trajectories.csv`: window values plus the participant slope repeated within each prespecified analysis set.
- `results/tables/benchmark_phase_geometry_inference.csv`: primary, secondary, duration/manipulation inference, plus the fixed-effect sensitivity row.
- `results/tables/benchmark_rest_transfer.csv`: two-outcome Holm correction, crosswalk sensitivity, and leave-one-participant-out diagnostics.
- `docs/benchmark_phase_geometry_manuscript_ready_results.md`: manuscript-ready numerical results text; no manuscript file was edited.
- `results/figures/benchmark_*_timecourses.png`: individual and group time courses for the five requested measures.

If missing control EDFs are recovered, rerun this identical script without changing parameters or windows as a locked-method confirmation.

No entropy, connectivity, classifier, extra band, or additional nonlinear descriptor was computed.
