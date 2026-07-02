"""SPT7: Comparison with previous Stuart-Landau outputs.

Compares the Stuart-Landau framework with the new
singular perturbation / fast-slow barrier framework.

Outputs
-------
outputs/tables/spt7_framework_comparison.csv
outputs/reports/spt7_framework_decision.md
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from utils.paths import ensure_repo_structure


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


COMPARISON_ROWS = [
    # Criterion, Stuart-Landau, SPT/Fast-slow, Winner
    {
        "criterion": "Matches empirical mixed result (no joint signature)",
        "stuart_landau": (
            "Weak: SL requires near-criticality regime with specific coupling. "
            "Mixed empirical result (SMR ~unchanged, beta increased) falls "
            "outside the joint-signature regime in most simulations."
        ),
        "spt_fast_slow": (
            "Better: SPT predicts that high-beta stabilization and SMR acquisition "
            "are independent processes. The observed mixed result (quadrant D or C) "
            "is a natural outcome when alpha_x is low, not a model failure."
        ),
        "winner": "SPT",
        "notes": "WP8 showed 0/5 joint-signature subjects; SPT predicts separability explicitly.",
    },
    {
        "criterion": "Supports non-diagnostic interpretation of high-beta suppression",
        "stuart_landau": (
            "Weak: in SL, beta suppression emerges from the same oscillator dynamics "
            "that produce SMR changes, making separation between the two difficult "
            "to argue mechanistically."
        ),
        "spt_fast_slow": (
            "Strong: SPT explicitly separates high-beta (fast, stabilization variable) "
            "from SMR (slow, learning variable). High-beta suppression is a constraint, "
            "not a surrogate of learning. Non-diagnostic interpretation follows directly."
        ),
        "winner": "SPT",
        "notes": "Central conceptual advantage of SPT framework.",
    },
    {
        "criterion": "Clear testable predictions",
        "stuart_landau": (
            "Moderate: SL predicts specific spectral signatures near bifurcation; "
            "hard to test without precise parameter estimation in vivo."
        ),
        "spt_fast_slow": (
            "Good: SPT predicts tau_beta << tau_SMR, four-quadrant separability, "
            "barrier violation -> instability. These are measurable in EEG data, "
            "though small sample size limits empirical verification."
        ),
        "winner": "SPT",
        "notes": "SPT yields clearer empirically-testable predictions.",
    },
    {
        "criterion": "Mechanistic richness / nonlinear detail",
        "stuart_landau": (
            "Strong: SL provides a specific nonlinear oscillator mechanism, "
            "bifurcation structure, and analytic regime boundaries."
        ),
        "spt_fast_slow": (
            "Moderate: SPT provides a general separation-of-timescales argument "
            "without committing to a specific nonlinear oscillator. "
            "Less mechanistically specific, but more flexible."
        ),
        "winner": "SL",
        "notes": "SL has richer mechanistic detail; SPT is more framework-level.",
    },
    {
        "criterion": "Empirical support (ds004446, n=5)",
        "stuart_landau": (
            "Unsupported: joint signature (SMR up + beta down) found in 0/5 subjects. "
            "SL-predicted regime not clearly observed."
        ),
        "spt_fast_slow": (
            "Partial: separability hypothesis consistent with mixed empirical result. "
            "No positive evidence of separability, but mixed result is not a failure "
            "of SPT as it would be for SL."
        ),
        "winner": "SPT",
        "notes": "Neither framework is strongly supported; SPT is not falsified by mixed data.",
    },
    {
        "criterion": "Simulation support for separability",
        "stuart_landau": (
            "Partial: SL can show domains where beta suppression occurs without SMR "
            "acquisition, but the coupling structure makes full separability limited."
        ),
        "spt_fast_slow": (
            "Strong: SPT simulations directly demonstrate four separable regimes "
            "(both, acquisition only, stabilization only, neither). "
            "Separability is built into the model structure."
        ),
        "winner": "SPT",
        "notes": "SPT1 simulations confirm four-regime separability.",
    },
    {
        "criterion": "Validity domain requirements",
        "stuart_landau": (
            "Specific: requires near-criticality, specific coupling strength, "
            "and feedback gain within narrow validity domain (WP1-WP6)."
        ),
        "spt_fast_slow": (
            "General: valid when epsilon << 1 (tau_beta << tau_SMR). "
            "SPT2 shows validity for epsilon <= 0.03 in simulations. "
            "Whether real EEG satisfies this is uncertain (SPT4 weak/partial support)."
        ),
        "winner": "Draw",
        "notes": "Both require specific conditions; SPT conditions are simpler to state.",
    },
    {
        "criterion": "Conservative causal claims",
        "stuart_landau": (
            "Risk: SL can be interpreted as implying that beta suppression causes "
            "or is causally linked to SMR changes through the oscillator mechanism."
        ),
        "spt_fast_slow": (
            "Safe: SPT explicitly models high-beta as a constraint variable, not a "
            "target-learning variable. Framework explicitly prohibits causal claims "
            "about beta suppression -> SMR acquisition."
        ),
        "winner": "SPT",
        "notes": "SPT is safer for conservative framing consistent with editorial requirements.",
    },
]


def make_comparison_table() -> pd.DataFrame:
    return pd.DataFrame(COMPARISON_ROWS)


def write_report(comp_df: pd.DataFrame) -> None:
    rep_dir = ROOT / "outputs" / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)

    n_spt = int((comp_df["winner"] == "SPT").sum())
    n_sl = int((comp_df["winner"] == "SL").sum())
    n_draw = int((comp_df["winner"] == "Draw").sum())

    report = f"""# SPT7: Stuart-Landau vs Singular Perturbation Framework Decision

