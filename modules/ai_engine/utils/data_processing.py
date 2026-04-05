"""
Data Processing Utilities
For processing simulation data and preparing it for visualization
"""

import numpy as np
from typing import List, Dict, Any, Tuple
import cv2

def create_heatmap(
    agent_positions: List[Dict[str, Any]], 
    width: int = 100, 
    height: int = 100,
    world_bounds: Tuple[float, float, float, float] = None
) -> np.ndarray:
    """
    Create heatmap from agent positions
    
    Args:
        agent_positions: List of agent position data
        width: Heatmap width in pixels
        height: Heatmap height in pixels
        world_bounds: (min_x, min_y, max_x, max_y) world coordinates
        
    Returns:
        2D numpy array representing heatmap
    """
    heatmap = np.zeros((height, width), dtype=np.float32)
    
    if not agent_positions:
        return heatmap
    
    # Determine world bounds if not provided
    if world_bounds is None:
        xs = [agent.get("x", 0) for agent in agent_positions]
        ys = [agent.get("y", 0) for agent in agent_positions]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        # Add padding
        padding = 5.0
        world_bounds = (min_x - padding, min_y - padding, max_x + padding, max_y + padding)
    
    min_x, min_y, max_x, max_y = world_bounds
    
    # Map world coordinates to pixel coordinates
    for agent in agent_positions:
        x = agent.get("x", 0)
        y = agent.get("y", 0)
        
        # Convert to pixel coordinates
        pixel_x = int((x - min_x) / (max_x - min_x) * width)
        pixel_y = int((y - min_y) / (max_y - min_y) * height)
        
        # Clamp to bounds
        pixel_x = max(0, min(width - 1, pixel_x))
        pixel_y = max(0, min(height - 1, pixel_y))
        
        # Add to heatmap
        heatmap[pixel_y, pixel_x] += 1.0
    
    # Apply Gaussian blur for smoother heatmap
    heatmap = cv2.GaussianBlur(heatmap, (15, 15), 0)
    
    # Normalize
    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
    
    return heatmap

def create_density_map(
    agent_positions: List[Dict[str, Any]],
    grid_size: float = 2.0,
    world_bounds: Tuple[float, float, float, float] = None
) -> Dict[str, Any]:
    """
    Create density map from agent positions
    
    Args:
        agent_positions: List of agent position data
        grid_size: Size of each grid cell in world units
        world_bounds: World coordinate bounds
        
    Returns:
        Dictionary with density map data
    """
    if not agent_positions:
        return {"grid": {}, "max_density": 0, "grid_size": grid_size}
    
    # Determine world bounds
    if world_bounds is None:
        xs = [agent.get("x", 0) for agent in agent_positions]
        ys = [agent.get("y", 0) for agent in agent_positions]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        padding = 5.0
        world_bounds = (min_x - padding, min_y - padding, max_x + padding, max_y + padding)
    
    min_x, min_y, max_x, max_y = world_bounds
    
    # Create grid
    grid: Dict[Tuple[int, int], int] = {}
    
    for agent in agent_positions:
        x = agent.get("x", 0)
        y = agent.get("y", 0)
        
        # Convert to grid coordinates
        grid_x = int((x - min_x) / grid_size)
        grid_y = int((y - min_y) / grid_size)
        grid_key = (grid_x, grid_y)
        
        grid[grid_key] = grid.get(grid_key, 0) + 1
    
    max_density = max(grid.values()) if grid else 0
    
    # Convert to list format for client tools
    grid_list = [
        {
            "x": grid_x * grid_size + min_x + grid_size / 2,
            "y": grid_y * grid_size + min_y + grid_size / 2,
            "density": count,
        }
        for (grid_x, grid_y), count in grid.items()
    ]
    
    return {
        "grid": grid_list,
        "max_density": max_density,
        "grid_size": grid_size,
        "bounds": world_bounds,
    }

def process_simulation_frames(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process simulation frames to extract key metrics
    
    Args:
        frames: List of simulation frame data
        
    Returns:
        Processed data with metrics
    """
    if not frames:
        return {}
    
    # Extract agent positions over time
    agent_trajectories: Dict[int, List[Dict[str, Any]]] = {}
    
    for frame in frames:
        timestamp = frame.get("timestamp", 0)
        agents = frame.get("agents", [])
        
        for agent in agents:
            agent_id = agent.get("agent_id", 0)
            if agent_id not in agent_trajectories:
                agent_trajectories[agent_id] = []
            
            agent_trajectories[agent_id].append({
                "timestamp": timestamp,
                "x": agent.get("x", 0),
                "y": agent.get("y", 0),
                "z": agent.get("z", 0),
                "speed": agent.get("speed", 0),
                "status": agent.get("status", "moving"),
            })
    
    # Calculate statistics
    total_agents = len(agent_trajectories)
    evacuated = sum(
        1 for traj in agent_trajectories.values()
        if traj and traj[-1].get("status") == "evacuated"
    )
    
    return {
        "total_agents": total_agents,
        "evacuated": evacuated,
        "trajectories": agent_trajectories,
        "frames_count": len(frames),
    }

