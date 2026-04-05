"""
Metrics aggregation utilities.
"""
import json
from pathlib import Path
import csv


from . import OUTPUT_DIR
from .artifact_manifests import build_export_manifest, is_experiment_run_record


def export_csv(output_dir: str | None = None, csv_path: str | None = None):
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    rows = []
    for path in out_dir.glob("*.json"):
        if path.name == "index.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not is_experiment_run_record(data):
                continue
            config = data.get("config", {})
            metrics = data.get("metrics", {})
            validation = data.get("validation", {})
            ablation = config.get("ablation", {})
            metadata = data.get("metadata", {})
            provenance = data.get("provenance", {})
            validation_summary = validation.get("summary", {}) if isinstance(validation, dict) else {}
            validation_checks = validation.get("checks", {}) if isinstance(validation, dict) else {}
            eth_check = validation_checks.get("eth_trajectory", {}) if isinstance(validation_checks, dict) else {}
            eth_details = eth_check.get("details", {}) if isinstance(eth_check, dict) else {}
            row = {
                "name": config.get("name"),
                "config_hash": data.get("config_hash"),
                "seed": provenance.get("seed", config.get("seed")),
                "num_agents": config.get("num_agents"),
                "emergency_type": config.get("emergency_type"),
                "floor_plan_id": provenance.get("floor_plan_id", config.get("floor_plan_id")),
                "floor_plan_revision": provenance.get("floor_plan_revision"),
                "engine_version": provenance.get("engine_version"),
                "generated_at": provenance.get("generated_at", metadata.get("generated_at")),
            }
            row.update({
                "ablation_social_force": ablation.get("use_social_force"),
                "ablation_pathfinding": ablation.get("use_pathfinding"),
                "ablation_behavioral": ablation.get("use_behavioral_decisions"),
                "ablation_hazard": ablation.get("use_hazard_effects"),
            })
            row.update({
                "total_time": metrics.get("total_evacuation_time"),
                "avg_time": metrics.get("average_evacuation_time"),
                "median_time": metrics.get("median_evacuation_time"),
                "peak_flow": metrics.get("peak_flow_rate"),
                "avg_delay": metrics.get("average_delay"),
                "safety_score": metrics.get("safety_score"),
                "survival_probability": metrics.get("survival_probability"),
                "exit_balance": metrics.get("exit_load_balance"),
                "optimal_exit_utilization": metrics.get("optimal_exit_utilization"),
                "validation_overall": validation_summary.get("overall_score", validation.get("overall_score")),
                "validation_status": validation_summary.get("status"),
                "eth_validation_status": eth_check.get("status"),
                "eth_validation_rmse": eth_details.get("rmse"),
                "eth_validation_ade": eth_details.get("ade"),
                "eth_validation_fde": eth_details.get("fde"),
                "eth_validation_oscillation_deg": eth_details.get("oscillation_strength_deg"),
                "eth_validation_path_smoothness": eth_details.get("path_smoothness"),
                "eth_validation_success_ratio": eth_details.get("successful_trajectory_ratio"),
                "eth_validation_overlap_proportion": eth_details.get("overlap_proportion"),
                "eth_validation_scenes": eth_details.get("scenes_evaluated"),
                "optimization_score": data.get("optimization_score"),
            })
            rows.append(row)
        except Exception:
            continue

    target_path = Path(csv_path) if csv_path else out_dir / "metrics.csv"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with open(target_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)
    manifest = build_export_manifest(
        row_count=len(rows),
        source_dir=str(out_dir),
        csv_path=str(target_path),
        columns=fieldnames,
        metadata={"export_name": target_path.name},
    )
    manifest_path = target_path.with_suffix(f"{target_path.suffix}.manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    export_csv()
