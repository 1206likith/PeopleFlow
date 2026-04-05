from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class AgentProfile(str, Enum):
    NORMAL_ADULT = "normal_adult"
    ELDERLY = "elderly"
    INJURED = "injured"
    CHILD = "child"
    DISABLED = "disabled"


@dataclass
class AgentState:
    agent_id: int
    x: float
    y: float
    z: float
    speed: float
    status: str
    panic_level: float = 0.0
    stress_level: float = 0.0
    profile: AgentProfile = AgentProfile.NORMAL_ADULT
    decision_model: Optional[str] = None
    metadata: Optional[Dict] = None
