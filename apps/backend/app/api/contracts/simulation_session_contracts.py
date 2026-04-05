"""
Canonical v3 simulation session contracts.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.validation import AgentProfileSchema, BoundarySchema, ExitSchema, HazardSchema


SimulationMode = Literal["studio", "batch", "validation"]
SimulationEventType = Literal[
    "state_change",
    "hazard_activation",
    "reroute",
    "bottleneck",
    "exit_closed",
    "exit_opened",
    "run_completed",
    "run_error",
]
SimulationControlAction = Literal[
    "start",
    "pause",
    "resume",
    "stop",
    "reset",
    "close_exit",
    "open_exit",
    "redirect_crowd",
    "emergency_announcement",
]


class SimulationStoragePolicySchema(BaseModel):
    record_frames: bool = True
    max_frames: int = Field(default=1200, ge=20, le=10000)
    frame_stride: int = Field(default=1, ge=1, le=100)
    persist_frames: bool = True


class SimulationSessionConfigSchema(BaseModel):
    floor_plan_ref: Optional[str] = Field(default=None, min_length=1, max_length=100)
    floor_plan_snapshot: Optional[Dict[str, Any]] = None
    floor_number: int = Field(default=1, ge=1, le=100)
    mode: SimulationMode = "studio"
    num_agents: int = Field(..., ge=1, le=10000)
    emergency_type: str = Field(default="fire", min_length=1, max_length=64)
    routing_policy: str = Field(default="shortest_path", min_length=1, max_length=100)
    panic_level: float = Field(default=0.45, ge=0.0, le=1.0)
    seed: Optional[int] = Field(default=None, ge=0)
    hazards: List[HazardSchema] = Field(default_factory=list, max_length=200)
    agent_profiles: List[AgentProfileSchema] = Field(default_factory=list, max_length=50)
    blocked_exits: List[str] = Field(default_factory=list, max_length=200)
    exits: List[ExitSchema] = Field(default_factory=list, max_length=100)
    boundary: Optional[BoundarySchema] = None
    parameter_overrides: Dict[str, float] = Field(default_factory=dict)
    storage_policy: SimulationStoragePolicySchema = Field(default_factory=SimulationStoragePolicySchema)
    max_runtime_seconds: Optional[float] = Field(default=180.0, ge=5.0, le=36000.0)

    model_config = ConfigDict(extra="ignore")


class SimulationSessionStateSchema(BaseModel):
    status: str = "draft"
    connection_state: str = "idle"
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    frame_count: int = 0
    event_count: int = 0
    latest_frame_id: Optional[int] = None
    latest_timestamp: Optional[float] = None
    latest_error: Optional[str] = None


class SimulationSessionSchema(BaseModel):
    id: str
    config: SimulationSessionConfigSchema
    state: SimulationSessionStateSchema
    created_at: datetime
    updated_at: datetime
    analysis_available: bool = False
    replay_available: bool = False
    status_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class SimulationControlCommandSchema(BaseModel):
    action: SimulationControlAction
    exit_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    target_exit: Optional[str] = Field(default=None, min_length=1, max_length=100)
    message: Optional[str] = Field(default=None, min_length=1, max_length=2000)


class SimulationEventSchema(BaseModel):
    event_id: str
    session_id: str
    type: SimulationEventType
    timestamp: float = Field(..., ge=0.0, le=36000.0)
    frame_id: Optional[int] = Field(default=None, ge=0)
    severity: str = Field(default="info", min_length=1, max_length=32)
    title: str = Field(..., min_length=1, max_length=240)
    message: str = Field(..., min_length=1, max_length=4000)
    data: Dict[str, Any] = Field(default_factory=dict)


class SimulationAnalysisSnapshotSchema(BaseModel):
    session_id: str
    status: str
    simulation_time: float = Field(default=0.0, ge=0.0, le=36000.0)
    frame_count: int = Field(default=0, ge=0)
    total_agents: int = Field(default=0, ge=0)
    evacuated: int = Field(default=0, ge=0)
    remaining: int = Field(default=0, ge=0)
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    flow_rate: float = 0.0
    peak_density: float = 0.0
    exit_usage: Dict[str, int] = Field(default_factory=dict)
    profile_counts: Dict[str, int] = Field(default_factory=dict)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    event_markers: List[Dict[str, Any]] = Field(default_factory=list)
    density_heatmap: List[List[float]] = Field(default_factory=list)
    final_summary: Dict[str, Any] = Field(default_factory=dict)


class SimulationReplaySliceSchema(BaseModel):
    session_id: str
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=120, ge=1, le=2000)
    count: int = Field(default=0, ge=0)
    frames: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[SimulationEventSchema] = Field(default_factory=list)


class SimulationStreamDescriptorSchema(BaseModel):
    session_id: str
    websocket_path: str
    latest_frame: Optional[Dict[str, Any]] = None
    recent_events: List[SimulationEventSchema] = Field(default_factory=list)
    connection_state: str = "idle"
