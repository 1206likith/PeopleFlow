"""
Scenario launch routes extracted from the main simulation router.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.contracts.simulation_contracts import ScenarioStartRequest
from app.core.request_context import get_request_actor
from app.services.simulation_scenario_service import simulation_scenario_application_service
from app.services.simulation_start_service import simulation_start_service

router = APIRouter()


@router.post("/start-scenario")
async def start_scenario_simulations(
    request: Request,
    scenario: ScenarioStartRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Start multiple simulations for a multi-floor/multi-building scenario."""
    return await simulation_scenario_application_service.start_scenario(
        request,
        scenario,
        current_user,
        start_simulation_fn=simulation_start_service.start_simulation,
    )
