"""
API endpoints for scenario builder and presets
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import logging

from app.core.request_context import get_request_actor
from app.services.scenario_application_service import scenario_application_service

logger = logging.getLogger(__name__)

router = APIRouter()

class CustomScenarioRequest(BaseModel):
    """Request to create custom scenario"""
    name: str = Field(..., min_length=1)
    emergency_type: str = Field(..., min_length=1)
    building_type: str = Field(..., min_length=1)
    panic_level: float = 0.5
    custom_exits: List[Dict[str, Any]] = Field(default_factory=list)
    behavior_modifiers: Dict[str, float] = Field(default_factory=dict)


class LegacyScenarioCreateRequest(BaseModel):
    """Compatibility payload for older scenario create clients."""
    name: str = Field(..., min_length=1)
    emergency_type: str = Field(..., min_length=1)
    building_type: str = Field(..., min_length=1)
    panic_level: float = 0.5
    custom_exits: List[Dict[str, Any]] = Field(default_factory=list)
    behavior_modifiers: Dict[str, float] = Field(default_factory=dict)

@router.get("/presets")
async def list_scenario_presets(
    request: Request,
    current_user: dict = Depends(get_request_actor)
):
    """List all available scenario presets"""
    try:
        del request, current_user
        return scenario_application_service.list_presets()
    except Exception as e:
        logger.error(f"Error listing presets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_scenario_presets_legacy(
    request: Request,
    current_user: dict = Depends(get_request_actor)
):
    """Legacy compatibility alias for older frontend/tests."""
    del request, current_user
    try:
        return scenario_application_service.list_presets()
    except Exception as e:
        logger.error(f"Error listing presets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/presets/{preset_id}")
async def get_scenario_preset(
    preset_id: str,
    current_user: dict = Depends(get_request_actor)
):
    """Get specific scenario preset"""
    try:
        del current_user
        preset = scenario_application_service.get_preset(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        return preset
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom")
async def create_custom_scenario(
    request: Request,
    scenario_data: CustomScenarioRequest,
    current_user: dict = Depends(get_request_actor)
):
    """Create custom scenario"""
    try:
        del request, current_user
        return scenario_application_service.create_custom_scenario(
            name=scenario_data.name,
            emergency_type=scenario_data.emergency_type,
            building_type=scenario_data.building_type,
            panic_level=scenario_data.panic_level,
            custom_exits=scenario_data.custom_exits,
            behavior_modifiers=scenario_data.behavior_modifiers,
        )
    except Exception as e:
        logger.error(f"Error creating custom scenario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_custom_scenario_legacy(
    request: Request,
    scenario_data: LegacyScenarioCreateRequest,
    current_user: dict = Depends(get_request_actor)
):
    """Legacy compatibility alias for older create flows."""
    normalized = CustomScenarioRequest(
        name=scenario_data.name,
        emergency_type=scenario_data.emergency_type,
        building_type=scenario_data.building_type,
        panic_level=scenario_data.panic_level,
        custom_exits=scenario_data.custom_exits,
        behavior_modifiers=scenario_data.behavior_modifiers,
    )
    preset = await create_custom_scenario(request, normalized, current_user)
    return {
        "scenario": preset,
        "status": "created",
    }

@router.get("/exits/{building_type}")
async def get_recommended_exits(
    building_type: str,
    building_width: float = 100.0,
    building_height: float = 100.0,
    current_user: dict = Depends(get_request_actor)
):
    """Get recommended exit placement for building type"""
    try:
        del current_user
        return scenario_application_service.get_recommended_exits(
            building_type=building_type,
            building_width=building_width,
            building_height=building_height,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid building type: {building_type}")
    except Exception as e:
        logger.error(f"Error getting recommended exits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


