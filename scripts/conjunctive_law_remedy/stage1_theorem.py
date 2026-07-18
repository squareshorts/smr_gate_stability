"""STAGE 1 — symbolic + high-precision verification of the composition theorem."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import sympy as sp

OUT = Path(__file__).resolve().parents[2] / "results" / "conjunctive_law_remedy" / "theory"
OUT.mkdir(parents=True, exist_ok=True)


def symbolic_verification() -> list[str]:
    P1, P2, Q, a, b, c = sp.symbols("P1 P2 Q a b c", positive=True)
    log = []
    J_old = Q / (P1 + P2 - Q)
    J_new = (Q * c) / (P1 * a + P2 * b - Q * c)

    # Cross-multiplied difference (denominators > 0). Sign of (J_old - J_new)
    # equals sign of numerator N below.
    N = sp.simplify((J_old - J_new) * (P1 + P2 - Q) * (P1 * a + P2 * b - Q * c))
    N = sp.expand(N)
    log.append("J_old = Q/(P1+P2-Q)")
    log.append("J_new = Q*c/(P1*a+P2*b-Q*c)")
    log.append(f"(J_old-J_new)*den_old*den_new expanded = {N}")

    # Factor: expected Q*(P1*a + P2*b - c*(P1+P2))
    target = sp.expand(Q * (P1 * a + P2 * b - c * (P1 + P2)))
    log.append(f"Q*(P1*a+P2*b - c*(P1+P2)) expanded = {target}")
    log.append(f"identity N == Q*(P1*a+P2*b-c*(P1+P2)) ? {sp.simplify(N - target) == 0}")

    # Therefore J_new <= J_old  <=>  P1*a + P2*b - c*(P1+P2) >= 0
    log.append("=> J_new <= J_old  iff  c*(P1+P2) <= P1*a + P2*b   [since Q>0, dens>0]")

    # Symmetric corollary a=b=p
    p = sp.symbols("p", positive=True)
    cond_sym = sp.simplify((P1 * p + P2 * p) - p * (P1 + P2))
    log.append(f"symmetric a=b=p: (P1*p+P2*p) - p*(P1+P2) = {cond_sym}  => condition reduces to c <= p")

    # Under independence c<=min(a,b): P1*(a-c)+P2*(b-c) >= 0 always
    log.append("rewrite condition as P1*(a-c) + P2*(b-c) >= 0")
    log.append("under independence within replicate c=P(A1&A2)<=min(a,b) => a-c>=0 and b-c>=0")
    log.append("=> condition ALWAYS holds under independence => J_new <= J_old (non-increasing)")

    # Equality: P1*(a-c)+P2*(b-c)=0 with both terms>=0 => a=c and b=c (or degenerate P)
    log.append("equality iff a=c and b=c (added criterion perfectly reproducible) or P1=P2=0 degenerate")

    # Monotone dJ/dx>0, dJ/dy<0 for J=x/(y-x)
    x, y = sp.symbols("x y", positive=True)
    J = x / (y - x)
    log.append(f"J=x/(y-x): dJ/dx = {sp.simplify(sp.diff(J,x))} (>0), dJ/dy = {sp.simplify(sp.diff(J,y))} (<0)")
    return log


def monte_carlo() -> pd.DataFrame:
    """Two checks:
    (A) Factorized-identity check on random valid probability tuples: sign(J_old-J_new_fac)
        must equal sign(P1*a+P2*b - c*(P1+P2)). This is the exact theorem — expect 100%.
    (B) Window-level regimes: with the new criterion independent of the gate, the empirical
        J_new is non-increasing; under engineered dependence the empirical J_new can rise,
        showing independence is required (the Stage-2 limitation)."""
    rng = np.random.default_rng(2026)
    rows = []
    # (A) probability-tuple identity check
    for trial in range(20000):
        P1 = rng.uniform(0.05, 0.99); P2 = rng.uniform(0.05, 0.99)
        Qv = rng.uniform(0, min(P1, P2))               # valid joint <= min marginals
        a = rng.uniform(0.05, 0.99); bb = rng.uniform(0.05, 0.99)
        cv = rng.uniform(0, min(a, bb))
        den_old = P1 + P2 - Qv
        den_new = P1 * a + P2 * bb - Qv * cv
        if den_old <= 1e-9 or den_new <= 1e-9:
            continue
        j_old = Qv / den_old
        j_new_fac = (Qv * cv) / den_new                # factorized (independence) prediction
        cond = (cv * (P1 + P2)) <= (P1 * a + P2 * bb) + 1e-12
        rows.append({"check": "A_factorized_identity", "regime": "probability_tuple",
                     "J_old": j_old, "J_new": j_new_fac,
                     "cond_predicts_nonincrease": bool(cond),
                     "observed_nonincrease": bool(j_new_fac <= j_old + 1e-9),
                     "cond_matches_observed": bool(cond == (j_new_fac <= j_old + 1e-9))})
    # (B) window-level empirical regimes
    def jac(g1, g2):
        un = np.sum(g1 | g2)
        return (np.sum(g1 & g2) / un) if un else 1.0
    for trial in range(20000):
        n = 4000
        base = rng.random(n) < rng.uniform(0.3, 0.95)
        G1 = base ^ (rng.random(n) < rng.uniform(0, 0.25))
        G2 = base ^ (rng.random(n) < rng.uniform(0, 0.25))
        dependent = trial % 2 == 1
        if dependent:
            disagree = G1 ^ G2
            keep_p = np.where(disagree, rng.uniform(0.0, 0.3), rng.uniform(0.7, 1.0))
            A1 = rng.random(n) < keep_p
            A2 = A1 ^ (rng.random(n) < rng.uniform(0, 0.1))
        else:
            abase = rng.random(n) < rng.uniform(0.4, 0.99)
            A1 = abase ^ (rng.random(n) < rng.uniform(0, 0.2))
            A2 = abase ^ (rng.random(n) < rng.uniform(0, 0.2))
        j_old = jac(G1, G2); j_new = jac(G1 & A1, G2 & A2)
        rows.append({"check": "B_window_regime", "regime": "dependent" if dependent else "independent",
                     "J_old": j_old, "J_new": j_new,
                     "cond_predicts_nonincrease": np.nan,
                     "observed_nonincrease": bool(j_new <= j_old + 1e-9),
                     "cond_matches_observed": np.nan})
    return pd.DataFrame(rows)


def main() -> int:
    log = symbolic_verification()
    (OUT / "algebra_verification.txt").write_text("\n".join(log) + "\n", encoding="utf-8")

    # theorem_conditions.csv
    pd.DataFrame([
        {"name": "old_jaccard", "expression": "J_old = Q/(P1+P2-Q)"},
        {"name": "new_jaccard", "expression": "J_new = Q*c/(P1*a+P2*b-Q*c)"},
        {"name": "monotone_condition", "expression": "J_new <= J_old  iff  c*(P1+P2) <= P1*a+P2*b"},
        {"name": "equivalent_form", "expression": "P1*(a-c) + P2*(b-c) >= 0"},
        {"name": "symmetric_corollary", "expression": "a=b=p  =>  condition reduces to c <= p"},
        {"name": "independence_implication", "expression": "c<=min(a,b) => condition always holds => non-increasing"},
        {"name": "equality", "expression": "a=c and b=c (added criterion perfectly reproducible)"},
        {"name": "increase_possible", "expression": "only if c*(P1+P2) > P1*a+P2*b, impossible under independence; requires dependence"},
        {"name": "K_extension", "expression": "J_K = prod(q_j)/(prod(p_j1)+prod(p_j2)-prod(q_j)); one-step condition applies recursively"},
        {"name": "agreement_relation", "expression": "overall=(tp+tn)/n rises via tn; accepted-set Jaccard=tp/(tp+fp+fn) falls; positive agreement tracks Jaccard, negative agreement rises"},
    ]).to_csv(OUT / "theorem_conditions.csv", index=False)

    mc = monte_carlo()
    mc.to_csv(OUT / "simulated_sanity_checks.csv", index=False)

    A = mc[mc.check == "A_factorized_identity"]
    B = mc[mc.check == "B_window_regime"]
    A_match = float(A.cond_matches_observed.mean())
    B_ind_noninc = float(B[B.regime == "independent"].observed_nonincrease.mean())
    B_dep_inc = int((B[B.regime == "dependent"].J_new > B[B.regime == "dependent"].J_old + 1e-9).sum())
    B_ind_inc = int((B[B.regime == "independent"].J_new > B[B.regime == "independent"].J_old + 1e-9).sum())

    eq_rows = pd.DataFrame([
        {"case": "A_factorized_identity_match_fraction", "value": round(A_match, 6)},
        {"case": "B_independent_regime_nonincrease_fraction", "value": round(B_ind_noninc, 6)},
        {"case": "B_dependent_regime_increase_count", "value": B_dep_inc},
        {"case": "B_independent_regime_increase_count", "value": B_ind_inc},
        {"case": "interpretation", "value": "exact identity holds; dependence (not independence) enables J increase"},
    ])
    eq_rows.to_csv(OUT / "equality_and_counterexamples.csv", index=False)

    print("symbolic identity verified:", sp_ok(log))
    print("A factorized-identity match fraction:", round(A_match, 6))
    print("B independent-regime non-increase fraction:", round(B_ind_noninc, 6))
    print("B dependent-regime increase count:", B_dep_inc, "| independent increase count:", B_ind_inc)
    return 0


def sp_ok(log):
    return any("identity N ==" in l and "True" in l for l in log)


if __name__ == "__main__":
    raise SystemExit(main())
