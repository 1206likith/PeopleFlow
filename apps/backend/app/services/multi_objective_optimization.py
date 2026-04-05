"""
Multi-Objective Optimization & Policy Testing Engine
Genetic algorithms, reinforcement learning, multi-objective optimization
Research: Multi-objective optimization in evacuation (OUCI)
"""

import numpy as np
from typing import Dict, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class OptimizationObjective(Enum):
    """Optimization objectives"""
    MINIMIZE_TIME = "minimize_time"
    MAXIMIZE_SAFETY = "maximize_safety"
    MINIMIZE_COST = "minimize_cost"
    BALANCE_EXITS = "balance_exits"

@dataclass
class OptimizationResult:
    """Result of optimization"""
    solution: Dict
    objectives: Dict[str, float]  # objective_name -> value
    pareto_rank: int = 0  # For multi-objective: rank in Pareto front
    fitness: float = 0.0

class MultiObjectiveOptimizer:
    """
    Multi-objective optimization using Pareto optimization
    Optimizes multiple objectives simultaneously (time, safety, cost)
    Research: Multi-objective optimization (OUCI)
    """
    
    def __init__(self):
        self.objectives: List[OptimizationObjective] = []
        self.objective_weights: Dict[str, float] = {}
    
    def optimize(
        self,
        parameter_space: Dict[str, Tuple[float, float]],
        objective_functions: Dict[str, Callable],
        population_size: int = 100,
        generations: int = 50
    ) -> List[OptimizationResult]:
        """
        Multi-objective optimization using NSGA-II-like algorithm
        
        Returns:
            Pareto front of solutions
        """
        # Initialize population
        population = self._initialize_population(parameter_space, population_size)
        
        for generation in range(generations):
            # Evaluate objectives for each individual
            evaluated_population = []
            for individual in population:
                objectives = {}
                for obj_name, obj_func in objective_functions.items():
                    objectives[obj_name] = obj_func(individual)
                
                evaluated_population.append(OptimizationResult(
                    solution=individual,
                    objectives=objectives
                ))
            
            # Calculate Pareto ranks
            pareto_fronts = self._calculate_pareto_fronts(evaluated_population)
            
            # Select next generation (elitism + diversity)
            population = self._select_next_generation(
                evaluated_population,
                pareto_fronts,
                population_size
            )
            
            if generation % 10 == 0:
                logger.info(f"Generation {generation}: Pareto front size = {len(pareto_fronts[0])}")
        
        # Return final Pareto front
        final_pareto = self._calculate_pareto_fronts(evaluated_population)[0]
        return final_pareto
    
    def _initialize_population(
        self,
        parameter_space: Dict[str, Tuple[float, float]],
        size: int
    ) -> List[Dict]:
        """Initialize random population"""
        population = []
        for _ in range(size):
            individual = {}
            for param_name, (min_val, max_val) in parameter_space.items():
                individual[param_name] = np.random.uniform(min_val, max_val)
            population.append(individual)
        return population
    
    def _calculate_pareto_fronts(
        self,
        population: List[OptimizationResult]
    ) -> List[List[OptimizationResult]]:
        """
        Calculate Pareto fronts (non-dominated sorting)
        Returns list of fronts, where front[0] is the Pareto-optimal front
        """
        fronts = []
        remaining = population.copy()
        
        while remaining:
            current_front = []
            dominated = []
            
            for i, candidate in enumerate(remaining):
                is_dominated = False
                
                for other in remaining:
                    if candidate == other:
                        continue
                    
                    # Check if other dominates candidate
                    if self._dominates(other, candidate):
                        is_dominated = True
                        break
                
                if not is_dominated:
                    current_front.append(candidate)
                else:
                    dominated.append(candidate)
            
            fronts.append(current_front)
            remaining = dominated
        
        # Assign ranks
        for rank, front in enumerate(fronts):
            for solution in front:
                solution.pareto_rank = rank
        
        return fronts
    
    def _dominates(
        self,
        solution1: OptimizationResult,
        solution2: OptimizationResult
    ) -> bool:
        """
        Check if solution1 dominates solution2
        solution1 dominates if it's better in all objectives
        """
        # Assume minimization for all objectives
        better_in_all = True
        better_in_any = False
        
        for obj_name in solution1.objectives.keys():
            val1 = solution1.objectives[obj_name]
            val2 = solution2.objectives[obj_name]
            
            if val1 > val2:  # solution2 is better
                better_in_all = False
            elif val1 < val2:  # solution1 is better
                better_in_any = True
        
        return better_in_all and better_in_any
    
    def _select_next_generation(
        self,
        population: List[OptimizationResult],
        pareto_fronts: List[List[OptimizationResult]],
        size: int
    ) -> List[Dict]:
        """Select next generation using crowding distance"""
        selected = []
        
        # Select from Pareto fronts in order
        for front in pareto_fronts:
            if len(selected) + len(front) <= size:
                selected.extend([s.solution for s in front])
            else:
                # Need to select subset using crowding distance
                remaining = size - len(selected)
                sorted_front = self._sort_by_crowding_distance(front)
                selected.extend([s.solution for s in sorted_front[:remaining]])
                break
        
        # Crossover and mutation
        new_population = []
        for _ in range(size):
            if len(selected) >= 2:
                parent1 = np.random.choice(selected)
                parent2 = np.random.choice(selected)
                child = self._crossover(parent1, parent2)
                child = self._mutate(child, 0.1)
                new_population.append(child)
            else:
                new_population.append(selected[0] if selected else {})
        
        return new_population
    
    def _sort_by_crowding_distance(
        self,
        front: List[OptimizationResult]
    ) -> List[OptimizationResult]:
        """Sort by crowding distance (diversity metric)"""
        if len(front) <= 2:
            return front
        
        # Calculate crowding distance for each solution
        for solution in front:
            solution.crowding_distance = 0.0
        
        # For each objective
        for obj_name in front[0].objectives.keys():
            # Sort by this objective
            sorted_front = sorted(front, key=lambda s: s.objectives[obj_name])
            
            # Boundary solutions get infinite distance
            sorted_front[0].crowding_distance = float('inf')
            sorted_front[-1].crowding_distance = float('inf')
            
            # Calculate range
            obj_min = sorted_front[0].objectives[obj_name]
            obj_max = sorted_front[-1].objectives[obj_name]
            obj_range = obj_max - obj_min if obj_max > obj_min else 1.0
            
            # Add distance for interior solutions
            for i in range(1, len(sorted_front) - 1):
                distance = (sorted_front[i+1].objectives[obj_name] - 
                           sorted_front[i-1].objectives[obj_name]) / obj_range
                sorted_front[i].crowding_distance += distance
        
        # Sort by crowding distance (descending)
        return sorted(front, key=lambda s: s.crowding_distance, reverse=True)
    
    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """Crossover two parents"""
        child = {}
        for key in parent1.keys():
            if np.random.random() < 0.5:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        return child
    
    def _mutate(self, individual: Dict, mutation_rate: float) -> Dict:
        """Mutate individual"""
        mutated = individual.copy()
        for key in mutated.keys():
            if np.random.random() < mutation_rate:
                # Add small random change
                mutated[key] += np.random.normal(0, 0.1 * abs(mutated[key]))
        return mutated

