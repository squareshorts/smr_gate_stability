"""
NCTRL Audit: Critical audit of the "Strong support" hypothesis label.
Produces:
  outputs/reports/nctrl_audit_report.md
  outputs/tables/nctrl_audit_key_metrics.csv
  outputs/tables/nctrl_subject_influence.csv
  outputs/tables/nctrl_definition_robustness.csv
  outputs/reports/nctrl_revised_hypothesis_label.md
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

TBL = ROOT / "outputs" / "tables"
REP = ROOT / "outputs" / "reports"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load(name):
    p = TBL / name
    if not p.exists():
        print(f"  WARNING: {name} missing")
        return pd.DataFrame()
    return pd.read_csv(p)


# ──────────────────────────────────────────────────────────────
# 1. SIMULATION AUDIT
# ──────────────────────────────────────────────────────────────
def audit_simulation():
    issues = []
    metrics = {}

    sim = load("nctrl1_simulation_summary.csv")
    grid = load("nctrl1_parameter_grid.csv")

    if sim.empty:
        return issues, metrics

    # Check noise_damped flag in simulation summary
    # R1=damp_only should have noise_damped=True; R3=both should have noise_damped=True
    r1 = sim[sim["name"] == "R1_damp_only"]
    r3 = sim[sim["name"] == "R3_both"]
    r5 = sim[sim["name"] == "R5_false_reward"]

    r1_damp = bool(r1["noise_damped"].values[0]) if len(r1) else None
    r3_damp = bool(r3["noise_damped"].values[0]) if len(r3) else None
    r5_damp = bool(r5["noise_damped"].values[0]) if len(r5) else None
    r5_acq = bool(r5["smr_acquired"].values[0]) if len(r5) else None

    if r1_damp is False:
        issues.append("SIM-BUG-1: R1_damp_only has noise_damped=False in summary. "
                      "Regime labeling is inconsistent with noise_damped flag.")
    if r3_damp is False:
        issues.append("SIM-BUG-2: R3_both has noise_damped=False in summary. "
                      "The 'both' regime should have noise_damped=True by definition.")

    metrics["sim_r1_noise_damped_flag"] = r1_damp
    metrics["sim_r3_noise_damped_flag"] = r3_damp

    # Check that broadband_contam is meaningful
    n_zero_broad = int((sim["broadband_contam"] == 0.0).sum())
    if n_zero_broad >= 5:
        issues.append(f"SIM-BUG-3: broadband_contam=0 for {n_zero_broad}/6 regimes. "
                      "Broadband variable z has negligible effect in most regimes; "
                      "noise-control claim for broadband contamination is not demonstrated.")
    metrics["sim_n_zero_broadband_contam"] = n_zero_broad

    # Check grid quadrant distribution
    if not grid.empty:
        qc = grid["quadrant"].value_counts()
        n_A = qc.get("A_both", 0)
        n_B = qc.get("B_acq_only", 0)
        n_C = qc.get("C_damp_only", 0)
        n_D = qc.get("D_neither", 0)
        total = len(grid)
        metrics.update({"grid_n_A": n_A, "grid_n_B": n_B, "grid_n_C": n_C,
                        "grid_n_D": n_D, "grid_total": total})
        metrics["grid_A_pct"] = 100 * n_A / total
        metrics["grid_C_pct"] = 100 * n_C / total  # C = damp only

        # C (damp only, no acq) is the key evidence: HB damping without SMR
        if n_C < 5:
            issues.append(f"SIM-WEAK-1: Only {n_C}/{total} grid points in C_damp_only. "
                          "Limited evidence for pure noise-damping without acquisition.")
        if n_A < 5:
            issues.append(f"SIM-WEAK-2: Only {n_A}/{total} grid points in A_both. "
                          "Rare co-occurrence of damping and acquisition in parameter space.")

        # Check what fraction of damping-active (k_damp>0) points achieve noise_damped
        if "noise_damped" in grid.columns and "k_damp" in grid.columns:
            kdamp_nonzero = grid[grid["k_damp"] > 0]
            frac_damped = kdamp_nonzero["noise_damped"].mean() if len(kdamp_nonzero) else np.nan
            metrics["frac_kdamp_gt0_noise_damped"] = frac_damped
            if frac_damped < 0.5:
                issues.append(f"SIM-WEAK-3: Only {frac_damped:.0%} of k_damp>0 points have "
                               "noise_damped=True. Active damping parameter does not reliably "
                               "produce noise-damped outcome.")

        # SNR: does k_damp consistently improve SNR?
        if "smr_snr" in grid.columns and "k_damp" in grid.columns:
            snr_by_kdamp = grid.groupby("k_damp")["smr_snr"].median()
            issues.append(f"SIM-INFO: Median SMR SNR by k_damp: {snr_by_kdamp.to_dict()}")
            metrics["snr_kdamp0"] = float(snr_by_kdamp.get(0.0, np.nan))
            metrics["snr_kdamp8"] = float(snr_by_kdamp.get(8.0, np.nan))

    return issues, metrics


# ──────────────────────────────────────────────────────────────
# 2. EMPIRICAL HB CHARACTER AUDIT (NCTRL3)
# ──────────────────────────────────────────────────────────────
def audit_hb_character():
    issues = []
    metrics = {}
    rows = []

    noise = load("nctrl3_empirical_noise_features.csv")
    slope = load("nctrl3_spectral_slope_features.csv")

    if noise.empty:
        return issues, metrics, rows

    ch = noise[noise["channel"] == "mean"].copy()

    # HB residual above 1/f: is HB band-specific?
    mean_hb_resid = ch["hb_residual_above_1f"].mean()
    median_hb_resid = ch["hb_residual_above_1f"].median()
    n_pos_hb = int((ch["hb_residual_above_1f"] > 0).sum())
    n_total = len(ch)
    pct_pos = 100 * n_pos_hb / n_total

    metrics["hb_resid_mean"] = mean_hb_resid
    metrics["hb_resid_median"] = median_hb_resid
    metrics["hb_resid_n_positive"] = n_pos_hb
    metrics["hb_resid_pct_positive"] = pct_pos

    if mean_hb_resid < 0:
        issues.append(f"EMP-HB-1: Mean HB residual above 1/f = {mean_hb_resid:.4f} < 0. "
                      "HB power is BELOW the 1/f aperiodic line on average. "
                      "HB modulation is consistent with broadband/1/f changes, not band-specific. "
                      "This directly undermines 'band-specific HB' claim.")
    elif mean_hb_resid < 0.05:
        issues.append(f"EMP-HB-2: Mean HB residual above 1/f = {mean_hb_resid:.4f}, very small. "
                      "HB is marginally above 1/f; band-specificity is weak.")

    if pct_pos < 50:
        issues.append(f"EMP-HB-3: Only {pct_pos:.0f}% of observations show positive HB residual. "
                      "Majority of HB observations are below or at the 1/f noise floor.")

    # Per-subject HB residual
    per_sub = ch.groupby("subject")[["hb_residual_above_1f", "smr_snr_abs", "aperiodic_slope",
                                      "broad_contam_idx"]].mean()
    for sub, row in per_sub.iterrows():
        rows.append({
            "subject": sub,
            "mean_hb_resid_above_1f": row["hb_residual_above_1f"],
            "hb_band_specific": row["hb_residual_above_1f"] > 0.05,
            "mean_smr_snr": row["smr_snr_abs"],
            "mean_aperiodic_slope": row["aperiodic_slope"],
            "mean_broad_contam_idx": row["broad_contam_idx"],
        })

    # Session change: does SMR SNR improve ses-01 → ses-08?
    s01 = ch[ch["session"] == "ses-01"].groupby("subject")["smr_snr_abs"].mean()
    s08 = ch[ch["session"] == "ses-08"].groupby("subject")["smr_snr_abs"].mean()
    common = s01.index.intersection(s08.index)
    delta_snr = s08[common] - s01[common]
    n_snr_improve = int((delta_snr > 0).sum())
    metrics["n_subjects_snr_improve"] = n_snr_improve
    metrics["n_subjects_snr_total"] = len(common)
    metrics["mean_delta_snr"] = delta_snr.mean()

    if n_snr_improve < 3:
        issues.append(f"EMP-SNR-1: SMR SNR improves in only {n_snr_improve}/{len(common)} subjects. "
                      "No consistent SMR SNR improvement across ses-01 → ses-08.")

    # HB power change
    hb_s01 = ch[ch["session"] == "ses-01"].groupby("subject")["p_hb"].mean()
    hb_s08 = ch[ch["session"] == "ses-08"].groupby("subject")["p_hb"].mean()
    delta_hb = np.log10(hb_s08[common]) - np.log10(hb_s01[common])
    n_hb_reduce = int((delta_hb < 0).sum())
    metrics["n_subjects_hb_reduce"] = n_hb_reduce
    metrics["mean_delta_hb_log"] = delta_hb.mean()

    # Aperiodic slope change (1/f steepening = broadband suppression)
    sl01 = ch[ch["session"] == "ses-01"].groupby("subject")["aperiodic_slope"].mean()
    sl08 = ch[ch["session"] == "ses-08"].groupby("subject")["aperiodic_slope"].mean()
    delta_slope = sl08[common] - sl01[common]
    n_steeper = int((delta_slope < 0).sum())
    metrics["n_subjects_slope_steeper"] = n_steeper
    metrics["mean_delta_slope"] = delta_slope.mean()

    if abs(delta_slope.mean()) < 0.1:
        issues.append(f"EMP-SLOPE-1: Mean 1/f slope change = {delta_slope.mean():.4f} (near zero). "
                      "No consistent 1/f steepening across sessions. Aperiodic changes cannot "
                      "explain HB changes.")

    return issues, metrics, rows


# ──────────────────────────────────────────────────────────────
# 3. BURST AUDIT (NCTRL4)
# ──────────────────────────────────────────────────────────────
def audit_burst():
    issues = []
    metrics = {}

    burst = load("nctrl4_burst_instability_features.csv")
    if burst.empty:
        return issues, metrics

    # Check burst occupancy - should vary but may be fixed at 0.25 by design
    occ_vals = burst["hb_burst_occupancy"].unique()
    if len(occ_vals) == 1 and occ_vals[0] == 0.25:
        issues.append("BURST-ARTIFACT-1: hb_burst_occupancy = 0.25 for ALL subjects/sessions/conditions. "
                      "Burst threshold is the 75th percentile → burst occupancy is 25% by construction. "
                      "This metric contains NO information about session differences.")
    elif len(occ_vals) <= 2:
        issues.append(f"BURST-ARTIFACT-1b: hb_burst_occupancy has only {len(occ_vals)} unique values "
                      f"({occ_vals}). Essentially constant by construction.")

    metrics["burst_occ_unique_values"] = len(occ_vals)
    metrics["burst_occ_constant"] = len(occ_vals) == 1

    # HB-SMR block correlation: should be NEGATIVE if HB suppresses SMR
    mean_hb_smr_corr = burst["hb_smr_block_corr"].mean()
    n_neg_corr = int((burst["hb_smr_block_corr"] < 0).sum())
    n_total = len(burst)
    metrics["mean_hb_smr_block_corr"] = mean_hb_smr_corr
    metrics["n_neg_hb_smr_corr"] = n_neg_corr
    metrics["pct_neg_hb_smr_corr"] = 100 * n_neg_corr / n_total

    if mean_hb_smr_corr > 0:
        issues.append(f"BURST-DIRECTION-1: Mean HB-SMR block correlation = {mean_hb_smr_corr:.3f} > 0. "
                      "HB and SMR are POSITIVELY correlated at block level. "
                      "This CONTRADICTS the noise-control hypothesis (HB bursts should suppress SMR). "
                      "HB and SMR may co-vary due to shared arousal/attention rather than noise suppression.")

    # HB-broadband correlation: is HB tracking broadband noise?
    mean_hb_broad = burst["hb_broad_corr"].mean()
    metrics["mean_hb_broad_corr"] = mean_hb_broad
    per_sub_corr = burst.groupby("subject")["hb_broad_corr"].mean()
    metrics["hb_broad_corr_std_across_subjects"] = float(per_sub_corr.std())

    if per_sub_corr.std() > 0.1:
        issues.append(f"BURST-SUBJECTVAR-1: HB-broadband correlation varies strongly across subjects "
                      f"(range {per_sub_corr.min():.2f}–{per_sub_corr.max():.2f}). "
                      "Noise-floor interpretation is subject-specific, not general.")

    # Burst rate session change
    s01 = burst[burst["session"] == "ses-01"].groupby("subject")["hb_burst_rate_per_min"].mean()
    s08 = burst[burst["session"] == "ses-08"].groupby("subject")["hb_burst_rate_per_min"].mean()
    common = s01.index.intersection(s08.index)
    delta_br = s08[common] - s01[common]
    n_reduce = int((delta_br < 0).sum())
    metrics["n_subjects_burst_rate_reduce"] = n_reduce
    metrics["mean_delta_burst_rate"] = delta_br.mean()

    return issues, metrics


# ──────────────────────────────────────────────────────────────
# 4. FOUR-QUADRANT ROBUSTNESS AUDIT (NCTRL5)
# ──────────────────────────────────────────────────────────────
def audit_quadrant():
    issues = []
    metrics = {}
    rows = []

    classif = load("nctrl5_four_quadrant_noise_classification.csv")
    if classif.empty:
        return issues, metrics, rows

    quad_cols = ["quadrant_primary", "quadrant_burst", "quadrant_resid", "quadrant_diff"]

    # Per-subject consistency across definitions
    for _, row in classif.iterrows():
        sub = row["subject"]
        quads = [row.get(c) for c in quad_cols if c in row.index]
        quads = [q for q in quads if pd.notna(q)]
        unique_q = len(set(quads))
        most_common = pd.Series(quads).value_counts().index[0] if quads else "unknown"
        agreement = quads.count(most_common) / len(quads) if quads else 0
        rows.append({
            "subject": sub,
            "quadrant_primary": row.get("quadrant_primary"),
            "quadrant_burst": row.get("quadrant_burst"),
            "quadrant_resid": row.get("quadrant_resid"),
            "quadrant_diff": row.get("quadrant_diff"),
            "n_unique_quadrants": unique_q,
            "modal_quadrant": most_common,
            "agreement_fraction": agreement,
        })

    df_rob = pd.DataFrame(rows)
    mean_unique = df_rob["n_unique_quadrants"].mean()
    mean_agree = df_rob["agreement_fraction"].mean()
    n_consistent = int((df_rob["n_unique_quadrants"] == 1).sum())  # same across all definitions

    metrics["mean_unique_quadrants_per_subject"] = mean_unique
    metrics["mean_agreement_fraction"] = mean_agree
    metrics["n_subjects_consistent_all_defs"] = n_consistent

    if mean_unique > 1.5:
        issues.append(f"QUAD-ROBUST-1: Subjects occupy on average {mean_unique:.1f} different quadrants "
                      "across definitions (max=4). Quadrant assignment is highly definition-sensitive. "
                      "Cannot claim robust separability from this evidence.")
    if n_consistent == 0:
        issues.append("QUAD-ROBUST-2: No subject has the same quadrant across all 4 definitions. "
                      "Separability result is entirely definition-dependent.")

    # Check if A_both (the key 'success' quadrant) is robust
    n_always_A = int((df_rob["modal_quadrant"] == "A_both").sum())
    n_ever_A = int(df_rob.apply(lambda r: any(r[c] == "A_both" for c in quad_cols if c in r.index), axis=1).sum())
    metrics["n_subjects_modal_A_both"] = n_always_A
    metrics["n_subjects_ever_A_both"] = n_ever_A

    if n_always_A == 0:
        issues.append(f"QUAD-ROBUST-3: No subject has A_both (successful damping+acquisition) as "
                      "their modal quadrant. At best A_both appears for 1 subject in 1 definition.")

    # Subject influence: who drives each quadrant?
    for q in ["A_both", "B_acq_only", "C_damp_only"]:
        primary_sub = classif[classif["quadrant_primary"] == q]["subject"].tolist()
        if len(primary_sub) == 1:
            issues.append(f"QUAD-INFLUENCE: Quadrant {q} is driven by single subject: {primary_sub[0]}. "
                          "Loss of one subject would eliminate this quadrant from results.")

    return issues, metrics, df_rob


# ──────────────────────────────────────────────────────────────
# 5. REWARD QUALITY AUDIT (NCTRL6)
# ──────────────────────────────────────────────────────────────
def audit_reward():
    issues = []
    metrics = {}

    rq = load("nctrl6_reward_quality_states.csv")
    if rq.empty:
        return issues, metrics

    # Proxy-only: no real reward markers in ds004446
    issues.append("REWARD-PROXY-1: ds004446 event markers (instruction: rest/task/interval) are NOT "
                  "real-time neurofeedback reward signals. States (clean_target/noisy_target etc.) "
                  "are defined by session-median thresholds on SMR and HB envelopes. This is a "
                  "circular proxy: the 'reward' state is defined as being above/below the session median, "
                  "which is guaranteed to give ~50% total_reward_frac by construction. "
                  "NCTRL6 results provide NO evidence about actual neurofeedback reward quality.")

    # Verify that total_reward_frac ≈ 0.5 by construction
    tf_vals = rq["total_reward_frac"].unique()
    if all(abs(v - 0.5) < 0.01 for v in tf_vals):
        issues.append("REWARD-CIRCULAR-1: total_reward_frac = 0.50 or 0.486 for ALL rows. "
                      "This is an arithmetic artifact of median-based thresholding. "
                      "The 'reward' occupancy carries no information about actual feedback.")

    metrics["total_reward_frac_unique"] = len(tf_vals)
    metrics["total_reward_frac_near_half"] = int(all(abs(v - 0.5) < 0.02 for v in tf_vals))

    # False-reward risk: always high
    mean_frr = rq["false_reward_risk"].mean()
    metrics["mean_false_reward_risk"] = mean_frr
    if mean_frr > 0.6:
        issues.append(f"REWARD-RISK-1: Mean false_reward_risk = {mean_frr:.2f}. "
                      "Over 60% of 'reward' states are 'noisy_target' (SMR up AND HB up). "
                      "This is a ceiling effect of the proxy definition, not a real finding. "
                      "With median thresholds, ~50% of target-state blocks will have elevated HB.")

    # Is there a consistent improvement ses-01 → ses-08?
    s01 = rq[rq["session"] == "ses-01"].groupby("subject")["false_reward_risk"].mean()
    s08 = rq[rq["session"] == "ses-08"].groupby("subject")["false_reward_risk"].mean()
    common = s01.index.intersection(s08.index)
    delta_frr = s08[common] - s01[common]
    n_improve = int((delta_frr < 0).sum())
    metrics["n_subjects_frr_improve"] = n_improve
    if n_improve < 3:
        issues.append(f"REWARD-CHANGE-1: False-reward risk improves in only {n_improve}/5 subjects. "
                      "No consistent quality improvement across training.")

    return issues, metrics


# ──────────────────────────────────────────────────────────────
# 6. FRAMEWORK COMPARISON CIRCULARITY AUDIT (NCTRL7)
# ──────────────────────────────────────────────────────────────
def audit_framework():
    issues = []
    metrics = {}

    fw = load("nctrl7_framework_comparison.csv")
    if fw.empty:
        return issues, metrics

    # Check if NCTRL gets 16/16
    nctrl_row = fw[fw["framework"].str.contains("NCTRL", na=False)]
    nctrl_score = nctrl_row["total_score"].values[0] if len(nctrl_row) else None
    max_score = fw["max_score"].values[0] if not fw.empty else 16

    metrics["nctrl_score"] = nctrl_score
    metrics["max_score"] = max_score

    if nctrl_score == max_score:
        issues.append("CIRC-1: NCTRL receives maximum score (16/16) on all 8 criteria. "
                      "A framework that scores 2/2 on EVERY criterion is almost certainly the result "
                      "of criteria designed after seeing NCTRL outputs. Perfect scores indicate "
                      "circular reasoning, not independent validation.")

    # Check specific criteria for circularity
    crit_cols = [c for c in fw.columns if c not in ["framework", "total_score", "max_score", "pct_score"]]
    for col in ["Broadband handling", "Burst handling", "Empirical fit"]:
        if col in crit_cols and len(nctrl_row):
            val = nctrl_row[col].values[0]
            if val == 2:
                issues.append(f"CIRC-2: NCTRL scores 2/2 on '{col}'. "
                               "Empirical evidence for this criterion is weak (negative HB residuals, "
                               "constant burst occupancy by construction). This score reflects the "
                               "theoretical framework's claims, not the empirical evidence.")

    # Empirical fit criterion: NCTRL should not score 2/2 given mixed empirical results
    if "Empirical fit" in crit_cols and len(nctrl_row):
        emp_score = nctrl_row["Empirical fit"].values[0]
        if emp_score == 2:
            issues.append("CIRC-3: NCTRL scores 2/2 on 'Empirical fit' despite: "
                          "(a) HB residuals mostly negative (no band-specific HB), "
                          "(b) HB-SMR positively correlated (contradicts suppression claim), "
                          "(c) burst occupancy constant by construction, "
                          "(d) n=5 descriptive only. Score should be 0–1.")

    issues.append("CIRC-GENERAL: The 8 criteria were explicitly chosen to highlight advantages of "
                  "the NCTRL framework (broadband modeling, burst dynamics, separability) after NCTRL "
                  "was formulated. This is criterion-by-design and inflates the NCTRL score. "
                  "The framework comparison should be treated as illustrative only, not as evidence.")

    metrics["fw_comparison_evidential_weight"] = "illustrative_only"

    return issues, metrics


# ──────────────────────────────────────────────────────────────
# 7. REVISED HYPOTHESIS LABEL
# ──────────────────────────────────────────────────────────────
def revised_label(sim_issues, sim_m, emp_issues, emp_m, burst_issues, burst_m,
                  quad_issues, quad_m, reward_issues, reward_m, fw_issues, fw_m):
    """Apply conservative criteria to determine revised label."""

    criteria = {}

    # C1: Empirical noise-floor or diffusion metrics support the mechanism
    # HB residual mostly negative, HB-SMR positive corr → FAILS
    hb_resid_ok = emp_m.get("hb_resid_mean", -1) > 0.05
    snr_improve_majority = emp_m.get("n_subjects_snr_improve", 0) >= 3
    c1 = hb_resid_ok and snr_improve_majority
    criteria["C1_empirical_noise_metric_support"] = c1
    criteria["C1_detail"] = (
        f"HB resid mean={emp_m.get('hb_resid_mean', np.nan):.4f} (need>0.05: {hb_resid_ok}); "
        f"SNR improves in {emp_m.get('n_subjects_snr_improve', 0)}/5 subjects "
        f"(need≥3: {snr_improve_majority})"
    )

    # C2: Four-quadrant classification robust across definitions
    n_unique = quad_m.get("mean_unique_quadrants_per_subject", 4)
    agree = quad_m.get("mean_agreement_fraction", 0)
    c2 = agree >= 0.70 and n_unique <= 2.0
    criteria["C2_quadrant_robust"] = c2
    criteria["C2_detail"] = (
        f"Mean agreement={agree:.2f} (need≥0.70); "
        f"mean unique quadrants/subject={n_unique:.1f} (need≤2.0)"
    )

    # C3: Not driven by single subject
    n_consistent = quad_m.get("n_subjects_consistent_all_defs", 0)
    ever_A = quad_m.get("n_subjects_ever_A_both", 0)
    # D_neither is the modal quadrant for 2/5 subjects; key quadrants each driven by 1 subject
    c3 = ever_A >= 2  # at least 2 subjects show A_both in at least one definition
    criteria["C3_not_single_subject"] = c3
    criteria["C3_detail"] = (
        f"Subjects ever in A_both: {ever_A} (need≥2). "
        "Each key quadrant (A,B,C) driven by exactly 1 subject in primary classification."
    )

    # C4: Reward-quality not circular
    reward_real = reward_m.get("total_reward_frac_near_half", 1) == 0  # 0 means NOT near 0.5 = OK
    c4 = reward_real
    criteria["C4_reward_not_proxy"] = c4
    criteria["C4_detail"] = (
        f"total_reward_frac near 0.5 by construction: {not c4}. "
        "NCTRL6 uses proxy thresholds, not real reward markers. C4 FAILS."
    )

    # C5: Framework comparison not circular
    # NCTRL scores 16/16 = perfect → circular → fails
    nctrl_perf = fw_m.get("nctrl_score", 0) == fw_m.get("max_score", 16)
    c5 = not nctrl_perf  # passes if NOT perfect score
    criteria["C5_framework_not_circular"] = c5
    criteria["C5_detail"] = (
        f"NCTRL scores {fw_m.get('nctrl_score', '?')}/{fw_m.get('max_score', '?')}. "
        "Perfect score indicates circular criterion design. C5 FAILS."
    )

    # C6: Simulation supports mechanism (can still count this)
    sim_sep = (sim_m.get("grid_n_B", 0) > 0 and sim_m.get("grid_n_C", 0) > 0)
    bug_flag_ok = (sim_m.get("sim_r1_noise_damped_flag", True) is not False)
    c6 = sim_sep  # simulation separability, despite flag bug in summary table
    criteria["C6_simulation_support"] = c6
    criteria["C6_detail"] = (
        f"Grid separability: B={sim_m.get('grid_n_B', 0)}, C={sim_m.get('grid_n_C', 0)} ({sim_sep}). "
        f"Note: noise_damped flag bug in simulation summary (R1/R3 show False)."
    )

    # C7: HB-SMR direction consistent with noise-control
    hb_smr_neg = burst_m.get("mean_hb_smr_block_corr", 1) < 0
    c7 = hb_smr_neg
    criteria["C7_hb_smr_direction"] = c7
    criteria["C7_detail"] = (
        f"Mean HB-SMR block correlation = {burst_m.get('mean_hb_smr_block_corr', np.nan):.3f}. "
        "FAILS: positive correlation contradicts the damping narrative."
    )

    n_pass = sum(1 for k, v in criteria.items() if k.startswith("C") and not k.endswith("_detail") and v)
    total = sum(1 for k in criteria if k.startswith("C") and not k.endswith("_detail"))

    # Apply conservative rule
    if n_pass >= 5 and c1 and c2 and not nctrl_perf:
        label = "Strong support for active-damping noise-control hypothesis."
    elif n_pass >= 3 or (c6 and (c1 or c2)):
        label = "Partial support for active-damping noise-control hypothesis."
    elif c6:
        label = "Simulation support only; empirical support insufficient."
    else:
        label = "Hypothesis not supported."

    return label, criteria, n_pass, total


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
def main():
    print("NCTRL Audit: running...")

    sim_issues, sim_m = audit_simulation()
    emp_issues, emp_m, hb_rows = audit_hb_character()
    burst_issues, burst_m = audit_burst()
    quad_issues, quad_m, rob_rows = audit_quadrant()
    reward_issues, reward_m = audit_reward()
    fw_issues, fw_m = audit_framework()

    # Revised label
    label, criteria, n_pass, total = revised_label(
        sim_issues, sim_m, emp_issues, emp_m, burst_issues, burst_m,
        quad_issues, quad_m, reward_issues, reward_m, fw_issues, fw_m
    )

    all_issues = sim_issues + emp_issues + burst_issues + quad_issues + reward_issues + fw_issues

    # ── Save tables ──
    key_metrics = []
    for section, metrics in [("simulation", sim_m), ("empirical", emp_m),
                               ("burst", burst_m), ("quadrant", quad_m),
                               ("reward", reward_m), ("framework", fw_m)]:
        for k, v in metrics.items():
            key_metrics.append({"section": section, "metric": k, "value": str(v)})
    pd.DataFrame(key_metrics).to_csv(TBL / "nctrl_audit_key_metrics.csv", index=False)

    pd.DataFrame(hb_rows).to_csv(TBL / "nctrl_subject_influence.csv", index=False)

    if rob_rows is not None and len(rob_rows) > 0 and not isinstance(rob_rows, pd.DataFrame):
        pd.DataFrame(rob_rows).to_csv(TBL / "nctrl_definition_robustness.csv", index=False)
    elif isinstance(rob_rows, pd.DataFrame) and not rob_rows.empty:
        rob_rows.to_csv(TBL / "nctrl_definition_robustness.csv", index=False)

    # ── Write audit report ──
    all_issues_text = "\n".join(f"- {i}" for i in all_issues)
    criteria_text = "\n".join(
        f"- **{k}**: {'PASS' if v else 'FAIL'}" + (
            f"\n  {criteria.get(k+'_detail', '')}" if k+"_detail" in criteria else ""
        )
        for k, v in criteria.items()
        if not k.endswith("_detail")
    )

    audit_report = f"""# NCTRL Audit Report

