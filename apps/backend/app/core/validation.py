"""
Comprehensive validation schemas for production-grade API
"""
from importlib.util import find_spec
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from enum import Enum


if find_spec("email_validator") is not None:
    from pydantic import EmailStr as EmailField
else:
    # Keep backend startup/test flows lightweight when auth extras are not installed.
    EmailField = Annotated[
        str,
        Field(
            min_length=3,
            max_length=254,
            pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        ),
    ]


class EmergencyType(str, Enum):
    FIRE = "fire"
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    BOMB_BLAST = "bomb_blast"
    GAS_LEAK = "gas_leak"
    TERRORIST = "terrorist"
    MEDICAL = "medical"
    OTHER = "other"


class HazardTypeSchema(str, Enum):
    FIRE = "fire"
    SMOKE = "smoke"
    FLOOD = "flood"
    GAS_LEAK = "gas_leak"
    EARTHQUAKE = "earthquake"
    TACTICAL_ATTACK = "tactical_attack"
    STRUCTURAL_COLLAPSE = "structural_collapse"
    BLOCKED_EXIT = "blocked_exit"


class HazardSchema(BaseModel):
    """Hazard configuration schema"""
    id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    type: HazardTypeSchema = HazardTypeSchema.FIRE
    x: float = Field(default=0.0, ge=-10000, le=10000)
    y: float = Field(default=0.0, ge=-10000, le=10000)
    z: float = Field(default=0.0, ge=-10000, le=10000)
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    radius: float = Field(default=10.0, ge=0.1, le=10000)
    start_time: float = Field(default=0.0, ge=0.0, le=3600)
    duration: Optional[float] = Field(default=None, ge=0.0, le=3600)
    exit_id: Optional[str] = Field(default=None, min_length=1, max_length=100)
    exit_ids: List[str] = Field(default_factory=list, max_length=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("exit_ids", mode="before")
    def normalize_exit_ids(cls, v, info):
        if v:
            return v
        exit_id = info.data.get("exit_id") if info.data else None
        if exit_id:
            return [exit_id]
        return []


class AgentProfileSchema(BaseModel):
    """Agent profile / behavior group schema"""
    name: str = Field(..., min_length=1, max_length=100)
    ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    count: Optional[int] = Field(default=None, ge=1, le=100000)
    population_profile: Optional[str] = Field(default=None, max_length=50)
    role: Optional[str] = Field(default=None, max_length=50)
    personality_type: Optional[str] = Field(default=None, max_length=50)
    decision_model: Optional[str] = Field(default=None, max_length=50)
    speed_multiplier: float = Field(default=1.0, ge=0.1, le=3.0)
    pre_evacuation_delay: Optional[float] = Field(default=None, ge=0.0, le=300.0)
    panic_bias: float = Field(default=0.0, ge=-1.0, le=1.0)
    stress_bias: float = Field(default=0.0, ge=-1.0, le=1.0)
    familiarity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    base_speed: Optional[float] = Field(default=None, ge=0.1, le=6.0)
    max_speed: Optional[float] = Field(default=None, ge=0.1, le=8.0)
    reaction_time: Optional[float] = Field(default=None, ge=0.0, le=30.0)
    panic_susceptibility: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mobility: Optional[float] = Field(default=None, ge=0.1, le=3.0)
    compliance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    group_cohesion: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    patience: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    vision_range: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    hazard_aversion: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    staff: Optional[bool] = None
    mobility_limited: Optional[bool] = None
    needs_assistance: Optional[bool] = None

    model_config = ConfigDict(extra="allow")


class AblationSchema(BaseModel):
    """Feature toggle schema for simulation ablations"""
    use_social_force: Optional[bool] = True
    use_pathfinding: Optional[bool] = True
    use_behavioral_decisions: Optional[bool] = True
    use_hazard_effects: Optional[bool] = True


class ExitSchema(BaseModel):
    """Exit point schema"""
    id: str = Field(..., min_length=1, max_length=50)
    x: float = Field(..., ge=-10000, le=10000)
    y: float = Field(..., ge=-10000, le=10000)
    z: Optional[float] = Field(default=None, ge=-10000, le=10000)
    width: float = Field(default=2.0, ge=0.5, le=10.0)
    capacity: int = Field(default=100, ge=1, le=10000)
    floor_number: Optional[int] = Field(default=None, ge=1, le=100)


class ManualExitSchema(BaseModel):
    """Manual exit input schema (id optional)."""
    id: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, max_length=100)
    x: float = Field(..., ge=-10000, le=10000)
    y: float = Field(..., ge=-10000, le=10000)
    z: Optional[float] = Field(default=None, ge=-10000, le=10000)
    width: float = Field(default=2.0, ge=0.5, le=50.0)
    height: Optional[float] = Field(default=None, ge=0.5, le=50.0)
    capacity: Optional[int] = Field(default=None, ge=1, le=10000)
    floor_number: Optional[int] = Field(default=None, ge=1, le=100)
    is_emergency: Optional[bool] = True
    is_accessible: Optional[bool] = True
    source: Optional[str] = None


