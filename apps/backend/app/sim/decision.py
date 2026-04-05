"""
Decision models wrapper for research-grade behavior selection.
"""
from typing import Dict, List
from app.services.behavioral_models import behavioral_engine


def choose_exit(agent_behavior, agent_position, exits: List[Dict], nearby_agents: List[Dict], current_time: float) -> str:
    return behavioral_engine.choose_exit(agent_behavior, agent_position, exits, nearby_agents, current_time)