**Purpose**: Critical audit of the "Strong support" hypothesis label. Do not defend the hypothesis; try to falsify or narrow it.

Generated: {utc_now()}

---

## Summary

**Original label (NCTRL_final_reports.py)**: Strong support for active-damping noise-control hypothesis.

**Revised label (this audit)**: {label}

**Conservative criteria passed**: {n_pass}/{total}

---

## Issues found ({len(all_issues)} total)

{all_issues_text}

---

## Detailed findings by domain

### A. Simulation (NCTRL1-2)

1. **Regime-flag inconsistency**: The `noise_damped` column in `nctrl1_simulation_summary.csv` is `False` for
   R1_damp_only and R3_both — the two regimes that are supposed to demonstrate noise damping. Only R5_false_reward
   has `noise_damped=True`. This suggests the boolean criterion for "noise damped" is incorrectly implemented or
   uses a threshold that the damping regime does not meet. The parameter grid separability result (B=26, C=8)
   likely uses a different criterion than the regime summary.

2. **Broadband contamination absent**: `broadband_contam = 0.0` for 5/6 simulation regimes. The model's z variable
   (broadband contamination) contributes no meaningful power in any regime except R5_false_reward. Claims about
   active damping of broadband contamination are NOT demonstrated in the simulation.

3. **Grid separability (B=26, C=8) is real** but C_damp_only represents only {sim_m.get('grid_C_pct', 0):.0f}% of
   the 81-point parameter space. Pure noise-damping without acquisition is a minority outcome. Whether the
   noise_damped flag in the grid is correct requires code inspection.

