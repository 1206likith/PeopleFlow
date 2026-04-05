"""
Calibration runner for parameter tuning against validation targets.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, Any, List

from app.services.evacuation_parameters import parameter_database
from app.validation.runner import run_validation

from .config import ExperimentConfig
from .artifact_manifests import write_suite_manifest
from .runner import run_experiment_sync
from . import OUTPUT_DIR, EXPERIMENTS_DIR


def _get_nested(params: Dict[str, Any], path: str):
    node = params
    for key in path.split("."):
        node = node[key]
    return node


def _sample_value(spec: Dict[str, Any], base_params: Dict[str, Any], rng: random.Random):
    mode = spec.get("mode", "range")
    path = spec["path"]

    if mode == "scale_list":
        base_list = list(_get_nested(base_params, path))
        scale = rng.uniform(spec.get("scale_min", 0.8), spec.get("scale_max", 1.2))
        return [max(0.01, v * scale) for v in base_list]

    if "choices" in spec:
        return rng.choice(spec["choices"])

    return rng.uniform(spec["min"], spec["max"])


def run_calibration(
    base: ExperimentConfig,
    calibration_config_path: str | None = None,
) -> Dict[str, Any]:
    cfg_path = Path(calibration_config_path) if calibration_config_path else EXPERIMENTS_DIR / "calibration.json"
    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    trials = int(config.get("trials", 10))
    seed = int(config.get("seed", 123))
    parameters = config.get("parameters", [])

    rng = random.Random(seed)
    base_params = parameter_database.snapshot()

    results: List[Dict[str, Any]] = []
    best = None

    for i in range(trials):
        overrides = {}
        for spec in parameters:
            overrides[spec["path"]] = _sample_value(spec, base_params, rng)

        parameter_database.apply_overrides(overrides)

        trial_cfg = base.model_copy(deep=True)
        trial_cfg.name = f"{base.name}__calib_{i:03d}"
        trial_cfg.metadata = {
            **trial_cfg.metadata,
            "calibration_overrides": overrides,
            "calibration_seed": seed,
        }

        result = run_experiment_sync(trial_cfg)
        out_path = OUTPUT_DIR / f"{result['config']['name']}.json"
        validation = run_validation(str(out_path))
        score = validation.get("overall_score")
        result["validation"] = validation
        result["calibration_score"] = score

        data = json.loads(out_path.read_text(encoding="utf-8"))
        data["validation"] = validation
        data["calibration_score"] = score
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        validation_summary = validation.get("summary", {}) if isinstance(validation, dict) else {}
        results.append({
            "name": result["config"]["name"],
            "config_hash": result.get("config_hash"),
            "score": score,
            "overrides": overrides,
            "validation_status": validation_summary.get("status"),
            "validation_score": validation_summary.get("overall_score", validation.get("overall_score")),
            "output_file": f"{result['config']['name']}.json",
        })

        if score is not None and (best is None or score > best["score"]):
            best = {
                "name": result["config"]["name"],
                "config_hash": result.get("config_hash"),
                "score": score,
                "overrides": overrides,
                "output_file": f"{result['config']['name']}.json",
            }

        parameter_database.reset()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "calibration_summary.json"
    return write_suite_manifest(
        suite_type="calibration",
        base_config_payload=base.model_dump(),
        results=results,
        output_path=summary_path,
        source_config_path=str(cfg_path),
        best=best,
        metadata={
            "trials": trials,
            "parameter_count": len(parameters),
            "search_seed": seed,
        },
    )