class FloorSchema(BaseModel):
    """Floor schema for multi-floor buildings"""
    floorNumber: int = Field(..., ge=1, le=100)
    name: str = Field(..., min_length=1, max_length=100)
    exits: List[ExitSchema] = Field(default_factory=list, max_length=50)
    width: float = Field(default=100.0, ge=10, le=10000)
    height: float = Field(default=100.0, ge=10, le=10000)


class BuildingPlanUpload(BaseModel):
    """Building plan upload schema"""
    buildingName: str = Field(..., min_length=1, max_length=200)
    floors: List[FloorSchema] = Field(..., min_length=1, max_length=100)
    
    @field_validator("floors")
    def validate_floor_numbers(cls, v):
        floor_numbers = [f.floorNumber for f in v]
        if len(floor_numbers) != len(set(floor_numbers)):
            raise ValueError('Floor numbers must be unique')
        return v


class BoundaryPointSchema(BaseModel):
    """Boundary polygon point"""
    x: float = Field(..., ge=-10000, le=10000)
    y: float = Field(..., ge=-10000, le=10000)


class BoundarySchema(BaseModel):
    """Boundary polygon schema"""
    points: List[BoundaryPointSchema] = Field(default_factory=list, max_length=5000)
    min_x: Optional[float] = Field(default=None, ge=-10000, le=10000)
    max_x: Optional[float] = Field(default=None, ge=-10000, le=10000)
    min_z: Optional[float] = Field(default=None, ge=-10000, le=10000)
    max_z: Optional[float] = Field(default=None, ge=-10000, le=10000)

    model_config = ConfigDict(extra="ignore")


class SimulationConfigSchema(BaseModel):
    """Simulation configuration schema"""
    floor_plan_id: Optional[str] = Field(None, min_length=1, max_length=100)
    floor_plan_snapshot: Optional[Dict[str, Any]] = None
    floor_number: Optional[int] = Field(None, ge=1, le=100)
    num_agents: int = Field(..., ge=1, le=10000)
    emergency_type: EmergencyType = EmergencyType.FIRE
    panic_level: float = Field(..., ge=0.0, le=1.0)
    exits: List[Dict[str, Any]] = Field(default_factory=list, max_length=100)
    hazards: List[HazardSchema] = Field(default_factory=list, max_length=200)
    agent_profiles: List[AgentProfileSchema] = Field(default_factory=list, max_length=50)
    blocked_exits: List[str] = Field(default_factory=list, max_length=200)
    parameter_overrides: Dict[str, float] = Field(default_factory=dict)
    ablation: Optional[AblationSchema] = None
    boundary: Optional[BoundarySchema] = None
    max_iterations: Optional[int] = Field(default=None, ge=1, le=100000)
    realtime: Optional[bool] = None
    seed: Optional[int] = Field(default=None, ge=0)
    tags: List[str] = Field(default_factory=list, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=2000)
    label: Optional[str] = Field(default=None, max_length=200)
    priority: Optional[int] = Field(default=None, ge=1, le=10)
    record_frames: bool = True
    frame_stride: int = Field(default=1, ge=1, le=100)
    store_agents: bool = True
    store_bottlenecks: bool = True
    store_walls: bool = True
    store_exits: bool = True
    store_obstacles: bool = True
    store_hazards: bool = True
    max_runtime_seconds: Optional[float] = Field(default=None, ge=1.0, le=36000)

    @field_validator("tags")
    def dedupe_tags(cls, v):
        if not v:
            return []
        seen = []
        for tag in v:
            if not isinstance(tag, str):
                continue
            if tag not in seen:
                seen.append(tag)
        return seen
    
    @field_validator("exits")
    def validate_exits(cls, v):
        for exit_data in v:
            if not isinstance(exit_data, dict):
                raise ValueError('Each exit must be a dictionary')
            if 'x' not in exit_data or 'y' not in exit_data:
                raise ValueError('Exits must have x and y coordinates')
        return v

    @field_validator("agent_profiles")
    def validate_agent_profiles(cls, v):
        if not v:
            return v
        ratios = [p.ratio for p in v if p.ratio is not None]
        counts = [p.count for p in v if p.count is not None]
        if counts and any(p.ratio is not None for p in v):
            raise ValueError("Provide either ratios or counts for agent profiles, not both")
        if counts:
            total = sum(counts)
            if total <= 0:
                raise ValueError("Agent profile counts must be positive")
            for profile in v:
                profile.ratio = (profile.count or 0) / total
            return v
        if not ratios or sum(ratios) <= 0:
            equal = 1.0 / len(v)
            for profile in v:
                profile.ratio = equal
            return v
        total_ratio = sum(ratios)
        if total_ratio <= 0:
            raise ValueError("Agent profile ratios must be positive")
        # Normalize ratios to sum to 1
        for profile in v:
            if profile.ratio is None:
                profile.ratio = 0.0
            profile.ratio = profile.ratio / total_ratio
        return v

    @field_validator("hazards")
    def validate_hazards(cls, v):
        for hazard in v:
            if hazard.type == HazardTypeSchema.BLOCKED_EXIT and not hazard.exit_ids:
                raise ValueError("blocked_exit hazards require exit_ids or exit_id")
        return v


