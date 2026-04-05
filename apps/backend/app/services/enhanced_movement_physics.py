"""
Enhanced Multi-Modal Physical Movement Models
Implements body shapes, collision avoidance, turning behavior, density-dependent velocity
Research: Social Force Model, body-based collision, fundamental diagrams
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

from app.services.heterogeneous_agents import AgentAttributes
from app.services.evacuation_parameters import parameter_database

logger = logging.getLogger(__name__)

@dataclass
class BodyShape:
    """Agent body shape for collision detection"""
    shape_type: str  # "rectangular" or "elliptical"
    width: float  # meters (shoulder width)
    depth: float  # meters (body depth)
    height: float = 1.7  # meters (average height)
    
    def get_collision_radius(self) -> float:
        """Get effective collision radius"""
        if self.shape_type == "elliptical":
            return max(self.width, self.depth) / 2.0
        else:  # rectangular
            return math.sqrt(self.width**2 + self.depth**2) / 2.0

class BodyCollisionModel:
    """
    Collision avoidance with body shapes
    Rectangular or elliptical body representation for realistic shoulder interactions
    Research: Body-based collision models (arXiv)
    """
    
    @staticmethod
    def check_collision(
        agent1_pos: Tuple[float, float, float],
        agent1_body: BodyShape,
        agent2_pos: Tuple[float, float, float],
        agent2_body: BodyShape
    ) -> Tuple[bool, float]:
        """
        Check if two agents are colliding
        
        Returns:
            (is_colliding, overlap_distance)
        """
        dx = agent1_pos[0] - agent2_pos[0]
        dz = agent1_pos[2] - agent2_pos[2]
        distance = math.sqrt(dx * dx + dz * dz)
        
        # Effective collision radius
        radius1 = agent1_body.get_collision_radius()
        radius2 = agent2_body.get_collision_radius()
        collision_distance = radius1 + radius2
        
        is_colliding = distance < collision_distance
        overlap = max(0.0, collision_distance - distance)
        
        return is_colliding, overlap
    
    @staticmethod
    def calculate_repulsion_force(
        agent_pos: Tuple[float, float, float],
        agent_body: BodyShape,
        other_pos: Tuple[float, float, float],
        other_body: BodyShape,
        repulsion_strength: float = 2000.0
    ) -> Tuple[float, float]:
        """
        Calculate repulsion force from body collision
        
        Returns:
            (fx, fz) force components
        """
        dx = agent_pos[0] - other_pos[0]
        dz = agent_pos[2] - other_pos[2]
        distance = math.sqrt(dx * dx + dz * dz)
        
        if distance < 0.01:
            # Overlapping, push in random direction
            angle = np.random.uniform(0, 2 * math.pi)
            force_magnitude = repulsion_strength * 2.0
            return math.cos(angle) * force_magnitude, math.sin(angle) * force_magnitude
        
        # Effective collision radius
        radius1 = agent_body.get_collision_radius()
        radius2 = other_body.get_collision_radius()
        collision_distance = radius1 + radius2
        
        if distance < collision_distance:
            # Exponential repulsion (stronger when closer)
            overlap = collision_distance - distance
            force_magnitude = repulsion_strength * math.exp(overlap / 0.1)
            
            # Normalize direction
            fx = (dx / distance) * force_magnitude
            fz = (dz / distance) * force_magnitude
            
            return fx, fz
        
        return 0.0, 0.0

class TurningBehaviorModel:
    """
    Turning behavior & dynamic gait adaptation
    Agents adapt step & turn rate based on density and panic
    Research: Turning behavior in crowds (arXiv)
    """
    
    @staticmethod
    def calculate_turning_rate(
        agent_attrs: AgentAttributes,
        current_velocity: Tuple[float, float],
        target_direction: Tuple[float, float],
        local_density: float,
        panic_level: float
    ) -> float:
        """
        Calculate turning rate (angular velocity) in rad/s
        
        Args:
            agent_attrs: Agent attributes
            current_velocity: Current velocity vector (vx, vz)
            target_direction: Desired direction vector (dx, dz)
            local_density: Local crowd density (persons/m²)
            panic_level: Current panic level (0-1)
        
        Returns:
            Angular velocity in rad/s
        """
        # Base turning rate (research: ~120 deg/s = 2.09 rad/s)
        base_turning_rate = 2.09  # rad/s
        
        # Density effect (higher density = slower turning)
        density_factor = max(0.3, 1.0 - (local_density / 6.0) * 0.7)
        
        # Panic effect (panic can cause erratic turning or freezing)
        if panic_level > 0.7:
            # Very high panic: erratic turning
            panic_factor = 1.5 + panic_level * 0.5
        elif panic_level > 0.4:
            # Moderate panic: faster turning
            panic_factor = 1.2
        else:
            panic_factor = 1.0
        
        # Age effect (elderly turn slower)
        age_factor = 1.0
        if agent_attrs.age_group.value in ["elderly", "middle_aged"]:
            age_factor = 0.7
        
        # Disability effect
        disability_factor = 1.0
        if agent_attrs.disability_type.value == "mobility_impaired":
            disability_factor = 0.6
        elif agent_attrs.disability_type.value == "wheelchair":
            disability_factor = 0.8
        
        turning_rate = base_turning_rate * density_factor * panic_factor * age_factor * disability_factor
        
        return turning_rate
    
    @staticmethod
    def calculate_step_length(
        agent_attrs: AgentAttributes,
        current_speed: float,
        local_density: float
    ) -> float:
        """
        Calculate step length (stride length) based on conditions
        
        Returns:
            Step length in meters
        """
        # Base step length (research: ~0.6-0.8m for normal walking)
        base_step_length = 0.7  # meters
        
        # Speed effect (faster = longer steps)
        speed_factor = current_speed / agent_attrs.base_walking_speed
        
        # Density effect (higher density = shorter steps)
        density_factor = max(0.4, 1.0 - (local_density / 5.0) * 0.6)
        
        # Age effect
        age_factor = 1.0
        if agent_attrs.age_group.value == "elderly":
            age_factor = 0.8
        elif agent_attrs.age_group.value == "child":
            age_factor = 0.7
        
        step_length = base_step_length * speed_factor * density_factor * age_factor
        
        return max(0.3, min(1.2, step_length))

class DensityDependentVelocityModel:
    """
    Density-dependent velocity decay
    Speed reduces with crowd pressure (fundamental diagram)
    Research: Fundamental diagrams in pedestrian dynamics (ScienceDirect)
    """
    
    @staticmethod
    def calculate_velocity(
        agent_attrs: AgentAttributes,
        local_density: float,
        desired_speed: Optional[float] = None
    ) -> float:
        """
        Calculate actual velocity based on density
        
        Implements fundamental diagram: v = f(ρ)
        where v is velocity and ρ is density
        
        Returns:
            Actual velocity in m/s
        """
        if desired_speed is None:
            desired_speed = agent_attrs.base_walking_speed
        
        # Get speed reduction from parameter database (fundamental diagram)
        speed_reduction = parameter_database.get_speed_reduction(local_density)
        
        # Apply reduction
        actual_velocity = desired_speed * speed_reduction
        
        # Ensure minimum velocity (agents don't completely stop)
        min_velocity = 0.1  # m/s
        actual_velocity = max(min_velocity, actual_velocity)
        
        # Panic can override density effects (at cost of collisions)
        if agent_attrs.current_panic_level > 0.7:
            panic_boost = 1.0 + (agent_attrs.current_panic_level - 0.7) * 0.3
            actual_velocity = min(agent_attrs.max_walking_speed, actual_velocity * panic_boost)
        
        return actual_velocity
    
    @staticmethod
    def calculate_density(
        agent_position: Tuple[float, float, float],
        all_agents: List[Dict],
        measurement_radius: float = 2.0
    ) -> float:
        """
        Calculate local density around agent
        
        Returns:
            Density in persons/m²
        """
        agent_x, agent_y, agent_z = agent_position
        
        nearby_count = 0
        for other_agent in all_agents:
            if other_agent.get("status") == "evacuated":
                continue
            
            other_x = other_agent.get("x", 0)
            other_z = other_agent.get("z", other_agent.get("y", 0))
            
            distance = math.sqrt(
                (agent_x - other_x)**2 +
                (agent_z - other_z)**2
            )
            
            if distance < measurement_radius:
                nearby_count += 1
        
        # Calculate density (persons per square meter)
        area = math.pi * measurement_radius**2
        density = nearby_count / area if area > 0 else 0.0
        
        return density

class EnhancedMovementPhysics:
    """
    Enhanced movement physics combining all models
    Integrates body collision, turning, density effects
    """
    
    def __init__(self):
        self.body_collision = BodyCollisionModel()
        self.turning_model = TurningBehaviorModel()
        self.density_model = DensityDependentVelocityModel()
    
    def calculate_movement(
        self,
        agent: Dict,
        agent_attrs: AgentAttributes,
        all_agents: List[Dict],
        target_position: Tuple[float, float, float],
        dt: float
    ) -> Tuple[float, float, float]:
        """
        Calculate agent movement for one time step
        
        Returns:
            (new_x, new_y, new_z) position
        """
        current_pos = (agent.get("x", 0), agent.get("y", 0), agent.get("z", agent.get("y", 0)))
        
        # Calculate local density
        local_density = self.density_model.calculate_density(current_pos, all_agents)
        
        # Calculate desired velocity (considering density)
        desired_velocity = self.density_model.calculate_velocity(
            agent_attrs,
            local_density,
            agent_attrs.base_walking_speed * (1.0 + agent_attrs.current_panic_level * 0.3)
        )
        
        # Calculate direction to target
        dx = target_position[0] - current_pos[0]
        dz = target_position[2] - current_pos[2]
        distance_to_target = math.sqrt(dx * dx + dz * dz)
        
        if distance_to_target < 0.1:
            # Reached target
            return current_pos
        
        # Normalize direction
        target_direction = (dx / distance_to_target, dz / distance_to_target)
        
        # Get current velocity direction
        current_vx = agent.get("velocity_x", 0.0)
        current_vz = agent.get("velocity_z", 0.0)
        current_speed = math.sqrt(current_vx * current_vx + current_vz * current_vz)
        
        if current_speed > 0.01:
            current_direction = (current_vx / current_speed, current_vz / current_speed)
        else:
            current_direction = target_direction
        
        # Calculate turning rate
        turning_rate = self.turning_model.calculate_turning_rate(
            agent_attrs,
            current_direction,
            target_direction,
            local_density,
            agent_attrs.current_panic_level
        )
        
        # Apply turning (rotate current direction towards target)
        angle_to_target = math.atan2(
            target_direction[1] * current_direction[0] - target_direction[0] * current_direction[1],
            target_direction[0] * current_direction[0] + target_direction[1] * current_direction[1]
        )
        
        max_turn = turning_rate * dt
        if abs(angle_to_target) > max_turn:
            # Rotate by max_turn
            turn_sign = 1.0 if angle_to_target > 0 else -1.0
            angle = math.atan2(current_direction[1], current_direction[0]) + turn_sign * max_turn
            new_direction = (math.cos(angle), math.sin(angle))
        else:
            new_direction = target_direction
        
        # Calculate body collision forces
        body_shape = BodyShape(
            shape_type="elliptical",
            width=agent_attrs.body_width,
            depth=agent_attrs.body_depth
        )
        
        collision_fx = 0.0
        collision_fz = 0.0
        
        for other_agent in all_agents:
            if other_agent.get("agent_id") == agent.get("agent_id"):
                continue
            if other_agent.get("status") == "evacuated":
                continue
            
            other_pos = (other_agent.get("x", 0), other_agent.get("y", 0), 
                        other_agent.get("z", other_agent.get("y", 0)))
            
            # Get other agent's body shape (would need to store in agent data)
            other_body = BodyShape(
                shape_type="elliptical",
                width=0.45,  # Default
                depth=0.30
            )
            
            fx, fz = self.body_collision.calculate_repulsion_force(
                current_pos, body_shape, other_pos, other_body
            )
            collision_fx += fx
            collision_fz += fz
        
        # Combine movement direction with collision forces
        # Normalize collision force direction
        collision_magnitude = math.sqrt(collision_fx * collision_fx + collision_fz * collision_fz)
        if collision_magnitude > 0.01:
            collision_direction = (collision_fx / collision_magnitude, collision_fz / collision_magnitude)
            # Blend desired direction with collision avoidance
            avoidance_weight = min(1.0, collision_magnitude / 1000.0)
            final_direction = (
                new_direction[0] * (1.0 - avoidance_weight) + collision_direction[0] * avoidance_weight,
                new_direction[1] * (1.0 - avoidance_weight) + collision_direction[1] * avoidance_weight
            )
            # Renormalize
            dir_mag = math.sqrt(final_direction[0]**2 + final_direction[1]**2)
            if dir_mag > 0.01:
                final_direction = (final_direction[0] / dir_mag, final_direction[1] / dir_mag)
        else:
            final_direction = new_direction
        
        # Calculate new velocity
        new_vx = final_direction[0] * desired_velocity
        new_vz = final_direction[1] * desired_velocity
        
        # Update position
        new_x = current_pos[0] + new_vx * dt
        new_y = current_pos[1]
        new_z = current_pos[2] + new_vz * dt
        
        return (new_x, new_y, new_z)

# Global movement physics instance
movement_physics = EnhancedMovementPhysics()

