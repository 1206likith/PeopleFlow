"""
Experiment runner.
Produces metrics and stores outputs for reproducibility.
"""

import asyncio
import hashlib
import json
import random
import threading
from typing import Any, Dict

import numpy as np

from app.services.evacuation_parameters import parameter_database
from app.services.floorplan_loader import load_floor_plan_data
from app.services.metrics_engine import MetricsEngine

from . import OUTPUT_DIR
from .config import ExperimentConfig
from .metadata import build_metadata, build_provenance
from .result import ExperimentResult


def _run_async_sync(awaitable: Any):
    """Bridge async floor-plan loading into sync experiment execution safely."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    result: Dict[str, Any] = {}
    error: Dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            result["value"] = asyncio.run(awaitable)
        except BaseException as exc:
            error["value"] = exc

    thread = threading.Thread(target=_worker, name="experiment-floorplan-loader", daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


def run_experiment_sync(config: ExperimentConfig) -> Dict:
    from app.sim.simulation import SimulationEngine

    random.seed(config.seed)
    np.random.seed(config.seed)
    metrics_engine = MetricsEngine()

    floor_plan_data, exits = (None, [])
    if config.floor_plan_id:
        floor_plan_data, exits = _run_async_sync(
            load_floor_plan_data(config.floor_plan_id, config.floor_number, [])
        )

    sim = SimulationEngine(
        config.num_agents,
        config.emergency_type,
        config.floor_number,
        seed=config.seed,
        ablation=config.ablation.model_dump() if config.ablation else None,
        engine=config.engine,
    )
    sim.initialize_from_floor_plan(floor_plan_data)
    sim.set_exits(exits)
    sim.initialize_agents()

    dt = 0.1
    steps = int(config.duration_seconds / dt)
    for _ in range(steps):
        sim.update(dt)
        frame = sim.get_frame()
        metrics_engine.add_frame(frame)
        if sim.is_complete():
            break

    metrics = metrics_engine.calculate_metrics()
    config_payload = config.model_dump()
    config_hash = hashlib.sha256(
        json.dumps(config_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    floor_plan_revision = None
    if isinstance(floor_plan_data, dict):
        floor_plan_revision = (
            floor_plan_data.get("revision")
            or floor_plan_data.get("version")
            or floor_plan_data.get("updated_at")
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{config.name}.json"
    metadata = build_metadata(
        config_payload,
        floor_plan_revision=str(floor_plan_revision) if floor_plan_revision is not None else None,
    ).to_dict()
    provenance = build_provenance(
        config_payload,
        config_hash=config_hash,
        floor_plan_revision=str(floor_plan_revision) if floor_plan_revision is not None else None,
    ).to_dict()
    result = ExperimentResult(
        config=config_payload,
        config_hash=config_hash,
        metrics=metrics.__dict__,
        metadata=metadata,
        provenance=provenance,
        artifacts={
            "output_path": str(out_path.as_posix()),
            "parameters_snapshot": parameter_database.snapshot(),
        },
    )
    out_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result.to_dict()
