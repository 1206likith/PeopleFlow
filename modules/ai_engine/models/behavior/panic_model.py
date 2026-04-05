"""
Panic Behavior Model
Models panic behavior in emergency evacuation scenarios
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class PanicState:
    """Represents the panic state of an agent"""
    panic_level: float  # 0.0 (calm) to 1.0 (extreme panic)
    speed_multiplier: float
    decision_quality: float  # How well agent makes decisions
    social_influence: float  # Susceptibility to crowd behavior


class PanicModel:
    """
    Models panic behavior based on:
    - Proximity to danger
    - Crowd density
    - Time pressure
    - Individual characteristics
    """
    
    def __init__(
        self,
        base_panic_threshold: float = 0.3,
        panic_decay_rate: float = 0.1,
        social_influence_strength: float = 0.5
    ):
        """
        Initialize panic model
        
        Args:
            base_panic_threshold: Base level at which panic starts
            panic_decay_rate: How quickly panic decreases when safe
            social_influence_strength: How much agents influence each other
        """
        self.base_panic_threshold = base_panic_threshold
        self.panic_decay_rate = panic_decay_rate
        self.social_influence_strength = social_influence_strength
    
    def calculate_panic_level(
        self,
        distance_to_danger: float,
        crowd_density: float,
        time_pressure: float,
        individual_trait: float = 0.5
    ) -> float:
        """
        Calculate panic level based on multiple factors
        
        Args:
            distance_to_danger: Distance to nearest danger source
            crowd_density: Local crowd density (0-1)
            time_pressure: Time pressure factor (0-1)
            individual_trait: Individual panic susceptibility (0-1)
            
        Returns:
            Panic level (0-1)
        """
        # Distance factor (closer = more panic)
        distance_factor = max(0, 1.0 - min(distance_to_danger / 10.0, 1.0))
        
        # Crowd density factor (higher density = more panic)
        density_factor = crowd_density
        
        # Combined panic level
        base_panic = (
            distance_factor * 0.4 +
            density_factor * 0.3 +
            time_pressure * 0.3
        )
        
        # Apply individual trait
        panic_level = base_panic * (0.5 + individual_trait)
        
        # Clamp to [0, 1]
        return np.clip(panic_level, 0.0, 1.0)
    
    def update_panic_state(
        self,
        current_state: PanicState,
        distance_to_danger: float,
        crowd_density: float,
        time_pressure: float,
        nearby_panic_levels: List[float] = None
    ) -> PanicState:
        """
        Update panic state based on current conditions
        
        Args:
            current_state: Current panic state
            distance_to_danger: Distance to danger
            crowd_density: Local crowd density
            time_pressure: Time pressure
            nearby_panic_levels: Panic levels of nearby agents
            
        Returns:
            Updated panic state
        """
        # Calculate new panic level
        new_panic = self.calculate_panic_level(
            distance_to_danger,
            crowd_density,
            time_pressure,
            current_state.social_influence
        )
        
        # Apply social influence (contagion effect)
        if nearby_panic_levels:
            avg_nearby_panic = np.mean(nearby_panic_levels)
            social_effect = (avg_nearby_panic - current_state.panic_level) * self.social_influence_strength
            new_panic += social_effect
        
        # Decay if safe
        if distance_to_danger > 20.0 and crowd_density < 0.3:
            new_panic = max(0, new_panic - self.panic_decay_rate)
        
        new_panic = np.clip(new_panic, 0.0, 1.0)
        
        # Update speed multiplier (panic increases speed up to a point)
        # Very high panic can cause erratic movement (reduced effective speed)
        if new_panic < 0.7:
            speed_multiplier = 1.0 + new_panic * 0.5  # Up to 1.35x speed
        else:
            speed_multiplier = 1.35 - (new_panic - 0.7) * 0.5  # Decrease at extreme panic
        
        # Decision quality decreases with panic
        decision_quality = 1.0 - new_panic * 0.4  # Up to 40% reduction
        
        return PanicState(
            panic_level=new_panic,
            speed_multiplier=speed_multiplier,
            decision_quality=decision_quality,
            social_influence=current_state.social_influence
        )
    
    def get_behavior_modifiers(self, panic_state: PanicState) -> Dict[str, float]:
        """
        Get behavior modifiers based on panic state
        
        Args:
            panic_state: Current panic state
            
        Returns:
            Dictionary of behavior modifiers
        """
        return {
            "speed_multiplier": panic_state.speed_multiplier,
            "decision_quality": panic_state.decision_quality,
            "path_deviation": panic_state.panic_level * 0.2,  # Random path deviation
            "exit_switching_probability": panic_state.panic_level * 0.1,  # Switch exits more
        }


def create_panic_model(config: Dict = None) -> PanicModel:
    """
    Factory function to create panic model with configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured PanicModel instance
    """
    if config is None:
        config = {}
    
    return PanicModel(
        base_panic_threshold=config.get("base_panic_threshold", 0.3),
        panic_decay_rate=config.get("panic_decay_rate", 0.1),
        social_influence_strength=config.get("social_influence_strength", 0.5)
    )


if __name__ == "__main__":
    # Example usage
    model = PanicModel()
    
    # Initial state
    state = PanicState(
        panic_level=0.0,
        speed_multiplier=1.0,
        decision_quality=1.0,
        social_influence=0.5
    )
    
    # Simulate panic increase
    print("Simulating panic behavior:")
    for i in range(10):
        state = model.update_panic_state(
            state,
            distance_to_danger=10.0 - i,
            crowd_density=0.5 + i * 0.05,
            time_pressure=0.3 + i * 0.05
        )
        modifiers = model.get_behavior_modifiers(state)
        print(f"Step {i+1}: Panic={state.panic_level:.2f}, "
              f"Speed={modifiers['speed_multiplier']:.2f}x, "
              f"Decision Quality={modifiers['decision_quality']:.2f}")

