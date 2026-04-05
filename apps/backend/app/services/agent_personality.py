"""
Agent Personality System
Implements personality-based behavior for evacuation agents
"""

import random
from enum import Enum
from dataclasses import dataclass

class PersonalityType(Enum):
    CALM = "calm"
    LEADER = "leader"
    PANICKED = "panicked"
    INJURED = "injured"
    DISABLED = "disabled"
    CHILD = "child"

class EmotionalState(Enum):
    NORMAL = "normal"
    STRESS = "stress"
    PANIC = "panic"
    BREAKDOWN = "breakdown"

@dataclass
class AgentPersonality:
    """Agent personality configuration"""
    personality_type: PersonalityType
    emotional_state: EmotionalState = EmotionalState.NORMAL
    panic_threshold: float = 0.5
    decision_delay: float = 0.0
    speed_multiplier: float = 1.0
    herd_following: float = 0.0
    family_group_id: int = None
    
    def update_emotional_state(self, stress_level: float, nearby_panic: float):
        """Update emotional state based on stress and environment"""
        combined_stress = stress_level + nearby_panic * 0.5
        
        if combined_stress > 0.8:
            self.emotional_state = EmotionalState.BREAKDOWN
        elif combined_stress > 0.6:
            self.emotional_state = EmotionalState.PANIC
        elif combined_stress > 0.3:
            self.emotional_state = EmotionalState.STRESS
        else:
            self.emotional_state = EmotionalState.NORMAL
    
    def get_speed_modifier(self) -> float:
        """Get speed modifier based on personality and emotional state"""
        base_speed = self.speed_multiplier
        
        if self.personality_type == PersonalityType.DISABLED:
            base_speed *= 0.5
        elif self.personality_type == PersonalityType.CHILD:
            base_speed *= 0.7
        elif self.personality_type == PersonalityType.INJURED:
            base_speed *= 0.6
        
        if self.emotional_state == EmotionalState.PANIC:
            base_speed *= 1.2  # Panic increases speed
        elif self.emotional_state == EmotionalState.BREAKDOWN:
            base_speed *= 0.3  # Breakdown reduces speed significantly
        
        return base_speed
    
    def get_decision_delay(self) -> float:
        """Get decision delay based on personality"""
        base_delay = self.decision_delay
        
        if self.personality_type == PersonalityType.LEADER:
            base_delay *= 0.5  # Leaders decide faster
        elif self.personality_type == PersonalityType.PANICKED:
            base_delay *= 2.0  # Panicked people hesitate more
        
        if self.emotional_state == EmotionalState.PANIC:
            base_delay *= 1.5
        
        return base_delay

class PersonalityGenerator:
    """Generate agent personalities"""
    
    @staticmethod
    def generate_personality() -> AgentPersonality:
        """Generate random personality for an agent"""
        personality_type = random.choice(list(PersonalityType))
        
        # Set personality-specific attributes
        if personality_type == PersonalityType.CALM:
            panic_threshold = 0.7
            decision_delay = 0.1
            speed_multiplier = 1.0
            herd_following = 0.2
        elif personality_type == PersonalityType.LEADER:
            panic_threshold = 0.8
            decision_delay = 0.05
            speed_multiplier = 1.1
            herd_following = -0.3  # Leaders don't follow, others follow them
        elif personality_type == PersonalityType.PANICKED:
            panic_threshold = 0.3
            decision_delay = 0.3
            speed_multiplier = 1.2
            herd_following = 0.8
        elif personality_type == PersonalityType.INJURED:
            panic_threshold = 0.5
            decision_delay = 0.2
            speed_multiplier = 0.6
            herd_following = 0.5
        elif personality_type == PersonalityType.DISABLED:
            panic_threshold = 0.6
            decision_delay = 0.25
            speed_multiplier = 0.5
            herd_following = 0.7
        else:  # CHILD
            panic_threshold = 0.4
            decision_delay = 0.4
            speed_multiplier = 0.7
            herd_following = 0.9
        
        return AgentPersonality(
            personality_type=personality_type,
            panic_threshold=panic_threshold,
            decision_delay=decision_delay,
            speed_multiplier=speed_multiplier,
            herd_following=herd_following,
            family_group_id=random.randint(1, 10) if random.random() < 0.3 else None
        )

