# Frozen remedy success criteria

Frozen before results. A single-score method qualifies as successful only if ALL twelve
primary conditions are met. REMEDY-GO is assigned only if one method passes all twelve.

1. Pooled median split-half accepted-set Jaccard >= 0.85.
2. >= 80% of sessions have split-half Jaccard >= 0.80.
3. Every dataset has median split-half Jaccard >= 0.80.
4. Pooled median accepted-set Jaccard exceeds ORIGINAL_AND by >= 0.10.
5. Improvement direction is positive in every dataset.
6. Cross-session transport Jaccard exceeds ORIGINAL_AND by >= 0.10 pooled.
7. Median transitions/min are >= 30% lower than ORIGINAL_AND at matched availability.
8. No increase in sessions with >30 s gaps at matched availability.
9. Natural-retention decoder performance is not more than 0.005 below no gate in pooled
   balanced accuracy, OR the 95% interval includes zero and excludes a loss worse than -0.01.
10. Count-matched decoder performance is not materially worse than ORIGINAL_AND.
11. p95 latency remains below 10 ms.
12. Fail-closed and deterministic behavior pass in all tested cases.

Criteria are not to be weakened. Stage 7 (degradation) runs only if a method passes 1-8.
