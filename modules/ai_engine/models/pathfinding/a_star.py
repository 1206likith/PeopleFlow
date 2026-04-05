"""
A* Pathfinding Algorithm Implementation
Used for optimal pathfinding in evacuation scenarios
"""

import heapq
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import math

@dataclass
class Node:
    """Represents a node in the pathfinding graph"""
    x: int
    y: int
    g_cost: float = float('inf')  # Cost from start
    h_cost: float = 0  # Heuristic cost to goal
    f_cost: float = float('inf')  # Total cost (g + h)
    parent: Optional['Node'] = None
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))

class AStar:
    """A* pathfinding algorithm implementation"""
    
    def __init__(self, grid: List[List[int]], allow_diagonal: bool = True):
        """
        Initialize A* pathfinder
        
        Args:
            grid: 2D grid where 0 = walkable, 1 = obstacle
            allow_diagonal: Whether to allow diagonal movement
        """
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if self.height > 0 else 0
        self.allow_diagonal = allow_diagonal
    
    def heuristic(self, node: Node, goal: Tuple[int, int]) -> float:
        """Calculate heuristic cost (Euclidean distance)"""
        dx = abs(node.x - goal[0])
        dy = abs(node.y - goal[1])
        
        if self.allow_diagonal:
            # Euclidean distance
            return math.sqrt(dx * dx + dy * dy)
        else:
            # Manhattan distance
            return dx + dy
    
    def get_neighbors(self, node: Node) -> List[Node]:
        """Get valid neighboring nodes"""
        neighbors = []
        
        # 8-directional movement if diagonal allowed, else 4-directional
        directions = [
            (0, 1), (1, 0), (0, -1), (-1, 0)  # Cardinal directions
        ]
        
        if self.allow_diagonal:
            directions.extend([
                (1, 1), (1, -1), (-1, 1), (-1, -1)  # Diagonal directions
            ])
        
        for dx, dy in directions:
            x, y = node.x + dx, node.y + dy
            
            # Check bounds
            if 0 <= x < self.width and 0 <= y < self.height:
                # Check if walkable
                if self.grid[y][x] == 0:
                    neighbors.append(Node(x, y))
        
        return neighbors
    
    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """
        Find path from start to goal using A* algorithm
        
        Args:
            start: (x, y) starting position
            goal: (x, y) goal position
            
        Returns:
            List of (x, y) coordinates representing the path, or None if no path exists
        """
        # Validate start and goal
        if not (0 <= start[0] < self.width and 0 <= start[1] < self.height):
            return None
        if not (0 <= goal[0] < self.width and 0 <= goal[1] < self.height):
            return None
        if self.grid[start[1]][start[0]] == 1 or self.grid[goal[1]][goal[0]] == 1:
            return None
        
        # Initialize start node
        start_node = Node(start[0], start[1], g_cost=0)
        start_node.h_cost = self.heuristic(start_node, goal)
        start_node.f_cost = start_node.g_cost + start_node.h_cost
        
        # Open set (nodes to be evaluated) - priority queue
        open_set = [start_node]
        heapq.heapify(open_set)
        
        # Closed set (nodes already evaluated)
        closed_set = set()
        
        # Track nodes for efficient lookup
        all_nodes: Dict[Tuple[int, int], Node] = {(start[0], start[1]): start_node}
        
        while open_set:
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            
            # Check if we reached the goal
            if current.x == goal[0] and current.y == goal[1]:
                # Reconstruct path
                path = []
                node = current
                while node:
                    path.append((node.x, node.y))
                    node = node.parent
                return path[::-1]  # Reverse to get path from start to goal
            
            # Add to closed set
            closed_set.add((current.x, current.y))
            
            # Check neighbors
            for neighbor_pos in self.get_neighbors(current):
                neighbor_key = (neighbor_pos.x, neighbor_pos.y)
                
                # Skip if already evaluated
                if neighbor_key in closed_set:
                    continue
                
                # Calculate movement cost
                dx = abs(neighbor_pos.x - current.x)
                dy = abs(neighbor_pos.y - current.y)
                move_cost = math.sqrt(dx * dx + dy * dy) if (dx > 0 and dy > 0) else 1.0
                
                tentative_g_cost = current.g_cost + move_cost
                
                # Get or create neighbor node
                if neighbor_key in all_nodes:
                    neighbor = all_nodes[neighbor_key]
                else:
                    neighbor = neighbor_pos
                    neighbor.h_cost = self.heuristic(neighbor, goal)
                    all_nodes[neighbor_key] = neighbor
                
                # Update if we found a better path
                if tentative_g_cost < neighbor.g_cost:
                    neighbor.parent = current
                    neighbor.g_cost = tentative_g_cost
                    neighbor.f_cost = neighbor.g_cost + neighbor.h_cost
                    
                    # Add to open set if not already there
                    if neighbor not in open_set:
                        heapq.heappush(open_set, neighbor)
        
        # No path found
        return None
    
    def find_paths_to_multiple_goals(
        self, 
        start: Tuple[int, int], 
        goals: List[Tuple[int, int]]
    ) -> Dict[Tuple[int, int], Optional[List[Tuple[int, int]]]]:
        """
        Find paths from start to multiple goals, returning the shortest one
        
        Args:
            start: Starting position
            goals: List of goal positions
            
        Returns:
            Dictionary mapping each goal to its path
        """
        results = {}
        for goal in goals:
            results[goal] = self.find_path(start, goal)
        return results
    
    def get_optimal_exit(
        self, 
        start: Tuple[int, int], 
        exits: List[Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        """
        Find the optimal exit (closest reachable exit)
        
        Args:
            start: Starting position
            exits: List of exit positions
            
        Returns:
            Optimal exit position, or None if no exit is reachable
        """
        paths = self.find_paths_to_multiple_goals(start, exits)
        
        best_exit = None
        shortest_path_length = float('inf')
        
        for exit_pos, path in paths.items():
            if path and len(path) < shortest_path_length:
                shortest_path_length = len(path)
                best_exit = exit_pos
        
        return best_exit

