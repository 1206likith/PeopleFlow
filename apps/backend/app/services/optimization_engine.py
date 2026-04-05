"""
Survival Optimization Engine
AI redesigns building using genetic algorithms
Optimizes: exit positions, widths, placements
Fitness = minimize death-zones & total evacuation time
"""
import random
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class GeneticOptimizer:
    """
    Genetic algorithm for building optimization
    Optimizes exit placement and configuration
    """
    
    def __init__(
        self,
        population_size: int = 50,
        generations: int = 100,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7
    ):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
    
    def optimize_exits(
        self,
        building_bounds: Dict,
        current_exits: List[Dict],
        num_agents: int = 100,
        simulation_runner=None
    ) -> Dict:
        """
        Optimize exit configuration using genetic algorithm
        
        Args:
            building_bounds: Building boundaries
            current_exits: Current exit configuration
            num_agents: Number of agents for simulation
            simulation_runner: Function to run simulation and get fitness
        
        Returns:
            Optimized exit configuration with fitness scores
        """
        # Initialize population
        population = self._initialize_population(building_bounds, len(current_exits))
        
        best_individual = None
        best_fitness = float('inf')
        
        for generation in range(self.generations):
            # Evaluate fitness
            fitness_scores = []
            for individual in population:
                fitness = self._evaluate_fitness(
                    individual,
                    building_bounds,
                    num_agents,
                    simulation_runner
                )
                fitness_scores.append(fitness)
                
                if fitness < best_fitness:
                    best_fitness = fitness
                    best_individual = individual.copy()
            
            # Selection, crossover, mutation
            population = self._evolve_population(population, fitness_scores)
            
            if generation % 10 == 0:
                logger.info(f"Generation {generation}: Best fitness = {best_fitness:.2f}")
        
        return {
            "optimized_exits": self._individual_to_exits(best_individual),
            "fitness": best_fitness,
            "improvement": self._calculate_improvement(current_exits, best_individual, building_bounds)
        }
    
    def _initialize_population(
        self,
        building_bounds: Dict,
        num_exits: int
    ) -> List[Dict]:
        """Initialize population of exit configurations"""
        population = []
        
        min_x = building_bounds.get("min_x", 0)
        max_x = building_bounds.get("max_x", 100)
        min_y = building_bounds.get("min_y", 0)
        max_y = building_bounds.get("max_y", 100)
        
        for _ in range(self.population_size):
            individual = {
                "exits": []
            }
            
            for i in range(num_exits):
                individual["exits"].append({
                    "x": random.uniform(min_x, max_x),
                    "y": random.uniform(min_y, max_y),
                    "width": random.uniform(1.5, 3.0),  # 1.5-3m width
                    "id": f"exit_{i+1}"
                })
            
            population.append(individual)
        
        return population
    
    def _evaluate_fitness(
        self,
        individual: Dict,
        building_bounds: Dict,
        num_agents: int,
        simulation_runner
    ) -> float:
        """
        Evaluate fitness of exit configuration
        Fitness = evacuation_time + death_zone_penalty + congestion_penalty
        Lower is better
        """
        if simulation_runner:
            # Run simulation with this exit configuration
            result = simulation_runner(individual["exits"], num_agents)
            evacuation_time = result.get("total_time", 1000.0)
            death_zones = result.get("death_zones", 0)
            peak_congestion = result.get("peak_congestion", 0.0)
        else:
            # Simplified fitness (without running simulation)
            evacuation_time = self._estimate_evacuation_time(individual["exits"], building_bounds, num_agents)
            death_zones = 0
            peak_congestion = 0.0
        
        # Fitness components
        time_penalty = evacuation_time * 10.0
        death_penalty = death_zones * 1000.0  # Heavy penalty for deaths
        congestion_penalty = peak_congestion * 50.0
        
        return time_penalty + death_penalty + congestion_penalty
    
    def _estimate_evacuation_time(
        self,
        exits: List[Dict],
        building_bounds: Dict,
        num_agents: int
    ) -> float:
        """Estimate evacuation time without full simulation"""
        # Calculate total exit capacity
        total_capacity = sum(exit.get("width", 2.0) * 1.33 for exit in exits)  # persons/second
        
        if total_capacity == 0:
            return 1000.0  # Very bad
        
        # Estimate time = agents / capacity
        estimated_time = num_agents / total_capacity
        
        # Add penalty for poor distribution
        if len(exits) > 1:
            # Check exit distribution
            xs = [e.get("x", 0) for e in exits]
            ys = [e.get("y", 0) for e in exits]
            
            # Calculate spread
            x_spread = max(xs) - min(xs) if xs else 0
            y_spread = max(ys) - min(ys) if ys else 0
            
            building_width = building_bounds.get("max_x", 100) - building_bounds.get("min_x", 0)
            building_height = building_bounds.get("max_y", 100) - building_bounds.get("min_y", 0)
            
            # Penalty if exits are too close together
            if x_spread < building_width * 0.3 or y_spread < building_height * 0.3:
                estimated_time *= 1.5
        
        return estimated_time
    
    def _evolve_population(
        self,
        population: List[Dict],
        fitness_scores: List[float]
    ) -> List[Dict]:
        """Evolve population: selection, crossover, mutation"""
        # Normalize fitness (lower is better, so invert)
        max_fitness = max(fitness_scores)
        normalized = [max_fitness - f + 1 for f in fitness_scores]
        total = sum(normalized)
        probabilities = [f / total for f in normalized]
        
        new_population = []
        
        # Elitism: keep best 10%
        elite_count = max(1, int(self.population_size * 0.1))
        elite_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i])[:elite_count]
        for idx in elite_indices:
            new_population.append(population[idx].copy())
        
        # Generate rest through crossover and mutation
        while len(new_population) < self.population_size:
            # Selection (roulette wheel)
            parent1 = self._select_parent(population, probabilities)
            parent2 = self._select_parent(population, probabilities)
            
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
    
    def _select_parent(self, population: List[Dict], probabilities: List[float]) -> Dict:
        """Select parent using roulette wheel selection"""
        return random.choices(population, weights=probabilities)[0]
    
    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """Crossover two exit configurations"""
        child = {"exits": []}
        
        for i in range(min(len(parent1["exits"]), len(parent2["exits"]))):
            if random.random() < 0.5:
                child["exits"].append(parent1["exits"][i].copy())
            else:
                child["exits"].append(parent2["exits"][i].copy())
        
        return child
    
    def _mutate(self, individual: Dict) -> Dict:
        """Mutate exit configuration"""
        mutated = {"exits": [exit.copy() for exit in individual["exits"]]}
        
        for exit in mutated["exits"]:
            if random.random() < 0.3:  # 30% chance to mutate each exit
                # Mutate position
                exit["x"] += random.uniform(-10, 10)
                exit["y"] += random.uniform(-10, 10)
            
            if random.random() < 0.2:  # 20% chance to mutate width
                exit["width"] = random.uniform(1.5, 3.0)
        
        return mutated
    
    def _individual_to_exits(self, individual: Dict) -> List[Dict]:
        """Convert individual to exit list format"""
        return individual.get("exits", [])
    
    def _calculate_improvement(
        self,
        current_exits: List[Dict],
        optimized_individual: Dict,
        building_bounds: Dict
    ) -> Dict:
        """Calculate improvement metrics"""
        current_time = self._estimate_evacuation_time(current_exits, building_bounds, 100)
        optimized_time = self._estimate_evacuation_time(
            optimized_individual["exits"],
            building_bounds,
            100
        )
        
        improvement_percent = ((current_time - optimized_time) / current_time) * 100 if current_time > 0 else 0
        
        return {
            "time_reduction": current_time - optimized_time,
            "improvement_percent": improvement_percent,
            "estimated_survival_increase": min(100, improvement_percent * 2)  # Rough estimate
        }

# Global optimizer
genetic_optimizer = GeneticOptimizer()

