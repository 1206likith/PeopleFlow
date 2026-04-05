"""
Experiment index generator.
Builds a client-friendly index.json from outputs.
"""
import json
from pathlib import Path

from . import OUTPUT_DIR, EXPERIMENT_INDEX_PATH
from .artifact_manifests import build_index_manifest, is_experiment_run_record


def build_index(
    output_dir: str | None = None,
    out_path: str | None = None,
):
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    results = []
    for path in out_dir.glob("*.json"):
        if path.name == "index.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not is_experiment_run_record(data):
                continue
            config = data.get("config", {})
            metrics = data.get("metrics", {})
            metadata = data.get("metadata", {})
            provenance = data.get("provenance", {})
            validation = data.get("validation", {})
            validation_summary = validation.get("summary", {}) if isinstance(validation, dict) else {}
            results.append({
                "name": config.get("name"),
                "config_hash": data.get("config_hash"),
                "seed": provenance.get("seed", config.get("seed")),
                "num_agents": config.get("num_agents"),
                "emergency_type": config.get("emergency_type"),
                "ablation": config.get("ablation", {}),
                "generated_at": provenance.get("generated_at", metadata.get("generated_at")),
                "metrics_summary": {
                    "total_time": metrics.get("total_evacuation_time"),
                    "avg_time": metrics.get("average_evacuation_time"),
                    "median_time": metrics.get("median_evacuation_time"),
                    "peak_flow": metrics.get("peak_flow_rate"),
                    "safety_score": metrics.get("safety_score"),
                    "survival_probability": metrics.get("survival_probability"),
                },
                "validation_summary": {
                    "exit89": validation.get("exit89", {}).get("status"),
                    "fundamental": validation.get("fundamental", {}).get("status"),
                    "overall_score": validation_summary.get("overall_score", validation.get("overall_score")),
                    "status": validation_summary.get("status"),
                    "calibration_score": data.get("calibration_score"),
                    "optimization_score": data.get("optimization_score"),
                } if validation else {},
                "output_file": path.name,
            })
        except Exception:
            continue
    results.sort(key=lambda r: r.get("generated_at") or "", reverse=True)
    index_path = Path(out_path) if out_path else EXPERIMENT_INDEX_PATH
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_index_manifest(
        results=results,
        source_dir=str(out_dir),
        output_path=str(index_path),
        metadata={"index_name": index_path.name},
    )
    index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    build_index()
