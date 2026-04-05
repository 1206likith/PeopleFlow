"""
Fundamental diagram validation utilities.
"""
from typing import Dict

from .targets import load_targets
from .metrics import compute_flow_curve_rmse

def validate_fundamental_diagram(metrics: Dict) -> Dict:
    data = metrics.get("fundamental_diagram_data", []) if metrics else []
    if not data:
        return {"status": "insufficient_data"}

    peak_flow = max((d.get("flow_rate", d.get("flow", 0)) for d in data), default=0)
    flows = [d.get("flow_rate", d.get("flow", 0)) for d in data]
    densities = [d.get("density", 0.0) for d in data]
    
    targets = load_targets().get("fundamental", {})
    target_range = targets.get("peak_flow_rate", {})
    min_val = target_range.get("min")
    max_val = target_range.get("max")
    rmse_tol = targets.get("rmse_tolerance", 0.5)

    rmse = compute_flow_curve_rmse(densities, flows)

    score = 0.0
    status = "ok"
    
    # Peak flow score
    peak_score = 0.0
    if min_val is not None and max_val is not None:
        if min_val <= peak_flow <= max_val:
            peak_score = 1.0
        else:
            dist = min(abs(peak_flow - min_val), abs(peak_flow - max_val))
            span = max(max_val - min_val, 1e-6)
            peak_score = max(0.0, 1.0 - (dist / span))

    # RMSE score (falls off smoothly as RMSE increases, hits 0 at 2 * tol)
    if rmse != float('inf'):
        rmse_score = max(0.0, 1.0 - (rmse / (2 * rmse_tol)))
    else:
        rmse_score = 0.0
        
    # Combined
    score = (peak_score + rmse_score) / 2.0
    
    if score < 0.5:
        status = "poor_fit"

    return {
        "status": status,
        "peak_flow_rate": peak_flow,
        "rmse": rmse,
        "score": score,
        "range": {"min": min_val, "max": max_val},
    }
