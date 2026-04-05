"""
Experiment configuration schema.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from .ablation import AblationConfig


class ExperimentConfig(BaseModel):
    name: str = Field(..., min_length=1)
    engine: str = Field("core", pattern="^(core|legacy)$")
    seed: int = 42
    num_agents: int = Field(100, ge=1, le=10000)
    emergency_type: str = "fire"
    floor_number: int = 1
    floor_plan_id: Optional[str] = None
    duration_seconds: int = 120
    ablation: AblationConfig = Field(default_factory=AblationConfig)
    metadata: Dict[str, Any] = Field(default_factory=dict)
