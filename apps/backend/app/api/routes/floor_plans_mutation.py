"""
Mutable floor-plan routes extracted from the main simulation router.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.request_context import get_request_actor
from app.core.validation import ManualExitSchema
from app.services.floor_plan_mutation_service import floor_plan_mutation_service

router = APIRouter()


class ManualExitUpdateRequest(BaseModel):
    exits: List[ManualExitSchema]
    merge: bool = True
    snap_to_boundary: bool = True


class FloorPlanReprocessRequest(BaseModel):
    mode: Literal["auto", "traditional", "semantic"] = "auto"
    debug: bool = False
    profile: Optional[str] = Field(default=None, max_length=100)


class FloorPlanAnnotationRequest(BaseModel):
    status: Optional[Literal["new", "in_review", "approved", "rejected"]] = None
    walls: List[Dict[str, Any]] = Field(default_factory=list)
    doors: List[Dict[str, Any]] = Field(default_factory=list)
    exits: List[Dict[str, Any]] = Field(default_factory=list)
    rooms: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None, max_length=5000)


@router.post("/floor-plans/{floor_plan_id}/reprocess")
async def reprocess_floor_plan(
    floor_plan_id: str,
    payload: FloorPlanReprocessRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Re-run floor plan detection pipeline with explicit mode controls."""
    return await floor_plan_mutation_service.reprocess(
        floor_plan_id,
        payload,
        current_user=current_user,
    )


@router.post("/floor-plans/{floor_plan_id}/annotations")
async def save_floor_plan_annotations(
    floor_plan_id: str,
    payload: FloorPlanAnnotationRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Store wall/door/exit/room labels for curated training datasets."""
    return await floor_plan_mutation_service.save_annotations(
        floor_plan_id,
        payload,
        current_user=current_user,
    )


@router.post("/floor-plans/{floor_plan_id}/exits")
async def add_floor_plan_exits(
    floor_plan_id: str,
    payload: ManualExitUpdateRequest,
    floor_number: Optional[int] = None,
    current_user: dict = Depends(get_request_actor),
):
    """Add manual exits to a floor plan."""
    return await floor_plan_mutation_service.add_exits(
        floor_plan_id,
        payload,
        floor_number=floor_number,
        current_user=current_user,
    )


@router.put("/floor-plans/{floor_plan_id}/exits")
async def replace_floor_plan_exits(
    floor_plan_id: str,
    payload: ManualExitUpdateRequest,
    floor_number: Optional[int] = None,
    current_user: dict = Depends(get_request_actor),
):
    """Replace manual exits for a floor plan."""
    return await floor_plan_mutation_service.add_exits(
        floor_plan_id,
        payload,
        floor_number=floor_number,
        current_user=current_user,
        merge=False,
    )


@router.delete("/floor-plans/{floor_plan_id}/exits/{exit_id}")
async def delete_floor_plan_exit(
    floor_plan_id: str,
    exit_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Delete a manual exit from a floor plan."""
    return await floor_plan_mutation_service.delete_exit(
        floor_plan_id,
        exit_id,
        current_user=current_user,
    )
