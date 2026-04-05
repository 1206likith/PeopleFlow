"""
Application service for scenario presets and custom scenario construction.
Keeps route handlers thin and centralizes scenario response shaping.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.scenario_builder import BuildingType, ScenarioPreset, scenario_builder


def _serialize_preset(preset_id: str, preset: ScenarioPreset) -> Dict[str, Any]:
    return {
        "id": preset_id,
        "name": preset.name,
        "description": preset.description,
        "scenario_type": preset.scenario_type.value,
        "building_type": preset.building_type.value,
        "emergency_type": preset.emergency_type,
        "panic_level": preset.panic_level,
        "smoke_opacity": preset.smoke_opacity,
        "smoke_propagation_rate": preset.smoke_propagation_rate,
        "exit_blockage_probability": preset.exit_blockage_probability,
        "agent_behavior_modifiers": preset.agent_behavior_modifiers,
        "recommended_exits": preset.recommended_exits,
        "validation_data": preset.validation_data,
    }


class ScenarioApplicationService:
    def __init__(self) -> None:
        presets = scenario_builder.presets
        self._preset_lookup = {
            preset_id: _serialize_preset(preset_id, preset)
            for preset_id, preset in presets.items()
        }
        self._preset_list_response = {
            "presets": scenario_builder.list_presets(),
            "count": len(presets),
        }

    def list_presets(self) -> Dict[str, Any]:
        return self._preset_list_response

    def get_preset(self, preset_id: str) -> Dict[str, Any] | None:
        return self._preset_lookup.get(preset_id)

    def create_custom_scenario(
        self,
        *,
        name: str,
        emergency_type: str,
        building_type: str,
        panic_level: float,
        custom_exits: List[Dict[str, Any]],
        behavior_modifiers: Dict[str, float],
    ) -> Dict[str, Any]:
        preset = scenario_builder.create_custom_scenario(
            name,
            emergency_type,
            building_type,
            panic_level,
            custom_exits,
            behavior_modifiers,
        )
        return {
            "name": preset.name,
            "description": preset.description,
            "emergency_type": preset.emergency_type,
            "panic_level": preset.panic_level,
            "recommended_exits": preset.recommended_exits,
            "agent_behavior_modifiers": preset.agent_behavior_modifiers,
        }

    def get_recommended_exits(
        self,
        *,
        building_type: str,
        building_width: float,
        building_height: float,
    ) -> Dict[str, Any]:
        exits = scenario_builder.get_recommended_exits_for_building(
            BuildingType(building_type),
            building_width,
            building_height,
        )
        return {"exits": exits, "building_type": building_type}


scenario_application_service = ScenarioApplicationService()
