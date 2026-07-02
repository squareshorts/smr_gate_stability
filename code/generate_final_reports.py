from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from utils.paths import ensure_repo_structure


def read_table(name: str) -> pd.DataFrame | None:
    path = ROOT / "outputs" / "tables" / name
    if not path.exists():
        return None
    return pd.read_csv(path)


def empirical_status() -> str:
    report = ROOT / "outputs" / "reports" / "wp8_results.md"
    if not report.exists():
        return "Empirical validation has not yet been run."
    text = report.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "Empirical validation was not run" in line:
            return line.strip()
    for line in text.splitlines():
        if line.strip() and not line.strip().startswith("#"):
            return line.strip()
    return "WP8 report exists, but no empirical status line was found."


def empirical_summary() -> dict[str, float | int | str]:
    features = read_table("wp8_empirical_features.csv")
    effects = read_table("wp8_prepost_or_sessionwise_effects.csv")
    regimes = read_table("wp8_regime_classification.csv")
    if features is None or effects is None or regimes is None or features.empty or effects.empty:
        return {"available": 0, "status": empirical_status()}
    primary = effects[effects["condition"] == "rest"]

    def mean_frac(metric: str) -> float:
        vals = primary.loc[primary["metric"] == metric, "fractional_change"]
        return float(vals.mean()) if len(vals) else float("nan")

    return {
        "available": 1,
        "subjects": int(features["subject"].nunique()),
        "sessions": int(features["session"].nunique()),
        "conditions": int(features["condition"].nunique()),
        "smr_change": mean_frac("smr_power"),
        "high_beta_change": mean_frac("high_beta_power"),
        "broadband_change": mean_frac("broadband_non_target_power"),
        "burst_rate_change": mean_frac("beta_burst_rate"),
        "signature_supported": int(regimes["signature_supported"].sum()) if "signature_supported" in regimes else 0,
        "regime_count": int(len(regimes)),
        "status": "real EEG subset analyzed",
    }


def generate_results_for_revision() -> None:
    wp1 = read_table("wp1_constraint_validity.csv")
    wp2 = read_table("wp2_bound_checks.csv")
    wp3 = read_table("wp3_model_comparison.csv")
    wp4 = read_table("wp4_lambda_sensitivity.csv")
    wp5 = read_table("wp5_threshold_sensitivity.csv")
    wp6 = read_table("wp6_parameter_sensitivity.csv")
    lines = ["# Results for Revision", ""]
    if wp1 is not None:
        lines.append(f"- WP1 validity rate: {wp1['directional_valid'].mean():.3f} across aggregate coupling/gain conditions.")
    if wp2 is not None:
        lines.append(f"- WP2 beta-derivative negative rate: {wp2['beta_derivative_negative_rate'].mean():.3f}; SMR-bound hold rate: {wp2['smr_bound_hold_rate'].mean():.3f}.")
    if wp3 is not None:
        max_gain = wp3["feedback_gain"].max()
        sub = wp3[wp3["feedback_gain"] == max_gain]
        lines.append(f"- WP3 at max gain: mean beta change {sub['beta_power_change_frac'].mean():.3f}, showing that generic feedback can also suppress beta power.")
    if wp4 is not None:
        lines.append(f"- WP4 suppression rate across criticality conditions: {(wp4['beta_power_change_frac'] < 0).mean():.3f}.")
    if wp5 is not None:
        feedback = wp5[wp5["condition"] == "feedback"]
        lines.append(f"- WP5 mean feedback burst-rate change across threshold definitions: {feedback['burst_rate_change_frac'].mean():.3f}.")
    if wp6 is not None:
        lines.append(f"- WP6 directional-validity rate across reduced parameter sweep: {wp6['directional_valid'].mean():.3f}.")
    emp = empirical_summary()
    if emp.get("available"):
        lines.append(
            f"- WP8 real EEG subset: {emp['subjects']} subjects; rest pre/post high-beta change {emp['high_beta_change']:.3f}, beta-burst-rate change {emp['burst_rate_change']:.3f}, SMR change {emp['smr_change']:.3f}; full joint signature {emp['signature_supported']} / {emp['regime_count']} subjects."
        )
    else:
        lines.append(f"- WP8 empirical status: {emp['status']}")
    lines.append("")
    lines.append("The theory package supports restricted validity-domain claims. The first real EEG subset provides empirical anchoring, but it is mixed and does not support a strong mechanistic or predictive claim.")
    (ROOT / "outputs" / "reports" / "results_for_revision.md").write_text("\n".join(lines), encoding="utf-8")


