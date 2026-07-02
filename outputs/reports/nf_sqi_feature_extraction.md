# Task 1: NF-SQI Feature Extraction

- **Subjects processed:** 22
- **Sessions processed:** 4
- **Total windows:** 53755
- **Channels used:** ['E36', 'E104', 'E128']
- **Missing data files:** 0

## Extracted Features
1. `smr_power`: Welch PSD (12-15 Hz) averaged across channels.
2. `smr_snr`: `smr_power` / `broadband_power`.
3. `high_beta_power`: Welch PSD (20-30 Hz).
4. `noise_floor_power`: Welch PSD (35-45 Hz).
5. `broadband_power`: Welch PSD (4-45 Hz, excluding SMR and high beta).
6. `spectral_slope`: Linear fit of log(PSD) vs log(freq) in the broadband range.
7. `transient_score`: Maximum absolute amplitude across channels in the window.
8. `channel_inconsistency`: Mean across-channel standard deviation of standardized power for SMR, High Beta, Broadband, and Noise Floor.
9. `channel_inconsistency_mad`: Robust median absolute deviation version.
10. `nonstationarity`: Absolute difference in `smr_power` from the previous window.