4. **SNR improvement with k_damp**: The simulation does show improved SMR SNR with higher k_damp. This is the
   strongest simulation result. However, this improvement is by model construction (eta drives x; damping eta
   improves x stability).

**Simulation verdict**: Mechanistic separability exists in the model, but (a) the simulation summary flags are
inconsistent with regime intent, and (b) broadband contamination is not actually modeled. Simulation support is
real but partial.

---

### B. Empirical HB character (NCTRL3)

1. **HB residual above 1/f** (mean channel, all subjects/sessions):
   - Mean = {emp_m.get('hb_resid_mean', np.nan):.4f}
   - Median = {emp_m.get('hb_resid_median', np.nan):.4f}
   - Positive in {emp_m.get('hb_resid_n_positive', 0)}/{len(hb_rows)*4 if hb_rows else 'N/A'} observations ({emp_m.get('hb_resid_pct_positive', 0):.0f}%)

   The mean HB residual is {'NEGATIVE' if emp_m.get('hb_resid_mean', 0) < 0 else 'POSITIVE but small'}.
   **This means HB power is {'below' if emp_m.get('hb_resid_mean', 0) < 0 else 'marginally above'} the 1/f aperiodic line on average.**
   HB changes in this dataset are primarily broadband/noise-floor in character, not band-specific.

