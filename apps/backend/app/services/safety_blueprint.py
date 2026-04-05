"""
AI-Generated Safety Blueprint Optimizer
Uses genetic algorithm to optimize building layout for safety
"""

import random
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """Result of safety optimization"""
    original_score: float
    optimized_score: float
    improvement_percentage: float
    suggested_exits: List[Dict]
    suggested_modifications: List[Dict]
    estimated_cost: float
    estimated_survival_increase: float

@dataclass
class BuildingModification:
    """Suggested building modification"""
    type: str  # "add_exit", "widen_corridor", "add_fire_door", "relocate_exit"
    location: Tuple[float, float, float]
    description: str
    estimated_cost: float
    survival_increase: float
    priority: str  # "high", "medium", "low"

class SafetyBlueprintOptimizer:
    """Optimizes building layout for maximum safety"""
    
    def __init__(self):
        self.population_size = 50
        self.generations = 20
        self.mutation_rate = 0.1
        self.crossover_rate = 0.7
    
    def optimize_building(
        self,
        current_exits: List[Dict],
        building_bounds: Dict,
        agent_positions: List[Dict],
        current_score: float,
        budget: Optional[float] = None
    ) -> OptimizationResult:
        """
        Optimize building layout using genetic algorithm
        
        Args:
            current_exits: Current exit locations
            building_bounds: Building dimensions {"width": float, "height": float}
            agent_positions: Initial agent positions
            current_score: Current survival score
            budget: Optional budget constraint
        
        Returns:
            OptimizationResult with suggestions
        """
        # Generate initial population of exit configurations
        population = self._generate_initial_population(
            current_exits, building_bounds, self.population_size
        )
        
        best_score = current_score
        best_config = current_exits
        
        # Evolve population
        for generation in range(self.generations):
            # Evaluate fitness
            fitness_scores = []
            for config in population:
                score = self._evaluate_config(config, agent_positions, building_bounds)
                fitness_scores.append((config, score))
            
            # Sort by fitness
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Update best
            if fitness_scores[0][1] > best_score:
                best_score = fitness_scores[0][1]
                best_config = fitness_scores[0][0]
            
            # Create next generation
            population = self._evolve_population(fitness_scores)
        
        # Generate suggestions
        suggested_exits = self._generate_exit_suggestions(best_config, current_exits)
        suggested_modifications = self._generate_modification_suggestions(
            best_config, current_exits, building_bounds
        )
        
        improvement = ((best_score - current_score) / current_score * 100) if current_score > 0 else 0
        estimated_cost = sum(m.get("estimated_cost", 0) for m in suggested_modifications)
        
        return OptimizationResult(
            original_score=current_score,
            optimized_score=best_score,
            improvement_percentage=improvement,
            suggested_exits=suggested_exits,
            suggested_modifications=suggested_modifications,
            estimated_cost=estimated_cost,
            estimated_survival_increase=improvement
        )
    
    def _generate_initial_population(
        self,
        current_exits: List[Dict],
        building_bounds: Dict,
        size: int
    ) -> List[List[Dict]]:
        """Generate initial population of exit configurations"""
        population = []
        
        for _ in range(size):
            config = []
            num_exits = len(current_exits) + random.randint(-1, 2)  # Vary exit count
            num_exits = max(1, min(num_exits, 10))  # Limit between 1 and 10
            
            for i in range(num_exits):
                if i < len(current_exits):
                    # Mutate existing exit
                    exit = current_exits[i].copy()
                    exit["x"] += random.uniform(-5, 5)
                    exit["z"] = exit.get("z", exit.get("y", 0)) + random.uniform(-5, 5)
                    config.append(exit)
                else:
                    # Add new exit
                    config.append({
                        "id": f"new_exit_{i}",
                        "x": random.uniform(-building_bounds.get("width", 100) / 2, building_bounds.get("width", 100) / 2),
                        "y": 0.0,
                        "z": random.uniform(-building_bounds.get("height", 100) / 2, building_bounds.get("height", 100) / 2),
                        "width": random.uniform(1.5, 3.0),
                        "capacity": random.randint(50, 200)
                    })
            
            population.append(config)
        
        return population
    
    def _evaluate_config(
        self,
        exits: List[Dict],
        agent_positions: List[Dict],
        building_bounds: Dict
    ) -> float:
        """Evaluate fitness of exit configuration"""
        if not exits or not agent_positions:
            return 0.0
        
        # Calculate average distance to nearest exit
        total_distance = 0.0
        for agent in agent_positions:
            agent_pos = (agent.get("x", 0), agent.get("z", agent.get("y", 0)))
            min_distance = float('inf')
            
            for exit in exits:
                exit_pos = (exit.get("x", 0), exit.get("z", exit.get("y", 0)))
                distance = math.sqrt(
                    (agent_pos[0] - exit_pos[0])**2 +
                    (agent_pos[1] - exit_pos[1])**2
                )
                min_distance = min(min_distance, distance)
            
            total_distance += min_distance
        
        avg_distance = total_distance / len(agent_positions) if agent_positions else 0
        
        # Score based on distance (closer is better)
        # Also consider exit capacity
        total_capacity = sum(e.get("capacity", 100) for e in exits)
        capacity_score = min(100, (total_capacity / len(agent_positions)) * 50) if agent_positions else 50
        
        distance_score = max(0, 100 - (avg_distance / 10))
        
        # Combined score
        return (distance_score * 0.6 + capacity_score * 0.4)
    
    def _evolve_population(
        self,
        fitness_scores: List[Tuple[List[Dict], float]]
    ) -> List[List[Dict]]:
        """Evolve population through selection, crossover, and mutation"""
        new_population = []
        
        # Keep top 20%
        elite_count = max(1, len(fitness_scores) // 5)
        for i in range(elite_count):
            new_population.append(fitness_scores[i][0].copy())
        
        # Generate rest through crossover and mutation
        while len(new_population) < self.population_size:
            # Selection (tournament)
            parent1 = self._tournament_selection(fitness_scores)
            parent2 = self._tournament_selection(fitness_scores)
            
            # Crossover
            if random.random() < self.crossover_rate:
                child = self._crossover(parent1, parent2)
            else:
                child = parent1.copy()
            
            # Mutation
            if random.random() < self.mutation_rate:
                child = self._mutate(child)
            
            new_population.append(child)
        
        return new_population
    
    def _tournament_selection(
        self,
        fitness_scores: List[Tuple[List[Dict], float]],
        tournament_size: int = 3
    ) -> List[Dict]:
        """Tournament selection"""
        tournament = random.sample(fitness_scores, min(tournament_size, len(fitness_scores)))
        tournament.sort(key=lambda x: x[1], reverse=True)
        return tournament[0][0].copy()
    
    def _crossover(self, parent1: List[Dict], parent2: List[Dict]) -> List[Dict]:
        """Crossover two parent configurations"""
        # Take exits from both parents
        child = []
        min_len = min(len(parent1), len(parent2))
        
        for i in range(min_len):
            if random.random() < 0.5:
                child.append(parent1[i].copy())
            else:
                child.append(parent2[i].copy())
        
        # Add remaining from longer parent
        if len(parent1) > len(parent2):
            child.extend(parent1[min_len:])
        elif len(parent2) > len(parent1):
            child.extend(parent2[min_len:])
        
        return child
    
    def _mutate(self, config: List[Dict]) -> List[Dict]:
        """Mutate configuration"""
        mutated = [exit.copy() for exit in config]
        
        # Randomly mutate some exits
        for exit in mutated:
            if random.random() < 0.3:
                exit["x"] += random.uniform(-10, 10)
                exit["z"] = exit.get("z", exit.get("y", 0)) + random.uniform(-10, 10)
                exit["capacity"] = max(50, exit.get("capacity", 100) + random.randint(-20, 20))
        
        return mutated
    
    def _generate_exit_suggestions(
        self,
        optimized_exits: List[Dict],
        current_exits: List[Dict]
    ) -> List[Dict]:
        """Generate exit addition/relocation suggestions"""
        suggestions = []
        
        # Find new exits not in current configuration
        current_positions = {(e.get("x", 0), e.get("z", e.get("y", 0))) for e in current_exits}
        
        for exit in optimized_exits:
            exit_pos = (exit.get("x", 0), exit.get("z", exit.get("y", 0)))
            
            # Check if this is a new exit
            is_new = True
            min_distance = float('inf')
            for curr_pos in current_positions:
                distance = math.sqrt(
                    (exit_pos[0] - curr_pos[0])**2 +
                    (exit_pos[1] - curr_pos[1])**2
                )
                if distance < 5.0:  # Within 5 meters, consider it existing
                    is_new = False
                    min_distance = min(min_distance, distance)
            
            if is_new:
                suggestions.append({
                    "action": "add_exit",
                    "location": exit_pos,
                    "width": exit.get("width", 2.0),
                    "capacity": exit.get("capacity", 100),
                    "priority": "high" if len(current_exits) < 3 else "medium"
                })
            elif min_distance > 2.0:
                # Suggest relocation
                suggestions.append({
                    "action": "relocate_exit",
                    "from": None,  # Would need to match to current exit
                    "to": exit_pos,
                    "priority": "medium"
                })
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def _generate_modification_suggestions(
        self,
        optimized_exits: List[Dict],
        current_exits: List[Dict],
        building_bounds: Dict
    ) -> List[Dict]:
        """Generate building modification suggestions"""
        modifications = []
        
        # Suggest wider corridors near exits
        for exit in optimized_exits:
            modifications.append({
                "type": "widen_corridor",
                "location": (exit.get("x", 0), exit.get("y", 0), exit.get("z", exit.get("y", 0))),
                "description": f"Widen corridor to {exit.get('width', 2.0) * 1.5:.1f}m near exit",
                "estimated_cost": 5000.0,
                "survival_increase": 5.0,
                "priority": "medium"
            })
        
        # Suggest fire doors
        if len(optimized_exits) > len(current_exits):
            modifications.append({
                "type": "add_fire_door",
                "location": (0, 0, 0),  # Central location
                "description": "Install fire doors to compartmentalize building",
                "estimated_cost": 10000.0,
                "survival_increase": 10.0,
                "priority": "high"
            })
        
        return modifications

# Global instance
safety_blueprint_optimizer = SafetyBlueprintOptimizer()