class AgentPositionSchema(BaseModel):
    """Agent position schema"""
    agent_id: int = Field(..., ge=0, le=100000)
    x: float = Field(..., ge=-10000, le=10000)
    y: float = Field(..., ge=-10000, le=10000)
    z: float = Field(..., ge=-10000, le=10000)
    speed: float = Field(..., ge=0, le=10)
    status: str = Field(..., pattern=r"^(waiting|moving|evacuated|stuck|panicking|collapsed)$")
    profile_id: Optional[str] = Field(default=None, max_length=100)
    panic_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stress_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    target_exit: Optional[str] = Field(default=None, max_length=100)
    profile_group: Optional[str] = Field(default=None, max_length=100)
    visibility: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    smoke_exposure: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="ignore")


class BottleneckSchema(BaseModel):
    """Bottleneck schema"""
    x: float = Field(..., ge=-10000, le=10000)
    y: float = Field(..., ge=-10000, le=10000)
    z: float = Field(..., ge=-10000, le=10000)
    density: float = Field(..., ge=0, le=1000)

    model_config = ConfigDict(extra="ignore")


class HazardSnapshotSchema(BaseModel):
    """Hazard snapshot schema"""
    hazard_id: Optional[str] = Field(default=None, max_length=100)
    hazard_type: Optional[str] = Field(default=None, max_length=50)
    x: float = Field(default=0.0, ge=-10000, le=10000)
    y: float = Field(default=0.0, ge=-10000, le=10000)
    z: float = Field(default=0.0, ge=-10000, le=10000)
    radius: float = Field(default=0.0, ge=0.0, le=10000)
    intensity: float = Field(default=0.0, ge=0.0, le=10.0)
    blocks_exits: Optional[bool] = None

    model_config = ConfigDict(extra="ignore")


class ExitUsageSchema(BaseModel):
    """Exit usage snapshot schema"""
    exit_id: str = Field(..., max_length=100)
    x: float = Field(default=0.0, ge=-10000, le=10000)
    y: float = Field(default=0.0, ge=-10000, le=10000)
    z: float = Field(default=0.0, ge=-10000, le=10000)
    width: float = Field(default=0.0, ge=0.0, le=10000)
    capacity: float = Field(default=0.0, ge=0.0, le=100000)
    queue_length: Optional[int] = Field(default=None, ge=0, le=100000)
    is_blocked: Optional[bool] = None
    estimated_wait: Optional[float] = Field(default=None, ge=0.0, le=100000)

    model_config = ConfigDict(extra="ignore")


class ExitEvacCountSchema(BaseModel):
    """Exit evacuation counts"""
    exit_id: str = Field(..., max_length=100)
    count: int = Field(default=0, ge=0, le=1000000)

    model_config = ConfigDict(extra="ignore")


class ProfileCountSchema(BaseModel):
    """Profile count snapshot"""
    profile_id: str = Field(..., max_length=100)
    count: int = Field(default=0, ge=0, le=1000000)

    model_config = ConfigDict(extra="ignore")


class SimulationFrameSchema(BaseModel):
    """Simulation frame schema"""
    timestamp: float = Field(..., ge=0, le=3600)
    floor_number: Optional[int] = Field(None, ge=1, le=100)
    agents: List[AgentPositionSchema] = Field(..., max_length=10000)
    bottlenecks: List[BottleneckSchema] = Field(default_factory=list, max_length=1000)
    hazards: List[HazardSnapshotSchema] = Field(default_factory=list, max_length=1000)
    exit_usage: List[ExitUsageSchema] = Field(default_factory=list, max_length=1000)
    exit_evac_counts: List[ExitEvacCountSchema] = Field(default_factory=list, max_length=1000)
    profile_counts: List[ProfileCountSchema] = Field(default_factory=list, max_length=1000)
    stats: Optional[Dict[str, Any]] = None
    hazard_state: Optional[Dict[str, Any]] = None
    collision_events: Optional[int] = Field(default=None, ge=0, le=100000000)
    wall_penetration_count: Optional[int] = Field(default=None, ge=0, le=100000000)
    nav_debug: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore")


class UserCreateSchema(BaseModel):
    """User creation schema"""
    email: EmailField
    password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    
    @field_validator("password")
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "name": "John Doe"
            }
        }
    )