def generate_claims_report() -> None:
    emp = empirical_summary()
    empirical_text = (
        f"- A five-subject real EEG subset was downloaded and analyzed. It provides proof-of-pipeline anchoring, but the full joint signature was observed in {emp.get('signature_supported', 0)} / {emp.get('regime_count', 0)} subjects."
        if emp.get("available")
        else "- No empirical support is available because no suitable local EEG analysis completed."
    )
    text = """# Claims Supported vs Unsupported

Supported by coarse theory outputs:

- Selective stabilization of the fast Stuart-Landau mode can suppress high-beta power in weakly coupled regimes.
- SMR invariance is a validity-domain condition, not a guaranteed global property.
- Coupling strength and coupling form determine where SMR contamination begins.
- Stationary beta suppression is not specific to the nonlinear model; null models can reproduce part of it.
- Burst and failure-boundary behavior are important added constraints for the nonlinear interpretation.

Supported by empirical acquisition/analysis:

""" + empirical_text + """

Unsupported or not yet tested:

- The model is not established as the physiological mechanism of SMR neurofeedback.
- Universal validity is not supported.
- Strong empirical support is not supported by the current five-subject subset.
- Learner/non-learner prediction is not supported in this pass.

Claims to narrow:

- Frame the model as a validity-domain analysis of selective fast-mode stabilization.
- Treat empirical results, if later obtained, as anchoring evidence rather than proof of mechanism.
"""
    (ROOT / "outputs" / "reports" / "claims_supported_vs_unsupported.md").write_text(text, encoding="utf-8")


def generate_reviewer_mapping() -> None:
    text = """# Reviewer Criticism to Analysis Mapping

| Reviewer concern | Analysis response | Output |
|---|---|---|
| Model lacks coupling realism | Coupled Stuart-Landau stress tests across linear, amplitude, asymmetric, and phase coupling | WP1, WP6 |
| Claim may only hold in cherry-picked regimes | Explicit validity and failure maps | WP1, WP6 |
| Weak-coupling argument is informal | Finite-difference derivative and bound checks | WP2 |
| Beta suppression could be generic feedback | Linear OU, damped harmonic, AR(2), and nonlinear oscillator comparison | WP3 |
| Near-critical dynamics may invalidate linearization | Growth-parameter and noise sweep with analytic-vs-simulation checks | WP4 |
| Burst results could be threshold artifacts | Baseline-fixed, absolute, z-score, MAD, post-feedback, and surrogate controls | WP5 |
| Empirical data are needed | WP7 acquisition plan and WP8 empirical gate prevent fabricated support | WP7, WP8 |
"""
    (ROOT / "outputs" / "reports" / "reviewer_criticism_to_analysis_mapping.md").write_text(text, encoding="utf-8")


def generate_submission_assessment() -> None:
    wp1 = read_table("wp1_constraint_validity.csv")
    wp6 = read_table("wp6_parameter_sensitivity.csv")
    empirical = empirical_status()
    validity = wp6["directional_valid"].mean() if wp6 is not None else float("nan")
    wp1_validity = wp1["directional_valid"].mean() if wp1 is not None else float("nan")
    emp = empirical_summary()
    if emp.get("available"):
        empirical_strength = (
            f"Real EEG anchoring was completed on {emp['subjects']} subjects from ds004446. The result is mixed/non-supportive for the full joint signature: high-beta change {emp['high_beta_change']:.3f}, burst-rate change {emp['burst_rate_change']:.3f}, SMR change {emp['smr_change']:.3f}, full signature {emp['signature_supported']} / {emp['regime_count']} subjects."
        )
    else:
        empirical_strength = empirical_status()
    text = f"""# Cognitive Neurodynamics Submission Assessment

1. Evidence supporting fit to Cognitive Neurodynamics:
   The repository now contains nonlinear-dynamics validity maps, weak-coupling checks, null-model comparisons, and near-Hopf sensitivity analyses. WP1 validity rate: {wp1_validity:.3f}. WP6 reduced-sweep validity rate: {validity:.3f}.

2. Evidence still missing:
   Strong empirical support remains missing. The first real EEG subset is useful as a pipeline anchor but not as mechanism-level validation.

3. Main-text figure candidates:
   WP9 Figures 1-5 are suitable theory-first candidates: model validity, coupling/failure, criticality/bursts, null models, and threshold/surrogate robustness.

4. Supplementary figure candidates:
   WP1 example spectra, WP2 derivative/bound summary, WP4 analytic-vs-simulation variance, and WP6 parameter-importance plots.

5. Claims now supported:
   A coupled Stuart-Landau model defines a restricted regime where fast-mode stabilization suppresses high beta while SMR remains approximately unchanged.

6. Claims remaining unsupported:
   Physiological mechanism, universal validity, clinical efficacy, strong empirical predictive validity, and learner/non-learner stratification.

7. Claims that should be narrowed:
   The central claim should be stated as a validity-domain constraint under weak coupling and appropriate feedback gain.

8. Empirical anchoring strength:
   {empirical_strength}

9. Submission recommendation:
   The theory package is ready for critical inspection after this coarse pass. The empirical section should be framed narrowly as mixed proof-of-pipeline anchoring unless a broader dataset subset or longitudinal analysis is completed.
"""
    (ROOT / "outputs" / "reports" / "Cognitive_Neurodynamics_submission_assessment.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_repo_structure(ROOT)
    generate_results_for_revision()
    generate_claims_report()
    generate_reviewer_mapping()
    generate_submission_assessment()


if __name__ == "__main__":
    main()
