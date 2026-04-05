"""
Group Dynamics & Social Interactions
Implements family groups, leaders/followers, cooperation vs selfish movement
Research: Group behavior in evacuation (ScienceDirect)
"""

import math
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.services.heterogeneous_agents import AgentAttributes

logger = logging.getLogger(__name__)

class GroupType(Enum):
    """Types of groups"""
    FAMILY = "family"
    FRIENDS = "friends"
    WORK_COLLEAGUES = "work_colleagues"
    STRANGERS = "strangers"  # Temporary grouping

@dataclass
class Group:
    """Represents a group of agents"""
    group_id: int
    group_type: GroupType
    member_ids: Set[int] = field(default_factory=set)
    leader_id: Optional[int] = None
    cohesion_strength: float = 1.0  # 0-1, how strongly group stays together
    cooperation_level: float = 0.8  # 0-1, willingness to help each other
    target_exit: Optional[str] = None
    is_evacuating: bool = False
    
    def add_member(self, agent_id: int):
        """Add member to group"""
        self.member_ids.add(agent_id)
    
    def remove_member(self, agent_id: int):
        """Remove member from group"""
        self.member_ids.discard(agent_id)
    
    def get_size(self) -> int:
        """Get group size"""
        return len(self.member_ids)
    
    def has_member(self, agent_id: int) -> bool:
        """Check if agent is in group"""
        return agent_id in self.member_ids

