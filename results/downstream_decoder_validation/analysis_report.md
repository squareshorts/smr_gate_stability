# Downstream decoder validation report

## Primary result

Natural retention — NFSQI_FULL minus HB: -0.0148 (95% bootstrap CI -0.0234 to -0.0065; permutation p=0.0008; n=57).

Count matched — NFSQI_FULL minus HB: -0.0058 (95% bootstrap CI -0.0134 to +0.0012; permutation p=0.1300; n=57).

## Other prespecified contrasts

NFSQI_FULL minus ALL: -0.0164 (95% bootstrap CI -0.0264 to -0.0067; permutation p=0.0012; n=57).

HB minus ALL: -0.0016 (95% bootstrap CI -0.0056 to +0.0023; permutation p=0.4253; n=57).

## By dataset

- ds004447: NFSQI_FULL minus HB: -0.0221 (95% bootstrap CI -0.0407 to -0.0047; permutation p=0.0224; n=22).
- ds004444: NFSQI_FULL minus HB: -0.0110 (95% bootstrap CI -0.0198 to -0.0031; permutation p=0.0194; n=30).
- ds004446: NFSQI_FULL minus HB: -0.0049 (95% bootstrap CI -0.0253 to +0.0155; permutation p=0.7576; n=5).

## Retention and feasibility

NFSQI_FULL retained a mean 39.4% of explicit rest windows and 43.5% of explicit task windows. This is a modestly higher task retention, not a task-selective filter. 9 fold-policy records were nonviable; all were the 150 microvolt amplitude baseline, not NFSQI_FULL.

## Interpretation

The complete quality-only rule did not improve held-out-session rest-versus-task decoding relative to high-beta-only filtering. In natural retention, the pooled estimate was negative and its interval excluded zero. After count matching the estimate remained negative, but its interval included zero; that analysis therefore does not establish a quantity-independent difference. All three dataset estimates were negative, although every dataset-specific interval included zero. NFSQI_FULL also performed worse than no filtering in the pooled natural analysis. High-beta-only filtering did not improve pooled decoding relative to no filtering. These results do not establish equivalence and do not validate artifacts or neurofeedback learning. They are evidence that this quality rule, in this decoder/task setting, can remove information useful for the downstream classifier.

## Scope limits

The expanded ROI sensitivity is not available because the repository's exact expanded name-based ROI (`C3`, `C4`, `Cz`, `FC*`, `CP*`) cannot be mapped to at least five channels in these EDFs; only `Cz` is present by that definition. No full covariance/tangent-space sensitivity was run because the frozen environment lacks a verified Riemannian dependency. Riemannian Potato/Field was likewise not implemented. Synthetic perturbation was not attempted after the primary analysis.