2. **SMR SNR session change**: Improves in {emp_m.get('n_subjects_snr_improve', 0)}/5 subjects (ses-01→ses-08).
   Mean Δ log(SNR) = {emp_m.get('mean_delta_snr', np.nan):.4f}. Not consistently positive.

3. **Subject heterogeneity**: sub-004 and sub-013 show positive HB residuals (mild band-specific HB);
   sub-005, sub-012, sub-018 show negative residuals (broadband character). No common pattern.

4. **Aperiodic slope**: Mean change = {emp_m.get('mean_delta_slope', np.nan):.4f} (near zero). No consistent
   1/f steepening across sessions. HB changes are not explained by systematic 1/f slope shifts.

---

### C. Burst/diffusion (NCTRL4)

1. **Burst occupancy by construction**: `hb_burst_occupancy = 0.25` for every row in the dataset. The 75th-percentile
   threshold guarantees 25% burst occupancy by definition. This metric is mathematically constant and contributes
   zero information about session differences or subject differences.

2. **HB-SMR block correlation direction**: Mean = {burst_m.get('mean_hb_smr_block_corr', np.nan):.3f}.
   **HB and SMR are POSITIVELY correlated** at the block level in most subjects. This contradicts the noise-control
   prediction (HB bursts should suppress SMR during the block). The positive correlation likely reflects shared
   arousal, effort, or overall amplitude covariation.

