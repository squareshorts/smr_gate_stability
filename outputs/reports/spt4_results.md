# SPT4 Results: Rigorous Empirical Time-scale Analysis

Generated: 2026-07-01T18:30:15.290675+00:00

## Dataset and method

Dataset: ds004446
Subjects: 5 (sub-004, sub-005, sub-012, sub-013, sub-018)
Sessions: ses-01, ses-08
Conditions: rest, task, interval
EEG segments analyzed: 30

Methods:
- Primary: AR1 autocorrelation tau at native sampling rate.
  KNOWN LIMITATION: confounded by bandwidth difference (SMR: 3 Hz BW, HB: 10 Hz BW).
- Control 1: bandwidth-matched comparison (SMR 12-15 Hz, HB 20-23 Hz; both 3 Hz BW).
- Control 2: block-mean tau (4-s blocks) — removes fast filter fluctuations.
- Control 3: 1-Hz decimated envelope — isolates regulation dynamics.
- Theory: expected tau ratio from Gaussian bandwidth prediction.

## Key results

### Primary tau (AR1 at native fs)
tau_SMR: mean = 43.7 s, median = 38.5 s, SD = 17.6 s
tau_HB:  mean = 4.4 s, median = 3.6 s, SD = 2.4 s
tau_ratio (HB/SMR): mean = 0.100, median = 0.094
30/30 segments: tau_HB < 0.5 * tau_SMR
One-sample t-test vs ratio=1.0: t = -191.84, p = 0.0000

### Bandwidth confound assessment
Gaussian bandwidth theory predicts tau ratio = 0.090
(from BW_SMR=3 Hz, BW_HB=10 Hz at fs=256 Hz)

Observed tau_ratio (primary) = 0.100
Expected from BW alone       = 0.090

>> IMPORTANT: The observed tau_ratio (0.100) is close to the bandwidth-predicted ratio (0.090).
A significant fraction of the observed time-scale separation may reflect the 3 Hz vs 10 Hz bandwidth difference, not genuine regulation dynamics.

### Bandwidth-matched control (3 Hz BW for both)
Mean tau_ratio (BW-matched): 1.047
This tests separation when bandwidth is equalized. A ratio < 1.0 would indicate separation beyond the bandwidth artifact.

### Block-mean tau (4-s blocks, regulation scale)
Mean tau_ratio (block): 0.918
Ratios close to 1.0 or variable here indicate that the separation may be driven primarily by bandwidth, not regulation.

### 1-Hz decimated tau
Mean tau_ratio (decimated): 1.379

## Interpretation

**BANDWIDTH CONFOUND WARNING**: The observed tau_ratio (0.100) is
within 0.05 of the bandwidth-predicted ratio (0.090). The primary tau analysis
CANNOT reliably distinguish filter bandwidth effects from genuine time-scale separation.
The high tau_ratio of 0.100 may be almost entirely explained by the fact that
the SMR band (3 Hz) is narrower than the high-beta band (10 Hz).

The bandwidth-matched control shows tau_ratio = 1.047 ≈ 1.0, indicating that most or all of the observed time-scale separation disappears when bandwidths are matched. This strongly implicates the bandwidth difference as the primary driver of the observed tau_ratio.

## Conclusion on time-scale separation

The primary AR1 tau analysis shows tau_HB ≈ 4.4 s and tau_SMR ≈ 43.7 s
(ratio ≈ 0.10). However, the Gaussian bandwidth prediction gives a ratio of
0.090 from filter properties alone. This means the observed time-scale separation
is at least partly (and possibly largely) a filter artifact.

The block-mean tau ratio = 0.918 and decimated tau ratio = 1.379
provide a more regulation-focused estimate.

**Claim status**: The claim of "empirical time-scale separation" from AR1 analysis at native fs
is **NOT RELIABLE** without bandwidth matching. The block-mean and BW-matched analyses are more
defensible. Results should be reported with the bandwidth caveat.

Generated: 2026-07-01T18:30:15.290675+00:00
