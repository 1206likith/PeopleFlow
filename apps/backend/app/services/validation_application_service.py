"""
Application service for validation workflows and benchmark discovery.
"""
from __future__ import annotations

from typing import Any, Dict

from app.core.config import settings
from app.services.simulation_mock_runtime_service import _build_mock_frame
from app.services.simulation_result_repository import get_simulation_result_repository
from app.services.validation_engine import validation_engine
from app.validation.benchmark_registry import get_validation_benchmark_registry
from app.validation.normalization import normalize_runtime_validation_report


class ValidationApplicationService:
    async def validate_simulation_by_id(self, simulation_id: str) -> Dict[str, Any]:
        if simulation_id.startswith("mock-") or simulation_id.startswith("demo-"):
            if not settings.IS_DEMO_MODE:
                raise LookupError("Simulation not found")
            simulation = _build_mock_frame(simulation_id)
        else:
            repository = await get_simulation_result_repository()
            simulation = await repository.get_latest_frame(simulation_id)
        if not simulation:
            raise LookupError("Simulation not found")

        agents = simulation.get("agents", [])
        exits = simulation.get("exits", [])
        raw_report = validation_engine.validate_simulation(simulation, agents, exits)
        return normalize_runtime_validation_report(raw_report, simulation_id=simulation_id)

    def list_benchmarks(self) -> Dict[str, Any]:
        registry = get_validation_benchmark_registry()
        runtime_benchmarks = [benchmark.to_dict() for benchmark in registry.list_runtime_benchmarks()]
        suite_benchmarks = [benchmark.to_dict() for benchmark in registry.list_suite_benchmarks()]
        legacy_runtime_benchmarks = []
        for benchmark in registry.list_runtime_benchmarks():
            entry = {
                "name": benchmark.benchmark_id,
                "description": benchmark.description,
                "unit": benchmark.unit,
            }
            if benchmark.benchmark_id == "corridor_flow_rate":
                entry["expected"] = benchmark.expected_results.get("flow_rate")
            elif benchmark.benchmark_id == "density_speed_curve":
                entry["expected_points"] = benchmark.expected_results.get("points")
            elif benchmark.benchmark_id == "pre_evacuation_delay":
                entry["expected_mean"] = benchmark.expected_results.get("mean")
            legacy_runtime_benchmarks.append(entry)
        return {
            "catalog_version": "peopleflow-validation-benchmarks-v1",
            "benchmarks": legacy_runtime_benchmarks,
            "runtime_benchmarks": runtime_benchmarks,
            "suite_benchmarks": suite_benchmarks,
            "targets": registry.load_targets(),
        }


validation_application_service = ValidationApplicationService()
