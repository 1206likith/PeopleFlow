"""
Multi-Scale Modeling Architecture
Implements macro ↔ micro coupling for large-scale evacuation simulation
Hybrid models: Social Force Model (SFM) + Cellular Automata (CA) + Agent-Based Model (ABM)
Research: Multi-scale evacuation simulation (ScienceDirect)
"""

import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.services.social_force_model import social_force_model
from app.services.heterogeneous_agents import AgentAttributes
from app.services.evacuation_parameters import parameter_database

logger = logging.getLogger(__name__)

class ScaleLevel(Enum):
    """Modeling scale levels"""
    MACRO = "macro"  # Large regions, flow-based
    MESO = "meso"  # Medium regions, density-based
    MICRO = "micro"  # Individual agents, agent-based

class ModelType(Enum):
    """Hybrid model types"""
    SFM = "sfm"  # Social Force Model
    CA = "ca"  # Cellular Automata
    ABM = "abm"  # Agent-Based Model
    HYBRID = "hybrid"  # Combination

@dataclass
class MacroCell:
    """Macro-scale cell for flow modeling"""
    cell_id: str
    position: Tuple[float, float, float]
    size: float  # Cell size in meters
    density: float = 0.0  # persons/m²
    flow_rate: float = 0.0  # persons/second
    velocity_field: Tuple[float, float] = (0.0, 0.0)  # Average velocity (vx, vz)
    capacity: int = 0  # Maximum capacity
    connected_cells: List[str] = field(default_factory=list)
    exit_distance: float = float('inf')  # Distance to nearest exit

@dataclass
class MesoCell:
    """Meso-scale cell for density-based modeling"""
    cell_id: str
    position: Tuple[float, float, float]
    size: float  # Cell size (smaller than macro)
    density: float = 0.0  # persons/m²
    agent_ids: List[int] = field(default_factory=list)
    local_velocity: float = 0.0  # m/s
    congestion_level: float = 0.0  # 0-1

