"""
Live simulation runtime update routes extracted from the main simulation router.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.request_context import get_request_actor
from app.core.validation import BoundarySchema, HazardSchema, ManualExitSchema
from app.services.simulation_live_update_service import simulation_live_update_service

router = APIRouter()


class HazardUpdateRequest(BaseModel):
    hazards: List[HazardSchema]


class ExitUpdateRequest(BaseModel):
    exits: List[ManualExitSchema]


class BoundaryUpdateRequest(BaseModel):
    boundary: BoundarySchema


@router.post("/{simulation_id}/hazards/update")
async def update_simulation_hazards(
    simulation_id: str,
    payload: HazardUpdateRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Broadcast hazard updates to Unity and connected listeners."""
    return await simulation_live_update_service.update_hazards(
        simulation_id,
        payload.hazards,
        current_user=current_user,
    )


@router.post("/{simulation_id}/exits/update")
async def update_simulation_exits(
    simulation_id: str,
    payload: ExitUpdateRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Broadcast exit updates to Unity and connected listeners."""
    return await simulation_live_update_service.update_exits(
        simulation_id,
        payload.exits,
        current_user=current_user,
    )


@router.post("/{simulation_id}/boundary/update")
async def update_simulation_boundary(
    simulation_id: str,
    payload: BoundaryUpdateRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Broadcast boundary updates to Unity and connected listeners."""
    return await simulation_live_update_service.update_boundary(
        simulation_id,
        payload.boundary,
        current_user=current_user,
    )
