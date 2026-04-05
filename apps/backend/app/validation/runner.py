"""
Calibration runner. Applies validation checks to experiment outputs.
"""
import json
from pathlib import Path
from typing import Dict

from app.validation.exit89 import validate_exit89
from app.validation.eth_trajectory import validate_eth_trajectory
from app.validation.fundamental import validate_fundamental_diagram
from app.validation.targets import load_targets
from app.validation.metrics import compute_evacuation_time_error, compute_density_distribution_error
from app.validation.normalization import normalize_literature_validation_report

def validate_evacuation_metrics(metrics: Dict) -> Dict:
    targets = load_targets().get("evacuation", {})
    time_target = targets.get("time_target", 60.0)
    time_tol = targets.get("time_tolerance_pct", 0.15)
    
    density_target = targets.get("density_target", 2.0)
    density_tol = targets.get("density_tolerance", 1.0)
    
    sim_time = metrics.get("total_evacuation_time", 0.0)
    # Average density across grid or max density
    max_densities = metrics.get("max_densities", [])
    if not max_densities:
        max_densities = [metrics.get("max_density", 0.0)]
        
    time_error = compute_evacuation_time_error(sim_time, time_target)
    time_score = max(0.0, 1.0 - (time_error / max(time_tol, 1e-6)))
    
    density_error = compute_density_distribution_error(max_densities, density_target)
    density_score = max(0.0, 1.0 - (density_error / max(density_tol, 1e-6)))

    score = (time_score + density_score) / 2.0

    return {
        "status": "ok" if score > 0.5 else "poor_fit",
        "time_error": time_error,
        "density_error": density_error,
        "score": score
    }

def run_validation(
    output_path: str,
    *,
    include_eth: bool = False,
    eth_dataset_root: str | None = None,
    eth_download_if_missing: bool = False,
    eth_dataset_url: str | None = None,
) -> Dict:
    data = json.loads(Path(output_path).read_text(encoding="utf-8"))
    metrics = data.get("metrics", {})
    
    exit89 = validate_exit89(metrics)
    fundamental = validate_fundamental_diagram(metrics)
    evac_metrics = validate_evacuation_metrics(metrics)

    eth_report: Dict | None = None
    if include_eth:
        eth_report = validate_eth_trajectory(
            dataset_root=eth_dataset_root,
            download_if_missing=eth_download_if_missing,
            dataset_url=eth_dataset_url or "https://data.vision.ee.ethz.ch/cvl/aem/ewap_dataset_full.tgz",
        )

    checks = [exit89, fundamental, evac_metrics]
    if eth_report is not None:
        checks.append(eth_report)
    scores = [v.get("score") for v in checks if isinstance(v, dict) and v.get("score") is not None]
    overall = sum(scores) / len(scores) if scores else None

    report = {
        "exit89": exit89,
        "fundamental": fundamental,
        "evacuation": evac_metrics,
        "overall_score": overall,
    }
    if eth_report is not None:
        report["eth_trajectory"] = eth_report
    return normalize_literature_validation_report(report, output_path=output_path)
