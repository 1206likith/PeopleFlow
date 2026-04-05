"""
Adaptive Exit Choice & Guidance Optimization
Dynamic exit signage optimization and cell-based adaptive guidance
Research: Adaptive guidance systems (arXiv)
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class GuidanceCell:
    """Cell in adaptive guidance grid"""
    cell_id: int
    position: Tuple[float, float, float]
    recommended_exit: Optional[str] = None
    guidance_strength: float = 1.0  # 0-1
    agent_count: int = 0
    congestion_level: float = 0.0  # 0-1
    last_update_time: float = 0.0

class AdaptiveGuidanceSystem:
    """
    Adaptive exit guidance using behavioral optimization loops
    Dynamically adjusts guidance based on real-time conditions
    Research: Cell-based adaptive guidance (arXiv)
    """
    
    def __init__(self, grid_resolution: float = 5.0):
        """
        Initialize adaptive guidance system
        
        Args:
            grid_resolution: Size of each guidance cell in meters
        """
        self.grid_resolution = grid_resolution
        self.guidance_cells: Dict[Tuple[int, int], GuidanceCell] = {}
        self.exit_utilizations: Dict[str, float] = {}  # exit_id -> utilization (0-1)
        self.optimization_interval = 2.0  # seconds
        self.last_optimization = 0.0
    
    def update_guidance(
        self,
        current_time: float,
        agents: List[Dict],
        exits: List[Dict],
        building_bounds: Dict
    ):
        """
        Update adaptive guidance based on current conditions
        
        Args:
            current_time: Current simulation time
            agents: List of all agents
            exits: List of all exits
            building_bounds: Building boundaries {min_x, max_x, min_z, max_z}
        """
        # Update exit utilizations
        self._update_exit_utilizations(agents, exits)
        
        # Optimize guidance periodically
        if current_time - self.last_optimization > self.optimization_interval:
            self._optimize_guidance(agents, exits, building_bounds)
            self.last_optimization = current_time
    
    def _update_exit_utilizations(self, agents: List[Dict], exits: List[Dict]):
        """Update exit utilization rates"""
        for exit in exits:
            exit_id = exit.get("id")
            exit_width = exit.get("width", 2.0)
            
            # Count agents heading to this exit
            agents_heading_to_exit = sum(
                1 for agent in agents
                if agent.get("target_exit") == exit_id and agent.get("status") != "evacuated"
            )
            
            # Calculate utilization (agents / capacity)
            # Capacity = flow_rate * width * time_window
            flow_rate = 1.33  # persons/second/meter (research-validated)
            capacity = flow_rate * exit_width * 10.0  # 10 second window
            utilization = min(1.0, agents_heading_to_exit / capacity) if capacity > 0 else 0.0
            
            self.exit_utilizations[exit_id] = utilization
    
    def _optimize_guidance(
        self,
        agents: List[Dict],
        exits: List[Dict],
        building_bounds: Dict
    ):
        """Optimize guidance for each cell"""
        # Create/update guidance cells
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            agent_x = agent.get("x", 0)
            agent_z = agent.get("z", agent.get("y", 0))
            
            # Get cell coordinates
            cell_x = int(agent_x / self.grid_resolution)
            cell_z = int(agent_z / self.grid_resolution)
            cell_key = (cell_x, cell_z)
            
            # Create cell if doesn't exist
            if cell_key not in self.guidance_cells:
                self.guidance_cells[cell_key] = GuidanceCell(
                    cell_id=len(self.guidance_cells),
                    position=(cell_x * self.grid_resolution, 0, cell_z * self.grid_resolution)
                )
            
            cell = self.guidance_cells[cell_key]
            cell.agent_count += 1
        
        # Optimize each cell's recommended exit
        for cell in self.guidance_cells.values():
            cell.recommended_exit = self._choose_optimal_exit(
                cell.position, exits, agents
            )
            cell.congestion_level = self._calculate_cell_congestion(
                cell.position, agents
            )
    
    def _choose_optimal_exit(
        self,
        cell_position: Tuple[float, float, float],
        exits: List[Dict],
        agents: List[Dict]
    ) -> Optional[str]:
        """
        Choose optimal exit for this cell using multi-objective optimization
        
        Considers:
        - Distance to exit
        - Exit utilization (congestion)
        - Expected travel time
        """
        if not exits:
            return None
        
        best_exit = None
        best_score = -float('inf')
        
        for exit in exits:
            exit_id = exit.get("id")
            exit_pos = (exit.get("x", 0), exit.get("y", 0), exit.get("z", exit.get("y", 0)))
            
            # Distance score (negative, prefer closer)
            distance = math.sqrt(
                (cell_position[0] - exit_pos[0])**2 +
                (cell_position[2] - exit_pos[2])**2
            )
            distance_score = -distance / 100.0  # Normalize
        
            # Utilization penalty (negative, prefer less congested)
            utilization = self.exit_utilizations.get(exit_id, 0.0)
            utilization_penalty = -utilization * 2.0
        
            # Expected travel time (considering congestion)
            base_speed = 1.35  # m/s
            congested_speed = base_speed * (1.0 - utilization * 0.5)
            expected_time = distance / congested_speed if congested_speed > 0 else float('inf')
            time_score = -expected_time / 60.0  # Normalize to minutes
        
            # Combined score
            total_score = distance_score + utilization_penalty + time_score
        
            if total_score > best_score:
                best_score = total_score
                best_exit = exit_id
        
        return best_exit
    
    def _calculate_cell_congestion(
        self,
        cell_position: Tuple[float, float, float],
        agents: List[Dict]
    ) -> float:
        """Calculate congestion level in cell"""
        measurement_radius = self.grid_resolution * 0.7
        nearby_count = 0
        
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            agent_x = agent.get("x", 0)
            agent_z = agent.get("z", agent.get("y", 0))
            
            distance = math.sqrt(
                (cell_position[0] - agent_x)**2 +
                (cell_position[2] - agent_z)**2
            )
            
            if distance < measurement_radius:
                nearby_count += 1
        
        # Density in persons/m²
        area = math.pi * measurement_radius**2
        density = nearby_count / area if area > 0 else 0.0
        
        # Normalize to 0-1 (critical density ~4 persons/m²)
        critical_density = 4.0
        congestion = min(1.0, density / critical_density)
        
        return congestion
    
    def get_guidance_for_position(
        self,
        position: Tuple[float, float, float]
    ) -> Optional[Dict]:
        """
        Get guidance recommendation for a position
        
        Returns:
            Dictionary with recommended_exit and guidance_strength
        """
        cell_x = int(position[0] / self.grid_resolution)
        cell_z = int(position[2] / self.grid_resolution)
        cell_key = (cell_x, cell_z)
        
        cell = self.guidance_cells.get(cell_key)
        if cell:
            return {
                "recommended_exit": cell.recommended_exit,
                "guidance_strength": cell.guidance_strength,
                "congestion_level": cell.congestion_level
            }
        
        return None

class DynamicSignageOptimizer:
    """
    Dynamic exit signage optimization
    Adjusts signage visibility and recommendations based on behavioral feedback
    Research: Dynamic signage optimization (arXiv)
    """
    
    def __init__(self):
        self.signage_locations: List[Dict] = []
        self.signage_effectiveness: Dict[str, float] = {}  # signage_id -> effectiveness
    
    def optimize_signage(
        self,
        signage_locations: List[Dict],
        agents: List[Dict],
        exits: List[Dict]
    ) -> List[Dict]:
        """
        Optimize signage recommendations
        
        Returns:
            Updated signage with optimized recommendations
        """
        optimized_signage = []
        
        for signage in signage_locations:
            signage_pos = (signage.get("x", 0), signage.get("y", 0), signage.get("z", signage.get("y", 0)))
            
            # Find optimal exit to recommend
            recommended_exit = self._choose_exit_for_signage(
                signage_pos, exits, agents
            )
            
            # Calculate visibility/effectiveness
            effectiveness = self._calculate_signage_effectiveness(
                signage_pos, agents, recommended_exit
            )
            
            optimized_signage.append({
                **signage,
                "recommended_exit": recommended_exit,
                "effectiveness": effectiveness,
                "visibility": min(1.0, effectiveness * 1.2)  # Visibility based on effectiveness
            })
        
        return optimized_signage
    
    def _choose_exit_for_signage(
        self,
        signage_position: Tuple[float, float, float],
        exits: List[Dict],
        agents: List[Dict]
    ) -> Optional[str]:
        """Choose which exit to recommend on this signage"""
        # Similar logic to adaptive guidance
        # Consider distance, utilization, expected time
        
        best_exit = None
        best_score = -float('inf')
        
        for exit in exits:
            exit_id = exit.get("id")
            exit_pos = (exit.get("x", 0), exit.get("y", 0), exit.get("z", exit.get("y", 0)))
            
            distance = math.sqrt(
                (signage_position[0] - exit_pos[0])**2 +
                (signage_position[2] - exit_pos[2])**2
            )
            
            # Count agents heading to exit
            agents_to_exit = sum(
                1 for agent in agents
                if agent.get("target_exit") == exit_id
            )
            
            # Score: distance (negative) + utilization (negative)
            distance_score = -distance / 100.0
            utilization_penalty = -(agents_to_exit / max(1, len(agents))) * 2.0
            
            total_score = distance_score + utilization_penalty
            
            if total_score > best_score:
                best_score = total_score
                best_exit = exit_id
        
        return best_exit
    
    def _calculate_signage_effectiveness(
        self,
        signage_position: Tuple[float, float, float],
        agents: List[Dict],
        recommended_exit: Optional[str]
    ) -> float:
        """Calculate how effective this signage is"""
        if not recommended_exit:
            return 0.0
        
        # Count agents near signage following recommendation
        visibility_radius = 10.0  # meters
        following_count = 0
        total_nearby = 0
        
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            agent_x = agent.get("x", 0)
            agent_z = agent.get("z", agent.get("y", 0))
            
            distance = math.sqrt(
                (signage_position[0] - agent_x)**2 +
                (signage_position[2] - agent_z)**2
            )
            
            if distance < visibility_radius:
                total_nearby += 1
                if agent.get("target_exit") == recommended_exit:
                    following_count += 1
        
        # Effectiveness = fraction following recommendation
        effectiveness = following_count / total_nearby if total_nearby > 0 else 0.0
        
        return effectiveness

# Global instances
adaptive_guidance = AdaptiveGuidanceSystem()
signage_optimizer = DynamicSignageOptimizer()

