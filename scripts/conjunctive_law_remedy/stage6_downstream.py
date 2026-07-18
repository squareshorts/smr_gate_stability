"""STAGE 6 (downstream) — information preservation for R1-R3 single-score masks.

Reuses the verified decoder framework: cached decoder features (no EDF), the frozen
fit_score model, identical fold test sets, and M4-retained count-matching targets.
Verified M0 (no gate) and R0=M4 (ORIGINAL_AND) per-fold results are reused, not recomputed.
"""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for c in (ROOT, ROOT / "src"):
    if str(c) not in sys.path:
        sys.path.insert(0, str(c))

from scripts.downstream_decoder_validation.run_decoder_validation import SEEDS, MIN_PER_CLASS, fit_score, valid_selection
from scripts.conjunctive_law_remedy.remedy_methods import calibrate_and_apply

CACHE = ROOT / "results" / "baseline_gate_stability" / "checkpoints" / "features"
DEC = ROOT / "results" / "baseline_gate_stability" / "checkpoints" / "downstream_decoder_features"
FOLDS = ROOT / "results" / "downstream_decoder_validation" / "fold_definition.csv"
BASE_DOWN = ROOT / "results" / "baseline_gate_stability" / "downstream"
OUT = ROOT / "results" / "conjunctive_law_remedy" / "remedy"
FCK = ROOT / "results" / "conjunctive_law_remedy" / "checkpoints" / "downstream_folds"
FCK.mkdir(parents=True, exist_ok=True)
METHODS = ["R1_MEAN_PERCENTILE", "R2_RMS_PERCENTILE", "R3_ROBUST_MAHALANOBIS_PERCENTILE"]
SEEDS = tuple(SEEDS)[:50]  # frozen 50 count-match seeds (yaml)


def load_gz(path):
    with gzip.open(path, "rt") as fh:
        return pd.read_csv(fh)


def decisions_for_session(ds, subj, sess, methods):
    fpath = CACHE / f"{ds}_{subj}_{sess}_canonical.csv.gz"
    frame = load_gz(fpath)
    rest = frame[frame.condition == "rest"].reset_index(drop=True)
    out = frame[["condition", "window_start_s"]].copy()
    for m in methods:
        out[m] = calibrate_and_apply(rest, frame.reset_index(drop=True), m, 75.0)
    return out


def decoder_frame(ds, subj, sess):
    return load_gz(DEC / f"{ds}_{subj}_{sess}_decoder.csv.gz")


