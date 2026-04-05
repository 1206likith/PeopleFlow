"""
Real Bottleneck Formation Model
Bottlenecks are emergent from density, not detected visually
Implements density-based speed collapse, exit saturation, shockwave propagation
"""
import math
import numpy as np
from typing import List, Dict, Tuple
from app.services.evacuation_parameters import parameter_database

class BottleneckFormationModel:
    """
    Emergent bottleneck detection and formation
    Based on density thresholds and flow saturation
    """
    
    def __init__(self):
        self.params = parameter_database.parameters.get("bottleneck_formation", {})
        self.critical_density = self.params.get("critical_density", 4.0)  # persons/m²
        self.shockwave_speed = self.params.get("shockwave_speed", 1.5)  # m/s
    
    def detect_bottlenecks(
        self,
        agents: List[Dict],
        exits: List[Dict],
        grid_resolution: float = 1.0  # meters
    ) -> List[Dict]:
        """
        Detect emergent bottlenecks from agent density
        
        Returns:
            List of bottleneck locations with severity
        """
        if not agents:
            return []
        
        # Create density grid
        density_grid, bounds = self._create_density_grid(agents, grid_resolution)
        
        bottlenecks = []
        
        # Find high-density cells (potential bottlenecks)
        for i in range(density_grid.shape[0]):
            for j in range(density_grid.shape[1]):
                density = density_grid[i, j]
                
                if density >= self.critical_density:
                    # Convert grid coordinates to world coordinates
                    x = bounds["min_x"] + i * grid_resolution
                    z = bounds["min_y"] + j * grid_resolution
                    
                    # Calculate severity (0-1)
                    severity = min(1.0, density / (self.critical_density * 2))
                    
                    bottlenecks.append({
                        "x": x,
                        "y": 0.0,
                        "z": z,
                        "density": density,
                        "severity": severity,
                        "radius": grid_resolution * 2,  # Affected area
                        "type": "congestion"
                    })
        
        # Check exit saturation
        exit_bottlenecks = self._check_exit_saturation(agents, exits)
        bottlenecks.extend(exit_bottlenecks)
        
        # Propagate shockwaves (backward from bottlenecks)
        bottlenecks = self._propagate_shockwaves(bottlenecks, agents)
        
        return bottlenecks
    
    def _create_density_grid(
        self,
        agents: List[Dict],
        resolution: float
    ) -> Tuple[np.ndarray, Dict]:
        """Create 2D density grid from agent positions"""
        if not agents:
            return np.zeros((10, 10)), {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 10}
        
        # Find bounds
        xs = [a.get("x", 0) for a in agents if a.get("status") != "evacuated"]
        zs = [a.get("z", a.get("y", 0)) for a in agents if a.get("status") != "evacuated"]
        
        if not xs or not zs:
            return np.zeros((10, 10)), {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 10}
        
        min_x, max_x = min(xs), max(xs)
        min_z, max_z = min(zs), max(zs)
        
        # Add padding
        padding = 5.0
        min_x -= padding
        max_x += padding
        min_z -= padding
        max_z += padding
        
        # Create grid
        width = max_x - min_x
        height = max_z - min_z
        grid_width = int(width / resolution) + 1
        grid_height = int(height / resolution) + 1
        
        grid = np.zeros((grid_width, grid_height))
        
        # Populate grid
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            x = agent.get("x", 0)
            z = agent.get("z", agent.get("y", 0))
            
            i = int((x - min_x) / resolution)
            j = int((z - min_z) / resolution)
            
            if 0 <= i < grid_width and 0 <= j < grid_height:
                # Add to density (persons per m²)
                grid[i, j] += 1.0 / (resolution ** 2)
        
        bounds = {"min_x": min_x, "max_x": max_x, "min_y": min_z, "max_y": max_z}
        return grid, bounds
    
    def _check_exit_saturation(
        self,
        agents: List[Dict],
        exits: List[Dict]
    ) -> List[Dict]:
        """Check if exits are saturated (bottleneck at exit)"""
        bottlenecks = []
        
        for exit_data in exits:
            exit_x = exit_data.get("x", 0.0)
            exit_z = exit_data.get("z", exit_data.get("y", 0.0))
            exit_width = exit_data.get("width", 2.0)
            
            # Count agents near exit
            agents_at_exit = []
            for agent in agents:
                if agent.get("status") == "evacuated":
                    continue
                
                agent_x = agent.get("x", 0.0)
                agent_z = agent.get("z", agent.get("y", 0.0))
                
                dist = math.sqrt((agent_x - exit_x)**2 + (agent_z - exit_z)**2)
                if dist < exit_width * 2:  # Within 2x exit width
                    agents_at_exit.append(agent)
            
            # Calculate density at exit
            area = math.pi * (exit_width * 2) ** 2
            density = len(agents_at_exit) / area if area > 0 else 0
            
            # Check saturation
            flow_capacity = parameter_database.get_flow_capacity(exit_width)
            agents_per_second = len(agents_at_exit) / 10.0  # Rough estimate
            utilization = agents_per_second / flow_capacity if flow_capacity > 0 else 0
            
            if density >= self.critical_density or utilization > 0.85:
                bottlenecks.append({
                    "x": exit_x,
                    "y": 0.0,
                    "z": exit_z,
                    "density": density,
                    "severity": min(1.0, utilization),
                    "radius": exit_width * 2,
                    "type": "exit_saturation",
                    "exit_id": exit_data.get("id", "unknown")
                })
        
        return bottlenecks
    
    def _propagate_shockwaves(
        self,
        bottlenecks: List[Dict],
        agents: List[Dict]
    ) -> List[Dict]:
        """Propagate shockwaves backward from bottlenecks"""
        # Shockwaves propagate backward as density increases
        # This creates a chain reaction effect
        
        propagated = []
        
        for bottleneck in bottlenecks:
            # Find agents upstream (moving towards bottleneck)
            for agent in agents:
                if agent.get("status") == "evacuated":
                    continue
                
                agent_x = agent.get("x", 0.0)
                agent_z = agent.get("z", agent.get("y", 0.0))
                
                # Distance to bottleneck
                dist = math.sqrt(
                    (agent_x - bottleneck["x"])**2 +
                    (agent_z - bottleneck["z"])**2
                )
                
                # Shockwave affects area up to 10m upstream
                if dist < 10.0 and dist > bottleneck["radius"]:
                    # Create secondary bottleneck
                    propagated.append({
                        "x": agent_x,
                        "y": 0.0,
                        "z": agent_z,
                        "density": bottleneck["density"] * (1 - dist / 10.0),
                        "severity": bottleneck["severity"] * 0.7,
                        "radius": 2.0,
                        "type": "shockwave",
                        "source_bottleneck": bottleneck.get("exit_id", "unknown")
                    })
        
        return bottlenecks + propagated
    
    def calculate_flow_rate(
        self,
        agents: List[Dict],
        exit: Dict,
        time_window: float = 1.0
    ) -> float:
        """Calculate actual flow rate at exit (persons/second)"""
        exit_x = exit.get("x", 0.0)
        exit_z = exit.get("z", exit.get("y", 0.0))
        exit_width = exit.get("width", 2.0)
        
        # Count agents that passed through exit in time window
        agents_passed = sum(
            1 for agent in agents
            if agent.get("status") == "evacuated" and
            math.sqrt(
                (agent.get("x", 0) - exit_x)**2 +
                (agent.get("z", agent.get("y", 0)) - exit_z)**2
            ) < exit_width
        )
        
        return agents_passed / time_window if time_window > 0 else 0