## Comparison summary

Criteria evaluated: {len(comp_df)}
- SPT/fast-slow wins: {n_spt}
- Stuart-Landau wins: {n_sl}
- Draw: {n_draw}

## Criterion-by-criterion comparison

"""
    for _, row in comp_df.iterrows():
        report += f"### {row['criterion']}\n\n"
        report += f"**Stuart-Landau:** {row['stuart_landau']}\n\n"
        report += f"**SPT/Fast-slow:** {row['spt_fast_slow']}\n\n"
        report += f"**Assessment:** {row['winner']}  \n"
        report += f"**Notes:** {row['notes']}\n\n"
        report += "---\n\n"

    report += f"""
## Framework decision

### Recommendation: DEMOTE Stuart-Landau to supplementary material.

Rationale:

1. The singular perturbation / fast-slow barrier framework is conceptually better
   aligned with the core hypothesis: high-beta suppression as a stabilization
   constraint, not a target-learning surrogate.

2. Stuart-Landau provides mechanistic detail but this detail is not supported
   by the empirical data (0/5 subjects showed the joint signature) and requires
   unrealistically specific parameter assumptions.

3. Stuart-Landau adds interpretive risk: the coupling structure in SL makes it
   harder to argue that high-beta suppression and SMR acquisition are independent,
   which is the central scientific claim.

4. The SPT framework does not replace Stuart-Landau as a dynamic systems model;
   rather, it provides a higher-level framework within which SL could be seen as
   one specific nonlinear mechanism. Stuart-Landau can be mentioned as a concrete
   example of a fast-slow oscillator system in a supplementary section.

5. The fast-slow framework yields clearer testable predictions (tau_ratio,
   four-quadrant separability, barrier violation prediction) even if current
   empirical support is only partial.

### What to retain from Stuart-Landau analysis

- The finding that beta suppression can occur in generic feedback models without
  mechanistic specificity supports the SPT framing.
- The validity-domain analysis (WP1-WP6) demonstrated that the full SMR-beta
  joint signature is not universally generated by oscillator dynamics, which
  is consistent with the SPT separability argument.
- Stuart-Landau can be cited as showing that the problem is not specific to
  any one dynamical mechanism, motivating the more general SPT framework.

### What NOT to carry forward

- Claims that Stuart-Landau is the primary mechanistic model for SMR neurofeedback.
- Regime-specific SL predictions as the main analytic framework.
- The near-criticality interpretation as necessary for high-beta suppression.

Generated: {utc_now()}
"""
    (rep_dir / "spt7_framework_decision.md").write_text(report, encoding="utf-8")
    print("  Saved spt7_framework_decision.md")


def main() -> None:
    ensure_repo_structure(ROOT)
    tbl_dir = ROOT / "outputs" / "tables"

    comp_df = make_comparison_table()
    comp_df.to_csv(tbl_dir / "spt7_framework_comparison.csv", index=False)
    print(f"SPT7: Saved spt7_framework_comparison.csv ({len(comp_df)} criteria)")

    write_report(comp_df)
    print("SPT7 done.")


if __name__ == "__main__":
    main()