def main():
    folds = pd.read_csv(FOLDS)
    folds = folds[folds.status == "valid"].reset_index(drop=True)
    retention = pd.read_csv(BASE_DOWN / "retention_results.csv")
    r0_targets = retention[retention.monitor == "M4_NFSQI_FULL_QUALITY"]

    # cache per-session decoder frames + decisions
    sess_cache = {}
    def get(ds, subj, sess):
        key = (ds, subj, sess)
        if key not in sess_cache:
            dec = decoder_frame(ds, subj, sess)
            dcs = decisions_for_session(ds, subj, sess, METHODS)
            merged = dec.merge(dcs, left_on=["event_label", "time_s"], right_on=["condition", "window_start_s"], how="left")
            sess_cache[key] = merged
        return sess_cache[key]

    decoder_cols = None
    natural_rows, count_rows, retention_rows, nonviable_rows = [], [], [], []
    for seq, fold in enumerate(folds.itertuples(index=False), 1):
        cp = FCK / f"{fold.fold_id}.parquet"
        if cp.exists():
            try:
                prev = pd.read_parquet(cp)
                natural_rows.extend(prev[prev.kind == "natural"].to_dict("records"))
                count_rows.extend(prev[prev.kind == "count_matched"].to_dict("records"))
                continue
            except Exception:
                pass
        train = get(fold.dataset, fold.subject, fold.train_session)
        test = get(fold.dataset, fold.subject, fold.test_session)
        if decoder_cols is None:
            decoder_cols = [c for c in train.columns if c.startswith("decoder_")]
        fold_records = []
        tgt = r0_targets[r0_targets.fold_id == fold.fold_id].set_index("class").retained_windows.to_dict()
        for m in METHODS:
            finite = np.isfinite(train[decoder_cols]).all(axis=1)
            dec_col = train[m].fillna(False).astype(bool)
            selected = train.loc[finite & dec_col].copy()
            if not valid_selection(selected):
                nonviable_rows.append({"fold_id": fold.fold_id, "method": m, "analysis": "natural",
                                       "reason": "fewer than 10 retained per class", "status": "nonviable"})
                continue
            score, _ = fit_score(selected, test, decoder_cols)
            rec = {"kind": "natural", "fold_id": fold.fold_id, "dataset": fold.dataset, "subject": fold.subject,
                   "method": m, "balanced_accuracy": score["balanced_accuracy"], "seed": np.nan}
            natural_rows.append(rec); fold_records.append(rec)
            # count-matched to R0 (M4) targets
            failed = False
            for seed in SEEDS:
                rng = np.random.default_rng(seed)
                chosen = []
                for label, name in ((0, "rest"), (1, "task")):
                    pool = selected.index[selected.y == label].to_numpy()
                    t = int(tgt.get(name, 0))
                    if t < MIN_PER_CLASS or len(pool) < t:
                        failed = True; break
                    chosen += rng.choice(pool, t, replace=False).tolist()
                if failed:
                    nonviable_rows.append({"fold_id": fold.fold_id, "method": m, "analysis": "count_matched",
                                           "reason": "target/pool < 10", "status": "nonviable"}); break
                sc, _ = fit_score(selected.loc[chosen], test, decoder_cols)
                rec = {"kind": "count_matched", "fold_id": fold.fold_id, "dataset": fold.dataset, "subject": fold.subject,
                       "method": m, "balanced_accuracy": sc["balanced_accuracy"], "seed": seed}
                count_rows.append(rec); fold_records.append(rec)
        if fold_records:
            pd.DataFrame(fold_records).to_parquet(cp, index=False)
        if seq % 20 == 0:
            print(f"[downstream {seq}/{len(folds)}]", flush=True)

    nat = pd.DataFrame(natural_rows); cnt = pd.DataFrame(count_rows)
    nat.to_csv(OUT / "downstream_natural_R.csv", index=False)
    cnt.to_csv(OUT / "downstream_countmatched_R.csv", index=False)
    pd.DataFrame(nonviable_rows).to_csv(OUT / "downstream_nonviable_R.csv", index=False)

    # reuse verified M0 / M4 per-fold natural + count-matched
    base = pd.read_csv(BASE_DOWN / "monitor_decoder_results.csv")
    def fold_ba(monitor, analysis):
        d = base[(base.monitor == monitor) & (base.analysis == analysis) & (base.status == "valid")]
        return d.groupby(["dataset", "subject", "fold_id"], as_index=False).balanced_accuracy.mean()
    m0_nat = fold_ba("M0_NO_GATE", "natural"); r0_nat = fold_ba("M4_NFSQI_FULL_QUALITY", "natural")
    r0_cnt = fold_ba("M4_NFSQI_FULL_QUALITY", "count_matched")

    def subj_mean(df, col="balanced_accuracy"):
        return df.groupby(["dataset", "subject"], as_index=False)[col].mean()

    rng = np.random.default_rng(20260717)
    def paired_diff(a, b):
        merged = subj_mean(a).merge(subj_mean(b), on=["dataset", "subject"], suffixes=("_a", "_b"))
        d = (merged.balanced_accuracy_a - merged.balanced_accuracy_b).to_numpy()
        groups = merged.dataset.to_numpy()
        mean = float(np.mean(d))
        # participant bootstrap
        boots = [float(np.mean(d[rng.integers(0, len(d), len(d))])) for _ in range(2000)]
        return mean, float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))

    contrasts = []
    for m in METHODS:
        rn = nat[nat.method == m]
        rc = cnt[cnt.method == m].groupby(["dataset", "subject", "fold_id"], as_index=False).balanced_accuracy.mean()
        d_nat, lo_n, hi_n = paired_diff(rn, m0_nat)          # vs no gate
        d_cnt, lo_c, hi_c = paired_diff(rc, r0_cnt)          # vs R0 count-matched
        contrasts.append({"method": m,
                          "natural_minus_nogate": round(d_nat, 4), "natural_ci_low": round(lo_n, 4), "natural_ci_high": round(hi_n, 4),
                          "countmatched_minus_R0": round(d_cnt, 4), "countmatched_ci_low": round(lo_c, 4), "countmatched_ci_high": round(hi_c, 4)})
    con = pd.DataFrame(contrasts)
    con.to_csv(OUT / "downstream_information_cost_R.csv", index=False)
    print(con.to_string(index=False))
    print("nonviable:", len(nonviable_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
