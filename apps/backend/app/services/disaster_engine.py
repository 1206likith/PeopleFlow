"""
Multi-Disaster Scenario Engine
Simulates different disaster types with physics-driven effects
"""

from enum import Enum
from typing import List, Tuple
from dataclasses import dataclass
import math

class DisasterType(Enum):
    FIRE = "fire"
    FLOOD = "flood"
    BOMB_BLAST = "bomb_blast"
    EARTHQUAKE = "earthquake"
    GAS_LEAK = "gas_leak"

@dataclass
class DisasterEffect:
    """Effect of disaster on environment"""
    visibility_reduction: float = 0.0  # 0-1, reduces agent vision
    path_obstruction: List[Tuple[float, float, float]] = None  # (x, y, radius) blocked areas
    health_decay_rate: float = 0.0  # Health loss per second
    speed_modifier: float = 1.0  # Speed multiplier
    panic_increase: float = 0.0  # Panic level increase per second

class DisasterEngine:
    """Manages disaster effects in simulation"""
    
    def __init__(self, disaster_type: DisasterType, origin: Tuple[float, float, float]):
        self.disaster_type = disaster_type
        self.origin = origin  # (x, y, z)
        self.time = 0.0
        self.intensity = 1.0
        
    def get_effect_at_position(self, position: Tuple[float, float, float]) -> DisasterEffect:
        """Get disaster effect at a specific position"""
        distance = math.sqrt(
            (position[0] - self.origin[0])**2 +
            (position[1] - self.origin[1])**2 +
            (position[2] - self.origin[2])**2
        )
        
        effect = DisasterEffect()
        
        if self.disaster_type == DisasterType.FIRE:
            # Fire: smoke reduces visibility, heat causes panic
            if distance < 20:
                effect.visibility_reduction = min(0.8, distance / 20)
                effect.panic_increase = 0.1 * (1 - distance / 20)
                effect.health_decay_rate = 0.05 * (1 - distance / 20)
                effect.speed_modifier = 0.9  # Crouching due to smoke
        elif self.disaster_type == DisasterType.FLOOD:
            # Flood: water blocks paths, drowning risk
            if distance < 30:
                effect.path_obstruction = [(self.origin[0], self.origin[1], 30 - distance)]
                if distance < 10:
                    effect.health_decay_rate = 0.2
                    effect.speed_modifier = 0.3  # Slowed by water
        elif self.disaster_type == DisasterType.BOMB_BLAST:
            # Bomb: shockwave, debris
            if distance < 25:
                effect.health_decay_rate = 0.3 * (1 - distance / 25)
                effect.panic_increase = 0.5
                effect.speed_modifier = 0.8 if distance < 15 else 1.2  # Run away
        elif self.disaster_type == DisasterType.EARTHQUAKE:
            # Earthquake: falling obstacles, exit collapse risk
            if distance < 40:
                effect.path_obstruction = [
                    (self.origin[0] + math.sin(self.time) * 10, self.origin[1], 5),
                    (self.origin[0] - math.cos(self.time) * 10, self.origin[1], 5),
                ]
                effect.panic_increase = 0.2
        elif self.disaster_type == DisasterType.GAS_LEAK:
            # Gas leak: oxygen decay, hallucination
            if distance < 35:
                effect.health_decay_rate = 0.1 * (1 - distance / 35)
                effect.visibility_reduction = 0.3
                effect.panic_increase = 0.15
        
        return effect
    
    def update(self, dt: float):
        """Update disaster over time"""
        self.time += dt
        # Disasters can intensify or spread
        if self.disaster_type == DisasterType.FIRE:
            self.intensity = min(2.0, self.intensity + dt * 0.1)

