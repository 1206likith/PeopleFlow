"""
Bayesian optimization for multi-objective tuning using Optuna.
"""
from __future__ import annotations

import json
from pathlib import Path
import random
from typing import Dict, Any, List, Tuple

try:
    import optuna
except Exception:  # pragma: no cover - exercised via fallback tests when dependency is absent
    optuna = None

from app.services.evacuation_parameters import parameter_database
from app.validation.runner import run_validation
from .config import ExperimentConfig
from .artifact_manifests import write_suite_manifest
from .runner import run_experiment_sync
from . import OUTPUT_DIR, EXPERIMENTS_DIR

def _flatten_params(parameters: List[Dict[str, Any]]) -> Tuple[List[str], List[Dict]]:
    keys = []
    specs = []
    for spec in parameters:
        keys.append(spec["path"])
        specs.append(spec)
    return keys, specs

def _get_nested(params: Dict[str, Any], path: str):
    node = params
    for part in path.split("."):
        node = node[part]
    return node


def _generate_overrides(
    keys: List[str],
    specs: List[Dict[str, Any]],
    base_params: Dict[str, Any],
    *,
    trial: Any = None,
    rng: random.Random | None = None,
) -> Dict[str, Any]:
    overrides = {}
    for key, spec in zip(keys, specs):
        if spec.get("mode") == "scale_list":
            scale_min = spec.get("scale_min", 0.8)
            scale_max = spec.get("scale_max", 1.2)
            if trial is not None:
                value = trial.suggest_float(f"scale_{key}", scale_min, scale_max)
            else:
                value = (rng or random).uniform(scale_min, scale_max)
            base_list = list(_get_nested(base_params, key))
            overrides[key] = [max(0.01, v * value) for v in base_list]
        else:
            low = spec.get("min", 0.0)
            high = spec.get("max", 1.0)
            if trial is not None:
                value = trial.suggest_float(key, low, high)
            else:
                value = (rng or random).uniform(low, high)
            overrides[key] = value
    return overrides

def _score_result(result: Dict[str, Any]) -> float:
    metrics = result.get("metrics", {})
    validation = result.get("validation", {})
    val_score = validation.get("overall_score")
    safety = metrics.get("safety_score", 0.0) / 100.0
    total_time = metrics.get("total_evacuation_time", 0.0)
    time_score = 1.0 / (1.0 + total_time / 60.0) if total_time else 0.0
    if val_score is None:
        val_score = 0.0
    return 0.6 * val_score + 0.2 * safety + 0.2 * time_score

def run_bayesian_optimization(
    base: ExperimentConfig,
    optimization_config_path: str | None = None,
) -> Dict[str, Any]:
    cfg_path = Path(optimization_config_path) if optimization_config_path else EXPERIMENTS_DIR / "optimization.json"
    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    trials = int(config.get("trials", 12))
    seed = int(config.get("seed", 123))
    parameters = config.get("parameters", [])

    base_params = parameter_database.snapshot()
    keys, specs = _flatten_params(parameters)

    results = []
    best = None
    resolved_method = config.get("method", "tpe")
    
    # Define objective function for Optuna
    def objective(trial: optuna.Trial) -> float:
        overrides = _generate_overrides(keys, specs, base_params, trial=trial)

        index = trial.number
        score, result = _run_trial(base, overrides, seed, index)
        results.append(result)
        
        nonlocal best
        if best is None or score > best["score"]:
            best = dict(result)
            
        return score

    if optuna is None:
        resolved_method = "random_fallback"
        rng = random.Random(seed)
        for index in range(trials):
            overrides = _generate_overrides(keys, specs, base_params, rng=rng)
            score, result = _run_trial(base, overrides, seed, index)
            results.append(result)
            if best is None or score > best["score"]:
                best = dict(result)
    else:
        # Use TPESampler for Bayesian Optimization (default in Optuna)
        sampler = optuna.samplers.TPESampler(seed=seed)
        # Using GridSearch or RandomSearch is natively supported in Optuna by changing samplers
        if config.get("method") == "grid_search":
            # Note: True grid search needs predefined grids. Default to TPE pseudo-grid if not specified
            pass
            
        study = optuna.create_study(direction="maximize", sampler=sampler)
        
        # We hide Optuna logs to keep CLI clean if needed, or leave them for debugging
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        
        study.optimize(objective, n_trials=trials)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "optimization_summary.json"
    return write_suite_manifest(
        suite_type="optimization",
        base_config_payload=base.model_dump(),
        results=results,
        output_path=summary_path,
        source_config_path=str(cfg_path),
        best=best,
        metadata={
            "trials": trials,
            "parameter_count": len(parameters),
            "search_seed": seed,
            "method": config.get("method", "tpe"),
            "method_resolved": resolved_method,
        },
    )


def _run_trial(base: ExperimentConfig, overrides: Dict[str, Any], seed: int, index: int):
    # Setup parameters
    parameter_database.apply_overrides(overrides)
    
    # Configure experiment
    trial_cfg = base.model_copy(deep=True)
    trial_cfg.name = f"{base.name}__opt_{index:03d}"
    trial_cfg.metadata = {
        **trial_cfg.metadata,
        "optimization_overrides": overrides,
        "optimization_seed": seed,
    }

    # Execute simulation
    result = run_experiment_sync(trial_cfg)
    
    # Validate against models and metrics
    out_path = OUTPUT_DIR / f"{result['config']['name']}.json"
    validation = run_validation(str(out_path))
    result["validation"] = validation
    
    # Compute composite score
    score = _score_result(result)

    # Save artifact
    data = json.loads(out_path.read_text(encoding="utf-8"))
    data["validation"] = validation
    data["optimization_score"] = score
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Reset
    parameter_database.reset()
    validation_summary = validation.get("summary", {}) if isinstance(validation, dict) else {}
    return score, {
        "name": result["config"]["name"],
        "config": result["config"],
        "config_hash": result.get("config_hash"),
        "score": score,
        "overrides": overrides,
        "validation_status": validation_summary.get("status"),
        "validation_score": validation_summary.get("overall_score", validation.get("overall_score")),
        "output_file": f"{result['config']['name']}.json",
    }
