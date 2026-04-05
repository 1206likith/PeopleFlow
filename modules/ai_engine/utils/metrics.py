"""
Metrics and Analytics Utilities
For calculating evacuation statistics and performance metrics
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from datetime import datetime

def calculate_evacuation_time(agent_times: List[float]) -> Dict[str, float]:
    """
    Calculate evacuation time statistics
    
    Args:
        agent_times: List of evacuation times for each agent
        
    Returns:
        Dictionary with statistics
    """
    if not agent_times:
        return {
            "min": 0,
            "max": 0,
            "mean": 0,
            "median": 0,
            "std": 0,
        }
    
    times_array = np.array(agent_times)
    
    return {
        "min": float(np.min(times_array)),
        "max": float(np.max(times_array)),
        "mean": float(np.mean(times_array)),
        "median": float(np.median(times_array)),
        "std": float(np.std(times_array)),
    }

def calculate_flow_rate(agent_positions: List[Dict[str, Any]], time_window: float = 1.0) -> float:
    """
    Calculate flow rate (agents per second through exits)
    
    Args:
        agent_positions: List of agent position data
        time_window: Time window in seconds
        
    Returns:
        Flow rate (agents/second)
    """
    if not agent_positions:
        return 0.0
    
    # Count agents that evacuated in the time window
    evacuated = sum(1 for agent in agent_positions if agent.get("status") == "evacuated")
    
    return evacuated / time_window if time_window > 0 else 0.0

def detect_bottlenecks(
    agent_positions: List[Dict[str, Any]], 
    threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Detect bottlenecks based on agent density
    
    Args:
        agent_positions: List of agent position data
        threshold: Density threshold for bottleneck detection
        
    Returns:
        List of bottleneck locations
    """
    if not agent_positions:
        return []
    
    # Group agents by grid cell
    grid_cells: Dict[Tuple[int, int], int] = {}
    cell_size = 2.0  # meters
    
    for agent in agent_positions:
        if agent.get("status") != "evacuated":
            x = agent.get("x", 0)
            y = agent.get("y", 0)
            cell_x = int(x / cell_size)
            cell_y = int(y / cell_size)
            cell_key = (cell_x, cell_y)
            grid_cells[cell_key] = grid_cells.get(cell_key, 0) + 1
    
    # Find cells with high density
    bottlenecks = []
    max_density = max(grid_cells.values()) if grid_cells else 0
    
    for (cell_x, cell_y), count in grid_cells.items():
        density = count / (cell_size * cell_size)  # agents per square meter
        if density > threshold:
            bottlenecks.append({
                "x": cell_x * cell_size + cell_size / 2,
                "y": cell_y * cell_size + cell_size / 2,
                "density": density,
                "agent_count": count,
            })
    
    return bottlenecks

def calculate_survival_rate(evacuated: int, total: int) -> float:
    """Calculate survival/evacuation rate"""
    if total == 0:
        return 0.0
    return evacuated / total

def calculate_path_efficiency(actual_path_length: float, optimal_path_length: float) -> float:
    """
    Calculate path efficiency (how close actual path is to optimal)
    
    Args:
        actual_path_length: Length of actual path taken
        optimal_path_length: Length of optimal path
        
    Returns:
        Efficiency ratio (1.0 = optimal, >1.0 = suboptimal)
    """
    if optimal_path_length == 0:
        return 1.0
    return actual_path_length / optimal_path_length

def aggregate_simulation_metrics(simulation_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate metrics from simulation data
    
    Args:
        simulation_data: List of simulation frame data
        
    Returns:
        Aggregated metrics
    """
    if not simulation_data:
        return {}
    
    all_agent_times = []
    all_bottlenecks = []
    total_agents = 0
    evacuated_agents = 0
    
    for frame in simulation_data:
        agents = frame.get("agents", [])
        total_agents = max(total_agents, len(agents))
        
        for agent in agents:
            if agent.get("status") == "evacuated":
                evacuated_agents += 1
                # Extract evacuation time if available
                if "evacuation_time" in agent:
                    all_agent_times.append(agent["evacuation_time"])
        
        all_bottlenecks.extend(frame.get("bottlenecks", []))
    
    evacuation_stats = calculate_evacuation_time(all_agent_times) if all_agent_times else {}
    
    return {
        "total_agents": total_agents,
        "evacuated_agents": evacuated_agents,
        "survival_rate": calculate_survival_rate(evacuated_agents, total_agents),
        "evacuation_time_stats": evacuation_stats,
        "bottlenecks_detected": len(all_bottlenecks),
        "unique_bottlenecks": len(set((b["x"], b["y"]) for b in all_bottlenecks)),
    }

