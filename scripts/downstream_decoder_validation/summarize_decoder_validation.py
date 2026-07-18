#!/usr/bin/env python3
"""Regenerate participant-level contrasts and plain-language reporting."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "downstream_decoder_validation"
DATASETS = ("ds004447", "ds004444", "ds004446")
CONTRASTS = (("NFSQI_FULL", "HB"), ("NFSQI_FULL", "ALL"), ("HB", "ALL"))


def seed_for(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:8], 16)


def main() -> int:
    subjects = pd.read_csv(OUT / "decoder_results_by_subject.csv")
    rows = []
    for analysis in sorted(subjects.analysis.unique()):
        for dataset in (*DATASETS, "pooled"):
            data = subjects.loc[subjects.analysis == analysis]
            if dataset != "pooled":
                data = data.loc[data.dataset == dataset]
            wide = data.pivot_table(index=["dataset", "subject"], columns="policy", values="balanced_accuracy", aggfunc="mean")
            for left, right in CONTRASTS:
                if left not in wide or right not in wide:
                    continue
                values = (wide[left] - wide[right]).dropna().to_numpy()
                if not len(values):
                    continue
                rng = np.random.default_rng(seed_for(analysis, dataset, left, right))
                boot = np.array([rng.choice(values, len(values), replace=True).mean() for _ in range(5000)])
                perm = np.array([np.mean(values * rng.choice([-1, 1], len(values))) for _ in range(5000)])
                rows.append({"dataset": dataset, "contrast": f"{left} minus {right}", "analysis": analysis,
                             "mean_paired_difference": values.mean(), "median_paired_difference": np.median(values),
                             "bootstrap_ci_low": np.quantile(boot, .025), "bootstrap_ci_high": np.quantile(boot, .975),
                             "p_value": (np.sum(np.abs(perm) >= abs(values.mean())) + 1) / 5001,
                             "n_participants": len(values), "status": "valid"})
    primary = pd.DataFrame(rows)
    primary.to_csv(OUT / "primary_contrasts.csv", index=False)
    retention = pd.read_csv(OUT / "retention_by_subject.csv")
    nonviable = pd.read_csv(OUT / "nonviable_folds.csv")
    def sentence(analysis: str, contrast: str, dataset: str = "pooled") -> str:
        row = primary.loc[(primary.analysis == analysis) & (primary.contrast == contrast) & (primary.dataset == dataset)].iloc[0]
        return f"{contrast}: {row.mean_paired_difference:+.4f} (95% bootstrap CI {row.bootstrap_ci_low:+.4f} to {row.bootstrap_ci_high:+.4f}; permutation p={row.p_value:.4f}; n={int(row.n_participants)})."
    full_ret = retention.loc[retention.policy == "NFSQI_FULL"].groupby("class").retention_proportion.mean()
    ds_lines = []
    for dataset in DATASETS:
        ds_lines.append("- " + dataset + ": " + sentence("natural", "NFSQI_FULL minus HB", dataset))
    report = "# Downstream decoder validation report\n\n## Primary result\n\n" + sentence("natural", "NFSQI_FULL minus HB") + "\n\n" + sentence("count_matched", "NFSQI_FULL minus HB") + "\n\n## Other prespecified contrasts\n\n" + sentence("natural", "NFSQI_FULL minus ALL") + "\n\n" + sentence("natural", "HB minus ALL") + "\n\n## By dataset\n\n" + "\n".join(ds_lines) + "\n\n## Retention and feasibility\n\n" + f"NFSQI_FULL retained a mean {full_ret['rest']:.1%} of explicit rest windows and {full_ret['task']:.1%} of explicit task windows. This is a modestly higher task retention, not a task-selective filter. {len(nonviable)} fold-policy records were nonviable; all were the 150 microvolt amplitude baseline, not NFSQI_FULL.\n\n## Interpretation\n\nThe complete quality-only rule did not improve held-out-session rest-versus-task decoding relative to high-beta-only filtering. In natural retention, the pooled estimate was negative and its interval excluded zero. After count matching the estimate remained negative, but its interval included zero; that analysis therefore does not establish a quantity-independent difference. All three dataset estimates were negative, although every dataset-specific interval included zero. NFSQI_FULL also performed worse than no filtering in the pooled natural analysis. High-beta-only filtering did not improve pooled decoding relative to no filtering. These results do not establish equivalence and do not validate artifacts or neurofeedback learning. They are evidence that this quality rule, in this decoder/task setting, can remove information useful for the downstream classifier.\n\n## Scope limits\n\nThe expanded ROI sensitivity is not available because the repository's exact expanded name-based ROI (`C3`, `C4`, `Cz`, `FC*`, `CP*`) cannot be mapped to at least five channels in these EDFs; only `Cz` is present by that definition. Riemannian Potato/Field was not implemented because no verified package is available in the frozen environment. Synthetic perturbation was not attempted after the primary analysis.\n"
    (OUT / "analysis_report.md").write_text(report, encoding="utf-8")
    notes = "# Manuscript update notes\n\nThe rule-defined classifier should become secondary because it has a circular target. The downstream held-out-session decoder analysis, event-label audit, fold definition, retention table, and paired-policy figures could replace it.\n\nSupported claim: under this independent rest-versus-task decoder evaluation, NFSQI_FULL did not improve held-out-session balanced accuracy relative to HB or no filtering; the pooled natural NFSQI_FULL minus HB difference was " + f"{primary.loc[(primary.dataset == 'pooled') & (primary.analysis == 'natural') & (primary.contrast == 'NFSQI_FULL minus HB')].iloc[0].mean_paired_difference:+.4f}.\n\nUnsupported claims: artifact validity, equivalence, better neurofeedback learning, or a universally harmful filter. The present title and abstract would need substantial revision before representing this evidence. No manuscript text was edited.\n"
    (OUT / "manuscript_update_notes.md").write_text(notes, encoding="utf-8")
    print(sentence("natural", "NFSQI_FULL minus HB"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
