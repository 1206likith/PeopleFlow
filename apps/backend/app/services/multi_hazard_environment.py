"""
Multi-Hazard Environment Models
Implements fire/smoke spread, flooding, tactical attacks, earthquake debris
Research-backed hazard propagation and agent interaction
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class HazardType(Enum):
    """Types of hazards"""
    FIRE = "fire"
    SMOKE = "smoke"
    FLOOD = "flood"
    TACTICAL_ATTACK = "tactical_attack"
    EARTHQUAKE = "earthquake"
    GAS_LEAK = "gas_leak"
    STRUCTURAL_COLLAPSE = "structural_collapse"

@dataclass
class HazardField:
    """Spatial field representing hazard intensity"""
    hazard_type: HazardType
    origin: Tuple[float, float, float]
    intensity: float  # 0-1
    radius: float  # meters
    propagation_speed: float  # m/s
    time_elapsed: float = 0.0
    affected_cells: List[Tuple[int, int]] = field(default_factory=list)
    
    def get_intensity_at_position(self, position: Tuple[float, float, float]) -> float:
        """Get hazard intensity at a specific position"""
        distance = math.sqrt(
            (position[0] - self.origin[0])**2 +
            (position[1] - self.origin[1])**2 +
            (position[2] - self.origin[2])**2
        )
        
        if distance > self.radius:
            return 0.0
        
        # Exponential decay with distance
        decay_factor = math.exp(-distance / (self.radius * 0.5))
        return self.intensity * decay_factor

class FireSmokeModel:
    """
    Fire & smoke spread model
    Visibility loss, choking effects, heat damage
    Research: Fire evacuation models (arXiv, ScienceDirect)
    """
    
    def __init__(self):
        self.smoke_propagation_rate = 0.05  # m/s (research-validated)
        self.fire_growth_rate = 0.02  # intensity per second
        self.max_smoke_opacity = 1.0
        self.visibility_reduction_factor = 0.3  # per unit smoke intensity
    
    def propagate_fire(
        self,
        fire_field: HazardField,
        dt: float,
        building_layout: Dict,
        wind_direction: Optional[Tuple[float, float]] = None
    ) -> HazardField:
        """
        Propagate fire and smoke over time
        
        Args:
            fire_field: Current fire field
            dt: Time step
            building_layout: Building structure (walls, rooms, etc.)
            wind_direction: Optional wind direction (x, z)
        """
        # Fire grows in intensity
        fire_field.intensity = min(1.0, fire_field.intensity + self.fire_growth_rate * dt)
        
        # Fire spreads (radius increases)
        fire_field.radius += self.smoke_propagation_rate * dt
        
        # Wind effect (if present)
        if wind_direction:
            # Fire spreads faster in wind direction
            wind_magnitude = math.sqrt(wind_direction[0]**2 + wind_direction[1]**2)
            if wind_magnitude > 0:
                fire_field.radius += wind_magnitude * 0.1 * dt
        
        fire_field.time_elapsed += dt
        
        return fire_field
    
    def get_smoke_effects(
        self,
        position: Tuple[float, float, float],
        fire_fields: List[HazardField]
    ) -> Dict[str, float]:
        """
        Get smoke effects at position
        
        Returns:
            Dictionary with:
            - visibility: 0-1, visibility level
            - breathing_difficulty: 0-1, affects movement speed
            - panic_increase: per second panic increase
        """
        max_intensity = 0.0
        for fire_field in fire_fields:
            intensity = fire_field.get_intensity_at_position(position)
            max_intensity = max(max_intensity, intensity)
        
        # Smoke opacity (higher intensity = more smoke)
        smoke_opacity = max_intensity * self.max_smoke_opacity
        
        # Visibility reduction
        visibility = max(0.0, 1.0 - smoke_opacity * self.visibility_reduction_factor)
        
        # Breathing difficulty (affects speed)
        breathing_difficulty = smoke_opacity * 0.7
        
        # Panic increase (smoke causes panic)
        panic_increase = smoke_opacity * 0.05  # per second
        
        return {
            "visibility": visibility,
            "breathing_difficulty": breathing_difficulty,
            "panic_increase": panic_increase,
            "smoke_intensity": smoke_opacity
        }
    
    def get_heat_damage(
        self,
        position: Tuple[float, float, float],
        fire_fields: List[HazardField],
        exposure_time: float
    ) -> float:
        """Calculate health damage from heat exposure"""
        max_intensity = 0.0
        for fire_field in fire_fields:
            intensity = fire_field.get_intensity_at_position(position)
            max_intensity = max(max_intensity, intensity)
        
        # Heat damage is cumulative over time
        # High intensity + long exposure = high damage
        damage_rate = max_intensity * 0.1  # per second at max intensity
        total_damage = damage_rate * exposure_time
        
        return min(1.0, total_damage)

class FloodModel:
    """
    Flooding & water movement coupling
    Water blocks paths, affects movement speed, drowning risk
    Research: Flood evacuation models (ScienceDirect)
    """
    
    def __init__(self):
        self.water_propagation_speed = 0.3  # m/s (depends on source)
        self.max_water_depth = 2.0  # meters
        self.drowning_threshold = 1.5  # meters (dangerous depth)
        self.speed_reduction_factor = 0.3  # per meter of water depth
    
    def propagate_flood(
        self,
        flood_field: HazardField,
        dt: float,
        building_layout: Dict,
        floor_elevation: float = 0.0
    ) -> HazardField:
        """Propagate flood water over time"""
        # Flood spreads
        flood_field.radius += self.water_propagation_speed * dt
        
        # Intensity represents water depth (0-1 maps to 0-max_water_depth)
        flood_field.intensity = min(1.0, flood_field.intensity + 0.01 * dt)
        
        flood_field.time_elapsed += dt
        
        return flood_field
    
    def get_water_depth(
        self,
        position: Tuple[float, float, float],
        flood_fields: List[HazardField],
        floor_elevation: float = 0.0
    ) -> float:
        """Get water depth at position (in meters)"""
        max_depth = 0.0
        
        for flood_field in flood_fields:
            intensity = flood_field.get_intensity_at_position(position)
            depth = intensity * self.max_water_depth
            max_depth = max(max_depth, depth)
        
        # Account for floor elevation
        position_elevation = position[1] - floor_elevation
        effective_depth = max(0.0, max_depth - position_elevation)
        
        return effective_depth
    
    def get_flood_effects(
        self,
        position: Tuple[float, float, float],
        flood_fields: List[HazardField],
        agent_height: float = 1.7  # Average person height
    ) -> Dict[str, float]:
        """
        Get flood effects at position
        
        Returns:
            Dictionary with:
            - water_depth: meters
            - path_blocked: bool (if water too deep)
            - speed_modifier: 0-1, movement speed reduction
            - drowning_risk: 0-1, risk of drowning
        """
        water_depth = self.get_water_depth(position, flood_fields)
        
        # Path blocked if water is too deep
        path_blocked = water_depth > agent_height * 0.6  # Blocked if water > 60% of height
        
        # Speed reduction (water resistance)
        if water_depth > 0:
            speed_modifier = max(0.1, 1.0 - (water_depth / self.max_water_depth) * self.speed_reduction_factor)
        else:
            speed_modifier = 1.0
        
        # Drowning risk (increases with depth and time)
        drowning_risk = 0.0
        if water_depth > self.drowning_threshold:
            drowning_risk = min(1.0, (water_depth - self.drowning_threshold) / 0.5)
        
        return {
            "water_depth": water_depth,
            "path_blocked": path_blocked,
            "speed_modifier": speed_modifier,
            "drowning_risk": drowning_risk
        }

class TacticalAttackModel:
    """
    Violent/tactical attack scenarios
    Obstacle hiding behavior, panic response
    Research: Tactical evacuation scenarios
    """
    
    def __init__(self):
        self.threat_radius = 20.0  # meters
        self.hiding_behavior_threshold = 0.5  # Panic level to trigger hiding
        self.panic_spike = 0.8  # Immediate panic increase
    
    def get_threat_effects(
        self,
        position: Tuple[float, float, float],
        threat_location: Tuple[float, float, float],
        time_since_attack: float
    ) -> Dict[str, float]:
        """
        Get threat effects at position
        
        Returns:
            Dictionary with:
            - threat_proximity: 0-1
            - panic_spike: immediate panic increase
            - hiding_urge: 0-1, urge to hide instead of evacuate
            - visibility_risk: 0-1, risk of being seen
        """
        distance = math.sqrt(
            (position[0] - threat_location[0])**2 +
            (position[1] - threat_location[1])**2 +
            (position[2] - threat_location[2])**2
        )
        
        threat_proximity = max(0.0, 1.0 - (distance / self.threat_radius))
        
        # Panic spike (immediate high panic)
        panic_spike = self.panic_spike * threat_proximity
        
        # Hiding urge (agents want to hide when threat is close)
        hiding_urge = threat_proximity * 0.8
        
        # Visibility risk (being seen by threat)
        visibility_risk = threat_proximity
        
        return {
            "threat_proximity": threat_proximity,
            "panic_spike": panic_spike,
            "hiding_urge": hiding_urge,
            "visibility_risk": visibility_risk
        }
    
    def should_hide(
        self,
        threat_effects: Dict[str, float],
        agent_panic_level: float,
        available_hiding_spots: List[Dict]
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Determine if agent should hide instead of evacuate
        
        Returns:
            (should_hide, hiding_spot)
        """
        hiding_urge = threat_effects.get("hiding_urge", 0.0)
        panic_level = agent_panic_level
        
        # Hide if hiding urge is high and panic is moderate (not too high to freeze)
        should_hide = (hiding_urge > self.hiding_behavior_threshold and 
                      0.3 < panic_level < 0.8)
        
        hiding_spot = None
        if should_hide and available_hiding_spots:
            # Choose nearest hiding spot
            for spot in available_hiding_spots:
                # Calculate distance (would need position)
                # For now, return first available
                hiding_spot = spot
                break
        
        return should_hide, hiding_spot

