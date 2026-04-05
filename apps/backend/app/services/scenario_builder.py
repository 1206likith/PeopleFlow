"""
Scenario Builder & Preset Policies
Research-validated evacuation scenarios
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ScenarioType(Enum):
    """Predefined scenario types"""
    FIRE_EMERGENCY = "fire_emergency"
    ACTIVE_SHOOTER = "active_shooter"
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    GAS_LEAK = "gas_leak"
    BOMB_THREAT = "bomb_threat"

class BuildingType(Enum):
    """Tested building layouts"""
    OFFICE = "office"
    STADIUM = "stadium"
    MALL = "mall"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    RESIDENTIAL = "residential"

@dataclass
class ScenarioPreset:
    """Predefined scenario configuration"""
    scenario_type: ScenarioType
    building_type: BuildingType
    name: str
    description: str
    emergency_type: str
    panic_level: float
    smoke_opacity: float
    smoke_propagation_rate: float
    exit_blockage_probability: float
    agent_behavior_modifiers: Dict[str, float]
    recommended_exits: List[Dict]
    validation_data: Optional[Dict] = None

class ScenarioBuilder:
    """Builds evacuation scenarios with research-validated presets"""
    
    def __init__(self):
        self.presets = self._load_presets()
    
    def _load_presets(self) -> Dict[str, ScenarioPreset]:
        """Load research-validated scenario presets"""
        return {
            "fire_emergency_office": ScenarioPreset(
                scenario_type=ScenarioType.FIRE_EMERGENCY,
                building_type=BuildingType.OFFICE,
                name="Fire Emergency - Office Building",
                description="Standard fire evacuation with increasing smoke opacity",
                emergency_type="fire",
                panic_level=0.6,
                smoke_opacity=0.0,  # Starts at 0, increases over time
                smoke_propagation_rate=0.05,  # 5% per second
                exit_blockage_probability=0.0,
                agent_behavior_modifiers={
                    "panic_increase_rate": 0.02,
                    "speed_reduction": 0.1,  # Smoke slows movement
                    "visibility_reduction": 0.3
                },
                recommended_exits=[
                    {"x": -50, "z": 0, "width": 2.0, "capacity": 100},
                    {"x": 50, "z": 0, "width": 2.0, "capacity": 100}
                ],
                validation_data={
                    "expected_evacuation_time": 180,  # 3 minutes for 100 agents
                    "source": "EXIT89 and office building studies"
                }
            ),
            "active_shooter_mall": ScenarioPreset(
                scenario_type=ScenarioType.ACTIVE_SHOOTER,
                building_type=BuildingType.MALL,
                name="Active Shooter - Shopping Mall",
                description="Threat scenario with redirection behavior and high panic",
                emergency_type="terrorist",
                panic_level=0.9,
                smoke_opacity=0.0,
                smoke_propagation_rate=0.0,
                exit_blockage_probability=0.1,  # 10% chance exits are blocked
                agent_behavior_modifiers={
                    "panic_increase_rate": 0.05,
                    "redirection_probability": 0.4,  # 40% change exit if threat nearby
                    "herd_behavior": 0.7,  # Strong herd following
                    "decision_delay_reduction": 0.5  # Faster decisions under threat
                },
                recommended_exits=[
                    {"x": -75, "z": -75, "width": 3.0, "capacity": 200},
                    {"x": 75, "z": -75, "width": 3.0, "capacity": 200},
                    {"x": -75, "z": 75, "width": 3.0, "capacity": 200},
                    {"x": 75, "z": 75, "width": 3.0, "capacity": 200}
                ],
                validation_data={
                    "expected_evacuation_time": 240,
                    "source": "Active shooter evacuation studies"
                }
            ),
            "earthquake_stadium": ScenarioPreset(
                scenario_type=ScenarioType.EARTHQUAKE,
                building_type=BuildingType.STADIUM,
                name="Earthquake - Stadium",
                description="Dynamic exit blockage and structural damage",
                emergency_type="earthquake",
                panic_level=0.7,
                smoke_opacity=0.0,
                smoke_propagation_rate=0.0,
                exit_blockage_probability=0.3,  # 30% chance exits become blocked
                agent_behavior_modifiers={
                    "panic_increase_rate": 0.03,
                    "exit_reroute_probability": 0.6,  # High rerouting when exit blocked
                    "structural_damage_impact": 0.2
                },
                recommended_exits=[
                    {"x": -100, "z": 0, "width": 4.0, "capacity": 500},
                    {"x": 100, "z": 0, "width": 4.0, "capacity": 500},
                    {"x": 0, "z": -100, "width": 4.0, "capacity": 500},
                    {"x": 0, "z": 100, "width": 4.0, "capacity": 500}
                ],
                validation_data={
                    "expected_evacuation_time": 600,  # 10 minutes for large crowd
                    "source": "Stadium evacuation research"
                }
            ),
            "fire_hospital": ScenarioPreset(
                scenario_type=ScenarioType.FIRE_EMERGENCY,
                building_type=BuildingType.HOSPITAL,
                name="Fire Emergency - Hospital",
                description="High-stakes evacuation with vulnerable populations",
                emergency_type="fire",
                panic_level=0.5,  # Lower panic (trained staff)
                smoke_opacity=0.1,
                smoke_propagation_rate=0.03,
                exit_blockage_probability=0.0,
                agent_behavior_modifiers={
                    "panic_increase_rate": 0.01,
                    "elderly_percentage": 0.3,  # Higher elderly population
                    "injured_percentage": 0.2,  # Injured patients
                    "staff_assistance": 0.5  # Staff help patients
                },
                recommended_exits=[
                    {"x": -40, "z": 0, "width": 2.5, "capacity": 150, "is_accessible": True},
                    {"x": 40, "z": 0, "width": 2.5, "capacity": 150, "is_accessible": True}
                ],
                validation_data={
                    "expected_evacuation_time": 300,
                    "source": "Hospital evacuation protocols"
                }
            )
        }
    
    def get_preset(self, preset_id: str) -> Optional[ScenarioPreset]:
        """Get scenario preset by ID"""
        return self.presets.get(preset_id)
    
    def list_presets(self) -> List[Dict]:
        """List all available presets"""
        return [
            {
                "id": preset_id,
                "name": preset.name,
                "description": preset.description,
                "scenario_type": preset.scenario_type.value,
                "building_type": preset.building_type.value,
                "emergency_type": preset.emergency_type,
                "validation_data": preset.validation_data
            }
            for preset_id, preset in self.presets.items()
        ]
    
    def create_custom_scenario(
        self,
        name: str,
        emergency_type: str,
        building_type: str,
        panic_level: float = 0.5,
        custom_exits: Optional[List[Dict]] = None,
        behavior_modifiers: Optional[Dict] = None
    ) -> ScenarioPreset:
        """Create custom scenario"""
        return ScenarioPreset(
            scenario_type=ScenarioType.FIRE_EMERGENCY,  # Default
            building_type=BuildingType(building_type) if building_type else BuildingType.OFFICE,
            name=name,
            description=f"Custom {emergency_type} scenario",
            emergency_type=emergency_type,
            panic_level=panic_level,
            smoke_opacity=0.0,
            smoke_propagation_rate=0.0,
            exit_blockage_probability=0.0,
            agent_behavior_modifiers=behavior_modifiers or {},
            recommended_exits=custom_exits or []
        )
    
    def get_recommended_exits_for_building(
        self,
        building_type: BuildingType,
        building_width: float,
        building_height: float
    ) -> List[Dict]:
        """Get recommended exit placement for building type"""
        # Research-based exit placement strategies
        if building_type == BuildingType.OFFICE:
            # Opposite walls strategy
            return [
                {"x": -building_width/2 + 10, "z": 0, "width": 2.0, "capacity": 100},
                {"x": building_width/2 - 10, "z": 0, "width": 2.0, "capacity": 100}
            ]
        elif building_type == BuildingType.STADIUM:
            # Multiple exits on all sides
            return [
                {"x": -building_width/2, "z": 0, "width": 4.0, "capacity": 500},
                {"x": building_width/2, "z": 0, "width": 4.0, "capacity": 500},
                {"x": 0, "z": -building_height/2, "width": 4.0, "capacity": 500},
                {"x": 0, "z": building_height/2, "width": 4.0, "capacity": 500}
            ]
        elif building_type == BuildingType.MALL:
            # Distributed exits
            return [
                {"x": -building_width/3, "z": -building_height/3, "width": 3.0, "capacity": 200},
                {"x": building_width/3, "z": -building_height/3, "width": 3.0, "capacity": 200},
                {"x": -building_width/3, "z": building_height/3, "width": 3.0, "capacity": 200},
                {"x": building_width/3, "z": building_height/3, "width": 3.0, "capacity": 200}
            ]
        else:
            # Default: opposite walls
            return [
                {"x": -building_width/2 + 10, "z": 0, "width": 2.0, "capacity": 100},
                {"x": building_width/2 - 10, "z": 0, "width": 2.0, "capacity": 100}
            ]

# Global instance
scenario_builder = ScenarioBuilder()