class MacroFlowModel:
    """
    Macro-scale flow model for large regions
    Uses continuum flow equations (fluid dynamics approach)
    Research: Continuum models for pedestrian flow
    """
    
    def __init__(self, cell_size: float = 10.0):
        """
        Initialize macro flow model
        
        Args:
            cell_size: Size of macro cells in meters
        """
        self.cell_size = cell_size
        self.macro_cells: Dict[str, MacroCell] = {}
        self.grid_resolution = cell_size
    
    def create_macro_grid(
        self,
        building_bounds: Dict,
        exits: List[Dict]
    ) -> Dict[str, MacroCell]:
        """
        Create macro-scale grid covering building
        
        Args:
            building_bounds: {min_x, max_x, min_z, max_z}
            exits: List of exit positions
        
        Returns:
            Dictionary of macro cells
        """
        min_x = building_bounds.get("min_x", 0)
        max_x = building_bounds.get("max_x", 100)
        min_z = building_bounds.get("min_z", 0)
        max_z = building_bounds.get("max_z", 100)
        
        cells = {}
        cell_id = 0
        
        # Create grid of cells
        for x in np.arange(min_x, max_x, self.cell_size):
            for z in np.arange(min_z, max_z, self.cell_size):
                cell_id_str = f"macro_{cell_id}"
                
                # Calculate distance to nearest exit
                min_exit_dist = float('inf')
                for exit in exits:
                    exit_x = exit.get("x", 0)
                    exit_z = exit.get("z", exit.get("y", 0))
                    dist = math.sqrt((x - exit_x)**2 + (z - exit_z)**2)
                    min_exit_dist = min(min_exit_dist, dist)
                
                cell = MacroCell(
                    cell_id=cell_id_str,
                    position=(x + self.cell_size/2, 0, z + self.cell_size/2),
                    size=self.cell_size,
                    exit_distance=min_exit_dist,
                    capacity=int(self.cell_size * self.cell_size * 4.0)  # 4 persons/m² max
                )
                
                cells[cell_id_str] = cell
                cell_id += 1
        
        # Connect adjacent cells
        self._connect_cells(cells)
        
        self.macro_cells = cells
        return cells
    
    def _connect_cells(self, cells: Dict[str, MacroCell]):
        """Connect adjacent cells"""
        for cell_id, cell in cells.items():
            cell_x, _, cell_z = cell.position
            
            # Check 4 neighbors (N, S, E, W)
            neighbors = [
                (cell_x, cell_z + self.cell_size),  # North
                (cell_x, cell_z - self.cell_size),  # South
                (cell_x + self.cell_size, cell_z),  # East
                (cell_x - self.cell_size, cell_z)   # West
            ]
            
            for nx, nz in neighbors:
                # Find neighbor cell
                for other_id, other_cell in cells.items():
                    if other_id == cell_id:
                        continue
                    other_x, _, other_z = other_cell.position
                    if abs(other_x - nx) < 0.1 and abs(other_z - nz) < 0.1:
                        cell.connected_cells.append(other_id)
                        break
    
    def update_macro_flow(
        self,
        agents: List[Dict],
        dt: float
    ):
        """
        Update macro-scale flow based on agent positions
        
        Implements continuity equation: ∂ρ/∂t + ∇·(ρv) = 0
        """
        # Reset cell densities
        for cell in self.macro_cells.values():
            cell.density = 0.0
            cell.flow_rate = 0.0
            cell.velocity_field = (0.0, 0.0)
        
        # Aggregate agents into macro cells
        velocity_sum_x = {}
        velocity_sum_z = {}
        agent_count = {}
        
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            agent_x = agent.get("x", 0)
            agent_z = agent.get("z", agent.get("y", 0))
            
            # Find which macro cell contains this agent
            cell_id = self._get_cell_id(agent_x, agent_z)
            if cell_id and cell_id in self.macro_cells:
                cell = self.macro_cells[cell_id]
                cell.density += 1.0 / (self.cell_size * self.cell_size)
                
                # Accumulate velocities
                if cell_id not in velocity_sum_x:
                    velocity_sum_x[cell_id] = 0.0
                    velocity_sum_z[cell_id] = 0.0
                    agent_count[cell_id] = 0
                
                vx = agent.get("velocity_x", 0.0)
                vz = agent.get("velocity_z", 0.0)
                velocity_sum_x[cell_id] += vx
                velocity_sum_z[cell_id] += vz
                agent_count[cell_id] += 1
        
        # Calculate average velocities and flow rates
        for cell_id, cell in self.macro_cells.items():
            if agent_count.get(cell_id, 0) > 0:
                avg_vx = velocity_sum_x[cell_id] / agent_count[cell_id]
                avg_vz = velocity_sum_z[cell_id] / agent_count[cell_id]
                cell.velocity_field = (avg_vx, avg_vz)
                
                # Flow rate = density * velocity magnitude
                velocity_mag = math.sqrt(avg_vx**2 + avg_vz**2)
                cell.flow_rate = cell.density * velocity_mag
    
    def _get_cell_id(self, x: float, z: float) -> Optional[str]:
        """Get macro cell ID for a position"""
        cell_x = int(x / self.cell_size) * self.cell_size + self.cell_size/2
        cell_z = int(z / self.cell_size) * self.cell_size + self.cell_size/2
        
        for cell_id, cell in self.macro_cells.items():
            cell_pos_x, _, cell_pos_z = cell.position
            if abs(cell_pos_x - cell_x) < 0.1 and abs(cell_pos_z - cell_z) < 0.1:
                return cell_id
        
        return None
    
    def get_macro_flow_direction(
        self,
        position: Tuple[float, float, float]
    ) -> Tuple[float, float]:
        """
        Get flow direction from macro model
        
        Returns:
            (vx, vz) flow direction vector
        """
        cell_id = self._get_cell_id(position[0], position[2])
        if cell_id and cell_id in self.macro_cells:
            return self.macro_cells[cell_id].velocity_field
        
        return (0.0, 0.0)

