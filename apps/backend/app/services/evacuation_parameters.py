import json
import logging
from typing import Dict, Optional, Any
from enum import Enum
from pathlib import Path
import copy
import numpy as np
from scipy import stats
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger(__name__)

class PopulationProfile(str, Enum):
    """Population profiles with research-validated parameters"""
    NORMAL_ADULT = "normal_adult"
    ELDERLY = "elderly"
    INJURED = "injured"
    CHILD = "child"
    DISABLED = "disabled"

class EvacuationPolicy(str, Enum):
    """Evacuation strategy policies"""
    NEAREST_EXIT = "nearest_exit"
    LEAST_CROWDED = "least_crowded"
    FOLLOW_LEADER = "follow_leader"
    RANDOM_PANIC = "random_panic"
    AUTHORITY_DIRECTED = "authority_directed"

# Pydantic Config Models
class PreEvacuationDelay(BaseModel):
    distribution: str = "lognormal"
    mean: float = 2.5
    std: float = 1.2
    min: float = 0.1
    max: float = 30.0

class WalkingSpeed(BaseModel):
    mean: float = 1.35
    std: float = 0.25
    min: float = 0.5
    max: float = 2.5

class DensitySpeedCurve(BaseModel):
    max_density: float = 6.0

class ExitFlowCapacity(BaseModel):
    base_flow_rate: float = 1.33
    width_factor: float = 1.0
    saturation_threshold: float = 0.85
    panic_reduction: float = 0.7

class BottleneckFormation(BaseModel):
    critical_density: float = 4.0
    shockwave_speed: float = 1.5
    congestion_decay_rate: float = 0.1

class PanicPropagation(BaseModel):
    contagion_rate: float = 0.15
    recovery_rate: float = 0.05
    influence_radius: float = 5.0
    leader_influence: float = 2.0

class SocialForces(BaseModel):
    repulsion_strength: float = 2000.0
    repulsion_range: float = 0.5
    attraction_strength: float = 500.0
    attraction_range: float = 2.0
    wall_repulsion: float = 1000.0
    wall_range: float = 0.3
    panic_pressure: float = 3000.0

class BoundedRationality(BaseModel):
    reconsider_probability: float = 0.1
    information_decay: float = 0.05

class BayesianTrust(BaseModel):
    leader_trust: float = 0.8
    crowd_following: float = 0.6
    authority_trust: float = 0.9

class DecisionModels(BaseModel):
    bounded_rationality: BoundedRationality = Field(default_factory=BoundedRationality)
    bayesian_trust: BayesianTrust = Field(default_factory=BayesianTrust)

class EvacuationParametersConfig(BaseModel):
    pre_evacuation_delay: PreEvacuationDelay = Field(default_factory=PreEvacuationDelay)
    walking_speed: Dict[str, WalkingSpeed] = Field(default_factory=lambda: {
        "normal_adult": WalkingSpeed(mean=1.35, std=0.25, min=0.5, max=2.5),
        "elderly": WalkingSpeed(mean=0.95, std=0.20, min=0.3, max=1.8),
        "injured": WalkingSpeed(mean=0.60, std=0.15, min=0.2, max=1.2),
        "child": WalkingSpeed(mean=1.10, std=0.30, min=0.4, max=2.0),
        "disabled": WalkingSpeed(mean=0.75, std=0.20, min=0.25, max=1.5)
    })
    density_speed_curve: DensitySpeedCurve = Field(default_factory=DensitySpeedCurve)
    exit_flow_capacity: ExitFlowCapacity = Field(default_factory=ExitFlowCapacity)
    bottleneck_formation: BottleneckFormation = Field(default_factory=BottleneckFormation)
    panic_propagation: PanicPropagation = Field(default_factory=PanicPropagation)
    social_forces: SocialForces = Field(default_factory=SocialForces)
    decision_models: DecisionModels = Field(default_factory=DecisionModels)


