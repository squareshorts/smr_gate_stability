import math
from dataclasses import dataclass, field
from typing import Dict, Set

SPECIFICATION_VERSION = "1.0.0-runtime-assurance"

@dataclass
class EvaluationResult:
    gate_a_requested: bool = False
    gate_c_allowed: bool = False
    withhold: bool = True
    invalid_input: bool = False
    reason_codes: Set[str] = field(default_factory=set)

def evaluate(features: Dict[str, float], limits: Dict[str, float]) -> EvaluationResult:
    result = EvaluationResult()
    
    expected_features = [
        "smr_snr", "high_beta_power", "broadband_power", 
        "noise_floor_power", "transient_score", "channel_inconsistency"
    ]
    
    # Check for missing or non-finite inputs
    for feat in expected_features:
        val = features.get(feat)
        if val is None or not math.isfinite(val):
            result.invalid_input = True
            result.withhold = True
            result.reason_codes.add("invalid_input")
            return result
            
    smr_snr = features["smr_snr"]
    smr_snr_min = limits["smr_snr_min"]
    if smr_snr > smr_snr_min:
        result.gate_a_requested = True
    else:
        result.reason_codes.add("smr_snr")
        
    result.gate_c_allowed = result.gate_a_requested
    
    if features["high_beta_power"] >= limits["high_beta_max"]:
        result.gate_c_allowed = False
        result.reason_codes.add("high_beta")
        
    if features["broadband_power"] >= limits["broadband_max"]:
        result.gate_c_allowed = False
        result.reason_codes.add("broadband")
        
    if features["noise_floor_power"] >= limits["noise_floor_max"]:
        result.gate_c_allowed = False
        result.reason_codes.add("noise_floor")
        
    if features["transient_score"] >= limits["transient_max"]:
        result.gate_c_allowed = False
        result.reason_codes.add("transient")
        
    if features["channel_inconsistency"] >= limits["channel_inconsistency_max"]:
        result.gate_c_allowed = False
        result.reason_codes.add("channel_inconsistency")
        
    result.withhold = not result.gate_c_allowed
    return result
