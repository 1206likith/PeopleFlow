from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional

class Exit(BaseModel):
    id: str
    x: float
    y: float
    z: float
    width: float

class SimulationConfig(BaseModel):
    floor_plan_id: Optional[str] = None
    num_agents: int = 100
    emergency_type: str = "fire"
    panic_level: float = 0.5
    exits: List[Exit] = []
    hazards: List[Dict[str, Any]] = []
    agent_profiles: List[Dict[str, Any]] = []
    blocked_exits: List[str] = []
    parameter_overrides: Dict[str, float] = {}
    ablation: Dict[str, bool] = {}
    max_iterations: Optional[int] = None
    realtime: Optional[bool] = None
    seed: Optional[int] = None

class Simulation(BaseModel):
    id: Optional[str] = None
    user_id: str
    floor_plan_id: Optional[str] = None
    num_agents: int
    emergency_type: str
    panic_level: float
    exits: List[Dict[str, Any]]
    hazards: List[Dict[str, Any]] = []
    agent_profiles: List[Dict[str, Any]] = []
    blocked_exits: List[str] = []
    parameter_overrides: Dict[str, float] = {}
    ablation: Dict[str, bool] = {}
    max_iterations: Optional[int] = None
    realtime: Optional[bool] = None
    seed: Optional[int] = None
    status: str  # running, paused, completed
    created_at: datetime
    updated_at: datetime