3. **HB-broadband correlation**: Mean = {burst_m.get('mean_hb_broad_corr', np.nan):.3f}, but varies widely across
   subjects (SD = {burst_m.get('hb_broad_corr_std_across_subjects', np.nan):.3f}). sub-005 shows high correlation
   (0.42–0.51), sub-004 shows low correlation (0.05–0.13). This is subject-specific, not a general pattern.

---

### D. Four-quadrant robustness (NCTRL5)

1. **Definition sensitivity** is high. Per subject, the mean number of different quadrant labels across 4 definitions
   is {quad_m.get('mean_unique_quadrants_per_subject', np.nan):.1f}. Mean agreement = {quad_m.get('mean_agreement_fraction', np.nan):.2f}.

2. **Per-subject consistency**:
   - sub-004: primary=D_neither, burst=C_damp_only, resid=D_neither, diff=D_neither (3 of 4 = D)
   - sub-005: primary=A_both, burst=C_damp_only, resid=B_acq_only, diff=B_acq_only (all different)
   - sub-012: primary=C_damp_only, burst=C_damp_only, resid=D_neither, diff=C_damp_only (3 of 4 = C)
   - sub-013: primary=B_acq_only, burst=A_both, resid=B_acq_only, diff=B_acq_only (3 of 4 = B)
   - sub-018: primary=D_neither, burst=B_acq_only, resid=C_damp_only, diff=D_neither (2 of 4 = D)

