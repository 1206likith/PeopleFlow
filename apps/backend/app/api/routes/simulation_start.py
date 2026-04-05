"""
Simulation start route extracted from the main simulation router.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.contracts.simulation_contracts import SimulationResponse
from app.core.request_context import get_request_actor
from app.core.validation import SimulationConfigSchema
from app.services.simulation_start_service import simulation_start_service

router = APIRouter()


@router.post("/start", response_model=SimulationResponse)
async def start_simulation(
    request: Request,
    config: SimulationConfigSchema,
    current_user: dict = Depends(get_request_actor),
):
    """Start a new simulation with production-grade validation."""
    return await simulation_start_service.start_simulation(request, config, current_user)
