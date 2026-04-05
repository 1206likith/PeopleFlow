"""
Grid Environment for Pathfinding
Converts floor plans and Unity coordinates to pathfinding grids
"""

import numpy as np
from typing import List, Tuple, Optional
from .a_star import AStar
from .dijkstra import Dijkstra

class GridEnvironment:
    """Manages grid-based environment for pathfinding"""
    
    def __init__(self, width: int, height: int, cell_size: float = 1.0):
        """
        Initialize grid environment
        
        Args:
            width: Grid width in cells
            height: Grid height in cells
            cell_size: Size of each cell in world units
        """
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.grid = np.zeros((height, width), dtype=int)
        self.obstacles: List[Tuple[int, int]] = []
    
    def add_obstacle(self, x: int, y: int):
        """Add obstacle at grid position"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = 1
            self.obstacles.append((x, y))
    
    def add_obstacle_rect(self, x1: int, y1: int, x2: int, y2: int):
        """Add rectangular obstacle"""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                self.add_obstacle(x, y)
    
    def remove_obstacle(self, x: int, y: int):
        """Remove obstacle at grid position"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = 0
            if (x, y) in self.obstacles:
                self.obstacles.remove((x, y))
    
    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates to grid coordinates"""
        grid_x = int(world_x / self.cell_size)
        grid_y = int(world_y / self.cell_size)
        return (grid_x, grid_y)
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convert grid coordinates to world coordinates"""
        world_x = grid_x * self.cell_size + self.cell_size / 2
        world_y = grid_y * self.cell_size + self.cell_size / 2
        return (world_x, world_y)
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is walkable"""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.grid[y][x] == 0
    
    def get_path_astar(
        self, 
        start: Tuple[float, float], 
        goal: Tuple[float, float],
        allow_diagonal: bool = True
    ) -> Optional[List[Tuple[float, float]]]:
        """Get path using A* algorithm"""
        start_grid = self.world_to_grid(start[0], start[1])
        goal_grid = self.world_to_grid(goal[0], goal[1])
        
        astar = AStar(self.grid.tolist(), allow_diagonal=allow_diagonal)
        path_grid = astar.find_path(start_grid, goal_grid)
        
        if path_grid is None:
            return None
        
        # Convert back to world coordinates
        path_world = [self.grid_to_world(x, y) for x, y in path_grid]
        return path_world
    
    def get_path_dijkstra(
        self, 
        start: Tuple[float, float], 
        goal: Tuple[float, float],
        allow_diagonal: bool = True
    ) -> Optional[List[Tuple[float, float]]]:
        """Get path using Dijkstra's algorithm"""
        start_grid = self.world_to_grid(start[0], start[1])
        goal_grid = self.world_to_grid(goal[0], goal[1])
        
        dijkstra = Dijkstra(self.grid.tolist(), allow_diagonal=allow_diagonal)
        path_grid = dijkstra.find_path(start_grid, goal_grid)
        
        if path_grid is None:
            return None
        
        # Convert back to world coordinates
        path_world = [self.grid_to_world(x, y) for x, y in path_grid]
        return path_world
    
    def get_optimal_exit(
        self, 
        start: Tuple[float, float], 
        exits: List[Tuple[float, float]],
        algorithm: str = "astar"
    ) -> Optional[Tuple[float, float]]:
        """
        Find optimal exit from starting position
        
        Args:
            start: Starting world position
            exits: List of exit world positions
            algorithm: "astar" or "dijkstra"
            
        Returns:
            Optimal exit world position, or None if no exit is reachable
        """
        start_grid = self.world_to_grid(start[0], start[1])
        exits_grid = [self.world_to_grid(exit[0], exit[1]) for exit in exits]
        
        if algorithm == "astar":
            astar = AStar(self.grid.tolist())
            optimal_exit_grid = astar.get_optimal_exit(start_grid, exits_grid)
        else:
            dijkstra = Dijkstra(self.grid.tolist())
            optimal_exit_grid = dijkstra.get_optimal_exit(start_grid, exits_grid)
        
        if optimal_exit_grid is None:
            return None
        
        return self.grid_to_world(optimal_exit_grid[0], optimal_exit_grid[1])
    
    def visualize(self) -> np.ndarray:
        """Create visualization of grid (for debugging)"""
        vis = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        vis[self.grid == 1] = [255, 0, 0]  # Red for obstacles
        vis[self.grid == 0] = [255, 255, 255]  # White for walkable
        return vis

