"""
Shared request/response contracts for simulation-related routes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.core.validation import (
    AgentProfileSchema,
    HazardSchema,
    SimulationConfigSchema,
)


class SimulationResponse(BaseModel):
    id: str
    status: str
    created_at: datetime


class BatchSimulationRequest(BaseModel):
    config: SimulationConfigSchema
    runs: int = Field(..., ge=1, le=50)
    seed_start: Optional[int] = Field(default=None, ge=0)
    seed_step: int = Field(default=1, ge=1, le=1000)
    realtime: bool = False
    max_iterations: Optional[int] = Field(default=None, ge=1, le=5000)


class ScenarioRunRequest(BaseModel):
    floor_plan_id: str = Field(..., min_length=1, max_length=100)
    floor_number: Optional[int] = Field(default=None, ge=1, le=100)
    num_agents: Optional[int] = Field(default=None, ge=1, le=10000)
    emergency_type: Optional[str] = Field(default=None)
    panic_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    exits: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    hazards: List[HazardSchema] = Field(default_factory=list, max_length=200)
    agent_profiles: List[AgentProfileSchema] = Field(default_factory=list, max_length=50)
    blocked_exits: List[str] = Field(default_factory=list, max_length=200)
    parameter_overrides: Dict[str, float] = Field(default_factory=dict)
    ablation: Optional[Dict[str, bool]] = None
    max_iterations: Optional[int] = Field(default=None, ge=1, le=100000)
    realtime: Optional[bool] = None
    seed: Optional[int] = Field(default=None, ge=0)
    tags: List[str] = Field(default_factory=list, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=2000)
    label: Optional[str] = Field(default=None, max_length=200)
    priority: Optional[int] = Field(default=None, ge=1, le=10)
    record_frames: Optional[bool] = None
    frame_stride: Optional[int] = Field(default=None, ge=1, le=100)
    store_agents: Optional[bool] = None
    store_bottlenecks: Optional[bool] = None
    store_walls: Optional[bool] = None
    store_exits: Optional[bool] = None
    store_obstacles: Optional[bool] = None
    store_hazards: Optional[bool] = None
    max_runtime_seconds: Optional[float] = Field(default=None, ge=1.0, le=36000)


class ScenarioStartRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    base_config: Optional[SimulationConfigSchema] = None
    runs: List[ScenarioRunRequest]


class SimulationCommandRequest(BaseModel):
    type: Literal["close_exit", "redirect_crowd", "trigger_fire_door", "emergency_announcement"]
    exit_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    target_exit: Optional[str] = Field(default=None, min_length=1, max_length=100)
    door_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    message: Optional[str] = Field(default=None, min_length=1, max_length=2000)
