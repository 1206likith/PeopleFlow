"""
Dijkstra's Algorithm Implementation
Alternative pathfinding algorithm for evacuation scenarios
"""

import heapq
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import math

@dataclass
class DijkstraNode:
    """Represents a node in Dijkstra's algorithm"""
    x: int
    y: int
    distance: float = float('inf')
    parent: Optional['DijkstraNode'] = None
    visited: bool = False
    
    def __lt__(self, other):
        return self.distance < other.distance
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))

class Dijkstra:
    """Dijkstra's shortest path algorithm implementation"""
    
    def __init__(self, grid: List[List[int]], allow_diagonal: bool = True):
        """
        Initialize Dijkstra pathfinder
        
        Args:
            grid: 2D grid where 0 = walkable, 1 = obstacle
            allow_diagonal: Whether to allow diagonal movement
        """
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if self.height > 0 else 0
        self.allow_diagonal = allow_diagonal
    
    def get_neighbors(self, node: DijkstraNode) -> List[Tuple[int, int, float]]:
        """
        Get valid neighboring nodes with their movement costs
        
        Returns:
            List of (x, y, cost) tuples
        """
        neighbors = []
        
        # 8-directional movement if diagonal allowed, else 4-directional
        directions = [
            (0, 1, 1.0), (1, 0, 1.0), (0, -1, 1.0), (-1, 0, 1.0)  # Cardinal
        ]
        
        if self.allow_diagonal:
            directions.extend([
                (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), 
                (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))  # Diagonal
            ])
        
        for dx, dy, cost in directions:
            x, y = node.x + dx, node.y + dy
            
            # Check bounds
            if 0 <= x < self.width and 0 <= y < self.height:
                # Check if walkable
                if self.grid[y][x] == 0:
                    neighbors.append((x, y, cost))
        
        return neighbors
    
    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """
        Find shortest path from start to goal using Dijkstra's algorithm
        
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
        start_node = DijkstraNode(start[0], start[1], distance=0)
        
        # Priority queue for unvisited nodes
        unvisited = [start_node]
        heapq.heapify(unvisited)
        
        # Track all nodes
        all_nodes: Dict[Tuple[int, int], DijkstraNode] = {(start[0], start[1]): start_node}
        
        while unvisited:
            # Get node with smallest distance
            current = heapq.heappop(unvisited)
            
            # Skip if already visited
            if current.visited:
                continue
            
            # Mark as visited
            current.visited = True
            
            # Check if we reached the goal
            if current.x == goal[0] and current.y == goal[1]:
                # Reconstruct path
                path = []
                node = current
                while node:
                    path.append((node.x, node.y))
                    node = node.parent
                return path[::-1]  # Reverse to get path from start to goal
            
            # Check neighbors
            for x, y, move_cost in self.get_neighbors(current):
                neighbor_key = (x, y)
                
                # Get or create neighbor node
                if neighbor_key in all_nodes:
                    neighbor = all_nodes[neighbor_key]
                else:
                    neighbor = DijkstraNode(x, y)
                    all_nodes[neighbor_key] = neighbor
                
                # Skip if already visited
                if neighbor.visited:
                    continue
                
                # Calculate new distance
                new_distance = current.distance + move_cost
                
                # Update if we found a shorter path
                if new_distance < neighbor.distance:
                    neighbor.distance = new_distance
                    neighbor.parent = current
                    heapq.heappush(unvisited, neighbor)
        
        # No path found
        return None
    
    def find_shortest_paths_from_start(
        self, 
        start: Tuple[int, int]
    ) -> Dict[Tuple[int, int], float]:
        """
        Find shortest distances from start to all reachable nodes
        
        Args:
            start: Starting position
            
        Returns:
            Dictionary mapping (x, y) positions to their shortest distance from start
        """
        # Validate start
        if not (0 <= start[0] < self.width and 0 <= start[1] < self.height):
            return {}
        if self.grid[start[1]][start[0]] == 1:
            return {}
        
        # Initialize start node
        start_node = DijkstraNode(start[0], start[1], distance=0)
        
        # Priority queue
        unvisited = [start_node]
        heapq.heapify(unvisited)
        
        # Track all nodes
        all_nodes: Dict[Tuple[int, int], DijkstraNode] = {(start[0], start[1]): start_node}
        distances = {}
        
        while unvisited:
            # Get node with smallest distance
            current = heapq.heappop(unvisited)
            
            # Skip if already visited
            if current.visited:
                continue
            
            # Mark as visited
            current.visited = True
            distances[(current.x, current.y)] = current.distance
            
            # Check neighbors
            for x, y, move_cost in self.get_neighbors(current):
                neighbor_key = (x, y)
                
                # Get or create neighbor node
                if neighbor_key in all_nodes:
                    neighbor = all_nodes[neighbor_key]
                else:
                    neighbor = DijkstraNode(x, y)
                    all_nodes[neighbor_key] = neighbor
                
                # Skip if already visited
                if neighbor.visited:
                    continue
                
                # Calculate new distance
                new_distance = current.distance + move_cost
                
                # Update if we found a shorter path
                if new_distance < neighbor.distance:
                    neighbor.distance = new_distance
                    neighbor.parent = current
                    heapq.heappush(unvisited, neighbor)
        
        return distances
    
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
        # Get distances to all reachable nodes
        distances = self.find_shortest_paths_from_start(start)
        
        best_exit = None
        shortest_distance = float('inf')
        
        for exit_pos in exits:
            if exit_pos in distances:
                distance = distances[exit_pos]
                if distance < shortest_distance:
                    shortest_distance = distance
                    best_exit = exit_pos
        
        return best_exit

