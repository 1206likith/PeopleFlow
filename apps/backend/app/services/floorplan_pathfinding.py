"""
Floor Plan-Aware Pathfinding
Uses processed floor plan data (walls, obstacles, rooms) for realistic agent navigation.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from ai_engine.models.pathfinding.a_star import AStar

logger = logging.getLogger(__name__)


@dataclass
class NavigationNode:
    """Node in navigation graph."""

    x: float
    z: float
    walkable: bool = True
    room_id: Optional[str] = None
    is_corridor: bool = False


class FloorPlanPathfinder:
    """
    Pathfinding that respects floor plan structure.
    Uses walls, obstacles, and room boundaries.
    """

    def __init__(self):
        self.grid: Optional[List[List[int]]] = None
        self.grid_resolution = 1.0  # world units per grid cell
        self.origin_x = 0.0
        self.origin_z = 0.0
        self.a_star: Optional[AStar] = None
        self.walls: List[Dict] = []
        self.obstacles: List[Dict] = []
        self.rooms: List[Dict] = []
        self.corridors: List[Dict] = []
        self.boundaries: List[Dict] = []
        self.boundary_polygon: List[Tuple[float, float]] = []
        self.wall_inflation_cells = 1
        self.obstacle_inflation_cells = 1

    def initialize_from_floor_plan(
        self,
        walls: List[Dict],
        obstacles: List[Dict],
        rooms: List[Dict],
        corridors: List[Dict],
        building_bounds: Dict,
        grid_resolution: float = 1.0,
        boundaries: Optional[List[Dict]] = None,
        wall_inflation_cells: int = 1,
        obstacle_inflation_cells: int = 1,
    ):
        """
        Initialize pathfinding grid from floor plan data.
        """
        self.walls = self._dedupe_walls(walls or [])
        self.obstacles = obstacles or []
        self.rooms = rooms or []
        self.corridors = corridors or []
        self.boundaries = boundaries or []
        self.boundary_polygon = self._boundary_polygon_from_segments(self.boundaries)
        self.grid_resolution = max(0.25, float(grid_resolution))
        self.wall_inflation_cells = max(1, int(wall_inflation_cells))
        self.obstacle_inflation_cells = max(1, int(obstacle_inflation_cells))

        min_x = float(building_bounds.get("min_x", 0))
        max_x = float(building_bounds.get("max_x", 100))
        min_z = float(building_bounds.get("min_y", 0))
        max_z = float(building_bounds.get("max_y", 100))
        if max_x <= min_x:
            max_x = min_x + 100.0
        if max_z <= min_z:
            max_z = min_z + 100.0

        self.origin_x = min_x
        self.origin_z = min_z

        grid_width = int((max_x - min_x) / self.grid_resolution) + 1
        grid_height = int((max_z - min_z) / self.grid_resolution) + 1
        self.grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]

        if self.boundary_polygon:
            for gz in range(grid_height):
                for gx in range(grid_width):
                    x = min_x + gx * self.grid_resolution
                    z = min_z + gz * self.grid_resolution
                    if not self._point_in_polygon(x, z, self.boundary_polygon):
                        self.grid[gz][gx] = 1

        for wall in self.walls:
            self._mark_wall_in_grid(wall, min_x, min_z)

        for obstacle in self.obstacles:
            self._mark_obstacle_in_grid(obstacle, min_x, min_z)

        self.a_star = AStar(self.grid, allow_diagonal=True)
        logger.info(
            "Initialized pathfinding grid: %sx%s, walls=%s, obstacles=%s",
            grid_width,
            grid_height,
            len(self.walls),
            len(self.obstacles),
        )

    def _dedupe_walls(self, walls: List[Dict], tolerance: float = 0.75) -> List[Dict]:
        deduped: List[Dict] = []
        seen = set()
        for wall in walls:
            try:
                x1 = float(wall.get("x1", 0.0))
                y1 = float(wall.get("y1", 0.0))
                x2 = float(wall.get("x2", 0.0))
                y2 = float(wall.get("y2", 0.0))
            except (TypeError, ValueError):
                continue
            length = math.hypot(x2 - x1, y2 - y1)
            if length < max(0.5, self.grid_resolution * 0.5):
                continue
            key = (
                round(min(x1, x2) / tolerance),
                round(min(y1, y2) / tolerance),
                round(max(x1, x2) / tolerance),
                round(max(y1, y2) / tolerance),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(
                {
                    **wall,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "length": float(wall.get("length", length)),
                }
            )
        return deduped

    def _inflate_cell(self, gx: int, gz: int, radius: int):
        if self.grid is None:
            return
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                if dx * dx + dz * dz > radius * radius:
                    continue
                ix = gx + dx
                iz = gz + dz
                if 0 <= ix < len(self.grid[0]) and 0 <= iz < len(self.grid):
                    self.grid[iz][ix] = 1

    def _mark_wall_in_grid(self, wall: Dict, origin_x: float, origin_z: float):
        if self.grid is None:
            return
        x1 = float(wall.get("x1", 0))
        y1 = float(wall.get("y1", 0))
        x2 = float(wall.get("x2", 0))
        y2 = float(wall.get("y2", 0))

        gx1 = int((x1 - origin_x) / self.grid_resolution)
        gz1 = int((y1 - origin_z) / self.grid_resolution)
        gx2 = int((x2 - origin_x) / self.grid_resolution)
        gz2 = int((y2 - origin_z) / self.grid_resolution)

        steps = max(abs(gx2 - gx1), abs(gz2 - gz1), 1)
        thickness_cells = max(
            self.wall_inflation_cells,
            int(float(wall.get("thickness", self.grid_resolution * 2)) / self.grid_resolution / 2) + 1,
        )
        for i in range(steps + 1):
            t = i / steps
            gx = int(round(gx1 + t * (gx2 - gx1)))
            gz = int(round(gz1 + t * (gz2 - gz1)))
            self._inflate_cell(gx, gz, thickness_cells)

    def _mark_obstacle_in_grid(self, obstacle: Dict, origin_x: float, origin_z: float):
        if self.grid is None:
            return
        obs_x = float(obstacle.get("x", 0))
        obs_z = float(obstacle.get("z", obstacle.get("y", 0)))
        obs_width = float(obstacle.get("width", 1.0)) / 2
        obs_depth = float(obstacle.get("depth", obstacle.get("height", 1.0))) / 2

        gx_center = int((obs_x - origin_x) / self.grid_resolution)
        gz_center = int((obs_z - origin_z) / self.grid_resolution)
        gx_radius = int(obs_width / self.grid_resolution) + self.obstacle_inflation_cells
        gz_radius = int(obs_depth / self.grid_resolution) + self.obstacle_inflation_cells

        for dx in range(-gx_radius, gx_radius + 1):
            for dz in range(-gz_radius, gz_radius + 1):
                gx = gx_center + dx
                gz = gz_center + dz
                if 0 <= gx < len(self.grid[0]) and 0 <= gz < len(self.grid):
                    self.grid[gz][gx] = 1

    def _boundary_polygon_from_segments(self, boundaries: List[Dict]) -> List[Tuple[float, float]]:
        if not boundaries:
            return []
        points = [(float(boundaries[0]["x1"]), float(boundaries[0]["y1"]))]
        for b in boundaries:
            points.append((float(b["x2"]), float(b["y2"])))
        if points[0] != points[-1]:
            points.append(points[0])
        return points

    def _point_in_polygon(self, x: float, z: float, polygon: List[Tuple[float, float]]) -> bool:
        if not polygon:
            return True
        inside = False
        for i in range(len(polygon) - 1):
            x1, y1 = polygon[i]
            x2, y2 = polygon[i + 1]
            if (y1 > z) != (y2 > z):
                xinters = (x2 - x1) * (z - y1) / (y2 - y1 + 1e-9) + x1
                if x < xinters:
                    inside = not inside
        return inside

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Find path from start to goal avoiding walls and obstacles.
        """
        if self.a_star is None or self.grid is None:
            return [start, goal]

        start_grid = self._world_to_grid(start[0], start[1])
        goal_grid = self._world_to_grid(goal[0], goal[1])
        if not self._is_valid_grid_pos(start_grid):
            start_grid = self._world_to_grid(*self.get_nearest_walkable(start[0], start[1], search_radius=6.0))
        if not self._is_valid_grid_pos(goal_grid):
            goal_grid = self._world_to_grid(*self.get_nearest_walkable(goal[0], goal[1], search_radius=6.0))

        if not self._is_valid_grid_pos(start_grid) or not self._is_valid_grid_pos(goal_grid):
            return [start, goal]

        start_node = (start_grid[0], start_grid[1])
        goal_node = (goal_grid[0], goal_grid[1])
        path_grid = self.a_star.find_path(start_node, goal_node)
        if not path_grid:
            return [start, goal]

        path_world = [self._grid_to_world(gx, gz) for gx, gz in path_grid]
        smoothed = self._smooth_path(path_world)
        return smoothed if smoothed else path_world

    def _smooth_path(self, path_world: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(path_world) <= 2:
            return path_world
        smoothed = [path_world[0]]
        anchor_index = 0
        while anchor_index < len(path_world) - 1:
            next_index = len(path_world) - 1
            while next_index > anchor_index + 1:
                if self._has_line_of_sight(path_world[anchor_index], path_world[next_index]):
                    break
                next_index -= 1
            smoothed.append(path_world[next_index])
            anchor_index = next_index
        return smoothed

    def _has_line_of_sight(self, start: Tuple[float, float], goal: Tuple[float, float]) -> bool:
        if self.grid is None:
            return True
        sx, sz = self._world_to_grid(start[0], start[1])
        gx, gz = self._world_to_grid(goal[0], goal[1])
        if not self._is_valid_grid_pos((sx, sz)) or not self._is_valid_grid_pos((gx, gz)):
            return False
        steps = max(abs(gx - sx), abs(gz - sz), 1)
        for i in range(steps + 1):
            t = i / steps
            ix = int(round(sx + (gx - sx) * t))
            iz = int(round(sz + (gz - sz) * t))
            if not self._is_valid_grid_pos((ix, iz)):
                return False
            if self.grid[iz][ix] != 0:
                return False
        return True

    def _world_to_grid(self, x: float, z: float) -> Tuple[int, int]:
        gx = int((x - self.origin_x) / self.grid_resolution)
        gz = int((z - self.origin_z) / self.grid_resolution)
        return gx, gz

    def _grid_to_world(self, gx: int, gz: int) -> Tuple[float, float]:
        x = self.origin_x + gx * self.grid_resolution
        z = self.origin_z + gz * self.grid_resolution
        return x, z

    def _is_valid_grid_pos(self, grid_pos: Tuple[int, int]) -> bool:
        if self.grid is None:
            return False
        gx, gz = grid_pos
        return 0 <= gx < len(self.grid[0]) and 0 <= gz < len(self.grid)

    def is_walkable(self, x: float, z: float) -> bool:
        if self.grid is None:
            return True
        gx, gz = self._world_to_grid(x, z)
        if not self._is_valid_grid_pos((gx, gz)):
            return False
        return self.grid[gz][gx] == 0

    def get_nearest_walkable(self, x: float, z: float, search_radius: float = 5.0) -> Tuple[float, float]:
        if self.is_walkable(x, z):
            return x, z
        if self.grid is None:
            return x, z

        steps = max(1, int(search_radius / self.grid_resolution))
        best_point = (x, z)
        best_score = float("inf")
        for radius in range(1, steps + 1):
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dz) != radius:
                        continue
                    test_x = x + dx * self.grid_resolution
                    test_z = z + dz * self.grid_resolution
                    if not self.is_walkable(test_x, test_z):
                        continue
                    score = math.hypot(test_x - x, test_z - z)
                    if score < best_score:
                        best_score = score
                        best_point = (test_x, test_z)
            if best_score < float("inf"):
                break
        return best_point


# Global pathfinder instance
floorplan_pathfinder = FloorPlanPathfinder()
