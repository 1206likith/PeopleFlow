"""
Runtime control routes extracted from the main simulation router.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts.simulation_contracts import SimulationCommandRequest
from app.core.request_context import get_request_actor
from app.services.simulation_control_service import simulation_control_application_service

router = APIRouter()


@router.post("/{simulation_id}/pause")
async def pause_simulation(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Pause a running simulation."""
    return await simulation_control_application_service.pause(simulation_id, current_user)


@router.post("/{simulation_id}/resume")
async def resume_simulation(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Resume a paused simulation."""
    return await simulation_control_application_service.resume(simulation_id, current_user)


@router.post("/{simulation_id}/stop")
async def stop_simulation(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Stop a running simulation."""
    return await simulation_control_application_service.stop(simulation_id, current_user)


@router.post("/{simulation_id}/command")
async def send_simulation_command(
    simulation_id: str,
    command: SimulationCommandRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Send validated control command to a running simulation."""
    return await simulation_control_application_service.send_command(simulation_id, command, current_user)