class CellularAutomataModel:
    """
    Cellular Automata model for meso-scale modeling
    Grid-based discrete model for density and flow
    Research: CA models for pedestrian dynamics
    """
    
    def __init__(self, cell_size: float = 2.0):
        """
        Initialize CA model
        
        Args:
            cell_size: Size of CA cells in meters (smaller than macro)
        """
        self.cell_size = cell_size
        self.meso_cells: Dict[str, MesoCell] = {}
        self.transition_rules = self._initialize_transition_rules()
    
    def create_meso_grid(
        self,
        building_bounds: Dict
    ) -> Dict[str, MesoCell]:
        """Create meso-scale grid"""
        min_x = building_bounds.get("min_x", 0)
        max_x = building_bounds.get("max_x", 100)
        min_z = building_bounds.get("min_z", 0)
        max_z = building_bounds.get("max_z", 100)
        
        cells = {}
        cell_id = 0
        
        for x in np.arange(min_x, max_x, self.cell_size):
            for z in np.arange(min_z, max_z, self.cell_size):
                cell_id_str = f"meso_{cell_id}"
                cell = MesoCell(
                    cell_id=cell_id_str,
                    position=(x + self.cell_size/2, 0, z + self.cell_size/2),
                    size=self.cell_size
                )
                cells[cell_id_str] = cell
                cell_id += 1
        
        self.meso_cells = cells
        return cells
    
    def update_ca_state(
        self,
        agents: List[Dict],
        exits: List[Dict]
    ):
        """
        Update CA state based on agent positions
        
        CA transition rules:
        - Agents move to adjacent cells based on density and exit direction
        - Higher density = lower probability of movement
        - Prefer cells closer to exits
        """
        # Reset cells
        for cell in self.meso_cells.values():
            cell.density = 0.0
            cell.agent_ids.clear()
            cell.local_velocity = 0.0
        
        # Assign agents to cells
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            agent_id = agent.get("agent_id")
            agent_x = agent.get("x", 0)
            agent_z = agent.get("z", agent.get("y", 0))
            
            cell_id = self._get_cell_id(agent_x, agent_z)
            if cell_id and cell_id in self.meso_cells:
                cell = self.meso_cells[cell_id]
                cell.agent_ids.append(agent_id)
                cell.density += 1.0 / (self.cell_size * self.cell_size)
        
        # Calculate local velocities and congestion
        for cell in self.meso_cells.values():
            if cell.density > 0:
                # Velocity decreases with density (fundamental diagram)
                base_speed = 1.35  # m/s
                density_factor = parameter_database.get_speed_reduction(cell.density)
                cell.local_velocity = base_speed * density_factor
                
                # Congestion level
                critical_density = 4.0  # persons/m²
                cell.congestion_level = min(1.0, cell.density / critical_density)
    
    def _get_cell_id(self, x: float, z: float) -> Optional[str]:
        """Get meso cell ID for position"""
        cell_x = int(x / self.cell_size) * self.cell_size + self.cell_size/2
        cell_z = int(z / self.cell_size) * self.cell_size + self.cell_size/2
        
        for cell_id, cell in self.meso_cells.items():
            cell_pos_x, _, cell_pos_z = cell.position
            if abs(cell_pos_x - cell_x) < 0.1 and abs(cell_pos_z - cell_z) < 0.1:
                return cell_id
        
        return None
    
    def _initialize_transition_rules(self) -> Dict:
        """Initialize CA transition rules"""
        return {
            "max_density": 4.0,  # persons/m²
            "movement_probability": 0.8,
            "density_penalty": 0.3
        }
    
    def get_ca_density(self, position: Tuple[float, float, float]) -> float:
        """Get density from CA model at position"""
        cell_id = self._get_cell_id(position[0], position[2])
        if cell_id and cell_id in self.meso_cells:
            return self.meso_cells[cell_id].density
        return 0.0