class EarthquakeModel:
    """
    Earthquake debris & unstable hazards
    Falling obstacles, exit collapse risk, structural damage
    """
    
    def __init__(self):
        self.shake_intensity = 1.0  # 0-1
        self.debris_fall_rate = 0.1  # probability per second
        self.exit_collapse_risk = 0.05  # per exit per major shake
    
    def generate_debris(
        self,
        building_layout: Dict,
        shake_intensity: float,
        time_elapsed: float
    ) -> List[Dict]:
        """
        Generate falling debris based on earthquake intensity
        
        Returns:
            List of debris obstacles with positions and sizes
        """
        debris = []
        
        # Debris falls from ceilings, walls, etc.
        if np.random.random() < self.debris_fall_rate * shake_intensity:
            # Generate random debris location
            # This would use building_layout to find valid locations
            debris.append({
                "position": (0, 0, 0),  # Would be calculated from layout
                "size": (2.0, 1.0, 2.0),  # width, height, depth
                "blocks_path": True
            })
        
        return debris
    
    def check_exit_collapse(
        self,
        exits: List[Dict],
        shake_intensity: float
    ) -> List[str]:
        """
        Check if any exits have collapsed
        
        Returns:
            List of collapsed exit IDs
        """
        collapsed_exits = []
        
        for exit in exits:
            # Higher intensity = higher collapse risk
            collapse_prob = self.exit_collapse_risk * shake_intensity
            
            if np.random.random() < collapse_prob:
                collapsed_exits.append(exit.get("id"))
        
        return collapsed_exits
    
    def get_earthquake_effects(
        self,
        position: Tuple[float, float, float],
        shake_intensity: float,
        debris_obstacles: List[Dict]
    ) -> Dict[str, float]:
        """
        Get earthquake effects at position
        
        Returns:
            Dictionary with:
            - movement_difficulty: 0-1, difficulty moving during shake
            - panic_increase: per second
            - path_blocked: bool, if debris blocks path
        """
        # Movement difficulty (hard to walk during earthquake)
        movement_difficulty = shake_intensity * 0.6
        
        # Panic increase
        panic_increase = shake_intensity * 0.1  # per second
        
        # Check if debris blocks path
        path_blocked = False
        for debris in debris_obstacles:
            debris_pos = debris.get("position", (0, 0, 0))
            distance = math.sqrt(
                (position[0] - debris_pos[0])**2 +
                (position[2] - debris_pos[2])**2
            )
            if distance < 2.0:  # Debris blocks nearby area
                path_blocked = True
                break
        
        return {
            "movement_difficulty": movement_difficulty,
            "panic_increase": panic_increase,
            "path_blocked": path_blocked
        }