class ParameterDatabase:
    """
    Research-driven parameter database
    Loads from JSON configuration files and validated with Pydantic
    """
    
    def __init__(self, config_path: Optional[str] = None):
        default_path = Path(__file__).resolve().parents[1] / "data" / "evacuation_parameters.json"
        self.config_path = config_path or settings.EVAC_PARAMS_PATH or str(default_path)
        self.parameters = self._load_parameters()
        self.config = EvacuationParametersConfig.model_validate(self.parameters)
        self._base_parameters = copy.deepcopy(self.parameters)
        self._validate_parameters()
    
    def _load_parameters(self) -> Dict:
        """Load parameters from JSON file or use defaults directly from Pydantic"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    params = json.load(f)
                    logger.info(f"Loaded evacuation parameters from {self.config_path}")
                    return params
        except Exception as e:
            logger.warning(f"Could not load parameters file: {e}. Using defaults.")
        
        # Use Pydantic defaults
        return EvacuationParametersConfig().model_dump()
    
    def _validate_parameters(self):
        """Validate parameter ranges against research literature"""
        # Additional custom validation beyond Pydantic could go here
        # E.g., validating walking speeds are within research bounds
        for profile, speeds in self.config.walking_speed.items():
            if speeds.mean < 0.2 or speeds.mean > 3.0:
                logger.warning(f"Walking speed for {profile} may be outside research bounds")

    def snapshot(self) -> Dict:
        """Return a deep copy of current parameters for reproducibility."""
        return copy.deepcopy(self.parameters)

    def reset(self) -> None:
        """Reset parameters back to the initial loaded values."""
        self.parameters = copy.deepcopy(self._base_parameters)
        self.config = EvacuationParametersConfig.model_validate(self.parameters)
        self._validate_parameters()

    def restore(self, snapshot: Dict) -> None:
        """Restore parameters from a previous snapshot."""
        if snapshot:
            self.parameters = copy.deepcopy(snapshot)
            self.config = EvacuationParametersConfig.model_validate(self.parameters)
            self._validate_parameters()

    def apply_overrides(self, overrides: Dict[str, Any]) -> None:
        """
        Apply dot-path overrides to parameter tree.
        Example: {"pre_evacuation_delay.mean": 3.0}
        """
        for path, value in overrides.items():
            keys = path.split(".")
            node = self.parameters
            for key in keys[:-1]:
                if key not in node or not isinstance(node[key], dict):
                    node[key] = {}
                node = node[key]
            node[keys[-1]] = value
            
        self.config = EvacuationParametersConfig.model_validate(self.parameters)
        self._validate_parameters()
    
    def get_pre_evacuation_delay(self, profile: PopulationProfile = PopulationProfile.NORMAL_ADULT) -> float:
        """Get pre-evacuation delay from log-normal distribution"""
        params = self.config.pre_evacuation_delay
        if params.distribution == "lognormal":
            # Convert mean/std to lognormal parameters
            mu = np.log(params.mean**2 / np.sqrt(params.std**2 + params.mean**2))
            sigma = np.sqrt(np.log(1 + params.std**2 / params.mean**2))
            delay = stats.lognorm.rvs(s=sigma, scale=np.exp(mu))
            return float(np.clip(delay, params.min, params.max))
        return params.mean
    
    def get_walking_speed(self, profile: PopulationProfile, density: float = 0.0) -> float:
        """Get walking speed based on profile and local density"""
        profile_key = profile.value if isinstance(profile, Enum) else profile
        if profile_key not in self.config.walking_speed:
            profile_key = "normal_adult"
            
        base_speeds = self.config.walking_speed[profile_key]
        
        # Base speed from profile
        base_speed = np.random.normal(base_speeds.mean, base_speeds.std)
        base_speed = np.clip(base_speed, base_speeds.min, base_speeds.max)
        
        # Apply density reduction (fundamental diagram)
        density_factor = self.get_speed_reduction(density)
        
        return float(base_speed * density_factor)
    
    def get_speed_reduction(self, density: float) -> float:
        """Get speed reduction factor based on density (fundamental diagram)"""
        curve = self.config.density_speed_curve
        
        # Linear fundamental diagram: v = v0 * (1 - density / max_density)
        max_density = curve.max_density
        
        if density <= 0.0:
            return 1.0
            
        speed_factor = 1.0 - (density / max_density)
        return max(0.0, float(speed_factor))
    
    def get_flow_capacity(self, exit_width: float) -> float:
        """Get exit flow capacity in persons/second"""
        params = self.config.exit_flow_capacity
        return float(params.base_flow_rate * exit_width * params.width_factor)
    
    def should_avoid_exit(self, exit_utilization: float) -> bool:
        """Check if exit should be avoided due to saturation"""
        threshold = self.config.exit_flow_capacity.saturation_threshold
        return exit_utilization > threshold
    
    def get_bottleneck_density(self) -> float:
        """Get critical density for bottleneck formation"""
        return float(self.config.bottleneck_formation.critical_density)
    
    def get_social_force_params(self) -> Dict:
        """Get social force model parameters"""
        return self.config.social_forces.model_dump()
    
    def get_panic_contagion_rate(self) -> float:
        """Get panic propagation rate (SIS model)"""
        return float(self.config.panic_propagation.contagion_rate)
    
    def get_leader_influence_radius(self) -> float:
        """Get leader influence radius for following behavior"""
        return float(self.config.panic_propagation.influence_radius)

    def should_follow_leader(self) -> bool:
        """Determines if an agent should follow a leader based on parameters"""
        # Example implementation, can adjust based on behavior/literature
        return np.random.rand() < self.config.decision_models.bayesian_trust.leader_trust

# Global parameter database instance
parameter_database = ParameterDatabase()
