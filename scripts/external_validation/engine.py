import numpy as np
import pandas as pd
from itertools import combinations
from scripts.conjunctive_gate_instability.common import CRITERIA, CRIT_ORDER, nonempty_subsets, subset_id
from scripts.conjunctive_gate_instability.run_law_study import empirical_threshold, pass_indicators
from scripts.conjunctive_gate_instability.common import channel_inconsistency as _ci

def channel_inconsistency(frame, baseline):
    return _ci(frame, baseline[0], baseline[1])

def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    a_bool = a.astype(bool)
    b_bool = b.astype(bool)
    union = a_bool | b_bool
    if not union.any():
        return 1.0
    return float((a_bool & b_bool).sum()) / float(union.sum())
