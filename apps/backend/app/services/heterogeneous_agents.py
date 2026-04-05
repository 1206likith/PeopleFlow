"""
Heterogeneous Agent Models - Research-Backed Human Diversity
Implements physiological, psychological, and demographic diversity
Based on evacuation research literature
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import logging

logger = logging.getLogger(__name__)

class AgeGroup(Enum):
    """Age groups with research-validated parameters"""
    CHILD = "child"  # 0-12
    TEEN = "teen"  # 13-17
    YOUNG_ADULT = "young_adult"  # 18-35
    ADULT = "adult"  # 36-55
    MIDDLE_AGED = "middle_aged"  # 56-70
    ELDERLY = "elderly"  # 71+

class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    CHRONIC_ILLNESS = "chronic_illness"
    TEMPORARY_INJURY = "temporary_injury"
    SEVERE_INJURY = "severe_injury"
    PREGNANT = "pregnant"

class DisabilityType(Enum):
    NONE = "none"
    WHEELCHAIR = "wheelchair"
    VISUALLY_IMPAIRED = "visually_impaired"
    HEARING_IMPAIRED = "hearing_impaired"
    MOBILITY_IMPAIRED = "mobility_impaired"
    COGNITIVE_IMPAIRED = "cognitive_impaired"

class CognitiveState(Enum):
    """Cognitive states affecting decision-making"""
    CALM = "calm"
    STRESSED = "stressed"
    PANICKED = "panicked"
    DISORIENTED = "disoriented"
    SHOCKED = "shocked"

class FamiliarityLevel(Enum):
    """Environment familiarity"""
    UNFAMILIAR = "unfamiliar"  # First time in building
    SOMEWHAT_FAMILIAR = "somewhat_familiar"  # Visited a few times
    FAMILIAR = "familiar"  # Regular visitor
    VERY_FAMILIAR = "very_familiar"  # Works/lives here

@dataclass
class AgentAttributes:
    """Comprehensive agent attributes for heterogeneous modeling"""
    # Demographics
    age_group: AgeGroup
    age: int  # Specific age
    gender: Gender
    health_status: HealthStatus
    disability_type: DisabilityType
    
    # Physiological
    base_walking_speed: float  # m/s (research-validated)
    max_walking_speed: float  # m/s
    reaction_time: float  # seconds (pre-evac decision time)
    physical_stamina: float  # 0-1, affects speed over time
    body_width: float  # meters (for collision)
    body_depth: float  # meters
    
    # Psychological
    cognitive_state: CognitiveState
    panic_susceptibility: float  # 0-1, how easily panicked
    risk_tolerance: float  # 0-1, willingness to take risks
    stress_resilience: float  # 0-1, ability to handle stress
    
    # Behavioral
    familiarity: FamiliarityLevel
    environment_knowledge: float  # 0-1, affects routing decisions
    leadership_tendency: float  # 0-1, tendency to lead others
    following_tendency: float  # 0-1, tendency to follow others
    cooperation_level: float  # 0-1, willingness to help others
    
    # Current state
    current_panic_level: float = 0.0  # 0-1
    current_stress_level: float = 0.0  # 0-1
    current_health: float = 1.0  # 0-1
    fatigue_level: float = 0.0  # 0-1
    
    # Group dynamics
    family_group_id: Optional[int] = None
    is_leader: bool = False
    following_agent_id: Optional[int] = None
    
    # Decision making
    pre_evacuation_delay: float = 0.0  # seconds
    decision_confidence: float = 0.5  # 0-1
    
    def __post_init__(self):
        """Validate and adjust attributes based on research constraints"""
        # Ensure physical constraints are realistic
        if self.disability_type == DisabilityType.WHEELCHAIR:
            self.base_walking_speed = min(self.base_walking_speed, 0.8)  # Wheelchair speed limit
            self.body_width = max(self.body_width, 0.6)  # Wheelchair width
        elif self.disability_type == DisabilityType.MOBILITY_IMPAIRED:
            self.base_walking_speed *= 0.6
        elif self.disability_type == DisabilityType.VISUALLY_IMPAIRED:
            self.environment_knowledge *= 0.5  # Reduced spatial awareness
        
        # Age-based adjustments (research-validated)
        if self.age_group == AgeGroup.CHILD:
            self.base_walking_speed = min(self.base_walking_speed, 1.2)
            self.panic_susceptibility = min(1.0, self.panic_susceptibility * 1.3)
            self.following_tendency = min(1.0, self.following_tendency * 1.2)
        elif self.age_group == AgeGroup.ELDERLY:
            self.base_walking_speed = min(self.base_walking_speed, 1.0)
            self.reaction_time *= 1.5
            self.physical_stamina *= 0.7
        
        # Health-based adjustments
        if self.health_status == HealthStatus.SEVERE_INJURY:
            self.base_walking_speed *= 0.4
            self.physical_stamina *= 0.3
        elif self.health_status == HealthStatus.PREGNANT:
            self.base_walking_speed *= 0.85
            self.physical_stamina *= 0.8

class HeterogeneousAgentGenerator:
    """Generates agents with research-validated heterogeneous attributes"""
    
    # Research-validated parameter distributions
    AGE_DISTRIBUTION = {
        AgeGroup.CHILD: 0.08,
        AgeGroup.TEEN: 0.05,
        AgeGroup.YOUNG_ADULT: 0.25,
        AgeGroup.ADULT: 0.35,
        AgeGroup.MIDDLE_AGED: 0.20,
        AgeGroup.ELDERLY: 0.07
    }
    
    GENDER_DISTRIBUTION = {
        Gender.MALE: 0.49,
        Gender.FEMALE: 0.50,
        Gender.OTHER: 0.01
    }
    
    HEALTH_DISTRIBUTION = {
        HealthStatus.HEALTHY: 0.85,
        HealthStatus.CHRONIC_ILLNESS: 0.08,
        HealthStatus.TEMPORARY_INJURY: 0.04,
        HealthStatus.SEVERE_INJURY: 0.02,
        HealthStatus.PREGNANT: 0.01
    }
    
    DISABILITY_DISTRIBUTION = {
        DisabilityType.NONE: 0.92,
        DisabilityType.WHEELCHAIR: 0.02,
        DisabilityType.VISUALLY_IMPAIRED: 0.02,
        DisabilityType.HEARING_IMPAIRED: 0.02,
        DisabilityType.MOBILITY_IMPAIRED: 0.015,
        DisabilityType.COGNITIVE_IMPAIRED: 0.005
    }
    
    FAMILIARITY_DISTRIBUTION = {
        FamiliarityLevel.UNFAMILIAR: 0.30,  # Visitors
        FamiliarityLevel.SOMEWHAT_FAMILIAR: 0.20,
        FamiliarityLevel.FAMILIAR: 0.30,  # Regular visitors
        FamiliarityLevel.VERY_FAMILIAR: 0.20  # Workers/residents
    }
    
    @staticmethod
    def generate_agent(agent_id: int, custom_profile: Optional[Dict] = None) -> AgentAttributes:
        """
        Generate a heterogeneous agent with research-validated attributes
        
        Args:
            agent_id: Unique agent identifier
            custom_profile: Optional custom attributes to override defaults
            
        Returns:
            AgentAttributes with all heterogeneous properties
        """
        if custom_profile:
            return HeterogeneousAgentGenerator._generate_from_profile(agent_id, custom_profile)
        
        # Randomly sample from research distributions
        age_group = np.random.choice(
            list(AgeGroup),
            p=[HeterogeneousAgentGenerator.AGE_DISTRIBUTION[ag] for ag in AgeGroup]
        )
        age = HeterogeneousAgentGenerator._sample_age(age_group)
        
        gender = np.random.choice(
            list(Gender),
            p=[HeterogeneousAgentGenerator.GENDER_DISTRIBUTION[g] for g in Gender]
        )
        
        health_status = np.random.choice(
            list(HealthStatus),
            p=[HeterogeneousAgentGenerator.HEALTH_DISTRIBUTION[h] for h in HealthStatus]
        )
        
        disability_type = np.random.choice(
            list(DisabilityType),
            p=[HeterogeneousAgentGenerator.DISABILITY_DISTRIBUTION[d] for d in DisabilityType]
        )
        
        familiarity = np.random.choice(
            list(FamiliarityLevel),
            p=[HeterogeneousAgentGenerator.FAMILIARITY_DISTRIBUTION[f] for f in FamiliarityLevel]
        )
        
        # Generate physiological attributes (research-validated ranges)
        base_speed, max_speed = HeterogeneousAgentGenerator._get_speed_attributes(
            age_group, health_status, disability_type
        )
        
        reaction_time = HeterogeneousAgentGenerator._get_reaction_time(
            age_group, health_status, cognitive_state=CognitiveState.CALM
        )
        
        # Generate psychological attributes
        panic_susceptibility = np.random.beta(2, 5)  # Skewed low (most people don't panic easily)
        risk_tolerance = np.random.beta(3, 4)
        stress_resilience = np.random.beta(4, 3)  # Skewed high
        
        # Generate behavioral attributes
        environment_knowledge = HeterogeneousAgentGenerator._get_environment_knowledge(familiarity)
        leadership_tendency = np.random.beta(2, 8)  # Few leaders
        following_tendency = np.random.beta(5, 3)  # Most follow
        cooperation_level = np.random.beta(4, 2)
        
        # Body dimensions (research-validated)
        body_width = np.random.normal(0.45, 0.05)  # Shoulder width
        body_depth = np.random.normal(0.30, 0.03)  # Body depth
        
        # Physical stamina (age and health dependent)
        physical_stamina = HeterogeneousAgentGenerator._get_stamina(
            age_group, health_status, disability_type
        )
        
        # Initial cognitive state
        cognitive_state = CognitiveState.CALM
        
        return AgentAttributes(
            age_group=age_group,
            age=age,
            gender=gender,
            health_status=health_status,
            disability_type=disability_type,
            base_walking_speed=base_speed,
            max_walking_speed=max_speed,
            reaction_time=reaction_time,
            physical_stamina=physical_stamina,
            body_width=max(0.35, min(0.65, body_width)),  # Clamp to realistic range
            body_depth=max(0.25, min(0.40, body_depth)),
            cognitive_state=cognitive_state,
            panic_susceptibility=panic_susceptibility,
            risk_tolerance=risk_tolerance,
            stress_resilience=stress_resilience,
            familiarity=familiarity,
            environment_knowledge=environment_knowledge,
            leadership_tendency=leadership_tendency,
            following_tendency=following_tendency,
            cooperation_level=cooperation_level
        )
    
    @staticmethod
    def _sample_age(age_group: AgeGroup) -> int:
        """Sample specific age from age group"""
        if age_group == AgeGroup.CHILD:
            return random.randint(5, 12)
        elif age_group == AgeGroup.TEEN:
            return random.randint(13, 17)
        elif age_group == AgeGroup.YOUNG_ADULT:
            return random.randint(18, 35)
        elif age_group == AgeGroup.ADULT:
            return random.randint(36, 55)
        elif age_group == AgeGroup.MIDDLE_AGED:
            return random.randint(56, 70)
        else:  # ELDERLY
            return random.randint(71, 90)
    
    @staticmethod
    def _get_speed_attributes(
        age_group: AgeGroup,
        health_status: HealthStatus,
        disability_type: DisabilityType
    ) -> Tuple[float, float]:
        """Get walking speed based on research-validated distributions"""
        # Base speeds by age (m/s) - from evacuation research
        age_speeds = {
            AgeGroup.CHILD: (1.1, 1.8),
            AgeGroup.TEEN: (1.3, 2.0),
            AgeGroup.YOUNG_ADULT: (1.35, 2.2),
            AgeGroup.ADULT: (1.3, 2.0),
            AgeGroup.MIDDLE_AGED: (1.2, 1.8),
            AgeGroup.ELDERLY: (0.95, 1.5)
        }
        
        base_mean, max_speed = age_speeds[age_group]
        base_speed = np.random.normal(base_mean, 0.25)
        
        # Health adjustments
        if health_status == HealthStatus.SEVERE_INJURY:
            base_speed *= 0.4
            max_speed *= 0.5
        elif health_status == HealthStatus.TEMPORARY_INJURY:
            base_speed *= 0.7
            max_speed *= 0.8
        elif health_status == HealthStatus.PREGNANT:
            base_speed *= 0.85
            max_speed *= 0.9
        
        # Disability adjustments
        if disability_type == DisabilityType.WHEELCHAIR:
            base_speed = np.random.normal(0.7, 0.15)  # Wheelchair speed
            max_speed = 1.0
        elif disability_type == DisabilityType.MOBILITY_IMPAIRED:
            base_speed *= 0.6
            max_speed *= 0.7
        
        return max(0.3, base_speed), max(0.5, max_speed)
    
    @staticmethod
    def _get_reaction_time(
        age_group: AgeGroup,
        health_status: HealthStatus,
        cognitive_state: CognitiveState
    ) -> float:
        """Get reaction time (pre-evacuation decision time) in seconds"""
        # Base reaction times (research: 0.5-5.0s typical, lognormal distribution)
        age_reaction = {
            AgeGroup.CHILD: 2.5,
            AgeGroup.TEEN: 1.8,
            AgeGroup.YOUNG_ADULT: 1.5,
            AgeGroup.ADULT: 2.0,
            AgeGroup.MIDDLE_AGED: 2.8,
            AgeGroup.ELDERLY: 3.5
        }
        
        base_time = age_reaction[age_group]
        
        # Health adjustments
        if health_status == HealthStatus.SEVERE_INJURY:
            base_time *= 1.8
        elif health_status == HealthStatus.CHRONIC_ILLNESS:
            base_time *= 1.3
        
        # Cognitive state adjustments
        if cognitive_state == CognitiveState.SHOCKED:
            base_time *= 2.5
        elif cognitive_state == CognitiveState.DISORIENTED:
            base_time *= 1.8
        elif cognitive_state == CognitiveState.PANICKED:
            base_time *= 1.5  # Panic can cause faster or slower decisions
        
        # Add lognormal noise
        mu = np.log(base_time**2 / np.sqrt(1.2**2 + base_time**2))
        sigma = np.sqrt(np.log(1 + 1.2**2 / base_time**2))
        reaction_time = np.random.lognormal(mu, sigma)
        
        return np.clip(reaction_time, 0.1, 30.0)
    
    @staticmethod
    def _get_environment_knowledge(familiarity: FamiliarityLevel) -> float:
        """Get environment knowledge based on familiarity"""
        knowledge_map = {
            FamiliarityLevel.UNFAMILIAR: 0.2,
            FamiliarityLevel.SOMEWHAT_FAMILIAR: 0.5,
            FamiliarityLevel.FAMILIAR: 0.75,
            FamiliarityLevel.VERY_FAMILIAR: 0.95
        }
        base = knowledge_map[familiarity]
        # Add some variation
        return np.clip(np.random.normal(base, 0.15), 0.0, 1.0)
    
    @staticmethod
    def _get_stamina(
        age_group: AgeGroup,
        health_status: HealthStatus,
        disability_type: DisabilityType
    ) -> float:
        """Get physical stamina (0-1)"""
        base_stamina = {
            AgeGroup.CHILD: 0.7,  # High energy but smaller
            AgeGroup.TEEN: 0.9,
            AgeGroup.YOUNG_ADULT: 0.95,
            AgeGroup.ADULT: 0.85,
            AgeGroup.MIDDLE_AGED: 0.70,
            AgeGroup.ELDERLY: 0.50
        }
        
        stamina = base_stamina[age_group]
        
        # Health adjustments
        if health_status == HealthStatus.SEVERE_INJURY:
            stamina *= 0.3
        elif health_status == HealthStatus.CHRONIC_ILLNESS:
            stamina *= 0.7
        elif health_status == HealthStatus.PREGNANT:
            stamina *= 0.8
        
        # Disability adjustments
        if disability_type == DisabilityType.WHEELCHAIR:
            stamina *= 0.8  # Wheelchair users have good upper body stamina
        elif disability_type == DisabilityType.MOBILITY_IMPAIRED:
            stamina *= 0.5
        
        return np.clip(stamina + np.random.normal(0, 0.1), 0.1, 1.0)
    
    @staticmethod
    def _generate_from_profile(agent_id: int, profile: Dict) -> AgentAttributes:
        """Generate agent from custom profile"""
        # This would parse a custom profile and create attributes
        # For now, use defaults with overrides
        attrs = HeterogeneousAgentGenerator.generate_agent(agent_id)
        
        # Apply custom overrides
        for key, value in profile.items():
            if hasattr(attrs, key):
                setattr(attrs, key, value)
        
        return attrs

# Global generator instance
agent_generator = HeterogeneousAgentGenerator()

