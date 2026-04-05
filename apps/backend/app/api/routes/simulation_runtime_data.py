"""
Read-only runtime data routes extracted from the main simulation router.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Response

from app.core.request_context import get_request_actor
from app.services.simulation_runtime_query_service import simulation_runtime_query_service

router = APIRouter()


@router.get("/{simulation_id}/summary")
async def get_simulation_summary(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Get simulation summary stats (mock store or last frame)."""
    del current_user
    return await simulation_runtime_query_service.get_summary(simulation_id)


@router.get("/{simulation_id}/frames")
async def get_simulation_frames(
    simulation_id: str,
    limit: int = 200,
    skip: int = 0,
    stride: int = 1,
    from_ts: Optional[float] = None,
    to_ts: Optional[float] = None,
    current_user: dict = Depends(get_request_actor),
):
    """Fetch persisted simulation frames with optional sampling."""
    del current_user
    return await simulation_runtime_query_service.get_frames(
        simulation_id,
        limit=limit,
        skip=skip,
        stride=stride,
        from_ts=from_ts,
        to_ts=to_ts,
    )


@router.get("/{simulation_id}/frames/latest")
async def get_latest_frame(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Fetch the latest simulation frame."""
    del current_user
    return await simulation_runtime_query_service.get_latest_frame(simulation_id)


@router.get("/{simulation_id}/frames/export")
async def export_frames_csv(
    simulation_id: str,
    limit: int = 2000,
    stride: int = 1,
    current_user: dict = Depends(get_request_actor),
):
    """Export frames as CSV (summary fields only)."""
    del current_user
    return Response(
        content=await simulation_runtime_query_service.export_frames_csv(
            simulation_id,
            limit=limit,
            stride=stride,
        ),
        media_type="text/csv",
    )


@router.get("/{simulation_id}/timeline")
async def get_simulation_timeline(
    simulation_id: str,
    stride: int = 5,
    current_user: dict = Depends(get_request_actor),
):
    """Return a lightweight timeline of evacuation progress."""
    del current_user
    return await simulation_runtime_query_service.get_timeline(simulation_id, stride=stride)


@router.get("/{simulation_id}/agents")
async def get_simulation_agents(
    simulation_id: str,
    status: Optional[str] = None,
    current_user: dict = Depends(get_request_actor),
):
    """Get latest agent snapshot for a simulation."""
    del current_user
    return await simulation_runtime_query_service.get_agents(simulation_id, status=status)


@router.get("/{simulation_id}/hazards")
async def get_simulation_hazards(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Get latest hazard state for a simulation."""
    del current_user
    return await simulation_runtime_query_service.get_hazards(simulation_id)


@router.get("/{simulation_id}/exit-usage")
async def get_simulation_exit_usage(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Get exit usage summary for a simulation."""
    del current_user
    return await simulation_runtime_query_service.get_exit_usage(simulation_id)


@router.get("/{simulation_id}/profile-counts")
async def get_simulation_profile_counts(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Get profile group counts for a simulation."""
    del current_user
    return await simulation_runtime_query_service.get_profile_counts(simulation_id)


@router.get("/{simulation_id}/metrics")
async def get_simulation_metrics(
    simulation_id: str,
    limit: int = 1000,
    stride: int = 1,
    current_user: dict = Depends(get_request_actor),
):
    """Compute research-grade metrics from stored frames."""
    del current_user
    return await simulation_runtime_query_service.get_metrics(
        simulation_id,
        limit=limit,
        stride=stride,
    )


@router.get("/{simulation_id}/survival-score")
async def get_simulation_survival_score(
    simulation_id: str,
    disaster_type: Optional[str] = None,
    current_user: dict = Depends(get_request_actor),
):
    """Calculate survival score from the latest frame."""
    del current_user
    return await simulation_runtime_query_service.get_survival_score(
        simulation_id,
        disaster_type=disaster_type,
    )
