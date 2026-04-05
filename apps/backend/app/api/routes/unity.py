"""
Unity-specific API endpoints for production integration.
"""

from typing import Any, Dict, List, Literal, Optional

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.request_context import get_request_actor
from app.services.simulation_repository import get_simulation_repository
from app.services.unity_bridge import unity_bridge
from app.services.unity_procedural import procedural_generator

logger = logging.getLogger(__name__)
router = APIRouter()


class UnityStartCommand(BaseModel):
    """Unity start simulation command."""

    simulation_id: str
    num_agents: int
    emergency_type: str
    panic_level: float = 0.5
    floor_number: int = 1
    exits: List[Dict[str, Any]] = Field(default_factory=list)


class UnityControlCommand(BaseModel):
    """Unity control command."""

    simulation_id: str
    command: Literal["pause", "resume", "stop"]


@router.post("/start")
async def unity_start_simulation(
    request: Request,
    command: UnityStartCommand,
    current_user: Optional[dict] = Depends(get_request_actor),
):
    """Start simulation in Unity."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    try:
        await unity_bridge.start_simulation(
            command.simulation_id,
            {
                "num_agents": command.num_agents,
                "emergency_type": command.emergency_type,
                "panic_level": command.panic_level,
                "floor_number": command.floor_number,
                "exits": command.exits,
            },
        )
        logger.info(
            "Unity simulation started: %s",
            command.simulation_id,
            extra={
                "correlation_id": correlation_id,
                "simulation_id": command.simulation_id,
                "num_agents": command.num_agents,
            },
        )
        return {"status": "started", "simulation_id": command.simulation_id}
    except ConnectionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(
            "Failed to start Unity simulation: %s",
            exc,
            extra={"correlation_id": correlation_id, "simulation_id": command.simulation_id},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to start Unity simulation: {str(exc)}")


@router.post("/control")
async def unity_control_simulation(
    request: Request,
    command: UnityControlCommand,
    current_user: Optional[dict] = Depends(get_request_actor),
):
    """Control Unity simulation (pause/resume/stop)."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    try:
        if command.command == "pause":
            await unity_bridge.pause_simulation(command.simulation_id)
        elif command.command == "resume":
            await unity_bridge.resume_simulation(command.simulation_id)
        else:
            await unity_bridge.stop_simulation(command.simulation_id)

        logger.info(
            "Unity simulation %s: %s",
            command.command,
            command.simulation_id,
            extra={
                "correlation_id": correlation_id,
                "simulation_id": command.simulation_id,
                "command": command.command,
            },
        )
        return {"status": command.command, "simulation_id": command.simulation_id}
    except ConnectionError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(
            "Failed to control Unity simulation: %s",
            exc,
            extra={"correlation_id": correlation_id, "simulation_id": command.simulation_id},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to control Unity simulation: {str(exc)}")


@router.get("/status/{simulation_id}")
async def unity_get_status(
    simulation_id: str,
    current_user: Optional[dict] = Depends(get_request_actor),
):
    """Get Unity connection status."""
    return unity_bridge.get_connection_status(simulation_id)


@router.get("/scene/{simulation_id}")
async def unity_get_scene(
    simulation_id: str,
    current_user: Optional[dict] = Depends(get_request_actor),
):
    """Get auto-generated 3D scene data for Unity frontend."""
    del current_user
    simulation_repository = await get_simulation_repository()
    sim_doc = await simulation_repository.get(simulation_id)

    if not sim_doc:
        raise HTTPException(status_code=404, detail="Simulation not found in database")

    floor_plan_id = sim_doc.get("floor_plan_id")
    floor_number = sim_doc.get("floor_number", 1)
    
    from app.services.floorplan_loader import load_floor_plan_data
    floor_plan_data, _ = await load_floor_plan_data(
        floor_plan_id=floor_plan_id,
        floor_number=floor_number,
        configured_exits=sim_doc.get("exits", [])
    )

    if not floor_plan_data:
        raise HTTPException(status_code=404, detail="Resolvable floor plan data could not be found")

    scene_data = procedural_generator.generate_unity_scene(floor_plan_data)
    return scene_data