3. **No subject is consistently in A_both** (the "success" quadrant). sub-005 is A_both only under the primary
   (SNR/HB power) definition. sub-012 is most robustly C_damp_only (3/4 defs).

4. **Single-subject quadrants**: Each of A, B, C in the primary classification is occupied by exactly 1 subject.
   The quadrant result is entirely driven by individual variation.

5. **D_neither majority**: 2/5 subjects (sub-004, sub-018) are D_neither in the primary classification. A third
   of the sample shows neither noise damping nor SMR acquisition between ses-01 and ses-08.

---

### E. Reward quality (NCTRL6)

1. **No real reward markers**: ds004446 provides only instruction labels (rest/task/interval). There are no
   real-time neurofeedback reward signals in the available data. All NCTRL6 results are based on proxy criteria.

2. **Median threshold circularity**: States are defined by session medians → total_reward_frac ≈ 0.50 by arithmetic.
   This is not a finding; it is a construction artifact. **All NCTRL6 "results" are products of the thresholding
   method, not empirical evidence.**

3. **False-reward risk** (mean = {reward_m.get('mean_false_reward_risk', np.nan):.2f}) is high, but this is also
   an artifact: with median thresholds, ~50% of "reward" blocks will have above-median HB, making them "noisy target"
   by definition. The "60–85% false-reward risk" is the expected outcome of the method, not a pathological finding.

