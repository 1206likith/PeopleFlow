"""
Canonical validation benchmark registry shared across runtime, suite, and target-based validators.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class BenchmarkDefinition:
    benchmark_id: str
    name: str
    description: str
    source: str
    category: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_results: Dict[str, Any] = field(default_factory=dict)
    tolerance: Dict[str, Any] = field(default_factory=dict)
    unit: Optional[str] = None
    target_section: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "id": self.benchmark_id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "category": self.category,
            "parameters": deepcopy(self.parameters),
            "expected_results": deepcopy(self.expected_results),
            "tolerance": deepcopy(self.tolerance),
        }
        if self.unit is not None:
            payload["unit"] = self.unit
        if self.target_section is not None:
            payload["target_section"] = self.target_section
        return payload


class ValidationBenchmarkRegistry:
    def __init__(
        self,
        *,
        runtime_benchmarks: Dict[str, BenchmarkDefinition],
        suite_benchmarks: Dict[str, BenchmarkDefinition],
        target_sections: Dict[str, Dict[str, Any]],
    ):
        self._runtime_benchmarks = runtime_benchmarks
        self._suite_benchmarks = suite_benchmarks
        self._target_sections = target_sections

    def get_runtime_benchmark(self, benchmark_id: str) -> Optional[BenchmarkDefinition]:
        return self._runtime_benchmarks.get(benchmark_id)

    def list_runtime_benchmarks(self) -> List[BenchmarkDefinition]:
        return list(self._runtime_benchmarks.values())

    def get_suite_benchmark(self, benchmark_id: str) -> Optional[BenchmarkDefinition]:
        return self._suite_benchmarks.get(benchmark_id)

    def list_suite_benchmarks(self) -> List[BenchmarkDefinition]:
        return list(self._suite_benchmarks.values())

    def get_target_section(self, section: str) -> Dict[str, Any]:
        return deepcopy(self._target_sections.get(section, {}))

    def load_targets(self) -> Dict[str, Dict[str, Any]]:
        return deepcopy(self._target_sections)


def _default_targets_path() -> Path:
    return Path(__file__).resolve().parent / "targets.json"


def _load_target_sections(path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    target_path = Path(path) if path else _default_targets_path()
    if not target_path.exists():
        return {}
    return json.loads(target_path.read_text(encoding="utf-8"))


def _build_runtime_benchmarks(targets: Dict[str, Dict[str, Any]]) -> Dict[str, BenchmarkDefinition]:
    evacuation_targets = targets.get("evacuation", {})
    fundamental_targets = targets.get("fundamental", {})
    exit89_targets = targets.get("exit89", {})
    eth_targets = targets.get("eth_trajectory", {})
    return {
        "corridor_flow_rate": BenchmarkDefinition(
            benchmark_id="corridor_flow_rate",
            name="Corridor Flow Rate",
            description="Fruin (1971) corridor flow rate benchmark for evacuation throughput.",
            source="Fruin (1971)",
            category="runtime",
            expected_results={"flow_rate": 1.33},
            tolerance={"relative_error": 0.15},
            unit="persons/second/meter",
            target_section="evacuation",
        ),
        "density_speed_curve": BenchmarkDefinition(
            benchmark_id="density_speed_curve",
            name="Density-Speed Curve",
            description="Fundamental diagram benchmark comparing local density against walking speed.",
            source="Crowd dynamics literature",
            category="runtime",
            expected_results={
                "points": [
                    (0.0, 1.35),
                    (1.0, 1.28),
                    (2.0, 1.10),
                    (3.0, 0.90),
                    (4.0, 0.65),
                    (5.0, 0.40),
                ],
                "peak_flow_rate_range": deepcopy(fundamental_targets.get("peak_flow_rate", {})),
            },
            tolerance={"rmse": float(fundamental_targets.get("rmse_tolerance", 0.20) or 0.20)},
            unit="m/s vs persons/m^2",
            target_section="fundamental",
        ),
        "pre_evacuation_delay": BenchmarkDefinition(
            benchmark_id="pre_evacuation_delay",
            name="Pre-Evacuation Delay",
            description="Distributional benchmark for pre-evacuation delays derived from EXIT89-like studies.",
            source="EXIT89 / evacuation delay literature",
            category="runtime",
            expected_results={
                "mean": float(exit89_targets.get("mean_delay", {}).get("target", 2.5) or 2.5),
                "std": 1.2,
            },
            tolerance={
                "mean_abs": float(exit89_targets.get("mean_delay", {}).get("tolerance", 2.0) or 2.0),
                "std_abs": 0.3,
            },
            unit="seconds",
            target_section="exit89",
        ),
        "eth_trajectory_rmse": BenchmarkDefinition(
            benchmark_id="eth_trajectory_rmse",
            name="ETH Trajectory RMSE",
            description="Short-horizon trajectory prediction RMSE benchmark on ETH-style trajectory files.",
            source="ETH/UCY Pedestrian Trajectory Dataset",
            category="runtime",
            expected_results={
                "rmse_tolerance": float(eth_targets.get("rmse_tolerance", 1.0) or 1.0),
                "min_scenes": int(eth_targets.get("min_scenes", 2) or 2),
            },
            tolerance={
                "rmse": float(eth_targets.get("rmse_tolerance", 1.0) or 1.0),
            },
            unit="meters",
            target_section="eth_trajectory",
        ),
    }


def _build_suite_benchmarks() -> Dict[str, BenchmarkDefinition]:
    return {
        "standard_corridor": BenchmarkDefinition(
            benchmark_id="standard_corridor",
            name="Standard Corridor Evacuation",
            description="Single corridor with known analytical evacuation results.",
            source="Crowd dynamics research - fundamental diagrams",
            category="suite",
            parameters={
                "corridor_length": 50.0,
                "corridor_width": 2.0,
                "num_agents": 50,
                "exit_width": 2.0,
                "agent_speed": 1.4,
            },
            expected_results={
                "evacuation_time": 35.7,
                "flow_rate": 2.66,
                "density_peak": 2.0,
            },
            tolerance={
                "evacuation_time": 5.0,
                "flow_rate": 0.3,
                "density_peak": 0.5,
            },
        ),
        "multi_exit_opposite_walls": BenchmarkDefinition(
            benchmark_id="multi_exit_opposite_walls",
            name="Multi-Exit Opposite Walls Configuration",
            description="Two exits on opposite walls representing the more balanced multi-exit configuration.",
            source="Springer - Exit configuration studies",
            category="suite",
            parameters={
                "room_width": 100.0,
                "room_height": 50.0,
                "num_agents": 100,
                "exits": [
                    {"x": -50, "z": 0, "width": 2.0},
                    {"x": 50, "z": 0, "width": 2.0},
                ],
            },
            expected_results={
                "evacuation_time": 120.0,
                "exit_utilization_balance": 0.8,
                "load_balance": 0.75,
            },
            tolerance={
                "evacuation_time": 15.0,
                "exit_utilization_balance": 0.2,
                "load_balance": 0.2,
            },
        ),
        "multi_exit_same_wall": BenchmarkDefinition(
            benchmark_id="multi_exit_same_wall",
            name="Multi-Exit Same Wall Configuration",
            description="Two exits on the same wall representing a less balanced evacuation layout.",
            source="Springer - Exit configuration studies",
            category="suite",
            parameters={
                "room_width": 100.0,
                "room_height": 50.0,
                "num_agents": 100,
                "exits": [
                    {"x": 0, "z": -25, "width": 2.0},
                    {"x": 0, "z": 25, "width": 2.0},
                ],
            },
            expected_results={
                "evacuation_time": 150.0,
                "exit_utilization_balance": 0.6,
                "load_balance": 0.5,
            },
            tolerance={
                "evacuation_time": 20.0,
                "exit_utilization_balance": 0.3,
                "load_balance": 0.3,
            },
        ),
        "exit89_validation": BenchmarkDefinition(
            benchmark_id="exit89_validation",
            name="EXIT89 Dataset Validation",
            description="Benchmark case matching EXIT89-style empirical pre-evacuation and walking-speed behavior.",
            source="EXIT89 evacuation study",
            category="suite",
            parameters={
                "num_agents": 89,
                "pre_evacuation_delay_mean": 30.0,
                "pre_evacuation_delay_std": 15.0,
                "walking_speed_mean": 1.4,
                "walking_speed_std": 0.3,
            },
            expected_results={
                "average_pre_evacuation_delay": 30.0,
                "average_walking_speed": 1.4,
                "evacuation_time": 180.0,
            },
            tolerance={
                "average_pre_evacuation_delay": 10.0,
                "average_walking_speed": 0.2,
                "evacuation_time": 30.0,
            },
            target_section="exit89",
        ),
    }


def get_validation_benchmark_registry(path: Optional[str] = None) -> ValidationBenchmarkRegistry:
    targets = _load_target_sections(path)
    return ValidationBenchmarkRegistry(
        runtime_benchmarks=_build_runtime_benchmarks(targets),
        suite_benchmarks=_build_suite_benchmarks(),
        target_sections=targets,
    )


def load_validation_targets(path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    return get_validation_benchmark_registry(path).load_targets()
