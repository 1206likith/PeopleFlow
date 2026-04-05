"""
Bottleneck & Death-Zone Predictor
Predicts congestion, exit overload, and high-risk areas
"""

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
import math
import logging

logger = logging.getLogger(__name__)

@dataclass
class BottleneckPrediction:
    """Predicted bottleneck location and severity"""
    x: float
    y: float
    z: float
    severity: float  # 0-1, where 1 is critical
    density: float  # Agents per unit area
    predicted_time: float  # When bottleneck will occur
    risk_level: str  # "low", "medium", "high", "critical"

@dataclass
class DeathZone:
    """High-risk area where casualties are likely"""
    x: float
    y: float
    z: float
    radius: float
    risk_score: float  # 0-100
    predicted_casualties: int
    factors: List[str]  # ["congestion", "exit_collapse", "trampling", etc.]

class BottleneckPredictor:
    """Predicts bottlenecks and death zones using flow analysis"""
    
    def __init__(self):
        self.grid_resolution = 5.0  # meters per grid cell
        self.critical_density = 2.0  # agents per square meter
        self.exit_capacity = 2.0  # agents per second per meter of exit width
    
    def predict_bottlenecks(
        self,
        agents: List[Dict],
        exits: List[Dict],
        time_horizon: float = 30.0
    ) -> List[BottleneckPrediction]:
        """
        Predict bottlenecks using agent positions and flow analysis
        
        Args:
            agents: List of agent positions and states
            exits: List of exit locations
            time_horizon: How far ahead to predict (seconds)
        
        Returns:
            List of predicted bottlenecks
        """
        if not agents or not exits:
            return []
        
        # Create occupancy grid
        grid, bounds = self._create_occupancy_grid(agents)
        
        # Find high-density areas
        bottlenecks = []
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                density = grid[i][j]
                if density > self.critical_density * 0.7:  # 70% of critical
                    x, y = self._grid_to_world(i, j, bounds)
                    
                    # Predict when bottleneck will occur
                    predicted_time = self._predict_bottleneck_time(
                        agents, (x, y), time_horizon
                    )
                    
                    severity = min(1.0, density / self.critical_density)
                    risk_level = self._calculate_risk_level(severity, density)
                    
                    bottlenecks.append(BottleneckPrediction(
                        x=x,
                        y=0.0,
                        z=y,
                        severity=severity,
                        density=density,
                        predicted_time=predicted_time,
                        risk_level=risk_level
                    ))
        
        # Sort by severity
        bottlenecks.sort(key=lambda b: b.severity, reverse=True)
        return bottlenecks[:20]  # Return top 20
    
    def predict_death_zones(
        self,
        agents: List[Dict],
        exits: List[Dict],
        bottlenecks: List[Dict],
        disaster_origin: Tuple[float, float, float] = None
    ) -> List[DeathZone]:
        """
        Predict death zones using multiple risk factors
        
        Args:
            agents: List of agent positions
            exits: List of exit locations
            bottlenecks: Current bottlenecks
            disaster_origin: Origin point of disaster
        
        Returns:
            List of predicted death zones
        """
        death_zones = []
        
        # 1. Exit overload zones
        for exit in exits:
            exit_pos = (exit.get("x", 0), exit.get("y", 0), exit.get("z", 0))
            nearby_agents = self._get_nearby_agents(agents, exit_pos, 10.0)
            
            if len(nearby_agents) > exit.get("capacity", 100) * 1.5:
                # Exit is overloaded
                risk_score = min(100, (len(nearby_agents) / exit.get("capacity", 100)) * 50)
                predicted_casualties = max(0, len(nearby_agents) - exit.get("capacity", 100))
                
                death_zones.append(DeathZone(
                    x=exit_pos[0],
                    y=exit_pos[1],
                    z=exit_pos[2],
                    radius=15.0,
                    risk_score=risk_score,
                    predicted_casualties=predicted_casualties,
                    factors=["exit_overload", "trampling_risk"]
                ))
        
        # 2. High-density bottleneck zones
        for bottleneck in bottlenecks:
            if bottleneck.get("density", 0) > self.critical_density * 1.5:
                risk_score = min(100, (bottleneck.get("density", 0) / self.critical_density) * 40)
                nearby_count = self._count_agents_in_radius(
                    agents, (bottleneck.get("x", 0), bottleneck.get("y", 0), bottleneck.get("z", 0)), 5.0
                )
                predicted_casualties = max(0, int(nearby_count * 0.1))  # 10% casualty rate
                
                death_zones.append(DeathZone(
                    x=bottleneck.get("x", 0),
                    y=bottleneck.get("y", 0),
                    z=bottleneck.get("z", 0),
                    radius=5.0,
                    risk_score=risk_score,
                    predicted_casualties=predicted_casualties,
                    factors=["congestion", "trampling_risk"]
                ))
        
        # 3. Disaster proximity zones
        if disaster_origin:
            nearby_agents = self._get_nearby_agents(agents, disaster_origin, 20.0)
            if nearby_agents:
                risk_score = min(100, len(nearby_agents) * 5)
                predicted_casualties = max(0, int(len(nearby_agents) * 0.3))  # 30% casualty rate near disaster
                
                death_zones.append(DeathZone(
                    x=disaster_origin[0],
                    y=disaster_origin[1],
                    z=disaster_origin[2],
                    radius=20.0,
                    risk_score=risk_score,
                    predicted_casualties=predicted_casualties,
                    factors=["disaster_proximity", "smoke_inhalation", "heat_exposure"]
                ))
        
        # Sort by risk score
        death_zones.sort(key=lambda z: z.risk_score, reverse=True)
        return death_zones[:10]  # Return top 10
    
    def predict_exit_collapse_chain(
        self,
        exits: List[Dict],
        agents: List[Dict],
        current_time: float
    ) -> List[Dict]:
        """
        Predict which exits might collapse due to overload
        
        Returns:
            List of exits at risk with collapse probability
        """
        at_risk_exits = []
        
        for exit in exits:
            exit_pos = (exit.get("x", 0), exit.get("y", 0), exit.get("z", 0))
            nearby_agents = self._get_nearby_agents(agents, exit_pos, 5.0)
            
            capacity = exit.get("capacity", 100)
            current_load = len(nearby_agents)
            load_ratio = current_load / capacity if capacity > 0 else 0
            
            # Calculate collapse probability
            if load_ratio > 1.5:
                collapse_probability = min(1.0, (load_ratio - 1.5) * 0.5)
                at_risk_exits.append({
                    "exit_id": exit.get("id", "unknown"),
                    "position": exit_pos,
                    "current_load": current_load,
                    "capacity": capacity,
                    "load_ratio": load_ratio,
                    "collapse_probability": collapse_probability,
                    "estimated_collapse_time": current_time + (30.0 / collapse_probability) if collapse_probability > 0 else None,
                    "risk_factors": ["overload", "structural_stress"]
                })
        
        return sorted(at_risk_exits, key=lambda e: e["collapse_probability"], reverse=True)
    
    def _create_occupancy_grid(self, agents: List[Dict]) -> Tuple[np.ndarray, Dict]:
        """Create 2D occupancy grid from agent positions"""
        if not agents:
            return np.zeros((10, 10)), {"min_x": -50, "max_x": 50, "min_y": -50, "max_y": 50}
        
        # Find bounds
        xs = [a.get("x", 0) for a in agents if a.get("status") != "evacuated"]
        zs = [a.get("z", a.get("y", 0)) for a in agents if a.get("status") != "evacuated"]
        
        if not xs or not zs:
            return np.zeros((10, 10)), {"min_x": -50, "max_x": 50, "min_y": -50, "max_y": 50}
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(zs), max(zs)
        
        # Add padding
        padding = 10.0
        min_x -= padding
        max_x += padding
        min_y -= padding
        max_y += padding
        
        # Create grid
        width = max_x - min_x
        height = max_y - min_y
        grid_width = int(width / self.grid_resolution) + 1
        grid_height = int(height / self.grid_resolution) + 1
        
        grid = np.zeros((grid_width, grid_height))
        
        # Populate grid
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            x = agent.get("x", 0)
            z = agent.get("z", agent.get("y", 0))
            
            i = int((x - min_x) / self.grid_resolution)
            j = int((z - min_y) / self.grid_resolution)
            
            if 0 <= i < grid_width and 0 <= j < grid_height:
                grid[i][j] += 1.0 / (self.grid_resolution ** 2)  # Density per square meter
        
        bounds = {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y}
        return grid, bounds
    
    def _grid_to_world(self, i: int, j: int, bounds: Dict) -> Tuple[float, float]:
        """Convert grid coordinates to world coordinates"""
        x = bounds["min_x"] + i * self.grid_resolution
        y = bounds["min_y"] + j * self.grid_resolution
        return x, y
    
    def _predict_bottleneck_time(
        self,
        agents: List[Dict],
        position: Tuple[float, float],
        time_horizon: float
    ) -> float:
        """Predict when bottleneck will occur at given position"""
        # Simple prediction: estimate based on agent velocities
        nearby_agents = self._get_nearby_agents(agents, (position[0], 0, position[1]), 20.0)
        
        if not nearby_agents:
            return time_horizon
        
        # Average time for agents to reach position
        times = []
        for agent in nearby_agents:
            agent_pos = (agent.get("x", 0), agent.get("z", agent.get("y", 0)))
            distance = math.sqrt(
                (agent_pos[0] - position[0])**2 + (agent_pos[1] - position[1])**2
            )
            speed = agent.get("speed", 2.0)
            if speed > 0:
                times.append(distance / speed)
        
        return min(time_horizon, np.mean(times) if times else time_horizon)
    
    def _calculate_risk_level(self, severity: float, density: float) -> str:
        """Calculate risk level from severity and density"""
        if severity > 0.9 or density > self.critical_density * 1.5:
            return "critical"
        elif severity > 0.7 or density > self.critical_density * 1.2:
            return "high"
        elif severity > 0.5 or density > self.critical_density:
            return "medium"
        else:
            return "low"
    
    def _get_nearby_agents(
        self,
        agents: List[Dict],
        position: Tuple[float, float, float],
        radius: float
    ) -> List[Dict]:
        """Get agents within radius of position"""
        nearby = []
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            agent_pos = (agent.get("x", 0), agent.get("y", 0), agent.get("z", agent.get("y", 0)))
            distance = math.sqrt(
                (agent_pos[0] - position[0])**2 +
                (agent_pos[2] - position[2])**2
            )
            if distance <= radius:
                nearby.append(agent)
        return nearby
    
    def _count_agents_in_radius(
        self,
        agents: List[Dict],
        position: Tuple[float, float, float],
        radius: float
    ) -> int:
        """Count agents within radius"""
        return len(self._get_nearby_agents(agents, position, radius))

# Global instance
bottleneck_predictor = BottleneckPredictor()