class MultiHazardEnvironment:
    """
    Multi-hazard environment manager
    Combines all hazard types and their interactions
    """
    
    def __init__(self):
        self.fire_model = FireSmokeModel()
        self.flood_model = FloodModel()
        self.attack_model = TacticalAttackModel()
        self.earthquake_model = EarthquakeModel()
        self.active_hazards: Dict[HazardType, List[HazardField]] = {}
    
    def add_hazard(
        self,
        hazard_type: HazardType,
        origin: Tuple[float, float, float],
        initial_intensity: float = 0.5,
        radius: float = 10.0
    ):
        """Add a new hazard to the environment"""
        hazard_field = HazardField(
            hazard_type=hazard_type,
            origin=origin,
            intensity=initial_intensity,
            radius=radius,
            propagation_speed=self._get_propagation_speed(hazard_type)
        )
        
        if hazard_type not in self.active_hazards:
            self.active_hazards[hazard_type] = []
        self.active_hazards[hazard_type].append(hazard_field)
        return hazard_field
    
    def update_hazards(self, dt: float, building_layout: Dict):
        """Update all hazards over time"""
        # Update fire/smoke
        if HazardType.FIRE in self.active_hazards:
            for fire_field in self.active_hazards[HazardType.FIRE]:
                self.fire_model.propagate_fire(fire_field, dt, building_layout)
        
        # Update flood
        if HazardType.FLOOD in self.active_hazards:
            for flood_field in self.active_hazards[HazardType.FLOOD]:
                self.flood_model.propagate_flood(flood_field, dt, building_layout)
    
    def get_environmental_effects(
        self,
        position: Tuple[float, float, float]
    ) -> Dict[str, any]:
        """
        Get all environmental effects at a position
        
        Returns:
            Comprehensive dictionary of all effects
        """
        effects = {
            "visibility": 1.0,
            "speed_modifier": 1.0,
            "panic_increase": 0.0,
            "health_decay": 0.0,
            "path_blocked": False,
            "breathing_difficulty": 0.0
        }
        
        # Fire/smoke effects
        if HazardType.FIRE in self.active_hazards:
            smoke_effects = self.fire_model.get_smoke_effects(
                position, self.active_hazards[HazardType.FIRE]
            )
            effects["visibility"] = min(effects["visibility"], smoke_effects["visibility"])
            effects["breathing_difficulty"] = smoke_effects["breathing_difficulty"]
            effects["panic_increase"] += smoke_effects["panic_increase"]
            effects["speed_modifier"] *= (1.0 - smoke_effects["breathing_difficulty"] * 0.3)
        
        # Flood effects
        if HazardType.FLOOD in self.active_hazards:
            flood_effects = self.flood_model.get_flood_effects(
                position, self.active_hazards[HazardType.FLOOD]
            )
            effects["speed_modifier"] *= flood_effects["speed_modifier"]
            effects["path_blocked"] = effects["path_blocked"] or flood_effects["path_blocked"]
            if flood_effects["drowning_risk"] > 0.5:
                effects["health_decay"] += flood_effects["drowning_risk"] * 0.1
        
        return effects
    
    def _get_propagation_speed(self, hazard_type: HazardType) -> float:
        """Get propagation speed for hazard type"""
        speeds = {
            HazardType.FIRE: 0.05,
            HazardType.SMOKE: 0.1,
            HazardType.FLOOD: 0.3,
            HazardType.TACTICAL_ATTACK: 0.0,  # Static threat
            HazardType.EARTHQUAKE: 0.0,  # Instant event
        }
        return speeds.get(hazard_type, 0.0)

# Global multi-hazard environment instance
multi_hazard_env = MultiHazardEnvironment()