class PolicyTester:
    """
    Policy testing engine
    Tests and compares different evacuation strategies
    """
    
    def __init__(self):
        self.policies: Dict[str, Dict] = {}
    
    def test_policy(
        self,
        policy_name: str,
        policy_config: Dict,
        simulation_runner: Callable,
        num_runs: int = 10
    ) -> Dict:
        """
        Test a policy with multiple simulation runs
        
        Returns:
            Policy performance metrics
        """
        results = []
        
        for run in range(num_runs):
            try:
                result = simulation_runner(policy_config)
                results.append(result)
            except Exception as e:
                logger.warning(f"Policy test run {run} failed: {e}")
        
        if not results:
            return {"error": "All simulation runs failed"}
        
        # Aggregate results
        metrics = {}
        for key in results[0].keys():
            if isinstance(results[0][key], (int, float)):
                values = [r[key] for r in results]
                metrics[key] = {
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values)
                }
            else:
                metrics[key] = results[0][key]  # Use first result for non-numeric
        
        return {
            "policy": policy_name,
            "runs": num_runs,
            "metrics": metrics
        }
    
    def compare_policies(
        self,
        policies: Dict[str, Dict],
        simulation_runner: Callable,
        num_runs: int = 10
    ) -> Dict:
        """
        Compare multiple policies
        
        Returns:
            Comparison report
        """
        policy_results = {}
        
        for policy_name, policy_config in policies.items():
            result = self.test_policy(policy_name, policy_config, simulation_runner, num_runs)
            policy_results[policy_name] = result
        
        # Rank policies by key metrics
        rankings = self._rank_policies(policy_results)
        
        return {
            "policy_results": policy_results,
            "rankings": rankings,
            "best_policy": max(rankings.items(), key=lambda x: x[1])[0] if rankings else None
        }
    
    def _rank_policies(self, policy_results: Dict[str, Dict]) -> Dict[str, float]:
        """Rank policies by composite score"""
        rankings = {}
        
        for policy_name, result in policy_results.items():
            if "error" in result:
                rankings[policy_name] = 0.0
                continue
            
            metrics = result.get("metrics", {})
            
            # Composite score (weighted combination)
            # Lower evacuation time = better
            # Higher safety = better
            time_score = 1.0 / (1.0 + metrics.get("evacuation_time", {}).get("mean", 100.0))
            safety_score = metrics.get("safety_score", {}).get("mean", 0.0) / 100.0
            
            composite_score = 0.6 * time_score + 0.4 * safety_score
            rankings[policy_name] = composite_score
        
        return rankings

# Global instances
multi_objective_optimizer = MultiObjectiveOptimizer()
policy_tester = PolicyTester()