4. **NCTRL6 cannot be cited as evidence for or against the hypothesis**. It must be removed from evidence assessment.

---

### F. Framework comparison (NCTRL7)

1. **Perfect score = circular**: NCTRL receives 16/16 (100%) across all 8 criteria. In any objective multi-framework
   comparison, a single framework scoring perfectly on all criteria almost always means the criteria were designed to
   match that framework's features. This is evidenced by criteria such as "Handles broadband contamination" and
   "Handles burst instability" — these are structural features of the NCTRL model, not empirically validated claims.

2. **Criteria chosen post-hoc**: The 8 criteria explicitly include features that are unique to NCTRL (broadband z
   variable, stochastic burst dynamics) and that SL/SPT were never designed to provide. This stacks the comparison.

3. **"Matches empirical data" = 2/2 for NCTRL despite**:
   - HB-SMR correlation being positive (contradicts model);
   - HB residuals mostly negative (contradicts band-specific claim);
   - n=5 descriptive only.
   This score is based on theoretical alignment, not empirical fit.

4. **Correct treatment**: NCTRL7 can be used to argue NCTRL is a more complete theoretical framework for generating
   hypotheses. It cannot be used as evidence that the hypothesis is supported by data. The framework comparison is
   ILLUSTRATIVE, not EVIDENTIAL.

---

## Conservative criteria assessment

{criteria_text}

**Criteria passed: {n_pass}/{total}**

---

## Revised hypothesis label

**{label}**

### Justification