class HybridMultiScaleModel:
    """
    Hybrid multi-scale model combining SFM + CA + ABM
    Couples macro flow with micro agent behavior
    Research: Hybrid models for evacuation (ScienceDirect)
    """
    
    def __init__(
        self,
        macro_cell_size: float = 10.0,
        meso_cell_size: float = 2.0
    ):
        """
        Initialize hybrid multi-scale model
        
        Args:
            macro_cell_size: Size of macro cells (flow model)
            meso_cell_size: Size of meso cells (CA model)
        """
        self.macro_model = MacroFlowModel(macro_cell_size)
        self.ca_model = CellularAutomataModel(meso_cell_size)
        self.use_macro = True
        self.use_ca = True
        self.use_sfm = True  # Agent-based SFM
    
    def initialize(
        self,
        building_bounds: Dict,
        exits: List[Dict]
    ):
        """Initialize all scale models"""
        self.macro_model.create_macro_grid(building_bounds, exits)
        self.ca_model.create_meso_grid(building_bounds)
        logger.info("Initialized hybrid multi-scale model")
    
    def update_all_scales(
        self,
        agents: List[Dict],
        dt: float,
        exits: List[Dict]
    ):
        """
        Update all scale models and couple them
        
        Coupling strategy:
        - Macro provides flow direction guidance
        - CA provides local density information
        - SFM provides individual agent forces
        """
        # Update macro flow
        if self.use_macro:
            self.macro_model.update_macro_flow(agents, dt)
        
        # Update CA state
        if self.use_ca:
            self.ca_model.update_ca_state(agents, exits)
    
    def get_coupled_guidance(
        self,
        agent_position: Tuple[float, float, float],
        agent_attrs: AgentAttributes
    ) -> Dict[str, Any]:
        """
        Get coupled guidance from all scales
        
        Returns:
            Dictionary with guidance from macro, meso, and micro scales
        """
        guidance = {
            "macro_flow": (0.0, 0.0),
            "ca_density": 0.0,
            "ca_congestion": 0.0,
            "recommended_direction": (0.0, 0.0),
            "scale_weights": {}
        }
        
        # Get macro flow direction
        if self.use_macro:
            macro_flow = self.macro_model.get_macro_flow_direction(agent_position)
            guidance["macro_flow"] = macro_flow
            guidance["scale_weights"]["macro"] = 0.3  # 30% weight
        
        # Get CA density and congestion
        if self.use_ca:
            ca_density = self.ca_model.get_ca_density(agent_position)
            guidance["ca_density"] = ca_density
            
            # Get congestion from CA cell
            cell_id = self.ca_model._get_cell_id(agent_position[0], agent_position[2])
            if cell_id and cell_id in self.ca_model.meso_cells:
                cell = self.ca_model.meso_cells[cell_id]
                guidance["ca_congestion"] = cell.congestion_level
                guidance["scale_weights"]["ca"] = 0.2  # 20% weight
        
        # Combine guidance (weighted average)
        # Macro flow provides global direction
        # CA provides local density avoidance
        macro_weight = guidance["scale_weights"].get("macro", 0.0)
        ca_weight = guidance["scale_weights"].get("ca", 0.0)
        sfm_weight = 1.0 - macro_weight - ca_weight  # Remaining for SFM
        
        # Recommended direction combines macro flow (avoid high density from CA)
        macro_vx, macro_vz = guidance["macro_flow"]
        
        # Adjust based on CA congestion (avoid congested areas)
        if guidance["ca_congestion"] > 0.7:
            # High congestion: reduce macro influence, increase avoidance
            macro_vx *= 0.5
            macro_vz *= 0.5
        
        guidance["recommended_direction"] = (macro_vx, macro_vz)
        guidance["scale_weights"]["sfm"] = sfm_weight
        
        return guidance
    
    def apply_hybrid_forces(
        self,
        agent: Dict,
        agent_attrs: AgentAttributes,
        all_agents: List[Dict],
        target_exit: Dict,
        walls: List[Dict]
    ) -> Tuple[float, float]:
        """
        Apply hybrid forces combining SFM + macro + CA guidance
        
        Returns:
            (fx, fz) total force components
        """
        agent_pos = (agent.get("x", 0), agent.get("y", 0), agent.get("z", agent.get("y", 0)))
        
        # Get coupled guidance
        guidance = self.get_coupled_guidance(agent_pos, agent_attrs)
        
        # SFM forces (micro-scale)
        if self.use_sfm:
            sfm_fx, sfm_fz = social_force_model.calculate_forces(
                agent, all_agents, walls, target_exit, agent_attrs.current_panic_level
            )
        else:
            sfm_fx, sfm_fz = 0.0, 0.0
        
        # Macro flow guidance (macro-scale)
        macro_vx, macro_vz = guidance["macro_flow"]
        macro_weight = guidance["scale_weights"].get("macro", 0.0)
        
        # CA density avoidance (meso-scale)
        ca_congestion = guidance["ca_congestion"]
        ca_weight = guidance["scale_weights"].get("ca", 0.0)
        
        # Combine forces
        # SFM provides detailed interactions
        # Macro provides flow direction
        # CA provides density-based adjustments
        
        # Macro flow force (towards flow direction)
        macro_fx = macro_vx * 100.0 * macro_weight  # Scale to force units
        macro_fz = macro_vz * 100.0 * macro_weight
        
        # CA avoidance force (away from high density)
        if ca_congestion > 0.5:
            # Find direction away from congestion
            # (Simplified - would use gradient of density field)
            ca_avoidance_strength = ca_congestion * 200.0 * ca_weight
            # Random direction for now (would use density gradient)
            angle = np.random.uniform(0, 2 * math.pi)
            ca_fx = math.cos(angle) * ca_avoidance_strength
            ca_fz = math.sin(angle) * ca_avoidance_strength
        else:
            ca_fx, ca_fz = 0.0, 0.0
        
        # Total force
        total_fx = sfm_fx + macro_fx + ca_fx
        total_fz = sfm_fz + macro_fz + ca_fz
        
        return total_fx, total_fz
    
    def get_scale_statistics(self) -> Dict[str, Any]:
        """Get statistics from all scales"""
        macro_stats = {
            "cell_count": len(self.macro_model.macro_cells),
            "avg_density": np.mean([c.density for c in self.macro_model.macro_cells.values()]),
            "avg_flow_rate": np.mean([c.flow_rate for c in self.macro_model.macro_cells.values()])
        }
        
        ca_stats = {
            "cell_count": len(self.ca_model.meso_cells),
            "avg_density": np.mean([c.density for c in self.ca_model.meso_cells.values()]),
            "avg_congestion": np.mean([c.congestion_level for c in self.ca_model.meso_cells.values()])
        }
        
        return {
            "macro": macro_stats,
            "meso": ca_stats,
            "micro": {"model": "SFM", "agent_based": True}
        }

# Global hybrid model instance
hybrid_multi_scale_model = HybridMultiScaleModel()

