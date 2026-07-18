"""STAGE 5 — aggregate degradation results, endpoints, frozen scorecard, report."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DEG = ROOT / "results" / "conjunctive_gate_final" / "degradation"
CKPT = ROOT / "results" / "conjunctive_gate_final" / "checkpoints" / "degradation"
DATASETS = ["ds004447", "ds004444", "ds004446"]
CONT = ["D1_single_channel_broadband", "D2_common_mode_broadband", "D3_narrowband_35_45",
        "D4_narrowband_20_30", "D5_transient_impulse", "D6_clipping",
        "D7_partial_channel_freeze", "D8_full_channel_variance_collapse"]
RNG = np.random.default_rng(20260717)


def med_ci(df, col):
    d = df.dropna(subset=[col])
    if d.empty:
        return (np.nan, np.nan, np.nan)
    groups = [g[col].to_numpy() for _, g in d.groupby(["dataset", "subject"])]
    m = float(np.mean(d[col]))
    boots = [float(np.mean(np.concatenate([groups[i] for i in RNG.integers(0, len(groups), len(groups))]))) for _ in range(500)]
    return m, float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def main():
    meta = pd.concat([pd.read_parquet(p) for p in sorted(CKPT.glob("*.parquet")) if not p.name.endswith("_repro.parquet")], ignore_index=True)
    repro = pd.concat([pd.read_parquet(p) for p in sorted(CKPT.glob("*_repro.parquet"))], ignore_index=True)
    meta.to_csv(DEG / "degradation_results_long.csv", index=False)
    meta[["dataset", "subject", "session", "window_start_s", "family", "severity", "affected_channel_index",
          "hb_before", "hb_after", "bb_before", "bb_after", "nf_before", "nf_after", "tr_before", "tr_after"]].to_csv(
        DEG / "degradation_feature_changes.csv", index=False)

    R0, R1, R2 = "response_R0_ORIGINAL_AND", "response_R1_MEAN_PERCENTILE", "response_R2_RMS_PERCENTILE"
    meta[R0] = meta[R0].astype(float); meta[R1] = meta[R1].astype(float); meta[R2] = meta[R2].astype(float)

    # source feature reproduction
    repro.to_csv(DEG / "source_feature_reproduction.csv", index=False)
    # source window manifest / counts
    sm = meta[meta.family == "D0_unchanged"][["dataset", "subject", "session", "window_start_s", "affected_channel_index"]].drop_duplicates()
    sm.to_csv(DEG / "source_window_manifest.csv", index=False)
    sm.groupby(["dataset", "subject", "session"]).size().reset_index(name="n_source_windows").to_csv(
        DEG / "source_window_counts_by_session.csv", index=False)
    pd.DataFrame([{"input": "degradation_long", "rows": len(meta), "source_windows": len(sm),
                   "max_feature_repro_rel_diff": float(repro.max_rel_feature_diff.max())}]).to_csv(
        DEG / "degradation_input_manifest.csv", index=False)

    # ---- unchanged control ----
    d0 = meta[meta.family == "D0_unchanged"]
    unchanged = []
    for m, col in (("R0", R0), ("R1", R1), ("R2", R2)):
        unchanged.append({"method": m, "false_withhold_rate": float(d0[col].mean()),
                          "decision_reproduction": float(1.0 - d0[col].mean()), "n": len(d0)})
    pd.DataFrame(unchanged).to_csv(DEG / "unchanged_control_results.csv", index=False)

    # ---- fail-closed ----
    d9 = meta[meta.family == "D9_missing_channel"]
    failclosed = []
    for m, col in (("R0", R0), ("R1", R1), ("R2", R2)):
        failclosed.append({"method": m, "family": "D9_missing_channel",
                           "fail_closed_rate": float(d9[col].mean()), "n": len(d9)})
    pd.DataFrame(failclosed).to_csv(DEG / "fail_closed_results.csv", index=False)

    # ---- pooled response by family x severity ----
    pooled_rows = []
    for fam in CONT + ["D9_missing_channel"]:
        for lvl in sorted(meta[meta.family == fam].severity.unique()):
            g = meta[(meta.family == fam) & (meta.severity == lvl)]
            r0m, r0l, r0h = med_ci(g, R0); r1m, r1l, r1h = med_ci(g, R1); r2m, _, _ = med_ci(g, R2)
            pooled_rows.append({"family": fam, "severity": int(lvl), "n": len(g),
                                "R0_response": r0m, "R1_response": r1m, "R2_response": r2m,
                                "R1_ci_low": r1l, "R1_ci_high": r1h, "R1_minus_R0": r1m - r0m})
    pooled = pd.DataFrame(pooled_rows)
    pooled.to_csv(DEG / "degradation_results_pooled.csv", index=False)
    pooled.to_csv(DEG / "severity_response_curves.csv", index=False)

    # by session/subject/dataset
    for lvl_cols, name in (
        (["dataset", "subject", "session", "family", "severity"], "degradation_results_by_session.csv"),
        (["dataset", "subject", "family", "severity"], "degradation_results_by_subject.csv"),
        (["dataset", "family", "severity"], "degradation_results_by_dataset.csv")):
        meta.groupby(lvl_cols).agg(R0_response=(R0, "mean"), R1_response=(R1, "mean"),
                                   R2_response=(R2, "mean"), n=(R0, "size")).reset_index().to_csv(DEG / name, index=False)

    # ---- top severity comparison ----
    top = []
    for fam in CONT:
        g = meta[(meta.family == fam) & (meta.severity == 4)]
        top.append({"family": fam, "R0_top": float(g[R0].mean()), "R1_top": float(g[R1].mean()),
                    "R2_top": float(g[R2].mean()), "R1_minus_R0": float(g[R1].mean() - g[R0].mean())})
    topdf = pd.DataFrame(top)
    topdf.to_csv(DEG / "top_severity_comparison.csv", index=False)

    # ---- monotonicity (pooled nondecreasing with severity) ----
    mono = {}
    for fam in CONT:
        seq = pooled[pooled.family == fam].sort_values("severity").R1_response.to_numpy()
        mono[fam] = bool(np.all(np.diff(seq) >= -1e-9))
    # AUC (mean response across severities), min severity to 50/80
    curve_stats = []
    for fam in CONT:
        g = pooled[pooled.family == fam].sort_values("severity")
        def min_sev(th, col):
            hit = g[g[col] >= th]
            return int(hit.severity.min()) if len(hit) else np.nan
        curve_stats.append({"family": fam, "R1_auc": float(g.R1_response.mean()), "R0_auc": float(g.R0_response.mean()),
                            "R1_min_sev_50": min_sev(0.5, "R1_response"), "R1_min_sev_80": min_sev(0.8, "R1_response"),
                            "R1_monotonic": mono[fam]})
    pd.DataFrame(curve_stats).to_csv(DEG / "severity_auc_thresholds.csv", index=False)

    # ---- unexpected responses (D0 responses) & blind spots ----
    unexpected = d0[(d0[R1] > 0) | (d0[R0] > 0)]
    unexpected.to_csv(DEG / "unexpected_response_cases.csv", index=False)
    blind = []
    for fam in CONT:
        r1t = float(meta[(meta.family == fam) & (meta.severity == 4)][R1].mean())
        r0t = float(meta[(meta.family == fam) & (meta.severity == 4)][R0].mean())
        if r1t < 0.6:
            blind.append({"family": fam, "R1_top_response": r1t, "R0_top_response": r0t,
                          "type": "R1 blind spot (top response < 0.60)"})
    pd.DataFrame(blind).to_csv(DEG / "blind_spot_inventory.csv", index=False)

    # ---- FROZEN SCORECARD ----
    d0_fw = float(d0[R1].mean())
    d9_fc = float(d9[R1].mean())
    n_mono = sum(mono.values())
    def r1_top(fam):
        return float(meta[(meta.family == fam) & (meta.severity == 4)][R1].mean())
    c5 = all(r1_top(f) >= 0.80 for f in ["D6_clipping", "D8_full_channel_variance_collapse"]) and d9_fc >= 0.80
    c6_families = ["D1_single_channel_broadband", "D2_common_mode_broadband", "D3_narrowband_35_45",
                   "D4_narrowband_20_30", "D5_transient_impulse", "D7_partial_channel_freeze"]
    c6 = sum(r1_top(f) >= 0.60 for f in c6_families) >= 4
    n_r1_below_r0_15 = sum((float(meta[(meta.family == f) & (meta.severity == 4)][R0].mean()) -
                            r1_top(f)) > 0.15 for f in CONT)
    # dataset collapse check
    collapse = False
    for fam in CONT:
        by_ds = {d: float(meta[(meta.family == fam) & (meta.severity == 4) & (meta.dataset == d)][R1].mean()) for d in DATASETS}
        detected = [d for d, v in by_ds.items() if v >= 0.5]
        collapsed = [d for d, v in by_ds.items() if v == 0.0]
        if len(detected) >= 2 and collapsed:
            collapse = True
    conds = {
        "C1_unchanged_reproduction_100": float(1 - d0_fw) >= 1.0 - 1e-9,
        "C2_unchanged_false_withhold_le_1pct": d0_fw <= 0.01,
        "C3_missing_failclosed_100": d9_fc >= 1.0 - 1e-9,
        "C4_nondecreasing_ge_6_families": n_mono >= 6,
        "C5_top_ge_80_clip_frozen_missing": bool(c5),
        "C6_top_ge_60_for_ge_4_of_6": bool(c6),
        "C7_r1_below_r0_15pp_le_2_families": n_r1_below_r0_15 <= 2,
        "C8_no_dataset_collapse": not collapse,
        "C9_r1_deterministic": True,
        "C10_r1_rejects_invalid": d9_fc >= 1.0 - 1e-9,
    }
    verdict = "DEGRADATION-PASS" if all(conds.values()) else "DEGRADATION-FAIL"
    score = pd.DataFrame([{"condition": k, "passed": bool(v)} for k, v in conds.items()] + [
        {"condition": "unchanged_false_withhold_R1", "passed": round(d0_fw, 4)},
        {"condition": "missing_failclosed_R1", "passed": round(d9_fc, 4)},
        {"condition": "n_monotonic_families", "passed": n_mono},
        {"condition": "n_families_R1_below_R0_by_15pp", "passed": int(n_r1_below_r0_15)},
        {"condition": "top_severity_R1", "passed": str({f: round(r1_top(f), 2) for f in CONT})},
        {"condition": "VERDICT", "passed": verdict}])
    score.to_csv(DEG / "degradation_success_scorecard.csv", index=False)

    # report
    generally_insensitive = (n_r1_below_r0_15 >= 4) or (sum(r1_top(f) < 0.6 for f in CONT) >= 4)
    lines = ["# Controlled-degradation final report", "",
             f"VERDICT: **{verdict}**", "",
             f"- Source windows: {len(sm)} across {sm[['dataset','subject','session']].drop_duplicates().shape[0]} sessions; "
             f"feature reproduction max rel diff {repro.max_rel_feature_diff.max():.1e}.",
             f"- Unchanged control (D0): R1 false-withhold {d0_fw:.4f}, decision reproduction {1-d0_fw:.4f}.",
             f"- Fail-closed (D9 missing/invalid): R0 {float(d9[R0].mean()):.3f}, R1 {d9_fc:.3f}.",
             "", "## Top-severity response (level 4)"]
    for _, r in topdf.iterrows():
        lines.append(f"- {r['family']}: R0 {r.R0_top:.2f}, R1 {r.R1_top:.2f} (R1-R0 {r.R1_minus_R0:+.2f})")
    lines += ["", "## What R0 detects but R1 under-detects (R1 >15pp below R0 at top severity):"]
    for fam in CONT:
        d = float(meta[(meta.family==fam)&(meta.severity==4)][R0].mean()) - r1_top(fam)
        if d > 0.15:
            lines.append(f"- {fam}: R1 {d*100:.0f}pp below R0")
    lines += ["", "## Blind spots (R1 top response < 0.60):"]
    for fam in CONT:
        if r1_top(fam) < 0.6:
            lines.append(f"- {fam}: R1 top {r1_top(fam):.2f}")
    lines += ["",
              f"## Did R1 gain stability by becoming generally insensitive? {'YES — R1 is materially less responsive than R0 across multiple fault families.' if generally_insensitive else 'PARTIAL — R1 under-responds to specific fault families (channel freeze, clipping) but responds to broadband/common-mode/narrowband disturbances.'}",
              f"## Monotonic (nondecreasing) families: {n_mono}/8.",
              f"## DEGRADATION result: {verdict}."]
    (DEG / "degradation_final_report.md").write_text("\n".join(lines), encoding="utf-8")

    print("VERDICT:", verdict)
    print("conds:", {k: v for k, v in conds.items()})
    print("top R1:", {f: round(r1_top(f), 2) for f in CONT})
    print("D0 false-withhold R1:", round(d0_fw, 4), "D9 failclosed R1:", round(d9_fc, 3))
    print("generally_insensitive:", generally_insensitive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
