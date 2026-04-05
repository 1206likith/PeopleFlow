"""
Canonical deterministic simulation kernel for v3 sessions.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, is_dataclass
import hashlib
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np # type: ignore

from app.sim.core_engine import CoreSimulationEngine, SimConfig


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if is_dataclass(value):
        return asdict(value)
    return value


def _stable_seed(session_id: str, emergency_type: str) -> int:
    digest = hashlib.sha256(f"{session_id}:{emergency_type}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _normalize_routing_policy(value: str) -> str:
    normalized = str(value or "shortest_path").strip().lower().replace(" ", "_")
    if normalized in {"shortest_path", "nearest"}:
        return "nearest"
    if normalized in {"least_crowded", "least-crowded", "congestion_aware"}:
        return "least_crowded"
    if normalized in {"guided_evacuation", "guided"}:
        return "guided"
    if normalized in {"stochastic", "probabilistic"}:
        return "stochastic"
    return "nearest"


def _normalize_exit(exit_data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(exit_data)
    normalized["x"] = float(exit_data.get("x", 0.0) or 0.0)
    normalized["y"] = float(exit_data.get("y", 0.0) or 0.0)
    normalized["z"] = float(exit_data.get("z", exit_data.get("y", 0.0)) or 0.0)
    normalized["width"] = float(exit_data.get("width", 2.0) or 2.0)
    normalized["capacity"] = int(exit_data.get("capacity", 100) or 100)
    return normalized


class SimulationKernel:
    def __init__(self, session_id: str, config: Dict[str, Any]):
        self.session_id = session_id
        self.config = deepcopy(config)
        self.seed = int(config.get("seed") or _stable_seed(session_id, str(config.get("emergency_type") or "fire")))
        self.mode = str(config.get("mode") or "studio")
        self.routing_policy = _normalize_routing_policy(str(config.get("routing_policy") or "shortest_path"))
        self.blocked_exits = set(str(exit_id) for exit_id in (config.get("blocked_exits") or []))
        self.command_log: List[Dict[str, Any]] = []
        self._latest_frame: Optional[Dict[str, Any]] = None
        self._last_evacuated = 0
        self._last_timestamp = 0.0

        parameter_overrides = dict(config.get("parameter_overrides") or {})
        ablation = dict(config.get("ablation") or {})
        duration_seconds = int(float(config.get("max_runtime_seconds") or 180.0))

        self.engine = CoreSimulationEngine(
            SimConfig(
                num_agents=int(config.get("num_agents") or 1),
                emergency_type=str(config.get("emergency_type") or "fire"),
                floor_number=int(config.get("floor_number") or 1),
                seed=self.seed,
                duration_seconds=duration_seconds,
                use_social_force=bool(ablation.get("use_social_force", True)),
                use_behavioral_decisions=bool(ablation.get("use_behavioral_decisions", True)),
                routing_policy=self.routing_policy,
                enable_hazards=not bool(parameter_overrides.get("disable_hazards", False)),
            )
        )

    def initialize(self, floor_plan_data: Optional[Dict[str, Any]]) -> None:
        random.seed(self.seed)
        np.random.seed(self.seed)

        merged = deepcopy(floor_plan_data or {})
        exits = [_normalize_exit(_to_plain(exit_data)) for exit_data in (self.config.get("exits") or merged.get("exits") or [])]
        if exits:
            merged["exits"] = exits

        hazards = [_to_plain(hazard) for hazard in (self.config.get("hazards") or [])]
        if hazards:
            merged["hazards"] = [
                {
                    "id": str(hazard.get("id") or f"hazard-{index + 1}"),
                    "type": str(hazard.get("type") or self.config.get("emergency_type") or "fire"),
                    "x": float(hazard.get("x", 0.0) or 0.0),
                    "z": float(hazard.get("z", hazard.get("y", 0.0)) or 0.0),
                    "rate": float(hazard.get("intensity", 0.6) or 0.6) * 12.0,
                    "radius": float(hazard.get("radius", 8.0) or 8.0),
                    "start_time": float(hazard.get("start_time", 0.0) or 0.0),
                    "duration": hazard.get("duration"),
                }
                for index, hazard in enumerate(hazards)
            ]

        self.engine.initialize_from_floor_plan(merged)
        if exits:
            self.engine.set_exits(exits)

        self._apply_exit_state()
        self.engine.initialize_agents()
        self._apply_agent_biases()
        self._latest_frame = None
        self._last_evacuated = 0
        self._last_timestamp = 0.0

    def step(self, dt: float) -> Dict[str, Any]:
        step_seed = self.seed + int(self.engine.frame_id) + 1
        random.seed(step_seed)
        np.random.seed(step_seed % (2**32 - 1))

        self._apply_exit_state()
        self.engine.config.routing_policy = self.routing_policy
        self.engine.update(dt)
        raw_frame = self.engine.get_frame()
        raw_frame["simulation_id"] = self.session_id
        raw_frame["session_id"] = self.session_id
        raw_frame["mode"] = self.mode
        raw_frame["emergency_type"] = self.config.get("emergency_type")
        raw_frame["hazard_state"] = self._build_hazard_state()
        raw_frame["command_log"] = list(self.command_log[-12:])
        self._latest_frame = raw_frame
        return raw_frame

    def current_frame(self) -> Dict[str, Any]:
        if self._latest_frame is None:
            self._latest_frame = self.step(0.0)
        return deepcopy(self._latest_frame)

    def is_complete(self) -> bool:
        return self.engine.is_complete()

    def apply_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        action = str(command.get("action") or "").strip().lower()
        if action == "close_exit":
            exit_id = str(command.get("exit_id") or "")
            if exit_id:
                self.blocked_exits.add(exit_id)
                self._apply_exit_state()
        elif action == "open_exit":
            exit_id = str(command.get("exit_id") or "")
            if exit_id:
                self.blocked_exits.discard(exit_id)
                self._apply_exit_state()
        elif action == "redirect_crowd":
            target_exit = str(command.get("target_exit") or "")
            for agent in self.engine.agents:
                if agent.status not in {"evacuated", "collapsed"}:
                    agent.target_exit = target_exit or agent.target_exit
                    agent.current_path = None
        elif action == "emergency_announcement":
            for agent in self.engine.agents:
                if agent.status == "waiting":
                    agent.pre_evacuation_delay = 0.0
                    agent.status = "moving"
                agent.panic_level = min(1.0, agent.panic_level + 0.04)
                if agent.behavior:
                    agent.behavior.panic_level = min(1.0, float(agent.behavior.panic_level) + 0.04)

        self.command_log.append(
            {
                "action": action,
                "exit_id": command.get("exit_id"),
                "target_exit": command.get("target_exit"),
                "message": command.get("message"),
                "timestamp": float(self.engine.time),
                "frame_id": int(self.engine.frame_id),
            }
        )
        if len(self.command_log) > 120:
            self.command_log = self.command_log[-120:]
        return {"ok": True, "action": action, "blocked_exits": sorted(self.blocked_exits)}

    def _apply_agent_biases(self) -> None:
        panic_level = float(self.config.get("panic_level") or 0.45)
        parameter_overrides = dict(self.config.get("parameter_overrides") or {})
        speed_multiplier = float(parameter_overrides.get("speed_multiplier", 1.0) or 1.0)

        for agent in self.engine.agents:
            agent.panic_level = max(float(agent.panic_level), panic_level)
            agent.stress_level = max(float(agent.stress_level), panic_level * 0.55)
            agent.speed = max(0.1, float(agent.speed) * speed_multiplier)
            if agent.behavior:
                agent.behavior.panic_level = agent.panic_level
                agent.behavior.stress_level = agent.stress_level
                agent.behavior.walking_speed = max(0.1, float(agent.behavior.walking_speed) * speed_multiplier)

    def _apply_exit_state(self) -> None:
        for exit_data in self.engine.exits:
            exit_id = str(exit_data.get("id") or "")
            is_blocked = exit_id in self.blocked_exits
            exit_data["blocked"] = is_blocked
            exit_data["is_blocked"] = is_blocked

    def _build_hazard_state(self) -> Dict[str, Any]:
        sources: Sequence[Tuple[float, float, float]] = getattr(getattr(self.engine, "hazard_engine", None), "sources", []) or []
        active = []
        for index, source in enumerate(sources):
            x, z, rate = source
            active.append(
                {
                    "id": f"source-{index + 1}",
                    "type": str(self.config.get("emergency_type") or "fire"),
                    "x": float(x),
                    "z": float(z),
                    "intensity": float(rate),
                }
            )

        max_concentration = 0.0
        hazard_engine = getattr(self.engine, "hazard_engine", None)
        smoke_grid = getattr(hazard_engine, "smoke_grid", None)
        if smoke_grid is not None and getattr(smoke_grid, "size", 0):
            max_concentration = float(smoke_grid.max())

        return {
            "active": active,
            "blocked_exits": sorted(self.blocked_exits),
            "max_concentration": max_concentration,
            "emergency_type": str(self.config.get("emergency_type") or "fire"),
        }
