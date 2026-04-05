"""
Data-Driven Human Behavior Modeling
Validated behavioral models from evacuation research
"""

import numpy as np
import math
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from app.services.evacuation_parameters import (
    parameter_database, PopulationProfile
)

logger = logging.getLogger(__name__)

class DecisionModel(Enum):
    """Decision-making models"""
    SHORTEST_PATH = "shortest_path"
    BOUNDED_RATIONALITY = "bounded_rationality"
    BAYESIAN_NASH = "bayesian_nash"
    SOCIAL_INFLUENCE = "social_influence"

@dataclass
class AgentBehavior:
    """Agent behavioral state"""
    profile: PopulationProfile
    decision_model: DecisionModel
    pre_evacuation_delay: float
    walking_speed: float
    panic_level: float
    stress_level: float
    cognitive_load: float
    social_influence: float
    bounded_rationality_factor: float

class BehavioralModelEngine:
    """Engine for data-driven behavioral modeling"""
    
    def __init__(self):
        self.parameter_db = parameter_database
    
    def initialize_agent_behavior(
        self,
        agent_id: int,
        profile: PopulationProfile = None
    ) -> AgentBehavior:
        """Initialize agent with research-validated behavior"""
        if profile is None:
            # Randomly assign profile based on typical distribution
            profiles = [
                PopulationProfile.NORMAL_ADULT,
                PopulationProfile.ELDERLY,
                PopulationProfile.INJURED,
                PopulationProfile.CHILD,
                PopulationProfile.DISABLED
            ]
            weights = [0.7, 0.15, 0.05, 0.05, 0.05]  # Typical distribution
            profile = np.random.choice(profiles, p=weights)
        
        # Get pre-evacuation delay
        delay = self.parameter_db.get_pre_evacuation_delay(profile)
        
        # Initialize panic and stress
        panic_level = np.random.uniform(0.1, 0.4)  # Initial panic
        stress_level = np.random.uniform(0.0, 0.3)  # Initial stress
        
        # Get walking speed
        walking_speed = self.parameter_db.get_walking_speed(profile, panic_level)
        
        # Decision model (most agents use bounded rationality)
        decision_models = [
            DecisionModel.SHORTEST_PATH,
            DecisionModel.BOUNDED_RATIONALITY,
            DecisionModel.BAYESIAN_NASH,
            DecisionModel.SOCIAL_INFLUENCE
        ]
        weights = [0.2, 0.5, 0.2, 0.1]  # Bounded rationality most common
        decision_model = np.random.choice(decision_models, p=weights)
        
        return AgentBehavior(
            profile=profile,
            decision_model=decision_model,
            pre_evacuation_delay=delay,
            walking_speed=walking_speed,
            panic_level=panic_level,
            stress_level=stress_level,
            cognitive_load=0.0,
            social_influence=np.random.uniform(0.0, 0.5),
            bounded_rationality_factor=np.random.uniform(0.6, 0.9)
        )
    
    def choose_exit(
        self,
        behavior: AgentBehavior,
        agent_position: Tuple[float, float, float],
        exits: List[Dict],
        nearby_agents: List[Dict],
        current_time: float
    ) -> str:
        """
        Choose exit using behavioral decision model
        
        Implements:
        - Shortest path (naive)
        - Bounded rationality (considers congestion)
        - Bayesian Nash (strategic choice)
        - Social influence (follows others)
        """
        if behavior.decision_model == DecisionModel.SHORTEST_PATH:
            return self._shortest_path_choice(agent_position, exits)
        
        elif behavior.decision_model == DecisionModel.BOUNDED_RATIONALITY:
            return self._bounded_rationality_choice(
                behavior, agent_position, exits, nearby_agents
            )
        
        elif behavior.decision_model == DecisionModel.BAYESIAN_NASH:
            return self._bayesian_nash_choice(
                behavior, agent_position, exits, nearby_agents
            )
        
        elif behavior.decision_model == DecisionModel.SOCIAL_INFLUENCE:
            return self._social_influence_choice(
                behavior, agent_position, exits, nearby_agents
            )
        
        else:
            return self._shortest_path_choice(agent_position, exits)
    
    def _shortest_path_choice(
        self,
        position: Tuple[float, float, float],
        exits: List[Dict]
    ) -> str:
        """Naive shortest path choice"""
        min_distance = float('inf')
        chosen_exit = exits[0].get("id") if exits else None
        
        for exit in exits:
            exit_pos = (exit.get("x", 0), exit.get("y", 0), exit.get("z", exit.get("y", 0)))
            distance = math.sqrt(
                (position[0] - exit_pos[0])**2 +
                (position[2] - exit_pos[2])**2
            )
            if distance < min_distance:
                min_distance = distance
                chosen_exit = exit.get("id")
        
        return chosen_exit
    
    def _bounded_rationality_choice(
        self,
        behavior: AgentBehavior,
        position: Tuple[float, float, float],
        exits: List[Dict],
        nearby_agents: List[Dict]
    ) -> str:
        """
        Bounded rationality: considers distance and perceived congestion
        Agents don't have perfect information and make satisficing decisions
        """
        best_score = -float('inf')
        chosen_exit = exits[0].get("id") if exits else None
        
        for exit in exits:
            exit_pos = (exit.get("x", 0), exit.get("y", 0), exit.get("z", exit.get("y", 0)))
            distance = math.sqrt(
                (position[0] - exit_pos[0])**2 +
                (position[2] - exit_pos[2])**2
            )
            
            # Count agents near exit (perceived congestion)
            agents_near_exit = sum(
                1 for a in nearby_agents
                if math.sqrt(
                    (a.get("x", 0) - exit_pos[0])**2 +
                    (a.get("z", a.get("y", 0)) - exit_pos[2])**2
                ) < 10.0
            )
            
            # Calculate utilization
            exit_width = exit.get("width", 2.0)
            flow_capacity = self.parameter_db.get_flow_capacity(exit_width)
            utilization = min(1.0, agents_near_exit / (flow_capacity * 10))  # 10 second window
            
            # Bounded rationality: weight distance and congestion
            # Higher stress reduces rationality
            rationality = behavior.bounded_rationality_factor * (1 - behavior.stress_level)
            
            # Score: distance (negative) + congestion penalty (negative)
            distance_score = -distance / 100.0  # Normalize
            congestion_penalty = -utilization * (1 - rationality) * 2.0
            
            score = distance_score + congestion_penalty
            
            if score > best_score:
                best_score = score
                chosen_exit = exit.get("id")
        
        return chosen_exit
    
    def _bayesian_nash_choice(
        self,
        behavior: AgentBehavior,
        position: Tuple[float, float, float],
        exits: List[Dict],
        nearby_agents: List[Dict]
    ) -> str:
        """
        Bayesian Nash: Strategic choice considering what others will do
        Agents predict future congestion and choose accordingly
        """
        # Predict future exit utilization
        exit_predictions = {}
        
        for exit in exits:
            exit_pos = (exit.get("x", 0), exit.get("y", 0), exit.get("z", exit.get("y", 0)))
            
            # Count agents heading to this exit
            agents_heading_here = sum(
                1 for a in nearby_agents
                if a.get("target_exit") == exit.get("id")
            )
            
            # Predict future congestion
            exit_width = exit.get("width", 2.0)
            flow_capacity = self.parameter_db.get_flow_capacity(exit_width)
            predicted_utilization = min(1.0, agents_heading_here / (flow_capacity * 15))
            
            exit_predictions[exit.get("id")] = predicted_utilization
        
        # Choose exit with best predicted outcome
        best_score = -float('inf')
        chosen_exit = exits[0].get("id") if exits else None
        
        for exit in exits:
            exit_pos = (exit.get("x", 0), exit.get("y", 0), exit.get("z", exit.get("y", 0)))
            distance = math.sqrt(
                (position[0] - exit_pos[0])**2 +
                (position[2] - exit_pos[2])**2
            )
            
            predicted_utilization = exit_predictions.get(exit.get("id"), 0.5)
            
            # Score: distance + predicted congestion
            distance_score = -distance / 100.0
            congestion_penalty = -predicted_utilization * 1.5
            
            score = distance_score + congestion_penalty
            
            if score > best_score:
                best_score = score
                chosen_exit = exit.get("id")
        
        return chosen_exit
    
    def _social_influence_choice(
        self,
        behavior: AgentBehavior,
        position: Tuple[float, float, float],
        exits: List[Dict],
        nearby_agents: List[Dict]
    ) -> str:
        """
        Social influence: Follow nearby agents or leaders
        Implements herd behavior and leader following
        """
        # Check if should follow leader
        if self.parameter_db.should_follow_leader():
            # Find nearest agent with high social influence (leader)
            leaders = [
                a for a in nearby_agents
                if a.get("personality") == "leader" or a.get("social_influence", 0) > 0.7
            ]
            
            if leaders:
                # Follow nearest leader
                nearest_leader = min(
                    leaders,
                    key=lambda a: math.sqrt(
                        (a.get("x", 0) - position[0])**2 +
                        (a.get("z", a.get("y", 0)) - position[2])**2
                    )
                )
                return nearest_leader.get("target_exit", exits[0].get("id") if exits else None)
        
        # Otherwise, follow majority (herd behavior)
        exit_counts = {}
        for agent in nearby_agents:
            exit_id = agent.get("target_exit")
            if exit_id:
                exit_counts[exit_id] = exit_counts.get(exit_id, 0) + 1
        
        if exit_counts:
            # Choose most popular exit
            chosen_exit = max(exit_counts.items(), key=lambda x: x[1])[0]
            return chosen_exit
        
        # Fallback to shortest path
        return self._shortest_path_choice(position, exits)
    
    def update_behavior(
        self,
        behavior: AgentBehavior,
        nearby_panic: float = 0.0,
        congestion_level: float = 0.0,
        time_in_simulation: float = 0.0,
        disaster_proximity: float = 0.0,
    ) -> AgentBehavior:
        """Update behavior based on social panic, congestion, and nearby hazard pressure."""
        nearby_panic = max(0.0, min(1.0, float(nearby_panic)))
        disaster_proximity = max(0.0, min(1.0, float(disaster_proximity)))
        congestion_level = max(0.0, float(congestion_level))

        # Panic propagation (S -> I model)
        contagion_rate = self.parameter_db.get_panic_contagion_rate()

        # Combine social contagion with direct hazard pressure so fire/smoke proximity
        # can elevate panic even when nearby agents are still calm.
        effective_panic_signal = max(nearby_panic, disaster_proximity * 0.85)

        # ds = contagion_rate * panic_signal * (1 - current_panic)
        panic_increase = contagion_rate * effective_panic_signal * (1.0 - behavior.panic_level)
        behavior.panic_level = min(1.0, behavior.panic_level + panic_increase)

        # Congestion increases stress steadily; nearby hazards add sharper urgency.
        stress_increase = congestion_level * 0.05 + disaster_proximity * 0.08
        if time_in_simulation > behavior.pre_evacuation_delay:
            stress_increase += disaster_proximity * 0.02
        behavior.stress_level = min(1.0, behavior.stress_level + stress_increase)

        # Update cognitive load (higher under stress and prolonged exposure)
        time_pressure = min(0.2, max(0.0, float(time_in_simulation)) / 900.0)
        behavior.cognitive_load = min(1.0, behavior.stress_level * 0.8 + time_pressure)

        # Update walking speed based on panic
        behavior.walking_speed = self.parameter_db.get_walking_speed(
            behavior.profile, behavior.panic_level
        )

        # Reduce bounded rationality under stress
        behavior.bounded_rationality_factor = max(
            0.3, behavior.bounded_rationality_factor - behavior.stress_level * 0.2
        )
        
        return behavior

# Global instance
behavioral_engine = BehavioralModelEngine()

