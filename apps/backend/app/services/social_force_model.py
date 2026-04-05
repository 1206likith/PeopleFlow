"""
Social Force Model for Realistic Crowd Physics
Implements Helbing & Molnár (1995) social force model with extensions
"""
import math
import numpy as np
from typing import List, Dict, Tuple
from app.services.evacuation_parameters import parameter_database

class SocialForceModel:
    """
    Social Force Model for agent movement
    F_total = F_goal + F_repulsion + F_attraction + F_wall + F_panic
    """
    
    def __init__(self):
        self.params = parameter_database.get_social_force_params()
    
    def calculate_forces(
        self,
        agent: Dict,
        agents: List[Dict],
        walls: List[Dict],
        target_exit: Dict,
        panic_level: float = 0.0
    ) -> Tuple[float, float]:
        """
        Calculate total force vector for an agent
        
        Returns:
            (fx, fz) - Force components in x and z directions
        """
        agent_x = agent.get("x", 0.0)
        agent_z = agent.get("z", agent.get("y", 0.0))
        
        # Goal force (towards exit)
        fx_goal, fz_goal = self._goal_force(agent_x, agent_z, target_exit)
        
        # Repulsion from other agents (body collision)
        fx_repulsion, fz_repulsion = self._agent_repulsion(agent, agents)
        
        # Attraction to group/family
        fx_attraction, fz_attraction = self._group_attraction(agent, agents)
        
        # Wall repulsion
        fx_wall, fz_wall = self._wall_repulsion(agent_x, agent_z, walls)
        
        # Panic pressure (push behavior under stress)
        fx_panic, fz_panic = self._panic_force(agent, agents, panic_level)
        
        # Sum all forces
        fx_total = fx_goal + fx_repulsion + fx_attraction + fx_wall + fx_panic
        fz_total = fz_goal + fz_repulsion + fz_attraction + fz_wall + fz_panic
        
        return fx_total, fz_total
    
    def _goal_force(self, x: float, z: float, target_exit: Dict) -> Tuple[float, float]:
        """Force towards goal (exit)"""
        exit_x = target_exit.get("x", 0.0)
        exit_z = target_exit.get("z", target_exit.get("y", 0.0))
        
        dx = exit_x - x
        dz = exit_z - z
        distance = math.sqrt(dx * dx + dz * dz)
        
        if distance < 0.1:
            return 0.0, 0.0
        
        # Normalize direction
        fx = dx / distance
        fz = dz / distance
        
        # Goal force strength (desired speed)
        desired_speed = 1.35  # m/s (can be parameterized)
        
        return fx * desired_speed, fz * desired_speed
    
    def _agent_repulsion(self, agent: Dict, other_agents: List[Dict]) -> Tuple[float, float]:
        """Repulsion force from nearby agents (body collision prevention)"""
        agent_x = agent.get("x", 0.0)
        agent_z = agent.get("z", agent.get("y", 0.0))
        agent_id = agent.get("agent_id", -1)
        
        fx_total = 0.0
        fz_total = 0.0
        
        repulsion_strength = self.params["repulsion_strength"]
        repulsion_range = self.params["repulsion_range"]
        
        for other in other_agents:
            if other.get("agent_id") == agent_id or other.get("status") == "evacuated":
                continue
            
            other_x = other.get("x", 0.0)
            other_z = other.get("z", other.get("y", 0.0))
            
            dx = agent_x - other_x
            dz = agent_z - other_z
            distance = math.sqrt(dx * dx + dz * dz)
            
            if distance < 0.01:  # Avoid division by zero
                # Random push to separate
                angle = np.random.uniform(0, 2 * math.pi)
                fx_total += math.cos(angle) * repulsion_strength
                fz_total += math.sin(angle) * repulsion_strength
                continue
            
            if distance < repulsion_range:
                # Exponential repulsion (stronger when closer)
                force_magnitude = repulsion_strength * math.exp(-distance / 0.2)
                
                # Normalize direction
                fx_total += (dx / distance) * force_magnitude
                fz_total += (dz / distance) * force_magnitude
        
        return fx_total, fz_total
    
    def _group_attraction(self, agent: Dict, other_agents: List[Dict]) -> Tuple[float, float]:
        """Attraction force to group/family members"""
        agent_x = agent.get("x", 0.0)
        agent_z = agent.get("z", agent.get("y", 0.0))
        family_id = agent.get("family_group_id")
        
        if not family_id:
            return 0.0, 0.0
        
        fx_total = 0.0
        fz_total = 0.0
        
        attraction_strength = self.params["attraction_strength"]
        attraction_range = self.params["attraction_range"]
        
        for other in other_agents:
            if other.get("family_group_id") != family_id:
                continue
            
            other_x = other.get("x", 0.0)
            other_z = other.get("z", other.get("y", 0.0))
            
            dx = other_x - agent_x
            dz = other_z - agent_z
            distance = math.sqrt(dx * dx + dz * dz)
            
            if 0.5 < distance < attraction_range:  # Don't attract if too close
                force_magnitude = attraction_strength / (distance + 0.1)
                
                fx_total += (dx / distance) * force_magnitude
                fz_total += (dz / distance) * force_magnitude
        
        return fx_total, fz_total
    
    def _wall_repulsion(self, x: float, z: float, walls: List[Dict]) -> Tuple[float, float]:
        """Repulsion force from walls"""
        fx_total = 0.0
        fz_total = 0.0
        
        wall_repulsion = self.params["wall_repulsion"]
        wall_range = self.params["wall_range"]
        
        for wall in walls:
            # Calculate distance from point to wall line segment
            x1, y1 = wall.get("x1", 0), wall.get("y1", 0)
            x2, y2 = wall.get("x2", 0), wall.get("y2", 0)
            
            # Point-to-line distance
            A = x - x1
            B = z - y1
            C = x2 - x1
            D = y2 - y1
            
            dot = A * C + B * D
            len_sq = C * C + D * D
            
            if len_sq == 0:
                dist = math.sqrt(A * A + B * B)
                closest_x, closest_z = x1, y1
            else:
                param = dot / len_sq
                if param < 0:
                    closest_x, closest_z = x1, y1
                elif param > 1:
                    closest_x, closest_z = x2, y2
                else:
                    closest_x = x1 + param * C
                    closest_z = y1 + param * D
                
                dx = x - closest_x
                dz = z - closest_z
                dist = math.sqrt(dx * dx + dz * dz)
            
            if dist < wall_range:
                # Exponential repulsion
                force_magnitude = wall_repulsion * math.exp(-dist / 0.1)
                
                if dist > 0.01:
                    fx_total += (dx / dist) * force_magnitude
                    fz_total += (dz / dist) * force_magnitude
        
        return fx_total, fz_total
    
    def _panic_force(self, agent: Dict, other_agents: List[Dict], panic_level: float) -> Tuple[float, float]:
        """Panic-induced pushing force"""
        if panic_level < 0.5:
            return 0.0, 0.0
        
        agent_x = agent.get("x", 0.0)
        agent_z = agent.get("z", agent.get("y", 0.0))
        
        fx_total = 0.0
        fz_total = 0.0
        
        panic_pressure = self.params["panic_pressure"] * panic_level
        
        # Push away from high-density areas
        for other in other_agents:
            if other.get("status") == "evacuated":
                continue
            
            other_x = other.get("x", 0.0)
            other_z = other.get("z", other.get("y", 0.0))
            
            dx = agent_x - other_x
            dz = agent_z - other_z
            distance = math.sqrt(dx * dx + dz * dz)
            
            if distance < 1.0:  # Close proximity
                force_magnitude = panic_pressure / (distance + 0.1)
                
                if distance > 0.01:
                    fx_total += (dx / distance) * force_magnitude
                    fz_total += (dz / distance) * force_magnitude
        
        return fx_total, fz_total

# Global instance
social_force_model = SocialForceModel()

