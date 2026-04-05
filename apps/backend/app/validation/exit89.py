"""
Validation against EXIT89-like delay distributions (placeholder).
"""
from typing import Dict

from .targets import load_targets


def validate_exit89(metrics: Dict) -> Dict:
    # Placeholder: compare pre-evac delays if available
    delays = metrics.get("pre_evacuation_delays", []) if metrics else []
    if not delays:
        return {"status": "insufficient_data"}

    avg_delay = sum(delays) / len(delays)
    targets = load_targets().get("exit89", {})
    target = targets.get("mean_delay", {})
    target_value = target.get("target")
    tolerance = target.get("tolerance", 1.0)

    score = None
    status = "ok"
    if target_value is not None:
        # Score falls off linearly with deviation.
        deviation = abs(avg_delay - target_value)
        score = max(0.0, 1.0 - (deviation / max(tolerance, 1e-6)))
        status = "ok" if score >= 0.5 else "out_of_range"

    return {
        "status": status,
        "avg_delay": avg_delay,
        "n": len(delays),
        "score": score,
        "target": target_value,
        "tolerance": tolerance
    }
