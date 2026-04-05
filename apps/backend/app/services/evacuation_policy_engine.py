"""
Evacuation Policy Lab
Allows toggling different evacuation strategies:
- Nearest-exit
- Least-crowded
- Follow-leader
- Random-panic
- Authority-directed
"""
import math
import random
import logging
from typing import List, Dict, Optional
from app.services.evacuation_parameters import EvacuationPolicy, parameter_database

logger = logging.getLogger(__name__)

class PolicyEngine:
    """
    Evacuation policy engine
    Implements different evacuation strategies
    """
    
    def __init__(self, policy: EvacuationPolicy = EvacuationPolicy.NEAREST_EXIT):
        self.policy = policy
        self.leaders = []  # Track leader agents
        self.authority_directives = {}  # Authority commands
    
    def choose_exit(
        self,
        agent: Dict,
        agent_position: tuple,
        exits: List[Dict],
        nearby_agents: List[Dict],
        current_time: float
    ) -> Optional[str]:
        """
        Choose exit based on current policy
        
        Args:
            agent: Agent data
            agent_position: (x, y, z) position
            exits: Available exits
            nearby_agents: Nearby agents for group behavior
            current_time: Current simulation time
        
        Returns:
            Exit ID or None
        """
        if not exits:
            return None
        
        agent_x, agent_y, agent_z = agent_position
        
        if self.policy == EvacuationPolicy.NEAREST_EXIT:
            return self._nearest_exit(agent_x, agent_z, exits)
        
        elif self.policy == EvacuationPolicy.LEAST_CROWDED:
            return self._least_crowded_exit(agent_x, agent_z, exits, nearby_agents)
        
        elif self.policy == EvacuationPolicy.FOLLOW_LEADER:
            return self._follow_leader(agent, exits, nearby_agents)
        
        elif self.policy == EvacuationPolicy.RANDOM_PANIC:
            return self._random_panic_exit(exits, agent.get("panic_level", 0.0))
        
        elif self.policy == EvacuationPolicy.AUTHORITY_DIRECTED:
            return self._authority_directed(agent, exits)
        
        # Default to nearest
        return self._nearest_exit(agent_x, agent_z, exits)
    
    def _nearest_exit(self, x: float, z: float, exits: List[Dict]) -> str:
        """Nearest exit policy"""
        min_dist = float('inf')
        nearest_id = None
        
        for exit_data in exits:
            exit_x = exit_data.get("x", 0.0)
            exit_z = exit_data.get("z", exit_data.get("y", 0.0))
            
            dist = math.sqrt((x - exit_x)**2 + (z - exit_z)**2)
            if dist < min_dist:
                min_dist = dist
                nearest_id = exit_data.get("id", f"exit_{exits.index(exit_data)}")
        
        return nearest_id
    
    def _least_crowded_exit(
        self,
        x: float,
        z: float,
        exits: List[Dict],
        nearby_agents: List[Dict]
    ) -> str:
        """Least crowded exit policy"""
        best_exit = None
        best_score = float('inf')
        
        for exit_data in exits:
            exit_x = exit_data.get("x", 0.0)
            exit_z = exit_data.get("z", exit_data.get("y", 0.0))
            
            # Distance to exit
            dist = math.sqrt((x - exit_x)**2 + (z - exit_z)**2)
            
            # Count agents heading to this exit
            agents_to_exit = sum(
                1 for agent in nearby_agents
                if agent.get("target_exit") == exit_data.get("id")
            )
            
            # Score = distance + crowding penalty
            crowding_penalty = agents_to_exit * 5.0  # 5m penalty per agent
            score = dist + crowding_penalty
            
            if score < best_score:
                best_score = score
                best_exit = exit_data.get("id", f"exit_{exits.index(exit_data)}")
        
        return best_exit
    
    def _follow_leader(
        self,
        agent: Dict,
        exits: List[Dict],
        nearby_agents: List[Dict]
    ) -> Optional[str]:
        """Follow leader policy"""
        # Check if agent is a leader
        if agent.get("personality") == "leader":
            # Leaders use least-crowded strategy
            agent_x = agent.get("x", 0.0)
            agent_z = agent.get("z", agent.get("y", 0.0))
            return self._least_crowded_exit(agent_x, agent_z, exits, nearby_agents)
        
        # Find nearest leader
        agent_x = agent.get("x", 0.0)
        agent_z = agent.get("z", agent.get("y", 0.0))
        
        influence_radius = parameter_database.get_leader_influence_radius()
        nearest_leader = None
        min_leader_dist = float('inf')
        
        for other in nearby_agents:
            if other.get("personality") == "leader":
                other_x = other.get("x", 0.0)
                other_z = other.get("z", other.get("y", 0.0))
                
                dist = math.sqrt((agent_x - other_x)**2 + (agent_z - other_z)**2)
                if dist < influence_radius and dist < min_leader_dist:
                    min_leader_dist = dist
                    nearest_leader = other
        
        if nearest_leader:
            # Follow leader's exit choice
            return nearest_leader.get("target_exit")
        
        # No leader nearby, use nearest exit
        return self._nearest_exit(agent_x, agent_z, exits)
    
    def _random_panic_exit(self, exits: List[Dict], panic_level: float) -> str:
        """Random panic policy (higher panic = more random)"""
        if panic_level > 0.7:
            # High panic: completely random
            exit_data = random.choice(exits)
        else:
            # Low panic: weighted by distance
            # Simplified - in reality would weight by distance
            exit_data = random.choice(exits)
        
        return exit_data.get("id", f"exit_{exits.index(exit_data)}")
    
    def _authority_directed(self, agent: Dict, exits: List[Dict]) -> Optional[str]:
        """Authority-directed policy"""
        agent_id = agent.get("agent_id")
        
        # Check if authority has directed this agent
        if agent_id in self.authority_directives:
            directed_exit = self.authority_directives[agent_id]
            # Verify exit still exists
            for exit_data in exits:
                if exit_data.get("id") == directed_exit:
                    return directed_exit
        
        # No directive, use nearest
        agent_x = agent.get("x", 0.0)
        agent_z = agent.get("z", agent.get("y", 0.0))
        return self._nearest_exit(agent_x, agent_z, exits)
    
    def set_authority_directive(self, agent_id: int, exit_id: str):
        """Set authority directive for an agent"""
        self.authority_directives[agent_id] = exit_id
    
    def clear_authority_directives(self):
        """Clear all authority directives"""
        self.authority_directives.clear()
    
    def set_policy(self, policy: EvacuationPolicy):
        """Change evacuation policy"""
        self.policy = policy
        logger.info(f"Changed evacuation policy to: {policy.value}")

# Global policy engine
policy_engine = PolicyEngine()

