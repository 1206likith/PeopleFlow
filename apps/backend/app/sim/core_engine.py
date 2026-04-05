"""
Core simulation engine (deterministic, research-focused).
Minimal, well-structured engine for experiments and reproducibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import math
import random
import numpy as np # type: ignore

from app.services.evacuation_parameters import PopulationProfile # type: ignore
from app.services.behavioral_models import behavioral_engine # type: ignore
from app.services.social_force_model import social_force_model # type: ignore
from app.services.structural_graph import BuildingGraph # type: ignore
from app.services.fundamental_diagram import FundamentalDiagram # type: ignore


@dataclass
class SimConfig:
    num_agents: int
    emergency_type: str = "fire"
    floor_number: int = 1
    seed: Optional[int] = None
    duration_seconds: int = 120
    use_social_force: bool = True
    use_behavioral_decisions: bool = True
    routing_policy: str = "nearest" # nearest, least_crowded, guided, stochastic
    enable_hazards: bool = True


@dataclass
class AgentState:
    agent_id: int
    x: float
    y: float
    z: float
    speed: float
    status: str
    panic_level: float
    stress_level: float
    target_exit: Optional[str]
    pre_evacuation_delay: float
    behavior: Any = None
    current_path: Optional[List[str]] = None
    current_waypoint: Optional[Tuple[float, float]] = None
    toxicity: float = 0.0
    visibility_radius: float = 20.0


class CoreSimulationEngine:
    def __init__(self, config: SimConfig):
        self.config = config
        if config.seed is not None:
            random.seed(config.seed)
            np.random.seed(config.seed)
        self.time = 0.0
        self.frame_id = 0
        self.evacuated_count = 0
        self.agents: List[AgentState] = []
        self.exits: List[Dict[str, Any]] = []
        self.walls: List[Dict[str, Any]] = []
        self.obstacles: List[Dict[str, Any]] = []
        self.rooms: List[Dict[str, Any]] = []
        self.building_bounds: Any = None
        self._bounds = (0.0, 100.0, 0.0, 100.0)
        self.graph = BuildingGraph()
        self._kd_tree: Any = None
        
        from app.sim.hazard_engine import HazardEngine # type: ignore
        self.hazard_engine: Any = HazardEngine() if config.enable_hazards else None

    def initialize_from_floor_plan(self, floor_plan_data: Optional[Dict[str, Any]]):
        if not floor_plan_data:
            return
        self.walls = floor_plan_data.get("detected_walls", [])
        self.obstacles = floor_plan_data.get("detected_obstacles", [])
        self.building_bounds = floor_plan_data.get("building_bounds", None)
        self.rooms = floor_plan_data.get("rooms", [])
        self.exits = floor_plan_data.get("exits", [])
        
        hz: Any = self.hazard_engine
        if hz is not None:
            found_hazards = floor_plan_data.get("hazards", [])
            for h in found_hazards:
                hz.add_source(h.get("x", 0), h.get("z", h.get("y", 0)), h.get("rate", 5.0))
            if not found_hazards and self.config.enable_hazards:
                # Add default center fire
                hz.add_source(50.0, 50.0, 10.0)
        
        self.graph.build_from_floor_plan(
            self.walls,
            self.exits,
            self.obstacles,
            self.rooms,
            floor_plan_data.get("image_dimensions", {})
        )
        
        bb: Any = self.building_bounds
        if bb is not None:
            self._bounds = (
                bb.get("min_x", 0.0),
                bb.get("max_x", 100.0),
                bb.get("min_y", 0.0),
                bb.get("max_y", 100.0),
            )

    def set_exits(self, exits: List[Dict[str, Any]]):
        self.exits = exits or []

    def initialize_agents(self):
        self.agents = []
        min_x, max_x, min_z, max_z = self._bounds

        profiles = [
            PopulationProfile.NORMAL_ADULT,
            PopulationProfile.ELDERLY,
            PopulationProfile.INJURED,
            PopulationProfile.CHILD,
            PopulationProfile.DISABLED,
        ]
        weights = [0.7, 0.15, 0.05, 0.05, 0.05]

        for i in range(self.config.num_agents):
            x = random.uniform(min_x + 5, max_x - 5)
            z = random.uniform(min_z + 5, max_z - 5)
            profile = random.choices(profiles, weights=weights)[0]
            behavior = behavioral_engine.initialize_agent_behavior(i, profile)
            target_exit_id = None
            if self.exits:
                target_exit_id = self.exits[0].get("id")
            agent = AgentState(
                agent_id=i,
                x=x,
                y=0.0,
                z=z,
                speed=behavior.walking_speed,
                status="waiting" if behavior.pre_evacuation_delay > 0 else "moving",
                panic_level=behavior.panic_level,
                stress_level=behavior.stress_level,
                target_exit=target_exit_id,
                pre_evacuation_delay=behavior.pre_evacuation_delay,
                behavior=behavior,
            )
            self.agents.append(agent)

    def update(self, dt: float):
        self.time += dt
        
        # Accumulate evacuation capacity budget for exits based on Strict physical bottlenecks
        for exit_data in self.exits:
            if "evac_budget" not in exit_data:
                exit_data["evac_budget"] = 0.0
            exit_width = exit_data.get("width", 2.0)
            
            # Flow capacity: flow_rate = width * 1.3 persons/second/meter
            specific_flow = 1.3 
            flow_capacity = exit_width * specific_flow
            exit_data["evac_budget"] += flow_capacity * dt

        # Build KD-Tree for spatial density mapping
        active_agents = [a for a in self.agents if a.status not in ["evacuated", "collapsed"]]
        if active_agents:
            positions = [[a.x, a.z] for a in active_agents]
            self._kd_tree = np.array(positions)
        else:
            self._kd_tree = None
            
        hz: Any = self.hazard_engine
        if hz is not None:
            hz.update(dt)
            
        for agent in self.agents:
            if agent.status in ["evacuated", "collapsed"]:
                continue
            if agent.status == "waiting":
                agent.pre_evacuation_delay = max(0.0, agent.pre_evacuation_delay - dt)
                if agent.pre_evacuation_delay <= 0:
                    agent.status = "moving"
                continue

            # Update behavioral state
            if agent.behavior and self.config.use_behavioral_decisions:
                density, nearby_panic = self._local_density_and_panic(agent, active_agents)
                agent.behavior = behavioral_engine.update_behavior(
                    agent.behavior,
                    nearby_panic=nearby_panic,
                    congestion_level=density,
                    time_in_simulation=self.time,
                )
                
                # Apply strictly calibrated v(ρ) mathematical curves
                agent.speed = FundamentalDiagram.compute_speed(density, agent.behavior.walking_speed)

            # Health & Visibility Model (Phase 3)
            hz2: Any = self.hazard_engine
            if hz2 is not None:
                c = hz2.get_concentration(agent.x, agent.z)
                agent.toxicity += c * dt
                # Fatigue scaling: heavily exposed agents slow down dramatically
                health_speed_mult = max(0.1, 1.0 - (agent.toxicity / 200.0))
                agent.speed *= health_speed_mult
                
                # Fog of War / Smoke visibility bounding
                agent.visibility_radius = max(2.5, 20.0 - (c * 0.4))
                
                if agent.toxicity >= 200.0:
                    agent.status = "collapsed"
                    agent.speed = 0.0
                    continue

            target_exit = self._resolve_exit(agent)
            if not target_exit:
                continue

            # Graph pathfinding logic
            if agent.current_path is None and len(self.graph.nodes) > 0:
                # Find nearest room/junction to agent
                best_dist = float('inf')
                best_node = None
                for n_id, node in self.graph.nodes.items():
                    if node.node_type in ('room', 'junction'):
                        d = math.hypot(node.x - agent.x, node.y - agent.z)
                        if d < best_dist:
                            best_dist = d
                            best_node = node
                
                # Find target exit node
                exit_node_id = None
                target_exit_id = target_exit.get("id")
                if target_exit_id:
                    # Look for matching exit in graph nodes
                    for n_id, node in self.graph.nodes.items():
                        if node.node_type == 'exit' and str(target_exit_id) in n_id:
                            exit_node_id = n_id
                            break
                if not exit_node_id:
                    for n_id, node in self.graph.nodes.items():
                        if node.node_type == 'exit':
                            exit_node_id = n_id
                            break
                            
                if best_node and exit_node_id:
                    agent.current_path = self.graph.find_path(best_node.node_id, exit_node_id)
                else:
                    agent.current_path = []
            
            # Select current waypoint from path
            wx, wz = float(target_exit.get("x") or 0.0), float(target_exit.get("z", target_exit.get("y")) or 0.0)
            target_path = agent.current_path
            if target_path is not None and len(target_path) > 0:
                next_node_id = target_path[0]
                next_node = self.graph.nodes.get(next_node_id)
                if next_node:
                    wx, wz = next_node.x, next_node.y
                    # Check if reached waypoint
                    if math.hypot(wx - agent.x, wz - agent.z) < 2.0 and len(target_path) > 1:
                        target_path.pop(0)
                        next_node_id = target_path[0]
                        next_node = self.graph.nodes.get(next_node_id)
                        if next_node:
                            wx, wz = next_node.x, next_node.y

            dx = wx - agent.x
            dz = wz - agent.z
            dist = math.hypot(dx, dz)
            
            # Check if ultimately reached actual exit
            actual_dx = float(target_exit.get("x") or 0.0) - agent.x
            actual_dz = float(target_exit.get("z", target_exit.get("y")) or 0.0) - agent.z
            actual_dist = math.hypot(actual_dx, actual_dz)
            
            # Flow capacity accumulation
            if "evac_budget" not in target_exit:
                target_exit["evac_budget"] = 0.0
            
            if actual_dist < target_exit.get("width", 2.0):
                if target_exit.get("evac_budget", 0.0) >= 1.0:
                    agent.status = "evacuated"
                    self.evacuated_count += 1
                    target_exit["evac_budget"] -= 1.0
                    continue
                else:
                    dir_x, dir_z = 0.0, 0.0
                    
            elif dist > 0.01:
                dir_x = dx / dist
                dir_z = dz / dist
            else:
                dir_x = 0.0
                dir_z = 0.0

            fx_social, fz_social = 0.0, 0.0
            if dist >= target_exit.get("width", 2.0) and self.config.use_social_force:
                fx_social, fz_social = social_force_model.calculate_forces(
                    agent.__dict__,
                    [a.__dict__ for a in self.agents if a.agent_id != agent.agent_id],
                    self.walls,
                    target_exit,
                    agent.panic_level,
                )

            vx = dir_x * agent.speed + fx_social * 0.2
            vz = dir_z * agent.speed + fz_social * 0.2
            agent.x += vx * dt
            agent.z += vz * dt

            if self.building_bounds:
                min_x, max_x, min_z, max_z = self._bounds
                margin = 2.0
                agent.x = max(min_x + margin, min(max_x - margin, agent.x))
                agent.z = max(min_z + margin, min(max_z - margin, agent.z))

    def _local_density_and_panic(self, agent: AgentState, active_agents: List[AgentState]) -> Tuple[float, float]:
        positions: Any = self._kd_tree
        if positions is None or len(positions) == 0:
            return 0.0, 0.0
            
        radius = 2.0
        # Query numpy array
        agent_pos = np.array([agent.x, agent.z])
        distances = np.linalg.norm(positions - agent_pos, axis=1)
        indices = np.where(distances <= radius)[0].tolist()
        
        nearby = 0
        panic_sum = 0.0
        for idx in indices:
            other = active_agents[idx]
            if other.agent_id == agent.agent_id:
                continue
            nearby += 1
            panic_sum += other.panic_level
            
        area = math.pi * (radius ** 2)
        density = nearby / area
        nearby_panic = (panic_sum / nearby) if nearby > 0 else 0.0
        return density, nearby_panic

    def _resolve_exit(self, agent: AgentState) -> Optional[Dict[str, Any]]:
        if not self.exits:
            return None
        available_exits = [
            exit_data
            for exit_data in self.exits
            if not bool(exit_data.get("blocked") or exit_data.get("is_blocked"))
        ]
        if not available_exits:
            return None
            
        if self.config.routing_policy == "nearest":
            best_exit = min(available_exits, key=lambda e: math.hypot(e.get("x", 0) - agent.x, e.get("z", e.get("y", 0)) - agent.z))
            return best_exit
            
        elif self.config.routing_policy == "least_crowded":
            def exit_cost(e):
                dist = math.hypot(e.get("x", 0) - agent.x, e.get("z", e.get("y", 0)) - agent.z)
                # Count agents already targeting this exit (rough proxy for crowdedness)
                # We use evac_budget inverses here to simulate queue perception
                queue = sum(1 for a in self.agents if math.hypot(e.get("x", 0) - a.x, e.get("z", e.get("y", 0)) - a.z) < 5.0)
                return dist + (queue * 2.0)
            best_exit = min(available_exits, key=exit_cost)
            return best_exit
            
        elif self.config.routing_policy == "guided":
            if not agent.target_exit:
                # Evenly distribute based on agent ID proxying staff guidance
                assigned_exit = available_exits[agent.agent_id % len(available_exits)]
                agent.target_exit = assigned_exit.get("id")
            for e in available_exits:
                if e.get("id") == agent.target_exit:
                    return e
            return available_exits[0]
            
        elif self.config.routing_policy == "stochastic":
            # Probability proportional to inverse utility (Softmax pathfinding)
            costs = []
            hz: Any = self.hazard_engine
            for e in available_exits:
                ex = float(e.get("x") or 0.0)
                ez = float(e.get("z", e.get("y")) or 0.0)
                dist = math.hypot(ex - agent.x, ez - agent.z)
                queue = sum(1 for a in self.agents if math.hypot(ex - a.x, ez - a.z) < 5.0)
                smoke_penalty = 0.0
                if hz is not None:
                    c = hz.get_concentration(ex, ez) # type: ignore
                    smoke_penalty = c * 0.5
                costs.append(dist + (queue * 2.0) + smoke_penalty)
                
            T = 15.0 # Temperature scaling (Panic noise)
            arr_costs = np.array(costs)
            weights = np.exp(-arr_costs / T)
            probs = weights / np.sum(weights)
            
            chosen_idx = np.random.choice(len(available_exits), p=probs)
            return available_exits[chosen_idx]
            
        # fallback
        return available_exits[0]

    def get_frame(self) -> Dict[str, Any]:
        self.frame_id += 1
        agents_data = [
            {
                "agent_id": a.agent_id,
                "x": a.x,
                "y": a.y,
                "z": a.z,
                "speed": a.speed,
                "status": a.status,
                "panic_level": a.panic_level,
                "stress_level": a.stress_level,
                "target_exit": a.target_exit,
                "pre_evacuation_delay": a.pre_evacuation_delay,
            }
            for a in self.agents
        ]
        return {
            "type": "simulation_update",
            "schema_version": 1,
            "frame_id": self.frame_id,
            "timestamp": self.time,
            "floor_number": self.config.floor_number,
            "agents": agents_data,
            "exits": self.exits,
            "walls": self.walls,
            "obstacles": self.obstacles,
            "stats": {
                "total_agents": self.config.num_agents,
                "evacuated": self.evacuated_count,
                "remaining": self.config.num_agents - self.evacuated_count,
                "completion_percentage": (self.evacuated_count / self.config.num_agents) * 100,
            },
            "seed": self.config.seed,
        }

    def is_complete(self) -> bool:
        if self.time < 5.0:
            return False
        return self.evacuated_count >= self.config.num_agents * 0.95
