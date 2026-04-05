"""
Survival Score Engine
Calculates building safety score based on multiple risk factors
"""

from typing import Dict, List
from dataclasses import dataclass
import math
import logging

logger = logging.getLogger(__name__)

@dataclass
class SurvivalScore:
    """Overall survival score and breakdown"""
    total_score: float  # 0-100
    grade: str  # "A" (90+), "B" (70-89), "C" (50-69), "D" (<50)
    evacuation_time_score: float
    exit_capacity_score: float
    bottleneck_score: float
    disaster_resilience_score: float
    accessibility_score: float
    factors: List[str]  # Positive and negative factors
    recommendations: List[str]

class SurvivalScoreEngine:
    """Calculates survival score for building/simulation"""
    
    def __init__(self):
        # Weight factors for different components
        self.weights = {
            "evacuation_time": 0.25,
            "exit_capacity": 0.25,
            "bottleneck": 0.20,
            "disaster_resilience": 0.15,
            "accessibility": 0.15
        }
    
    def calculate_score(
        self,
        simulation_data: Dict,
        agents: List[Dict],
        exits: List[Dict],
        bottlenecks: List[Dict],
        disaster_type: str = "fire"
    ) -> SurvivalScore:
        """
        Calculate overall survival score
        
        Args:
            simulation_data: Simulation metadata
            agents: List of agents
            exits: List of exits
            bottlenecks: List of bottlenecks
            disaster_type: Type of disaster
        
        Returns:
            SurvivalScore object
        """
        # Calculate component scores
        evacuation_time_score = self._calculate_evacuation_time_score(agents, simulation_data)
        exit_capacity_score = self._calculate_exit_capacity_score(agents, exits)
        bottleneck_score = self._calculate_bottleneck_score(bottlenecks, agents)
        disaster_resilience_score = self._calculate_disaster_resilience_score(disaster_type, exits)
        accessibility_score = self._calculate_accessibility_score(agents, exits)
        
        # Weighted total
        total_score = (
            evacuation_time_score * self.weights["evacuation_time"] +
            exit_capacity_score * self.weights["exit_capacity"] +
            bottleneck_score * self.weights["bottleneck"] +
            disaster_resilience_score * self.weights["disaster_resilience"] +
            accessibility_score * self.weights["accessibility"]
        )
        
        # Determine grade
        if total_score >= 90:
            grade = "A"
        elif total_score >= 70:
            grade = "B"
        elif total_score >= 50:
            grade = "C"
        else:
            grade = "D"
        
        # Generate factors and recommendations
        factors = self._identify_factors(
            evacuation_time_score, exit_capacity_score, bottleneck_score,
            disaster_resilience_score, accessibility_score
        )
        recommendations = self._generate_recommendations(
            total_score, evacuation_time_score, exit_capacity_score,
            bottleneck_score, disaster_resilience_score, accessibility_score,
            exits, bottlenecks
        )
        
        return SurvivalScore(
            total_score=round(total_score, 1),
            grade=grade,
            evacuation_time_score=round(evacuation_time_score, 1),
            exit_capacity_score=round(exit_capacity_score, 1),
            bottleneck_score=round(bottleneck_score, 1),
            disaster_resilience_score=round(disaster_resilience_score, 1),
            accessibility_score=round(accessibility_score, 1),
            factors=factors,
            recommendations=recommendations
        )
    
    def _calculate_evacuation_time_score(self, agents: List[Dict], simulation_data: Dict) -> float:
        """Score based on evacuation time (lower is better, but normalized)"""
        total_agents = len(agents)
        if total_agents == 0:
            return 100.0
        
        # Ideal evacuation time: 2 minutes per 100 agents
        ideal_time = (total_agents / 100) * 120  # seconds
        actual_time = simulation_data.get("total_time", ideal_time * 2)
        
        if actual_time <= ideal_time:
            return 100.0
        elif actual_time <= ideal_time * 1.5:
            return 80.0
        elif actual_time <= ideal_time * 2:
            return 60.0
        elif actual_time <= ideal_time * 3:
            return 40.0
        else:
            return 20.0
    
    def _calculate_exit_capacity_score(self, agents: List[Dict], exits: List[Dict]) -> float:
        """Score based on exit capacity adequacy"""
        if not exits:
            return 0.0
        
        total_agents = len([a for a in agents if a.get("status") != "evacuated"])
        total_capacity = sum(e.get("capacity", 100) for e in exits)
        
        if total_capacity == 0:
            return 0.0
        
        capacity_ratio = total_agents / total_capacity
        
        if capacity_ratio <= 0.5:
            return 100.0
        elif capacity_ratio <= 0.75:
            return 80.0
        elif capacity_ratio <= 1.0:
            return 60.0
        elif capacity_ratio <= 1.5:
            return 40.0
        else:
            return 20.0
    
    def _calculate_bottleneck_score(self, bottlenecks: List[Dict], agents: List[Dict]) -> float:
        """Score based on bottleneck severity"""
        if not bottlenecks:
            return 100.0
        
        total_agents = len([a for a in agents if a.get("status") != "evacuated"])
        if total_agents == 0:
            return 100.0
        
        # Count agents in bottlenecks
        agents_in_bottlenecks = 0
        for bottleneck in bottlenecks:
            bottleneck_pos = (bottleneck.get("x", 0), bottleneck.get("y", 0), bottleneck.get("z", 0))
            for agent in agents:
                if agent.get("status") == "evacuated":
                    continue
                agent_pos = (agent.get("x", 0), agent.get("y", 0), agent.get("z", agent.get("y", 0)))
                distance = math.sqrt(
                    (agent_pos[0] - bottleneck_pos[0])**2 +
                    (agent_pos[2] - bottleneck_pos[2])**2
                )
                if distance < 5.0:  # Within 5 meters
                    agents_in_bottlenecks += 1
        
        bottleneck_ratio = agents_in_bottlenecks / total_agents
        
        if bottleneck_ratio <= 0.1:
            return 100.0
        elif bottleneck_ratio <= 0.2:
            return 80.0
        elif bottleneck_ratio <= 0.3:
            return 60.0
        elif bottleneck_ratio <= 0.5:
            return 40.0
        else:
            return 20.0
    
    def _calculate_disaster_resilience_score(self, disaster_type: str, exits: List[Dict]) -> float:
        """Score based on disaster type and building resilience"""
        base_score = 80.0
        
        # Adjust based on disaster type
        disaster_penalties = {
            "fire": 10.0,
            "earthquake": 15.0,
            "flood": 20.0,
            "bomb_blast": 25.0,
            "gas_leak": 15.0
        }
        
        penalty = disaster_penalties.get(disaster_type, 10.0)
        score = base_score - penalty
        
        # Bonus for multiple exits
        if len(exits) >= 4:
            score += 10.0
        elif len(exits) >= 2:
            score += 5.0
        
        return max(0.0, min(100.0, score))
    
    def _calculate_accessibility_score(self, agents: List[Dict], exits: List[Dict]) -> float:
        """Score based on accessibility (distance to exits)"""
        if not exits or not agents:
            return 50.0
        
        total_distance = 0.0
        count = 0
        
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            agent_pos = (agent.get("x", 0), agent.get("z", agent.get("y", 0)))
            
            # Find nearest exit
            min_distance = float('inf')
            for exit in exits:
                exit_pos = (exit.get("x", 0), exit.get("z", exit.get("y", 0)))
                distance = math.sqrt(
                    (agent_pos[0] - exit_pos[0])**2 +
                    (agent_pos[1] - exit_pos[1])**2
                )
                min_distance = min(min_distance, distance)
            
            total_distance += min_distance
            count += 1
        
        if count == 0:
            return 50.0
        
        avg_distance = total_distance / count
        
        # Score based on average distance (closer is better)
        if avg_distance <= 20.0:
            return 100.0
        elif avg_distance <= 30.0:
            return 80.0
        elif avg_distance <= 40.0:
            return 60.0
        elif avg_distance <= 50.0:
            return 40.0
        else:
            return 20.0
    
    def _identify_factors(
        self,
        evacuation_time_score: float,
        exit_capacity_score: float,
        bottleneck_score: float,
        disaster_resilience_score: float,
        accessibility_score: float
    ) -> List[str]:
        """Identify positive and negative factors"""
        factors = []
        
        if evacuation_time_score >= 80:
            factors.append("✓ Fast evacuation time")
        elif evacuation_time_score < 50:
            factors.append("✗ Slow evacuation time")
        
        if exit_capacity_score >= 80:
            factors.append("✓ Adequate exit capacity")
        elif exit_capacity_score < 50:
            factors.append("✗ Insufficient exit capacity")
        
        if bottleneck_score >= 80:
            factors.append("✓ Minimal bottlenecks")
        elif bottleneck_score < 50:
            factors.append("✗ Severe bottlenecks detected")
        
        if disaster_resilience_score >= 80:
            factors.append("✓ Good disaster resilience")
        elif disaster_resilience_score < 50:
            factors.append("✗ Poor disaster resilience")
        
        if accessibility_score >= 80:
            factors.append("✓ Good exit accessibility")
        elif accessibility_score < 50:
            factors.append("✗ Poor exit accessibility")
        
        return factors
    
    def _generate_recommendations(
        self,
        total_score: float,
        evacuation_time_score: float,
        exit_capacity_score: float,
        bottleneck_score: float,
        disaster_resilience_score: float,
        accessibility_score: float,
        exits: List[Dict],
        bottlenecks: List[Dict]
    ) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if total_score < 70:
            recommendations.append("Building requires significant safety improvements")
        
        if exit_capacity_score < 60:
            recommendations.append(f"Add {max(1, len(exits))} additional exit(s) or widen existing exits")
        
        if bottleneck_score < 60:
            recommendations.append("Widen corridors and doorways in bottleneck areas")
            recommendations.append("Consider alternative evacuation routes")
        
        if evacuation_time_score < 60:
            recommendations.append("Improve exit signage and wayfinding")
            recommendations.append("Implement emergency lighting systems")
        
        if accessibility_score < 60:
            recommendations.append("Redistribute exits for better coverage")
            recommendations.append("Add emergency exits in remote areas")
        
        if disaster_resilience_score < 60:
            recommendations.append("Install fire suppression systems")
            recommendations.append("Strengthen structural elements")
            recommendations.append("Add emergency communication systems")
        
        if not recommendations:
            recommendations.append("Building meets safety standards")
        
        return recommendations

# Global instance
survival_score_engine = SurvivalScoreEngine()