class GroupDynamicsEngine:
    """
    Manages group dynamics and social interactions
    Handles family groups, leader-follower relationships, cooperation
    """
    
    def __init__(self):
        self.groups: Dict[int, Group] = {}
        self.agent_to_group: Dict[int, int] = {}  # agent_id -> group_id
        self.next_group_id = 1
    
    def create_group(
        self,
        group_type: GroupType,
        member_ids: List[int],
        leader_id: Optional[int] = None
    ) -> Group:
        """Create a new group"""
        group = Group(
            group_id=self.next_group_id,
            group_type=group_type,
            leader_id=leader_id
        )
        
        for agent_id in member_ids:
            group.add_member(agent_id)
            self.agent_to_group[agent_id] = group.group_id
        
        # Set cohesion based on group type
        if group_type == GroupType.FAMILY:
            group.cohesion_strength = 0.95
            group.cooperation_level = 0.95
        elif group_type == GroupType.FRIENDS:
            group.cohesion_strength = 0.75
            group.cooperation_level = 0.80
        elif group_type == GroupType.WORK_COLLEAGUES:
            group.cohesion_strength = 0.60
            group.cooperation_level = 0.70
        else:  # STRANGERS
            group.cohesion_strength = 0.30
            group.cooperation_level = 0.40
        
        self.groups[group.group_id] = group
        self.next_group_id += 1
        
        return group
    
    def get_agent_group(self, agent_id: int) -> Optional[Group]:
        """Get group for an agent"""
        group_id = self.agent_to_group.get(agent_id)
        if group_id:
            return self.groups.get(group_id)
        return None
    
    def calculate_group_cohesion_force(
        self,
        agent_id: int,
        agent_position: Tuple[float, float, float],
        all_agents: List[Dict]
    ) -> Tuple[float, float]:
        """
        Calculate force to keep group together
        
        Returns:
            (fx, fz) cohesion force components
        """
        group = self.get_agent_group(agent_id)
        if not group or group.get_size() < 2:
            return 0.0, 0.0
        
        agent_x, agent_y, agent_z = agent_position
        
        # Find group center (average position of group members)
        group_center_x = 0.0
        group_center_z = 0.0
        member_count = 0
        
        for other_agent in all_agents:
            other_id = other_agent.get("agent_id")
            if other_id and group.has_member(other_id) and other_id != agent_id:
                other_x = other_agent.get("x", 0)
                other_z = other_agent.get("z", other_agent.get("y", 0))
                group_center_x += other_x
                group_center_z += other_z
                member_count += 1
        
        if member_count == 0:
            return 0.0, 0.0
        
        group_center_x /= member_count
        group_center_z /= member_count
        
        # Calculate direction to group center
        dx = group_center_x - agent_x
        dz = group_center_z - agent_z
        distance = math.sqrt(dx * dx + dz * dz)
        
        # Cohesion force (stronger when further from group)
        if distance > 0.01:
            # Desired separation distance (research: ~2-3m for families)
            desired_separation = 2.0 if group.group_type == GroupType.FAMILY else 3.0
            
            if distance > desired_separation:
                # Pull towards group
                force_strength = group.cohesion_strength * 500.0 * (distance - desired_separation)
                fx = (dx / distance) * force_strength
                fz = (dz / distance) * force_strength
                return fx, fz
        
        return 0.0, 0.0
    
    def calculate_leader_following_force(
        self,
        agent_id: int,
        agent_position: Tuple[float, float, float],
        all_agents: List[Dict]
    ) -> Tuple[float, float, Optional[int]]:
        """
        Calculate force to follow leader
        
        Returns:
            (fx, fz, leader_id) force components and leader ID
        """
        group = self.get_agent_group(agent_id)
        if not group or not group.leader_id or group.leader_id == agent_id:
            return 0.0, 0.0, None
        
        # Find leader position
        leader_agent = None
        for agent in all_agents:
            if agent.get("agent_id") == group.leader_id:
                leader_agent = agent
                break
        
        if not leader_agent:
            return 0.0, 0.0, None
        
        agent_x, agent_y, agent_z = agent_position
        leader_x = leader_agent.get("x", 0)
        leader_z = leader_agent.get("z", leader_agent.get("y", 0))
        
        # Calculate direction to leader
        dx = leader_x - agent_x
        dz = leader_z - agent_z
        distance = math.sqrt(dx * dx + dz * dz)
        
        # Follow force (stronger when further from leader)
        max_follow_distance = 5.0  # meters
        if distance > max_follow_distance:
            force_strength = 400.0 * (distance - max_follow_distance)
            if distance > 0.01:
                fx = (dx / distance) * force_strength
                fz = (dz / distance) * force_strength
                return fx, fz, group.leader_id
        
        return 0.0, 0.0, group.leader_id
    
    def should_wait_for_group(
        self,
        agent_id: int,
        agent_attrs: AgentAttributes,
        group_members: List[Dict]
    ) -> bool:
        """
        Determine if agent should wait for slower group members
        
        Research: Family groups often wait for slower members
        """
        group = self.get_agent_group(agent_id)
        if not group or group.group_type != GroupType.FAMILY:
            return False
        
        # Check if any group members are far behind
        agent_pos = None
        for agent in group_members:
            if agent.get("agent_id") == agent_id:
                agent_pos = (agent.get("x", 0), agent.get("y", 0), agent.get("z", agent.get("y", 0)))
                break
        
        if not agent_pos:
            return False
        
        # Find furthest group member
        max_distance = 0.0
        for member in group_members:
            if member.get("agent_id") == agent_id:
                continue
            member_pos = (member.get("x", 0), member.get("y", 0), member.get("z", member.get("y", 0)))
            distance = math.sqrt(
                (agent_pos[0] - member_pos[0])**2 +
                (agent_pos[2] - member_pos[2])**2
            )
            max_distance = max(max_distance, distance)
        
        # Wait if group member is more than 5m behind
        wait_threshold = 5.0
        return max_distance > wait_threshold
    
    def calculate_cooperation_behavior(
        self,
        agent_id: int,
        agent_attrs: AgentAttributes,
        nearby_agents: List[Dict]
    ) -> Dict[str, any]:
        """
        Calculate cooperation behavior (helping others)
        
        Returns:
            Dictionary with cooperation actions
        """
        group = self.get_agent_group(agent_id)
        cooperation_level = group.cooperation_level if group else agent_attrs.cooperation_level
        
        cooperation_actions = {
            "help_injured": False,
            "guide_blind": False,
            "carry_child": False,
            "share_information": False
        }
        
        # Only cooperate if cooperation level is high enough
        if cooperation_level < 0.5:
            return cooperation_actions
        
        # Check for opportunities to help
        for other_agent in nearby_agents:
            other_id = other_agent.get("agent_id")
            if other_id == agent_id:
                continue
            
            # Help injured agents (if in same group or high cooperation)
            if other_agent.get("health_status") == "severe_injury":
                if group and group.has_member(other_id):
                    cooperation_actions["help_injured"] = True
                elif cooperation_level > 0.7:
                    cooperation_actions["help_injured"] = True
            
            # Guide visually impaired (if in same group)
            if other_agent.get("disability_type") == "visually_impaired":
                if group and group.has_member(other_id):
                    cooperation_actions["guide_blind"] = True
            
            # Carry children (family groups)
            if other_agent.get("age_group") == "child":
                if group and group.has_member(other_id) and group.group_type == GroupType.FAMILY:
                    cooperation_actions["carry_child"] = True
        
        # Share information about exits (if familiar with building)
        if agent_attrs.environment_knowledge > 0.7 and cooperation_level > 0.6:
            cooperation_actions["share_information"] = True
        
        return cooperation_actions
    
    def update_group_decision(
        self,
        group_id: int,
        suggested_exit: str,
        all_agents: List[Dict]
    ):
        """Update group's collective exit decision"""
        group = self.groups.get(group_id)
        if not group:
            return
        
        # Group decision: leader decides, or majority vote
        if group.leader_id:
            # Leader makes decision
            group.target_exit = suggested_exit
        else:
            # Majority vote (simplified)
            exit_votes = {}
            for agent in all_agents:
                if group.has_member(agent.get("agent_id")):
                    exit_id = agent.get("target_exit")
                    if exit_id:
                        exit_votes[exit_id] = exit_votes.get(exit_id, 0) + 1
            
            if exit_votes:
                group.target_exit = max(exit_votes.items(), key=lambda x: x[1])[0]
            else:
                group.target_exit = suggested_exit
        
        group.is_evacuating = True

# Global group dynamics engine
group_dynamics = GroupDynamicsEngine()

