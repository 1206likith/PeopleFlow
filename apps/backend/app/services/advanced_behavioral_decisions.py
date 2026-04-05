"""
Advanced Behavioral Decision Models
Research-backed decision-making for evacuation agents
Implements pre-evacuation timing, route choice under uncertainty, leader influence, social influence
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from app.services.heterogeneous_agents import AgentAttributes, CognitiveState

logger = logging.getLogger(__name__)

class DecisionType(Enum):
    """Types of decisions agents make"""
    PRE_EVACUATION_TIMING = "pre_evacuation_timing"
    ROUTE_CHOICE = "route_choice"
    EXIT_CHOICE = "exit_choice"
    SPEED_ADJUSTMENT = "speed_adjustment"
    GROUP_COHESION = "group_cohesion"

@dataclass
class DecisionContext:
    """Context for decision-making"""
    agent_attributes: AgentAttributes
    current_position: Tuple[float, float, float]
    available_exits: List[Dict]
    nearby_agents: List[Dict]
    hazard_proximity: float  # 0-1, distance to nearest hazard
    local_density: float  # persons/m²
    visibility: float  # 0-1, affected by smoke/fog
    time_elapsed: float  # seconds since alarm
    leader_available: Optional[Dict] = None
    group_members: List[Dict] = None

class PreEvacuationDecisionModel:
    """
    Pre-evacuation decision timing model
    Based on risk perception, neighbor influence, and personal tolerance
    Research: Pre-evacuation delay studies (PubMed)
    """
    
    @staticmethod
    def calculate_pre_evacuation_delay(
        agent_attrs: AgentAttributes,
        risk_perception: float,
        neighbor_influence: float,
        personal_tolerance: float
    ) -> float:
        """
        Calculate pre-evacuation delay based on research models
        
        Args:
            agent_attrs: Agent attributes
            risk_perception: 0-1, perceived risk level
            neighbor_influence: 0-1, influence from neighbors' actions
            personal_tolerance: 0-1, personal risk tolerance
        
        Returns:
            Delay in seconds before starting evacuation
        """
        # Base reaction time from agent attributes
        base_delay = agent_attrs.reaction_time
        
        # Risk perception effect (higher risk perception = faster reaction)
        risk_factor = 1.0 - (risk_perception * 0.4)  # Up to 40% reduction
        
        # Neighbor influence (if neighbors evacuate, agent follows faster)
        neighbor_factor = 1.0 - (neighbor_influence * 0.3)  # Up to 30% reduction
        
        # Personal tolerance (higher tolerance = slower reaction)
        tolerance_factor = 1.0 + (personal_tolerance * 0.5)  # Up to 50% increase
        
        # Cognitive state effects
        cognitive_factor = 1.0
        if agent_attrs.cognitive_state == CognitiveState.SHOCKED:
            cognitive_factor = 2.5
        elif agent_attrs.cognitive_state == CognitiveState.DISORIENTED:
            cognitive_factor = 1.8
        elif agent_attrs.cognitive_state == CognitiveState.PANICKED:
            cognitive_factor = 0.7  # Panic can cause faster (but less rational) decisions
        
        # Familiarity effect (familiar agents react faster)
        familiarity_factor = 1.0 - (agent_attrs.environment_knowledge * 0.2)
        
        # Calculate final delay
        delay = base_delay * risk_factor * neighbor_factor * tolerance_factor * cognitive_factor * familiarity_factor
        
        # Add lognormal noise (research shows lognormal distribution)
        mu = np.log(delay**2 / np.sqrt(0.5**2 + delay**2))
        sigma = np.sqrt(np.log(1 + 0.5**2 / delay**2))
        noisy_delay = np.random.lognormal(mu, sigma)
        
        return np.clip(noisy_delay, 0.1, 30.0)
    
    @staticmethod
    def update_risk_perception(
        current_perception: float,
        hazard_proximity: float,
        neighbor_actions: List[str],  # "evacuating", "waiting", "panicking"
        time_elapsed: float
    ) -> float:
        """
        Update risk perception based on environment and social cues
        
        Research: Risk perception evolves with information
        """
        # Hazard proximity directly increases risk perception
        hazard_effect = hazard_proximity * 0.6
        
        # Social influence: if many neighbors are evacuating, risk perception increases
        evacuating_count = sum(1 for action in neighbor_actions if action == "evacuating")
        total_neighbors = len(neighbor_actions) if neighbor_actions else 1
        social_effect = (evacuating_count / total_neighbors) * 0.4
        
        # Time effect: risk perception increases over time if hazard persists
        time_effect = min(0.3, time_elapsed / 60.0)  # Max 30% after 60 seconds
        
        new_perception = current_perception * 0.7 + hazard_effect + social_effect + time_effect
        
        return np.clip(new_perception, 0.0, 1.0)

class RouteChoiceDecisionModel:
    """
    Route choice decision under uncertainty
    Influenced by local density, visibility, and panic
    Research: Route choice models in evacuation (ScienceDirect)
    """
    
    @staticmethod
    def choose_route(
        context: DecisionContext,
        available_routes: List[Dict]
    ) -> Dict:
        """
        Choose route using Bayesian decision model
        
        Routes should have: distance, expected_density, visibility, safety_score
        """
        if not available_routes:
            return None
        
        agent_attrs = context.agent_attributes
        
        # Calculate utility for each route
        route_utilities = []
        for route in available_routes:
            utility = RouteChoiceDecisionModel._calculate_route_utility(
                route, context, agent_attrs
            )
            route_utilities.append((route, utility))
        
        # Sort by utility (highest first)
        route_utilities.sort(key=lambda x: x[1], reverse=True)
        
        # Bounded rationality: choose from top N routes with some randomness
        # Higher stress = less rational (more random)
        rationality = agent_attrs.stress_resilience * (1.0 - context.agent_attributes.current_stress_level)
        top_n = max(1, int(len(route_utilities) * (0.3 + rationality * 0.5)))
        
        top_routes = route_utilities[:top_n]
        
        # Softmax selection (allows some exploration)
        if len(top_routes) > 1 and rationality > 0.3:
            # Softmax with temperature based on rationality
            temperature = 1.0 / (rationality + 0.1)
            utilities = [u for _, u in top_routes]
            exp_utilities = np.exp(np.array(utilities) / temperature)
            probs = exp_utilities / exp_utilities.sum()
            selected_idx = np.random.choice(len(top_routes), p=probs)
            return top_routes[selected_idx][0]
        else:
            # Greedy selection (high stress = less exploration)
            return top_routes[0][0]
    
    @staticmethod
    def _calculate_route_utility(
        route: Dict,
        context: DecisionContext,
        agent_attrs: AgentAttributes
    ) -> float:
        """Calculate utility of a route using multi-factor model"""
        distance = route.get("distance", float('inf'))
        expected_density = route.get("expected_density", 0.0)
        visibility = route.get("visibility", 1.0)
        safety_score = route.get("safety_score", 1.0)
        
        # Distance utility (negative, prefer shorter)
        distance_utility = -distance / 100.0  # Normalize
        
        # Density penalty (negative, prefer less crowded)
        # Higher density = lower utility, effect increases with panic
        density_penalty = -expected_density * (1.0 + agent_attrs.current_panic_level * 2.0)
        
        # Visibility utility (positive, prefer visible routes)
        # More important for visually impaired agents
        visibility_weight = 1.0
        if agent_attrs.disability_type.value == "visually_impaired":
            visibility_weight = 3.0
        visibility_utility = visibility * visibility_weight
        
        # Safety utility (positive, prefer safer routes)
        safety_utility = safety_score * 2.0
        
        # Familiarity bonus (familiar agents prefer known routes)
        familiarity_bonus = 0.0
        if route.get("is_familiar", False):
            familiarity_bonus = agent_attrs.environment_knowledge * 0.5
        
        # Risk tolerance effect (risk-tolerant agents care less about safety)
        risk_adjustment = 1.0 - (agent_attrs.risk_tolerance * 0.5)
        safety_utility *= risk_adjustment
        
        total_utility = distance_utility + density_penalty + visibility_utility + safety_utility + familiarity_bonus
        
        return total_utility

class LeaderInfluenceModel:
    """
    Leader/guide influence model
    Static or dynamic guides improve overall efficiency
    Research: Leader influence in evacuation (MDPI)
    """
    
    @staticmethod
    def calculate_leader_influence(
        agent_attrs: AgentAttributes,
        leader: Dict,
        distance_to_leader: float,
        leader_credibility: float = 0.8
    ) -> Tuple[float, Optional[Dict]]:
        """
        Calculate influence of leader on agent's decision
        
        Returns:
            (influence_strength, suggested_action)
            influence_strength: 0-1, how much agent follows leader
            suggested_action: Action suggested by leader (exit choice, route, etc.)
        """
        if not leader:
            return 0.0, None
        
        # Base influence from agent's following tendency
        base_influence = agent_attrs.following_tendency
        
        # Distance decay (closer = more influence)
        max_influence_distance = 10.0  # meters
        distance_factor = max(0.0, 1.0 - (distance_to_leader / max_influence_distance))
        
        # Leader credibility
        credibility_factor = leader_credibility
        
        # Cognitive state effect (panicked agents follow more)
        cognitive_factor = 1.0
        if agent_attrs.cognitive_state == CognitiveState.PANICKED:
            cognitive_factor = 1.5
        elif agent_attrs.cognitive_state == CognitiveState.DISORIENTED:
            cognitive_factor = 1.3
        
        # Calculate total influence
        influence = base_influence * distance_factor * credibility_factor * cognitive_factor
        
        # Get leader's suggested action
        suggested_action = leader.get("suggested_exit") or leader.get("target_exit")
        
        return np.clip(influence, 0.0, 1.0), suggested_action
    
    @staticmethod
    def should_follow_leader(
        agent_attrs: AgentAttributes,
        leader_influence: float,
        own_decision_confidence: float
    ) -> bool:
        """Determine if agent should follow leader instead of own decision"""
        # Follow if leader influence is strong and own confidence is low
        threshold = 0.6 - (own_decision_confidence * 0.3)
        return leader_influence > threshold

class SocialInfluenceModel:
    """
    Social influence & herd movement model
    Fallback behaviors when exposed to panic
    Research: Social influence in evacuation (ScienceDirect)
    """
    
    @staticmethod
    def calculate_social_influence(
        agent_attrs: AgentAttributes,
        nearby_agents: List[Dict],
        influence_radius: float = 5.0
    ) -> Dict[str, float]:
        """
        Calculate social influence from nearby agents
        
        Returns:
            Dictionary with influence metrics:
            - herd_direction: Most common movement direction
            - panic_contagion: Panic level from neighbors
            - crowd_pressure: Pressure to follow majority
        """
        if not nearby_agents:
            return {
                "herd_direction": None,
                "panic_contagion": 0.0,
                "crowd_pressure": 0.0
            }
        
        # Calculate panic contagion (SIS model)
        panicked_count = sum(1 for a in nearby_agents if a.get("panic_level", 0) > 0.6)
        total_nearby = len(nearby_agents)
        panic_contagion = (panicked_count / total_nearby) * agent_attrs.panic_susceptibility
        
        # Calculate herd direction (most common exit choice)
        exit_choices = {}
        for agent in nearby_agents:
            exit_id = agent.get("target_exit")
            if exit_id:
                exit_choices[exit_id] = exit_choices.get(exit_id, 0) + 1
        
        herd_exit = max(exit_choices.items(), key=lambda x: x[1])[0] if exit_choices else None
        
        # Calculate crowd pressure (pressure to follow majority)
        if herd_exit:
            majority_fraction = exit_choices[herd_exit] / total_nearby
            crowd_pressure = majority_fraction * agent_attrs.following_tendency
        else:
            crowd_pressure = 0.0
        
        return {
            "herd_direction": herd_exit,
            "panic_contagion": np.clip(panic_contagion, 0.0, 1.0),
            "crowd_pressure": np.clip(crowd_pressure, 0.0, 1.0)
        }
    
    @staticmethod
    def apply_social_influence(
        agent_attrs: AgentAttributes,
        social_metrics: Dict[str, float],
        current_decision: str
    ) -> str:
        """
        Apply social influence to agent's decision
        
        Returns:
            Modified decision (may change exit choice due to herd behavior)
        """
        herd_exit = social_metrics.get("herd_direction")
        crowd_pressure = social_metrics.get("crowd_pressure", 0.0)
        panic_contagion = social_metrics.get("panic_contagion", 0.0)
        
        # Higher panic = more likely to follow herd
        follow_probability = crowd_pressure * (1.0 + panic_contagion * 0.5)
        
        # Leaders are less influenced
        if agent_attrs.is_leader:
            follow_probability *= 0.3
        
        # Decide whether to follow herd
        if herd_exit and np.random.random() < follow_probability:
            return herd_exit
        
        return current_decision

class BayesianDecisionEngine:
    """
    Bayesian decision engine for evacuation decisions
    Combines multiple information sources with uncertainty
    """
    
    def __init__(self):
        self.pre_evac_model = PreEvacuationDecisionModel()
        self.route_model = RouteChoiceDecisionModel()
        self.leader_model = LeaderInfluenceModel()
        self.social_model = SocialInfluenceModel()
    
    def make_pre_evacuation_decision(
        self,
        agent_attrs: AgentAttributes,
        context: DecisionContext
    ) -> float:
        """Make pre-evacuation timing decision"""
        # Calculate risk perception
        neighbor_actions = [a.get("status", "waiting") for a in context.nearby_agents]
        risk_perception = self.pre_evac_model.update_risk_perception(
            agent_attrs.current_stress_level,
            context.hazard_proximity,
            neighbor_actions,
            context.time_elapsed
        )
        
        # Calculate delay
        delay = self.pre_evac_model.calculate_pre_evacuation_delay(
            agent_attrs,
            risk_perception,
            context.local_density,  # Used as neighbor influence proxy
            agent_attrs.risk_tolerance
        )
        
        return delay
    
    def make_route_choice_decision(
        self,
        context: DecisionContext,
        available_routes: List[Dict]
    ) -> Dict:
        """Make route choice decision"""
        # Check for leader influence
        if context.leader_available:
            leader_influence, suggested_route = self.leader_model.calculate_leader_influence(
                context.agent_attributes,
                context.leader_available,
                math.sqrt(
                    (context.current_position[0] - context.leader_available.get("x", 0))**2 +
                    (context.current_position[2] - context.leader_available.get("z", 0))**2
                )
            )
            
            if self.leader_model.should_follow_leader(
                context.agent_attributes,
                leader_influence,
                context.agent_attributes.decision_confidence
            ) and suggested_route:
                # Find route matching leader's suggestion
                for route in available_routes:
                    if route.get("exit_id") == suggested_route:
                        return route
        
        # Calculate social influence
        social_metrics = self.social_model.calculate_social_influence(
            context.agent_attributes,
            context.nearby_agents
        )
        
        # Make route choice
        chosen_route = self.route_model.choose_route(context, available_routes)
        
        # Apply social influence
        if chosen_route and social_metrics.get("herd_direction"):
            herd_exit = social_metrics["herd_direction"]
            if chosen_route.get("exit_id") != herd_exit:
                # Check if should follow herd
                modified_decision = self.social_model.apply_social_influence(
                    context.agent_attributes,
                    social_metrics,
                    chosen_route.get("exit_id")
                )
                # Find route matching herd direction
                for route in available_routes:
                    if route.get("exit_id") == modified_decision:
                        return route
        
        return chosen_route

# Global decision engine instance
decision_engine = BayesianDecisionEngine()

