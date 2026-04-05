"""
Read-only floor-plan routes extracted from the main simulation router.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request, Response

from app.core.request_context import get_request_actor
from app.services.floor_plan_query_service import floor_plan_query_service

router = APIRouter()


@router.get("/floor-plans/{floor_plan_id}/exits")
async def get_floor_plan_exits(
    floor_plan_id: str,
    floor_number: Optional[int] = None,
    request: Request = None,
    response: Response = None,
    current_user: dict = Depends(get_request_actor),
):
    """Get exits for a floor plan, including manual and detected exits."""
    return await floor_plan_query_service.get_exits(
        floor_plan_id,
        floor_number=floor_number,
        current_user=current_user,
        request=request,
        response=response,
    )


@router.get("/floor-plans/{floor_plan_id}")
async def get_floor_plan_metadata(
    floor_plan_id: str,
    floor_number: Optional[int] = None,
    request: Request = None,
    response: Response = None,
    current_user: dict = Depends(get_request_actor),
):
    """Get full floor plan metadata for authoring tools."""
    return await floor_plan_query_service.get_metadata(
        floor_plan_id,
        floor_number=floor_number,
        current_user=current_user,
        request=request,
        response=response,
    )


@router.get("/floor-plans/{floor_plan_id}/pipeline")
async def get_floor_plan_pipeline(
    floor_plan_id: str,
    request: Request = None,
    response: Response = None,
    current_user: dict = Depends(get_request_actor),
):
    """Get processing pipeline details for a floor plan."""
    return await floor_plan_query_service.get_pipeline(
        floor_plan_id,
        current_user=current_user,
        request=request,
        response=response,
    )


@router.get("/floor-plans/{floor_plan_id}/quality-report")
async def get_floor_plan_quality_report(
    floor_plan_id: str,
    floor_number: Optional[int] = None,
    current_user: dict = Depends(get_request_actor),
):
    """Return floor plan detection quality diagnostics and simulation readiness."""
    return await floor_plan_query_service.get_quality_report(
        floor_plan_id,
        floor_number=floor_number,
        current_user=current_user,
    )


@router.get("/floor-plans/{floor_plan_id}/annotations")
async def get_floor_plan_annotations(
    floor_plan_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Fetch human annotations used for curated blueprint training."""
    return await floor_plan_query_service.get_annotations(
        floor_plan_id,
        current_user=current_user,
    )
