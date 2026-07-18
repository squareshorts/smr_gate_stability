# Runtime-assurance verification report

## Outcome: GO-B

The isolated strict interlock is formally coherent as a runtime measurement-admissibility monitor, but calibration stability and temporal availability require correction or an explicit operational policy before submission under this framing.

- Gate A and Gate C are formally separate: Gate A uses only SMR-SNR; Gate C applies only strict upper quality criteria after Gate B.
- Batch and streaming conformance is exact in the formal wrapper: 22,418/22,418 analyzed windows had identical Gate A/B/C decisions and reason codes. The historical ds004444 equality mismatch is eliminated by the explicit strict upper-limit policy.
- Threshold boundaries are deterministic: equality with a lower SMR threshold withholds; equality with an upper quality threshold withholds.
- Full feature-plus-decision timing had a maximum session p95 of 0.183 ms, far below the 0.5-s hop (this is desktop replay timing, not device certification).
- Every one of 114 analyzed sessions retained at least one Gate-C accepted task window. Median Gate-C density was 8.0, 9.0, and 11.0 accepted windows/min in ds004444, ds004446, and ds004447 respectively.
- Temporal starvation remains material: median longest Gate-C feedback-free period was 23.9 s and the maximum was 119 s. Nonzero availability therefore does not demonstrate acceptable temporal availability.
- Instantaneous Gate C had median 18 transitions/min. Two-consecutive-pass recovery reduced transitions but reduced median availability to 0.5 accepted windows/min; two-of-three voting reduced transitions with a median 13 accepted windows/min. Neither secondary variant changes the primary rule.
- Calibration stability fails the prespecified descriptive criterion: decision agreement reaches 0.95 at 30 s and 0.977 at 120 s, but median Jaccard agreement is only 0.735 at 120 s, below 0.90.
- Block-bootstrap uncertainty is nontrivial: median stable-decision proportions ranged from 0.894 to 0.942 across datasets.
- Cross-session transported calibration had median decision agreement of about 0.93-0.94 but low Jaccard agreement (0.15-0.41), supporting session-specific recalibration rather than transport claims.
- Controlled missing/nonfinite/malformed inputs all failed closed with explicit invalid-input reason codes. This verifies software behavior only.

The engineering-interlock framing is supportable only with the limitations above. It does not validate artifact labels, artifact removal, clinical safety, neurofeedback efficacy, or downstream decoder benefit. The archived negative decoder result remains a binding boundary condition.