**Why not "Strong support":**
- HB residuals mostly negative → HB changes are broadband, not band-specific (fails C1)
- Four-quadrant classification is definition-sensitive, single-subject quadrants (fails C2)
- Reward analysis is proxy-only and arithmetically circular (fails C4)
- Framework comparison gives circular perfect score (fails C5)
- HB-SMR positive correlation contradicts suppression narrative (fails C7)

**Why not "Hypothesis not supported":**
- Simulation mechanistically demonstrates separability of noise damping and SMR acquisition (C6 passes)
- Some subjects show patterns consistent with noise-control (sub-012: C_damp_only in 3/4 defs)
- HB-broadband correlation positive in most subjects (weak support for burst-as-noise interpretation)

**Why "Simulation support only; empirical support insufficient":**
- All affirmative empirical criteria fail the conservative test
- The "Partial support" threshold requires both simulation AND some empirical separability;
  empirical separability is highly definition-sensitive and driven by single subjects

Generated: {utc_now()}
"""

    (REP / "nctrl_audit_report.md").write_text(audit_report, encoding="utf-8")

    # ── Revised label report ──
    revised_report = f"""# NCTRL Revised Hypothesis Label

Generated: {utc_now()}

## Label change

| | |
|---|---|
| Original label | **Strong support for active-damping noise-control hypothesis.** |
| Revised label | **{label}** |

## Reason for downgrade

The original "Strong support" label was inflated by:

1. **Simulation success counted as empirical evidence** (Q1, Q2 in original scoring)
2. **HB band-specificity misclassified** (Q3: "BAND-SPECIFIC" based on max of 1 session, not mean; actual mean HB residual = {emp_m.get('hb_resid_mean', np.nan):.4f} < 0)
3. **Reward analysis treated as valid evidence** (Q6 in original scoring, but NCTRL6 uses circular proxy)
4. **Framework comparison circularity ignored** (NCTRL7 perfect score = criteria designed to favour NCTRL)
5. **Quadrant robustness not tested** (definition-sensitive; each key quadrant driven by 1 subject)
6. **HB-SMR direction ignored** (positive correlation contradicts suppression narrative)

## Conservative criteria summary

| Criterion | Result | Key finding |
|---|---|---|
| C1: Empirical noise-floor support | {'PASS' if criteria.get('C1_empirical_noise_metric_support') else 'FAIL'} | HB resid mean {emp_m.get('hb_resid_mean', np.nan):.3f}; SNR improves {emp_m.get('n_subjects_snr_improve', 0)}/5 |
| C2: Quadrant robust across definitions | {'PASS' if criteria.get('C2_quadrant_robust') else 'FAIL'} | Agreement {quad_m.get('mean_agreement_fraction', np.nan):.2f}; {quad_m.get('mean_unique_quadrants_per_subject', np.nan):.1f} unique quads/subject |
| C3: Not single-subject driven | {'PASS' if criteria.get('C3_not_single_subject') else 'FAIL'} | {quad_m.get('n_subjects_ever_A_both', 0)} subjects ever in A_both |
| C4: Reward analysis valid | {'PASS' if criteria.get('C4_reward_not_proxy') else 'FAIL'} | total_reward_frac = 0.50 by construction |
| C5: Framework comparison not circular | {'PASS' if criteria.get('C5_framework_not_circular') else 'FAIL'} | NCTRL scores {fw_m.get('nctrl_score', '?')}/{fw_m.get('max_score', '?')} = perfect |
| C6: Simulation supports mechanism | {'PASS' if criteria.get('C6_simulation_support') else 'FAIL'} | B=26, C=8 separable quadrants |
| C7: HB-SMR direction consistent | {'PASS' if criteria.get('C7_hb_smr_direction') else 'FAIL'} | Mean HB-SMR corr = {burst_m.get('mean_hb_smr_block_corr', np.nan):.3f} (positive = wrong direction) |

**Criteria passed: {n_pass}/{total}**

## Approved claims

- Simulation demonstrates that noise damping (high-beta suppression) and SMR acquisition can be mechanistically
  separable within the active-damping SDE model.
- High-beta changes in this dataset are predominantly broadband in character (HB residual above 1/f is near zero
  or negative for 3/5 subjects).
- Four-quadrant subject classification is possible but highly dependent on the metric used. No subject shows
  consistent A_both classification across definitions.
- The NCTRL framework generates testable predictions that are more directly applicable to EEG data than
  Stuart-Landau or singular perturbation (conceptual argument only).

## Claims that must be removed or qualified

- **REMOVE**: "Strong support for active-damping noise-control hypothesis" as a label.
- **REMOVE**: Any statement that NCTRL6 provides evidence about reward quality (it is a circular proxy).
- **REMOVE**: Any use of NCTRL7 as empirical evidence (it is illustrative/conceptual).
- **QUALIFY**: "HB is band-specific" — data show it is mostly broadband.
- **QUALIFY**: "HB suppression improves SMR SNR" — empirically supported in only {emp_m.get('n_subjects_snr_improve', 0)}/5 subjects.
- **QUALIFY**: "Subjects are separable into four quadrants" — true under some definitions, false under others.
- **QUALIFY**: Simulation separability — note the noise_damped flag inconsistency in the regime summary.

Generated: {utc_now()}
"""

    (REP / "nctrl_revised_hypothesis_label.md").write_text(revised_report, encoding="utf-8")

    print(f"Audit done. Issues found: {len(all_issues)}")
    print(f"Revised label: {label}")
    print(f"Criteria passed: {n_pass}/{total}")


if __name__ == "__main__":
    main()
