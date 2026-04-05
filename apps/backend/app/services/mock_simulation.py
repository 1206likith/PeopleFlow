"""
Mock Simulation Service
Generates lightweight simulation data for testing without Unity.
Optimized for speed and constrained to detected building boundaries.
"""

import asyncio
import random
import math
import logging
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MockSimulation:
    """Generates mock simulation data that mimics Unity output."""

    def __init__(self, num_agents: int = 100, emergency_type: str = "fire", seed: Optional[int] = None):
        self.num_agents = num_agents
        self.emergency_type = emergency_type
        self.seed = seed
        self.replay_id = None
        self.agents: List[Dict[str, Any]] = []
        self.exits: List[Dict[str, Any]] = []
        self.danger_zones = [{"x": 20.0, "y": 0.0, "z": 20.0, "radius": 15.0}]
        self.time = 0.0
        self.frame_id = 0
        self.evacuated_count = 0
        self.floor_plan_data = None
        self.walls: List[Dict[str, Any]] = []
        self.obstacles: List[Dict[str, Any]] = []
        self.boundaries: List[Dict[str, Any]] = []
        self.boundary_polygon: List[Tuple[float, float]] = []
        self.boundary_centroid: Optional[Tuple[float, float]] = None
        self.building_bounds: Optional[Dict[str, float]] = None
        self.pathfinder = None
        self.rooms: List[Dict[str, Any]] = []
        self.corridors: List[Dict[str, Any]] = []
        self.hazards: List[Dict[str, Any]] = []
        self.hazard_env = None
        self.hazard_schedule: List[Dict[str, Any]] = []
        self.blocked_exit_rules: List[Dict[str, Any]] = []
        self.blocked_exit_ids: set = set()
        self.agent_profiles: List[Dict[str, Any]] = []
        self.profile_weights: List[float] = []
        self.exit_usage: Dict[str, int] = {}
        self.evacuation_times: List[float] = []
        self.profile_counts: Dict[str, int] = {}
        self.collision_events: int = 0
        self.wall_penetration_count: int = 0
        self.stuck_events: int = 0
        self.raw_wall_count: int = 0
        self.runtime_wall_count: int = 0
        self.runtime_wall_orthogonal_ratio: float = 0.0

        # Ablation toggles (default on)
        self.use_social_force = True
        self.use_pathfinding = True
        self.use_behavioral_decisions = True
        self.use_hazard_effects = True

    def _build_spatial_index(self, cell_size: float = 5.0):
        grid = {}
        for agent in self.agents:
            if agent["status"] == "evacuated":
                continue
            cx = int(agent["x"] // cell_size)
            cz = int(agent["z"] // cell_size)
            grid.setdefault((cx, cz), []).append(agent)
        return grid, cell_size

    def _get_neighbors(self, agent: Dict[str, Any], grid: Dict, cell_size: float, radius: float) -> List[Dict]:
        cx = int(agent["x"] // cell_size)
        cz = int(agent["z"] // cell_size)
        neighbors = []
        r2 = radius * radius
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for other in grid.get((cx + dx, cz + dz), []):
                    if other is agent or other["status"] == "evacuated":
                        continue
                    ox = other["x"] - agent["x"]
                    oz = other["z"] - agent["z"]
                    if (ox * ox + oz * oz) <= r2:
                        neighbors.append(other)
        return neighbors

    def apply_ablation(self, ablation: Optional[Dict[str, bool]]):
        if not ablation:
            return
        mapping = {
            "use_social_force": "use_social_force",
            "use_pathfinding": "use_pathfinding",
            "use_behavioral_decisions": "use_behavioral_decisions",
            "use_hazard_effects": "use_hazard_effects",
        }
        for key, attr in mapping.items():
            if key in ablation and ablation[key] is not None:
                setattr(self, attr, bool(ablation[key]))

    def configure_agent_profiles(self, profiles: Optional[List[Dict[str, Any]]]):
        self.agent_profiles = [dict(p) for p in (profiles or [])]
        self.profile_weights = []
        if not self.agent_profiles:
            return
        for profile in self.agent_profiles:
            self._apply_role_defaults(profile)
        total = 0.0
        for profile in self.agent_profiles:
            ratio = profile.get("ratio")
            if ratio is None:
                ratio = 0.0
            ratio = float(max(0.0, ratio))
            self.profile_weights.append(ratio)
            total += ratio
        if total <= 0.0:
            equal = 1.0 / len(self.agent_profiles)
            self.profile_weights = [equal] * len(self.agent_profiles)
        else:
            self.profile_weights = [w / total for w in self.profile_weights]

    def _pick_profile(self) -> Optional[Dict[str, Any]]:
        if not self.agent_profiles:
            return None
        if len(self.agent_profiles) == 1:
            return self.agent_profiles[0]
        return random.choices(self.agent_profiles, weights=self.profile_weights, k=1)[0]

    def _apply_role_defaults(self, profile_data: Dict[str, Any]):
        role = (profile_data.get("role") or profile_data.get("name") or "").lower()
        defaults = {}
        if role in ("staff", "employee", "security", "teacher", "nurse"):
            defaults = {
                "speed_multiplier": 1.05,
                "panic_bias": -0.05,
                "pre_evacuation_delay": 0.5,
                "personality_type": "leader",
                "decision_model": "bounded_rationality",
            }
        elif role in ("child", "children", "kid"):
            defaults = {
                "speed_multiplier": 0.8,
                "panic_bias": 0.1,
                "personality_type": "child",
            }
        elif role in ("mobility_limited", "disabled", "wheelchair"):
            defaults = {
                "speed_multiplier": 0.6,
                "panic_bias": 0.05,
                "personality_type": "disabled",
            }
        elif role in ("injured",):
            defaults = {
                "speed_multiplier": 0.7,
                "panic_bias": 0.05,
                "personality_type": "injured",
            }

        for key, value in defaults.items():
            if profile_data.get(key) is None:
                profile_data[key] = value

    def _map_population_profile(self, profile_data: Dict[str, Any]):
        from app.services.evacuation_parameters import PopulationProfile

        raw = (profile_data.get("population_profile") or profile_data.get("role") or "").lower()
        mapping = {
            "normal": PopulationProfile.NORMAL_ADULT,
            "normal_adult": PopulationProfile.NORMAL_ADULT,
            "adult": PopulationProfile.NORMAL_ADULT,
            "staff": PopulationProfile.NORMAL_ADULT,
            "employee": PopulationProfile.NORMAL_ADULT,
            "elderly": PopulationProfile.ELDERLY,
            "senior": PopulationProfile.ELDERLY,
            "injured": PopulationProfile.INJURED,
            "child": PopulationProfile.CHILD,
            "children": PopulationProfile.CHILD,
            "disabled": PopulationProfile.DISABLED,
            "mobility_limited": PopulationProfile.DISABLED,
            "wheelchair": PopulationProfile.DISABLED,
        }
        return mapping.get(raw, PopulationProfile.NORMAL_ADULT)

    def _map_personality_type(self, profile_data: Dict[str, Any]):
        from app.services.agent_personality import PersonalityType

        raw = (profile_data.get("personality_type") or profile_data.get("role") or "").lower()
        mapping = {
            "calm": PersonalityType.CALM,
            "leader": PersonalityType.LEADER,
            "panicked": PersonalityType.PANICKED,
            "injured": PersonalityType.INJURED,
            "disabled": PersonalityType.DISABLED,
            "child": PersonalityType.CHILD,
        }
        return mapping.get(raw)

    def _map_decision_model(self, profile_data: Dict[str, Any]):
        from app.services.behavioral_models import DecisionModel

        raw = (profile_data.get("decision_model") or "").lower()
        mapping = {
            "shortest_path": DecisionModel.SHORTEST_PATH,
            "bounded_rationality": DecisionModel.BOUNDED_RATIONALITY,
            "bayesian_nash": DecisionModel.BAYESIAN_NASH,
            "social_influence": DecisionModel.SOCIAL_INFLUENCE,
        }
        return mapping.get(raw)

    def configure_hazards(self, hazards: Optional[List[Dict[str, Any]]], blocked_exits: Optional[List[str]] = None):
        from app.services.multi_hazard_environment import MultiHazardEnvironment, HazardType

        self.hazards = hazards or []
        self.hazard_env = MultiHazardEnvironment() if self.hazards else None
        self.hazard_schedule = []
        self.blocked_exit_rules = []
        self.blocked_exit_ids = set(blocked_exits or [])

        for hazard in self.hazards:
            hazard_type_raw = (hazard.get("type") or "fire").lower()
            if hazard_type_raw == "blocked_exit":
                self.blocked_exit_rules.append(hazard)
                continue
            if not self.hazard_env:
                self.hazard_env = MultiHazardEnvironment()

            type_mapping = {
                "fire": HazardType.FIRE,
                "smoke": HazardType.FIRE,
                "flood": HazardType.FLOOD,
                "gas_leak": HazardType.GAS_LEAK,
                "earthquake": HazardType.EARTHQUAKE,
                "tactical_attack": HazardType.TACTICAL_ATTACK,
                "structural_collapse": HazardType.STRUCTURAL_COLLAPSE,
            }
            hazard_type = type_mapping.get(hazard_type_raw, HazardType.FIRE)
            origin_x = float(hazard.get("x", 0.0))
            origin_y = float(hazard.get("y", 0.0))
            origin_z = float(hazard.get("z", 0.0))
            if self.building_bounds:
                min_x = self.building_bounds.get("min_x", origin_x)
                max_x = self.building_bounds.get("max_x", origin_x)
                min_z = self.building_bounds.get("min_y", origin_z)
                max_z = self.building_bounds.get("max_y", origin_z)
                origin_x = max(min_x, min(max_x, origin_x))
                origin_z = max(min_z, min(max_z, origin_z))
            origin = (origin_x, origin_y, origin_z)
            schedule = {
                "type": hazard_type,
                "origin": origin,
                "intensity": float(hazard.get("intensity", 0.5)),
                "radius": float(hazard.get("radius", 10.0)),
                "start_time": float(hazard.get("start_time", 0.0)),
                "duration": hazard.get("duration"),
                "field": None,
                "activated": False,
                "expired": False,
            }
            self.hazard_schedule.append(schedule)

        # Initialize blocked exits for time 0
        self._update_blocked_exits()

    def _update_blocked_exits(self):
        blocked = set(self.blocked_exit_ids)
        for rule in self.blocked_exit_rules:
            start_time = float(rule.get("start_time", 0.0))
            duration = rule.get("duration")
            if self.time < start_time:
                continue
            if duration is not None and self.time > start_time + float(duration):
                continue
            exit_ids = rule.get("exit_ids") or rule.get("exit_id") or []
            if isinstance(exit_ids, str):
                exit_ids = [exit_ids]
            for exit_id in exit_ids:
                blocked.add(exit_id)
        self.blocked_exit_ids = blocked

    def _update_hazards(self, dt: float):
        if not self.hazard_env:
            self._update_blocked_exits()
            return

        for schedule in self.hazard_schedule:
            if schedule["expired"]:
                continue
            start_time = schedule["start_time"]
            duration = schedule.get("duration")
            if not schedule["activated"] and self.time >= start_time:
                schedule["field"] = self.hazard_env.add_hazard(
                    schedule["type"],
                    schedule["origin"],
                    initial_intensity=schedule["intensity"],
                    radius=schedule["radius"],
                )
                schedule["activated"] = True
            if schedule["activated"] and duration is not None and self.time >= start_time + float(duration):
                schedule["expired"] = True

        # Remove expired hazards from environment
        for schedule in self.hazard_schedule:
            if schedule.get("expired") and schedule.get("field"):
                for hazard_type, fields in list(self.hazard_env.active_hazards.items()):
                    self.hazard_env.active_hazards[hazard_type] = [f for f in fields if f is not schedule["field"]]

        self.hazard_env.update_hazards(dt, {
            "walls": self.walls,
            "obstacles": self.obstacles,
            "boundaries": self.boundaries,
            "rooms": self.rooms,
        })
        self._update_blocked_exits()

    def _get_hazard_state(self) -> Dict[str, Any]:
        state = {
            "time": self.time,
            "active": [],
            "blocked_exits": list(self.blocked_exit_ids),
        }
        if not self.hazard_env:
            return state
        for hazard_type, fields in self.hazard_env.active_hazards.items():
            for field in fields:
                state["active"].append({
                    "type": hazard_type.value,
                    "origin": field.origin,
                    "intensity": field.intensity,
                    "radius": field.radius,
                    "time_elapsed": field.time_elapsed,
                })
        return state

    def _project_point_to_segment(
        self,
        x: float,
        y: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> Tuple[float, float, float]:
        A = x - x1
        B = y - y1
        C = x2 - x1
        D = y2 - y1
        len_sq = C * C + D * D
        if len_sq == 0:
            return x1, y1, math.sqrt(A * A + B * B)
        t = (A * C + B * D) / len_sq
        if t < 0:
            px, py = x1, y1
        elif t > 1:
            px, py = x2, y2
        else:
            px, py = x1 + t * C, y1 + t * D
        dx = x - px
        dy = y - py
        return px, py, math.sqrt(dx * dx + dy * dy)

    def _boundary_polygon_from_segments(self, boundaries: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
        if not boundaries:
            return []
        points = [(float(boundaries[0]["x1"]), float(boundaries[0]["y1"]))]
        for b in boundaries:
            points.append((float(b["x2"]), float(b["y2"])))
        if points[0] != points[-1]:
            points.append(points[0])
        return points

    def _update_boundary_polygon(self):
        self.boundary_polygon = self._boundary_polygon_from_segments(self.boundaries)
        if not self.boundary_polygon:
            self.boundary_centroid = None
            return
        xs = [p[0] for p in self.boundary_polygon[:-1]]
        ys = [p[1] for p in self.boundary_polygon[:-1]]
        if xs and ys:
            self.boundary_centroid = (sum(xs) / len(xs), sum(ys) / len(ys))
        else:
            self.boundary_centroid = None

    def _point_in_polygon(self, x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
        if not polygon:
            return True
        inside = False
        for i in range(len(polygon) - 1):
            x1, y1 = polygon[i]
            x2, y2 = polygon[i + 1]
            if (y1 > y) != (y2 > y):
                xinters = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
                if x < xinters:
                    inside = not inside
        return inside

    def _snap_inside_boundary(self, x: float, z: float) -> Tuple[float, float]:
        if not self.boundaries:
            return x, z
        best_dist = None
        best_point = None
        for b in self.boundaries:
            px, py, dist = self._project_point_to_segment(x, z, b["x1"], b["y1"], b["x2"], b["y2"])
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_point = (px, py)
        if best_point is None:
            return x, z
        if self.boundary_centroid:
            cx, cy = self.boundary_centroid
            dx = cx - best_point[0]
            dy = cy - best_point[1]
            norm = math.sqrt(dx * dx + dy * dy)
            if norm > 0.001:
                scale = 1.0
                return best_point[0] + (dx / norm) * scale, best_point[1] + (dy / norm) * scale
        return best_point[0], best_point[1]

    def _point_to_wall_distance(self, x: float, z: float, wall: Dict[str, Any]) -> float:
        x1, z1 = wall["x1"], wall["y1"]
        x2, z2 = wall["x2"], wall["y2"]
        _, _, dist = self._project_point_to_segment(x, z, x1, z1, x2, z2)
        return dist

    def _wall_angle_degrees(self, wall: Dict[str, Any]) -> float:
        dx = float(wall.get("x2", 0.0)) - float(wall.get("x1", 0.0))
        dz = float(wall.get("y2", 0.0)) - float(wall.get("y1", 0.0))
        angle = abs(math.degrees(math.atan2(dz, dx))) % 180.0
        if angle > 90.0:
            angle = 180.0 - angle
        return float(angle)

    def _is_near_orthogonal_wall(self, wall: Dict[str, Any], tolerance: float = 11.0) -> bool:
        angle = self._wall_angle_degrees(wall)
        return min(abs(angle), abs(90.0 - angle)) <= tolerance

    def _sanitize_runtime_walls(self, walls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reduce noisy wall storms before pathfinding/runtime.
        Keeps boundary/orthogonal structure and drops low-value diagonals.
        """
        if not walls:
            self.runtime_wall_count = 0
            self.runtime_wall_orthogonal_ratio = 0.0
            return []

        if self.building_bounds:
            width = max(
                1.0,
                float(self.building_bounds.get("max_x", 100.0)) - float(self.building_bounds.get("min_x", 0.0)),
            )
            height = max(
                1.0,
                float(self.building_bounds.get("max_y", 100.0)) - float(self.building_bounds.get("min_y", 0.0)),
            )
        else:
            width = 100.0
            height = 100.0
        min_span = min(width, height)
        diagonal = math.hypot(width, height)

        normalized: List[Dict[str, Any]] = []
        dedupe = set()
        tol = max(1.0, min_span * 0.004)
        min_length = max(2.0, min_span * 0.012)
        max_length = diagonal * 1.2

        for wall in walls:
            if not isinstance(wall, dict):
                continue
            try:
                x1 = float(wall.get("x1", 0.0))
                y1 = float(wall.get("y1", 0.0))
                x2 = float(wall.get("x2", 0.0))
                y2 = float(wall.get("y2", 0.0))
            except (TypeError, ValueError):
                continue

            length = float(wall.get("length", math.hypot(x2 - x1, y2 - y1)))
            if length < min_length or length > max_length:
                continue

            key = (
                round(min(x1, x2) / tol),
                round(min(y1, y2) / tol),
                round(max(x1, x2) / tol),
                round(max(y1, y2) / tol),
            )
            if key in dedupe:
                continue
            dedupe.add(key)

            wall_type = str(wall.get("type", "internal"))
            confidence = wall.get("confidence")
            try:
                thickness = max(0.8, float(wall.get("thickness", 1.0)))
            except (TypeError, ValueError):
                thickness = 1.0

            normalized.append(
                {
                    **wall,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "length": length,
                    "thickness": thickness,
                    "type": wall_type,
                    "confidence": confidence,
                }
            )

        def boundary_wall(item: Dict[str, Any]) -> bool:
            wall_type = str(item.get("type", "")).lower()
            return "boundary" in wall_type or wall_type in {"top", "bottom", "left", "right"}

        def orthogonal_ratio(items: List[Dict[str, Any]]) -> float:
            if not items:
                return 0.0
            orth = sum(1 for item in items if self._is_near_orthogonal_wall(item))
            return orth / max(1, len(items))

        ratio = orthogonal_ratio(normalized)
        if len(normalized) > 180 and ratio < 0.68:
            short_diag_limit = max(8.0, min_span * 0.05)
            filtered: List[Dict[str, Any]] = []
            for wall in normalized:
                if boundary_wall(wall):
                    filtered.append(wall)
                    continue
                if self._is_near_orthogonal_wall(wall):
                    if float(wall.get("length", 0.0)) >= max(4.0, min_span * 0.015):
                        filtered.append(wall)
                    continue
                confidence = wall.get("confidence")
                confidence_value = float(confidence) if confidence is not None else 0.0
                if float(wall.get("length", 0.0)) <= short_diag_limit and confidence_value >= 0.65:
                    filtered.append(wall)
            normalized = filtered
            ratio = orthogonal_ratio(normalized)

        if len(normalized) > 1000:
            normalized.sort(
                key=lambda item: (
                    1 if boundary_wall(item) else 0,
                    1 if self._is_near_orthogonal_wall(item) else 0,
                    float(item.get("confidence", 0.0) or 0.0),
                    float(item.get("length", 0.0)),
                ),
                reverse=True,
            )
            normalized = normalized[:1000]
            ratio = orthogonal_ratio(normalized)

        self.runtime_wall_count = len(normalized)
        self.runtime_wall_orthogonal_ratio = float(ratio)
        return normalized

    def _check_wall_collision(self, x: float, z: float, agent_radius: float = 0.3) -> bool:
        for wall in self.walls:
            dist = self._point_to_wall_distance(x, z, wall)
            if dist < agent_radius + wall.get("thickness", 0.2) / 2:
                return True
        return False

    def _check_obstacle_collision(self, x: float, z: float, agent_radius: float = 0.3) -> bool:
        for obstacle in self.obstacles:
            obs_x = float(obstacle.get("x", 0.0))
            obs_z = float(obstacle.get("z", obstacle.get("y", 0.0)))
            obs_width = float(obstacle.get("width", 1.0)) / 2
            obs_depth = float(obstacle.get("depth", obstacle.get("height", 1.0))) / 2
            if (abs(x - obs_x) < obs_width + agent_radius and
                    abs(z - obs_z) < obs_depth + agent_radius):
                return True
        return False

    def _is_valid_spawn_position(self, x: float, z: float) -> bool:
        if self.boundary_polygon and not self._point_in_polygon(x, z, self.boundary_polygon):
            return False
        if self._check_wall_collision(x, z, agent_radius=0.42):
            return False
        if self._check_obstacle_collision(x, z, agent_radius=0.42):
            return False
        if self.pathfinder and not self.pathfinder.is_walkable(x, z):
            return False
        return True

    def _sample_spawn_candidate(
        self,
        safe_min_x: float,
        safe_max_x: float,
        safe_min_z: float,
        safe_max_z: float,
    ) -> Tuple[float, float]:
        """
        Prefer room/corridor boxes for spawn sampling before global bounds.
        """
        candidate_spaces: List[Dict[str, Any]] = []
        for space in self.rooms or []:
            if isinstance(space, dict):
                candidate_spaces.append(space)
        for space in self.corridors or []:
            if isinstance(space, dict):
                candidate_spaces.append(space)

        if candidate_spaces and random.random() < 0.85:
            space = random.choice(candidate_spaces)
            sx = float(space.get("x", safe_min_x))
            sz = float(space.get("y", space.get("z", safe_min_z)))
            sw = max(1.0, float(space.get("width", safe_max_x - safe_min_x)))
            sh = max(1.0, float(space.get("height", safe_max_z - safe_min_z)))
            margin = min(sw, sh) * 0.08
            x = random.uniform(sx + margin, sx + max(margin, sw - margin))
            z = random.uniform(sz + margin, sz + max(margin, sh - margin))
            return x, z

        x = random.uniform(safe_min_x, safe_max_x)
        z = random.uniform(safe_min_z, safe_max_z)
        return x, z

    def initialize_agents(self):
        from app.services.behavioral_models import behavioral_engine
        from app.services.agent_personality import PersonalityGenerator
        from app.services.evacuation_parameters import parameter_database

        self.agents = []
        if self.building_bounds:
            min_x = self.building_bounds.get("min_x", 0)
            max_x = self.building_bounds.get("max_x", 100)
            min_z = self.building_bounds.get("min_y", 0)
            max_z = self.building_bounds.get("max_y", 100)
        else:
            min_x, max_x = 0, 100
            min_z, max_z = 0, 100

        margin = 5
        safe_min_x = min_x + margin
        safe_max_x = max_x - margin
        safe_min_z = min_z + margin
        safe_max_z = max_z - margin

        if safe_max_x <= safe_min_x:
            safe_min_x = min_x
            safe_max_x = max_x
        if safe_max_z <= safe_min_z:
            safe_min_z = min_z
            safe_max_z = max_z

        for i in range(self.num_agents):
            x, z = 0.0, 0.0
            valid_position = False
            for _ in range(40):
                x, z = self._sample_spawn_candidate(safe_min_x, safe_max_x, safe_min_z, safe_max_z)
                if self._is_valid_spawn_position(x, z):
                    if self.pathfinder:
                        x, z = self.pathfinder.get_nearest_walkable(x, z, search_radius=5.0)
                    valid_position = True
                    break
            if not valid_position:
                x = (safe_min_x + safe_max_x) / 2
                z = (safe_min_z + safe_max_z) / 2
                if self.boundary_polygon and not self._point_in_polygon(x, z, self.boundary_polygon):
                    x, z = self._snap_inside_boundary(x, z)
                logger.warning("Could not find valid spawn position for agent %s", i)

            profile_data = self._pick_profile()
            if profile_data:
                population_profile = self._map_population_profile(profile_data)
                behavior = behavioral_engine.initialize_agent_behavior(i, population_profile)
                decision_model = self._map_decision_model(profile_data)
                if decision_model is not None:
                    behavior.decision_model = decision_model
            else:
                behavior = behavioral_engine.initialize_agent_behavior(i)

            personality = PersonalityGenerator.generate_personality()
            if profile_data:
                personality_type = self._map_personality_type(profile_data)
                if personality_type is not None:
                    personality.personality_type = personality_type
                speed_multiplier = float(profile_data.get("speed_multiplier", 1.0))
                behavior.walking_speed *= speed_multiplier
                if profile_data.get("pre_evacuation_delay") is not None:
                    behavior.pre_evacuation_delay = float(profile_data["pre_evacuation_delay"])
                if profile_data.get("panic_bias") is not None:
                    behavior.panic_level = min(1.0, max(0.0, behavior.panic_level + float(profile_data["panic_bias"])))
                if profile_data.get("stress_bias") is not None:
                    behavior.stress_level = min(1.0, max(0.0, behavior.stress_level + float(profile_data["stress_bias"])))

            pre_delay = max(0.0, behavior.pre_evacuation_delay + personality.get_decision_delay())
            base_speed = behavior.walking_speed * personality.get_speed_modifier()

            available_exits = [e for e in self.exits if e.get("id") not in self.blocked_exit_ids]
            target_exit_id = behavioral_engine.choose_exit(
                behavior,
                (x, 0.0, z),
                available_exits,
                [],
                0.0,
            )
            if not target_exit_id:
                available_exits = [e for e in self.exits if e.get("id") not in self.blocked_exit_ids]
                target_exit = self._choose_exit((x, z), available_exits, panic_level=behavior.panic_level)
                target_exit_id = target_exit.get("id") if target_exit else None

            profile_group = profile_data.get("name") if profile_data else "default"
            self.profile_counts[profile_group] = self.profile_counts.get(profile_group, 0) + 1

            self.agents.append({
                "agent_id": i,
                "x": x,
                "y": 0.0,
                "z": z,
                "target_exit": target_exit_id,
                "target_exit_locked_until": random.uniform(1.2, 3.5),
                "speed": base_speed * parameter_database.get_speed_reduction(0.0),
                "status": "waiting" if pre_delay > 0.0 else "moving",
                "panic_level": behavior.panic_level,
                "stress_level": behavior.stress_level,
                "pre_evacuation_delay": pre_delay,
                "evacuation_time": None,
                "behavior": behavior,
                "personality": personality,
                "population_profile": getattr(behavior.profile, "value", "normal_adult"),
                "decision_model": behavior.decision_model.value,
                "family_group_id": personality.family_group_id,
                "profile_group": profile_group,
                "familiarity": (profile_data.get("familiarity") if profile_data else None),
                "stuck_counter": 0,
            })

    def _choose_exit(
        self,
        pos: Tuple[float, float],
        exits: Optional[List[Dict[str, Any]]] = None,
        current_exit_id: Optional[str] = None,
        panic_level: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        if exits is None:
            exits = self.exits
        if not exits:
            return None
        px, pz = pos
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for exit_item in exits:
            ex = float(exit_item.get("x", 0.0))
            ez = float(exit_item.get("z", exit_item.get("y", 0.0)))
            dist = math.sqrt((ex - px) ** 2 + (ez - pz) ** 2)
            capacity = max(1.0, float(exit_item.get("capacity", 100.0)))
            usage = float(self.exit_usage.get(str(exit_item.get("id", "")), 0))
            pressure = usage / capacity
            # Higher panic reduces willingness to take very long detours.
            panic_bias = max(0.1, 1.0 - min(0.8, panic_level * 0.6))
            score = dist * panic_bias + pressure * 45.0
            if current_exit_id and str(exit_item.get("id")) == str(current_exit_id):
                score *= 0.88
            scored.append((score, exit_item))
        scored.sort(key=lambda item: item[0])
        return scored[0][1] if scored else exits[0]

    def _estimate_disaster_proximity(self, x: float, z: float) -> float:
        """Estimate hazard proximity as normalized [0,1] signal."""
        if self.hazard_env and self.hazard_env.active_hazards:
            max_intensity = 0.0
            for fields in self.hazard_env.active_hazards.values():
                for field in fields:
                    intensity = field.get_intensity_at_position((x, 0.0, z))
                    if intensity > max_intensity:
                        max_intensity = intensity
            return max_intensity
        max_effect = 0.0
        for zone in self.danger_zones or []:
            zx = zone.get("x", 0.0)
            zz = zone.get("z", zone.get("y", 0.0))
            radius = max(1e-6, zone.get("radius", 1.0))
            dist = math.sqrt((x - zx) ** 2 + (z - zz) ** 2)
            if dist < radius:
                effect = 1.0 - (dist / radius)
                if effect > max_effect:
                    max_effect = effect
        return max_effect

    def update_agents(self, dt: float) -> List[Dict[str, Any]]:
        from app.services.behavioral_models import behavioral_engine
        from app.services.evacuation_parameters import parameter_database
        from app.services.social_force_model import social_force_model

        self.time += dt
        self.frame_id += 1

        if self.use_hazard_effects:
            self._update_hazards(dt)

        spatial_index, cell_size = self._build_spatial_index(cell_size=5.0)
        bottlenecks = []

        available_exits = [e for e in self.exits if e.get("id") not in self.blocked_exit_ids]

        for agent in self.agents:
            if agent["status"] == "evacuated":
                continue

            if agent.get("status") == "waiting":
                agent["pre_evacuation_delay"] = max(0.0, agent.get("pre_evacuation_delay", 0.0) - dt)
                if agent["pre_evacuation_delay"] <= 0.0:
                    agent["status"] = "moving"
                continue

            nearby_agents = self._get_neighbors(agent, spatial_index, cell_size, radius=5.0)
            density = len(nearby_agents) / (math.pi * 5.0 ** 2)
            nearby_panic = 0.0
            if nearby_agents:
                nearby_panic = sum(a.get("panic_level", 0.0) for a in nearby_agents) / len(nearby_agents)

            behavior = agent.get("behavior")
            personality = agent.get("personality")
            disaster_proximity = self._estimate_disaster_proximity(agent["x"], agent["z"])
            hazard_effects = {}
            if self.use_hazard_effects and self.hazard_env:
                hazard_effects = self.hazard_env.get_environmental_effects(
                    (agent["x"], agent["y"], agent["z"])
                )
                hazard_proximity = max(0.0, 1.0 - float(hazard_effects.get("visibility", 1.0)))
                disaster_proximity = max(disaster_proximity, hazard_proximity)

            if behavior and self.use_behavioral_decisions:
                behavior = behavioral_engine.update_behavior(
                    behavior,
                    nearby_panic=nearby_panic,
                    disaster_proximity=disaster_proximity,
                    congestion_level=density,
                    time_in_simulation=self.time,
                )
                agent["behavior"] = behavior
                agent["panic_level"] = behavior.panic_level
                agent["stress_level"] = behavior.stress_level

            if personality:
                personality.update_emotional_state(agent.get("stress_level", 0.0), nearby_panic)

            # Update speed using behavioral + density model
            if behavior:
                speed = behavior.walking_speed
            else:
                speed = agent.get("speed", 1.2)
            if personality:
                speed *= personality.get_speed_modifier()
            speed *= parameter_database.get_speed_reduction(density)
            if hazard_effects:
                speed *= float(hazard_effects.get("speed_modifier", 1.0))
            agent["speed"] = speed

            if hazard_effects:
                panic_increase = float(hazard_effects.get("panic_increase", 0.0)) * dt
                agent["panic_level"] = min(1.0, agent.get("panic_level", 0.0) + panic_increase)
                agent["stress_level"] = min(1.0, agent.get("stress_level", 0.0) + panic_increase * 0.5)
                agent["visibility"] = float(hazard_effects.get("visibility", 1.0))
                agent["smoke_exposure"] = float(hazard_effects.get("breathing_difficulty", 0.0))
                if behavior:
                    behavior.panic_level = agent["panic_level"]
                    behavior.stress_level = agent["stress_level"]

            # Re-evaluate exit choice occasionally
            force_reroute = bool(hazard_effects.get("path_blocked")) if hazard_effects else False
            reroute_window_open = self.time >= float(agent.get("target_exit_locked_until", 0.0))
            if force_reroute or (reroute_window_open and self.use_behavioral_decisions and random.random() < 0.08):
                previous_exit_id = agent.get("target_exit")
                if behavior:
                    chosen_exit = behavioral_engine.choose_exit(
                        behavior,
                        (agent["x"], agent["y"], agent["z"]),
                        available_exits,
                        nearby_agents,
                        self.time,
                    )
                    if chosen_exit:
                        agent["target_exit"] = chosen_exit
                else:
                    target_exit = self._choose_exit(
                        (agent["x"], agent["z"]),
                        available_exits,
                        current_exit_id=agent.get("target_exit"),
                        panic_level=float(agent.get("panic_level", 0.0)),
                    )
                    if target_exit:
                        agent["target_exit"] = target_exit.get("id")
                if agent.get("target_exit") != previous_exit_id:
                    agent["target_exit_locked_until"] = self.time + random.uniform(1.8, 4.0)

            if not available_exits:
                continue

            target_exit = next((e for e in available_exits if e.get("id") == agent.get("target_exit")), None)
            if not target_exit:
                target_exit = available_exits[0]
                agent["target_exit"] = target_exit.get("id")

            exit_x = target_exit.get("x", 0.0)
            exit_z = target_exit.get("z", target_exit.get("y", 0.0))

            dx = exit_x - agent["x"]
            dz = exit_z - agent["z"]
            dist = math.sqrt(dx * dx + dz * dz) + 1e-6

            # Optional pathfinding: steer to waypoint
            goal_exit = target_exit
            if self.pathfinder and self.use_pathfinding and dist > 5.0:
                try:
                    if (
                        "path" not in agent
                        or "path_time" not in agent
                        or self.time - agent.get("path_time", 0.0) > 2.0
                        or len(agent.get("path", [])) < 2
                    ):
                        path = self.pathfinder.find_path((agent["x"], agent["z"]), (exit_x, exit_z))
                        if path and len(path) >= 2:
                            agent["path"] = path
                            agent["path_index"] = 1
                            agent["path_time"] = self.time
                    if agent.get("path"):
                        path_index = agent.get("path_index", 1)
                        if path_index < len(agent["path"]):
                            waypoint_x, waypoint_z = agent["path"][path_index]
                            if math.sqrt((waypoint_x - agent["x"]) ** 2 + (waypoint_z - agent["z"]) ** 2) < 1.0:
                                agent["path_index"] = min(path_index + 1, len(agent["path"]) - 1)
                            goal_exit = {"x": waypoint_x, "y": 0.0, "z": waypoint_z}
                except Exception:
                    pass

            # Social force model for movement
            if self.use_social_force:
                fx, fz = social_force_model.calculate_forces(
                    agent,
                    nearby_agents,
                    self.walls,
                    goal_exit,
                    agent.get("panic_level", 0.0),
                )
                vx, vz = fx, fz
            else:
                vx = dx / dist
                vz = dz / dist

            speed = agent["speed"]
            vel_mag = math.sqrt(vx * vx + vz * vz)
            if vel_mag > 1e-6:
                max_speed = max(0.1, speed * 1.2)
                if vel_mag > max_speed:
                    scale = max_speed / vel_mag
                    vx *= scale
                    vz *= scale

            prev_x = float(agent["x"])
            prev_z = float(agent["z"])
            sub_steps = 3 if speed > 1.25 else 2
            step_dt = dt / sub_steps
            for _ in range(sub_steps):
                next_x = float(agent["x"]) + vx * step_dt
                next_z = float(agent["z"]) + vz * step_dt

                if self.pathfinder and self.use_pathfinding and not self.pathfinder.is_walkable(next_x, next_z):
                    self.collision_events += 1
                    next_x, next_z = self.pathfinder.get_nearest_walkable(next_x, next_z, search_radius=2.2)

                if self.boundary_polygon:
                    if not self._point_in_polygon(next_x, next_z, self.boundary_polygon):
                        self.collision_events += 1
                        next_x, next_z = self._snap_inside_boundary(next_x, next_z)
                elif self.building_bounds:
                    min_x = self.building_bounds.get("min_x", 0)
                    max_x = self.building_bounds.get("max_x", 100)
                    min_z = self.building_bounds.get("min_y", 0)
                    max_z = self.building_bounds.get("max_y", 100)
                    margin = 3
                    next_x = max(min_x + margin, min(max_x - margin, next_x))
                    next_z = max(min_z + margin, min(max_z - margin, next_z))

                wall_hit = self._check_wall_collision(next_x, next_z, agent_radius=0.45)
                obstacle_hit = self._check_obstacle_collision(next_x, next_z, agent_radius=0.45)
                if wall_hit or obstacle_hit:
                    self.collision_events += 1
                    if wall_hit:
                        self.wall_penetration_count += 1
                    if not self._check_wall_collision(prev_x, prev_z, agent_radius=0.45) and not self._check_obstacle_collision(prev_x, prev_z, agent_radius=0.45):
                        next_x, next_z = prev_x, prev_z
                    elif self.pathfinder and self.use_pathfinding:
                        next_x, next_z = self.pathfinder.get_nearest_walkable(prev_x, prev_z, search_radius=3.0)
                    else:
                        next_x, next_z = self._snap_inside_boundary(prev_x, prev_z)
                    agent["stuck_counter"] = int(agent.get("stuck_counter", 0)) + 1
                    agent["x"], agent["z"] = next_x, next_z
                    break

                agent["x"], agent["z"] = next_x, next_z

            moved = math.sqrt((float(agent["x"]) - prev_x) ** 2 + (float(agent["z"]) - prev_z) ** 2)
            if moved < 0.02:
                agent["stuck_counter"] = int(agent.get("stuck_counter", 0)) + 1
            else:
                agent["stuck_counter"] = 0

            if int(agent.get("stuck_counter", 0)) > 20:
                self.stuck_events += 1
                if self.pathfinder and self.use_pathfinding:
                    agent["x"], agent["z"] = self.pathfinder.get_nearest_walkable(agent["x"], agent["z"], search_radius=6.0)
                    agent["path"] = []
                    agent["path_index"] = 0
                agent["stuck_counter"] = 0

            exit_width = float(target_exit.get("width", 2.0))
            if math.sqrt((agent["x"] - exit_x) ** 2 + (agent["z"] - exit_z) ** 2) < exit_width:
                agent["status"] = "evacuated"
                agent["evacuation_time"] = self.time
                self.evacuated_count += 1
                exit_id = target_exit.get("id")
                if exit_id:
                    self.exit_usage[exit_id] = self.exit_usage.get(exit_id, 0) + 1
                self.evacuation_times.append(self.time)
                continue

            if len(nearby_agents) > 10:
                bottlenecks.append({
                    "x": agent["x"],
                    "y": agent["y"],
                    "z": agent["z"],
                    "density": len(nearby_agents),
                })

        # Periodic emergent bottleneck detection (costly)
        if self.frame_id % 10 == 0:
            try:
                from app.services.bottleneck_formation import BottleneckFormationModel
                model = BottleneckFormationModel()
                detected = model.detect_bottlenecks(
                    [a for a in self.agents if a["status"] != "evacuated"],
                    self.exits,
                )
                bottlenecks.extend(detected[:10])
            except Exception:
                pass

        return bottlenecks[:10]

    def get_frame_data(self) -> Dict[str, Any]:
        agents_data = [
            {
                "agent_id": agent["agent_id"],
                "x": agent["x"],
                "y": agent["y"],
                "z": agent["z"],
                "speed": agent["speed"],
                "status": agent["status"],
                "panic_level": agent.get("panic_level"),
                "stress_level": agent.get("stress_level"),
                "target_exit": agent.get("target_exit"),
                "profile_group": agent.get("profile_group"),
                "visibility": agent.get("visibility"),
                "smoke_exposure": agent.get("smoke_exposure"),
            }
            for agent in self.agents
        ]

        exits_data = []
        for exit_item in self.exits:
            exits_data.append({
                "id": exit_item.get("id", f"exit_{len(exits_data) + 1}"),
                "x": exit_item.get("x", 0.0),
                "y": exit_item.get("y", 0.0),
                "z": exit_item.get("z", exit_item.get("y", 0.0)),
                "name": exit_item.get("name", f"Exit {len(exits_data) + 1}"),
                "width": exit_item.get("width", 2.0),
                "capacity": exit_item.get("capacity", 100),
                "blocked": exit_item.get("id") in self.blocked_exit_ids,
            })

        exit_evac_counts = [
            {"exit_id": exit_id, "count": count}
            for exit_id, count in (self.exit_usage or {}).items()
        ]
        profile_counts = [
            {"profile_id": profile_id, "count": count}
            for profile_id, count in (self.profile_counts or {}).items()
        ]

        agent_count = len(agents_data)
        avg_speed = sum(a.get("speed", 0.0) for a in agents_data) / max(1, agent_count)
        avg_panic = sum(a.get("panic_level") or 0.0 for a in agents_data) / max(1, agent_count)
        avg_stress = sum(a.get("stress_level") or 0.0 for a in agents_data) / max(1, agent_count)

        return {
            "type": "simulation_update",
            "schema_version": 1,
            "frame_id": self.frame_id,
            "timestamp": self.time,
            "floor_number": getattr(self, "floor_number", 1),
            "agents": agents_data,
            "bottlenecks": [],
            "hazards": self.hazards,
            "exit_usage": [
                {"exit_id": exit_item.get("id", ""), "queue_length": 0}
                for exit_item in exits_data
                if exit_item.get("id")
            ],
            "exit_evac_counts": exit_evac_counts,
            "profile_counts": profile_counts,
            "walls": self.walls,
            "exits": exits_data,
            "obstacles": self.obstacles,
            "building_bounds": self.building_bounds,
            "seed": self.seed,
            "replay_id": self.replay_id,
            "hazard_state": self._get_hazard_state(),
            "collision_events": int(self.collision_events),
            "wall_penetration_count": int(self.wall_penetration_count),
            "nav_debug": {
                "pathfinding_enabled": bool(self.pathfinder is not None and self.use_pathfinding),
                "grid_resolution": getattr(self.pathfinder, "grid_resolution", None) if self.pathfinder else None,
                "blocked_exit_count": len(self.blocked_exit_ids),
                "stuck_events": int(self.stuck_events),
                "raw_wall_count": int(self.raw_wall_count),
                "runtime_wall_count": int(self.runtime_wall_count),
                "runtime_wall_orthogonal_ratio": round(float(self.runtime_wall_orthogonal_ratio), 3),
            },
            "stats": {
                "total_agents": self.num_agents,
                "evacuated": self.evacuated_count,
                "remaining": self.num_agents - self.evacuated_count,
                "completion_percentage": (self.evacuated_count / max(1, self.num_agents)) * 100,
                "exit_usage": self.exit_usage,
                "profile_counts": self.profile_counts,
                "avg_speed": avg_speed,
                "avg_panic": avg_panic,
                "avg_stress": avg_stress,
                "evacuation_rate": self.evacuated_count / max(1e-6, self.time),
            },
        }

    def is_complete(self) -> bool:
        if self.time < 5.0:
            return False
        return self.evacuated_count >= self.num_agents * 0.95


async def run_mock_simulation(
    simulation_id: str,
    num_agents: int = 100,
    emergency_type: str = "fire",
    callback=None,
    floor_number: int = 1,
    exits: List[Dict] = None,
    floor_plan_data: Optional[Dict] = None,
    seed: Optional[int] = None,
    hazards: Optional[List[Dict[str, Any]]] = None,
    agent_profiles: Optional[List[Dict[str, Any]]] = None,
    blocked_exits: Optional[List[str]] = None,
    parameter_overrides: Optional[Dict[str, float]] = None,
    ablation: Optional[Dict[str, bool]] = None,
    realtime: bool = True,
    return_summary: bool = False,
    max_iterations: int = 1000,
    max_runtime_seconds: Optional[float] = None,
):
    try:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        from app.services.evacuation_parameters import parameter_database
        param_snapshot = None
        if parameter_overrides:
            param_snapshot = parameter_database.snapshot()
            parameter_database.apply_overrides(parameter_overrides)

        sim = MockSimulation(num_agents, emergency_type, seed=seed)
        sim.replay_id = f"replay-{simulation_id}"
        sim.floor_number = floor_number
        sim.apply_ablation(ablation)

        if floor_plan_data:
            from app.services.floor_plan_document_service import normalize_detected_obstacles

            sim.floor_plan_data = floor_plan_data
            raw_walls = floor_plan_data.get("detected_walls", []) or []
            raw_boundaries = floor_plan_data.get("boundaries", []) or []
            if not raw_walls and raw_boundaries:
                raw_walls = raw_boundaries
            sim.raw_wall_count = len(raw_walls)
            sim.obstacles = normalize_detected_obstacles(floor_plan_data.get("detected_obstacles", []))
            sim.rooms = floor_plan_data.get("rooms", [])
            sim.corridors = floor_plan_data.get("corridors", [])
            sim.boundaries = raw_boundaries
            sim.building_bounds = floor_plan_data.get("building_bounds")
            sim.walls = sim._sanitize_runtime_walls(raw_walls)
            sim._update_boundary_polygon()

            if sim.building_bounds and (sim.walls or sim.obstacles or sim.boundaries):
                try:
                    from app.services.floorplan_pathfinding import floorplan_pathfinder
                    width = sim.building_bounds.get("max_x", 100) - sim.building_bounds.get("min_x", 0)
                    height = sim.building_bounds.get("max_y", 100) - sim.building_bounds.get("min_y", 0)
                    max_dim = max(width, height)
                    grid_resolution = max(1.0, min(5.0, max_dim / 200.0)) if max_dim > 0 else 2.0
                    wall_inflation_cells = 2 if sim.runtime_wall_count > 120 else 1
                    if sim.runtime_wall_orthogonal_ratio < 0.55 and sim.runtime_wall_count > 180:
                        wall_inflation_cells = max(2, wall_inflation_cells)
                    floorplan_pathfinder.initialize_from_floor_plan(
                        sim.walls,
                        sim.obstacles,
                        sim.rooms,
                        sim.corridors,
                        sim.building_bounds,
                        grid_resolution=grid_resolution,
                        boundaries=sim.boundaries,
                        wall_inflation_cells=wall_inflation_cells,
                        obstacle_inflation_cells=2,
                    )
                    sim.pathfinder = floorplan_pathfinder
                except Exception as e:
                    logger.debug("Pathfinding init skipped: %s", e)

        sim.exits = exits or []
        if not sim.exits:
            raise ValueError("Simulation requires at least one usable exit")
        if not sim.walls and not sim.boundaries:
            raise ValueError("Simulation requires detected walls or boundaries")

        sim.configure_agent_profiles(agent_profiles)
        sim.configure_hazards(hazards, blocked_exits)

        sim.initialize_agents()

        from app.services.simulation_state import simulation_state_manager
        simulation_state_manager.register_simulation(simulation_id, "running")

        iteration = 0
        stop_requested = False
        time_limit_hit = False

        while not sim.is_complete() and iteration < max_iterations:
            if max_runtime_seconds is not None and sim.time >= max_runtime_seconds:
                time_limit_hit = True
                break
            if simulation_state_manager.is_stop_requested(simulation_id):
                stop_requested = True
                break
            if simulation_state_manager.is_paused(simulation_id):
                if realtime:
                    await asyncio.sleep(0.1)
                else:
                    await asyncio.sleep(0)
                continue

            bottlenecks = sim.update_agents(0.1)
            frame_data = sim.get_frame_data()
            frame_data["simulation_id"] = simulation_id
            frame_data["floor_number"] = floor_number
            frame_data["bottlenecks"] = bottlenecks

            if callback:
                await callback(frame_data)

            if realtime:
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(0)
            iteration += 1

        final_status = (
            "stopped"
            if stop_requested
            else "time_limit"
            if time_limit_hit
            else "max_iterations"
            if iteration >= max_iterations
            else "completed"
        )
        simulation_state_manager.mark_completed(simulation_id, final_status=final_status)
        try:
            from app.core.metrics import simulations_completed_total, simulation_duration_seconds
            simulations_completed_total.labels(emergency_type=emergency_type, status=final_status).inc()
            simulation_duration_seconds.observe(sim.time)
        except Exception:
            pass

        def _percentile(values: List[float], pct: float) -> Optional[float]:
            if not values:
                return None
            return float(np.percentile(values, pct))

        evac_mean = float(np.mean(sim.evacuation_times)) if sim.evacuation_times else None
        evac_p50 = _percentile(sim.evacuation_times, 50)
        evac_p90 = _percentile(sim.evacuation_times, 90)
        evac_p99 = _percentile(sim.evacuation_times, 99)

        recommendations = []
        total_exits_used = sum(sim.exit_usage.values()) if sim.exit_usage else 0
        if total_exits_used > 0:
            max_share = max(sim.exit_usage.values()) / total_exits_used
            if max_share > 0.7:
                recommendations.append("Redistribute traffic with signage or additional exits to balance exit usage.")
        if evac_p90 and evac_p90 > 60:
            recommendations.append("Reduce long-tail evacuation time by widening corridors or adding nearer exits.")
        if sim.evacuated_count < max(1, int(num_agents * 0.9)):
            recommendations.append("Increase exit capacity or add emergency exits to improve clearance rate.")

        summary = {
            "simulation_id": simulation_id,
            "floor_number": floor_number,
            "timestamp": sim.time,
            "status": final_status,
            "config": {
                "num_agents": num_agents,
                "emergency_type": emergency_type,
                "seed": seed,
                "ablation": ablation,
                "parameter_overrides": parameter_overrides,
                "max_runtime_seconds": max_runtime_seconds,
            },
            "final_stats": {
                "total_agents": num_agents,
                "evacuated": sim.evacuated_count,
                "total_time": sim.time,
                "completion_percentage": (sim.evacuated_count / max(1, num_agents)) * 100,
                "exit_usage": sim.exit_usage,
                "profile_counts": sim.profile_counts,
                "evacuation_time_mean": evac_mean,
                "evacuation_time_p50": evac_p50,
                "evacuation_time_p90": evac_p90,
                "evacuation_time_p99": evac_p99,
            },
            "recommendations": recommendations,
        }
        try:
            from app.services.simulation_store import save_summary
            save_summary(simulation_id, summary)
        except Exception:
            pass
        if callback:
            await callback({
                "type": "simulation_complete",
                **summary,
            })
        if return_summary:
            return summary
    except Exception as e:
        logger.error("Error in mock simulation: %s", e, exc_info=True)
        try:
            from app.services.simulation_state import simulation_state_manager
            simulation_state_manager.mark_completed(simulation_id, final_status="error")
        except Exception:
            pass
        if return_summary:
            return {
                "simulation_id": simulation_id,
                "status": "error",
                "error": str(e),
            }
    finally:
        if "param_snapshot" in locals() and param_snapshot is not None:
            try:
                from app.services.evacuation_parameters import parameter_database
                parameter_database.restore(param_snapshot)
            except Exception:
                pass
