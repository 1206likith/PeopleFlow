"""
Simulation engine (research-grade facade).
Supports legacy MockSimulation and the new CoreSimulationEngine.
"""
from typing import Dict, Optional, Any
import random
import numpy as np

from app.services.mock_simulation import MockSimulation
from .core_engine import CoreSimulationEngine, SimConfig


class SimulationEngine:
    def __init__(
        self,
        num_agents: int,
        emergency_type: str,
        floor_number: int = 1,
        seed: Optional[int] = None,
        ablation: Optional[Dict[str, bool]] = None,
        engine: str = "legacy",
    ):
        self.engine = engine
        if engine == "core":
            config = SimConfig(
                num_agents=num_agents,
                emergency_type=emergency_type,
                floor_number=floor_number,
                seed=seed,
                use_social_force=ablation.get("use_social_force", True) if ablation else True,
                use_behavioral_decisions=ablation.get("use_behavioral_decisions", True) if ablation else True,
            )
            self.sim = CoreSimulationEngine(config)
        else:
            if seed is not None:
                random.seed(seed)
                np.random.seed(seed)
            self.sim = MockSimulation(num_agents, emergency_type, seed=seed)
            self.floor_number = floor_number
            self.sim.floor_number = floor_number
            if ablation:
                self.sim.use_social_force = ablation.get("use_social_force", True)
                self.sim.use_pathfinding = ablation.get("use_pathfinding", True)
                self.sim.use_behavioral_decisions = ablation.get("use_behavioral_decisions", True)
                self.sim.use_hazard_effects = ablation.get("use_hazard_effects", True)

    @property
    def num_agents(self):
        return self.sim.num_agents if self.engine != "core" else self.sim.config.num_agents

    @property
    def time(self):
        return self.sim.time

    @property
    def evacuated_count(self):
        return self.sim.evacuated_count

    def initialize_from_floor_plan(self, floor_plan_data: Optional[Dict[str, Any]]):
        if not floor_plan_data:
            return
        if self.engine == "core":
            self.sim.initialize_from_floor_plan(floor_plan_data)
            return
        self.sim.floor_plan_data = floor_plan_data
        self.sim.walls = floor_plan_data.get("detected_walls", [])
        self.sim.obstacles = floor_plan_data.get("detected_obstacles", [])
        self.sim.rooms = floor_plan_data.get("rooms", [])
        self.sim.corridors = floor_plan_data.get("corridors", [])
        self.sim.boundaries = floor_plan_data.get("boundaries", [])
        self.sim.building_bounds = floor_plan_data.get("building_bounds", None)
        if hasattr(self.sim, "_update_boundary_polygon"):
            self.sim._update_boundary_polygon()

    def set_exits(self, exits):
        if self.engine == "core":
            self.sim.set_exits(exits or [])
        else:
            self.sim.exits = exits or []

    def initialize_agents(self):
        self.sim.initialize_agents()

    def update(self, dt: float):
        if self.engine == "core":
            self.sim.update(dt)
        else:
            self.sim.update_agents(dt)

    def get_frame(self) -> Dict[str, Any]:
        if self.engine == "core":
            return self.sim.get_frame()
        return self.sim.get_frame_data()

    def is_complete(self) -> bool:
        return self.sim.is_complete()
