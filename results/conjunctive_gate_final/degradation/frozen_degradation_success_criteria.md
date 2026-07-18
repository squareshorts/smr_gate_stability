# Frozen degradation success criteria

Frozen before results. R1 is classified DEGRADATION-PASS only if ALL hold:

1. Unchanged-copy (D0) decision reproduction = 100%.
2. Unchanged-copy false withholding <= 1%.
3. Missing-channel / structurally invalid inputs (D9) fail closed in 100% of cases.
4. Response is nondecreasing with severity at the pooled level for at least 6 of the continuous
   degradation families (D1–D8).
5. Top-severity R1 response >= 80% for: clipping (D6); fully frozen channel (D8); missing/invalid (D9).
6. Top-severity R1 response >= 60% for at least 4 of: D1, D2, D3, D4, D5, D7.
7. R1 is more than 15 percentage points below R0 at top severity in no more than two families.
8. No dataset shows complete response collapse for a degradation detected in the other two datasets.
9. R1 remains deterministic.
10. R1 does not pass structurally invalid input.

If R1 fails: report the exact failure; do not redesign R1, add feature weights, change the final
threshold, or search for a more favourable scoring rule. R2 is sensitivity only regardless of outcome.
