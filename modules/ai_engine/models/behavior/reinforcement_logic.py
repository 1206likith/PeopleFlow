"""
Reinforcement Learning Logic
Reward functions and decision-making for evacuation agents
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class AgentState:
    """Represents the state of an agent"""
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    distance_to_exit: float
    distance_to_danger: float
    in_crowd: bool
    panic_level: float
    time_elapsed: float


class RewardFunction:
    """
    Defines reward function for reinforcement learning
    Encourages efficient evacuation while avoiding danger
    """
    
    def __init__(
        self,
        exit_reward: float = 100.0,
        step_penalty: float = -0.1,
        danger_penalty: float = -10.0,
        crowd_penalty: float = -0.5,
        progress_reward: float = 1.0
    ):
        """
        Initialize reward function
        
        Args:
            exit_reward: Reward for reaching exit
            step_penalty: Penalty per step (encourages speed)
            danger_penalty: Penalty for being near danger
            crowd_penalty: Penalty for high crowd density
            progress_reward: Reward for making progress toward exit
        """
        self.exit_reward = exit_reward
        self.step_penalty = step_penalty
        self.danger_penalty = danger_penalty
        self.crowd_penalty = crowd_penalty
        self.progress_reward = progress_reward
    
    def calculate_reward(
        self,
        current_state: AgentState,
        previous_state: Optional[AgentState],
        action_taken: str,
        reached_exit: bool = False
    ) -> float:
        """
        Calculate reward for agent action
        
        Args:
            current_state: Current agent state
            previous_state: Previous agent state (for progress calculation)
            action_taken: Action that was taken
            reached_exit: Whether agent reached exit
            
        Returns:
            Reward value
        """
        reward = 0.0
        
        # Large reward for reaching exit
        if reached_exit:
            reward += self.exit_reward
            # Bonus for quick evacuation
            time_bonus = max(0, 100.0 - current_state.time_elapsed)
            reward += time_bonus
            return reward
        
        # Step penalty (encourages efficiency)
        reward += self.step_penalty
        
        # Progress reward (moving closer to exit)
        if previous_state:
            progress = previous_state.distance_to_exit - current_state.distance_to_exit
            if progress > 0:
                reward += self.progress_reward * progress
            elif progress < 0:
                reward += self.progress_reward * progress * 0.5  # Smaller penalty for moving away
        
        # Danger penalty
        if current_state.distance_to_danger < 5.0:
            danger_factor = 1.0 - (current_state.distance_to_danger / 5.0)
            reward += self.danger_penalty * danger_factor
        
        # Crowd penalty (encourages avoiding bottlenecks)
        if current_state.in_crowd:
            reward += self.crowd_penalty
        
        # Panic penalty (encourages calm behavior)
        if current_state.panic_level > 0.7:
            reward += -2.0 * current_state.panic_level
        
        return reward
    
    def get_reward_components(
        self,
        current_state: AgentState,
        previous_state: Optional[AgentState],
        reached_exit: bool
    ) -> Dict[str, float]:
        """
        Get breakdown of reward components (for analysis)
        
        Returns:
            Dictionary with reward components
        """
        components = {
            "exit_reward": self.exit_reward if reached_exit else 0.0,
            "step_penalty": self.step_penalty,
            "danger_penalty": 0.0,
            "crowd_penalty": 0.0,
            "progress_reward": 0.0,
        }
        
        if not reached_exit:
            if current_state.distance_to_danger < 5.0:
                danger_factor = 1.0 - (current_state.distance_to_danger / 5.0)
                components["danger_penalty"] = self.danger_penalty * danger_factor
            
            if current_state.in_crowd:
                components["crowd_penalty"] = self.crowd_penalty
            
            if previous_state:
                progress = previous_state.distance_to_exit - current_state.distance_to_exit
                if progress > 0:
                    components["progress_reward"] = self.progress_reward * progress
        
        return components


class ActionSelector:
    """
    Selects actions for agents based on state
    Can be used for rule-based behavior or combined with RL
    """
    
    def __init__(self, use_rl: bool = True):
        """
        Initialize action selector
        
        Args:
            use_rl: Whether to use RL model or rule-based
        """
        self.use_rl = use_rl
    
    def select_action(
        self,
        state: AgentState,
        available_actions: List[str],
        rl_model=None
    ) -> str:
        """
        Select action based on state
        
        Args:
            state: Current agent state
            available_actions: List of available actions
            rl_model: RL model (if using RL)
            
        Returns:
            Selected action
        """
        if self.use_rl and rl_model:
            # Use RL model to select action
            # This would typically use the model's predict method
            # For now, return a placeholder
            return available_actions[0] if available_actions else "wait"
        else:
            # Rule-based action selection
            return self._rule_based_action(state, available_actions)
    
    def _rule_based_action(
        self,
        state: AgentState,
        available_actions: List[str]
    ) -> str:
        """Rule-based action selection"""
        # Prioritize moving toward exit
        if "move_to_exit" in available_actions:
            return "move_to_exit"
        
        # Avoid danger
        if state.distance_to_danger < 3.0 and "avoid_danger" in available_actions:
            return "avoid_danger"
        
        # Default to first available action
        return available_actions[0] if available_actions else "wait"


def create_reward_function(config: Dict = None) -> RewardFunction:
    """
    Factory function to create reward function
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured RewardFunction
    """
    if config is None:
        config = {}
    
    return RewardFunction(
        exit_reward=config.get("exit_reward", 100.0),
        step_penalty=config.get("step_penalty", -0.1),
        danger_penalty=config.get("danger_penalty", -10.0),
        crowd_penalty=config.get("crowd_penalty", -0.5),
        progress_reward=config.get("progress_reward", 1.0)
    )


if __name__ == "__main__":
    # Example usage
    reward_fn = RewardFunction()
    action_selector = ActionSelector(use_rl=False)
    
    # Example states
    prev_state = AgentState(
        position=(10.0, 0.0, 10.0),
        velocity=(1.0, 0.0, 1.0),
        distance_to_exit=15.0,
        distance_to_danger=8.0,
        in_crowd=False,
        panic_level=0.3,
        time_elapsed=5.0
    )
    
    curr_state = AgentState(
        position=(9.0, 0.0, 9.0),
        velocity=(1.0, 0.0, 1.0),
        distance_to_exit=12.7,  # Closer to exit
        distance_to_danger=7.0,
        in_crowd=True,
        panic_level=0.4,
        time_elapsed=6.0
    )
    
    reward = reward_fn.calculate_reward(curr_state, prev_state, "move_forward")
    components = reward_fn.get_reward_components(curr_state, prev_state, False)
    
    print(f"Reward: {reward:.2f}")
    print("Components:")
    for key, value in components.items():
        print(f"  {key}: {value:.2f}")

