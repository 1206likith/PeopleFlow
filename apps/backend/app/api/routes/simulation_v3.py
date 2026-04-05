"""
Canonical v3 session-oriented simulation API.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.api.contracts.simulation_session_contracts import (
    SimulationControlCommandSchema,
    SimulationSessionConfigSchema,
)
from app.services.simulation_session_service import simulation_session_service

router = APIRouter()


@router.post("/sessions")
async def create_simulation_session(request: Request, config: SimulationSessionConfigSchema):
    return await simulation_session_service.create_session(request, config)


@router.get("/sessions")
async def list_simulation_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
):
    return await simulation_session_service.list_sessions(skip=skip, limit=limit)


@router.get("/sessions/{session_id}")
async def get_simulation_session(session_id: str):
    return await simulation_session_service.get_session(session_id)


@router.post("/sessions/{session_id}/control")
async def control_simulation_session(request: Request, session_id: str, command: SimulationControlCommandSchema):
    return await simulation_session_service.control_session(request, session_id, command)


@router.get("/sessions/{session_id}/stream")
async def get_simulation_session_stream(session_id: str):
    return await simulation_session_service.get_stream_descriptor(session_id)


@router.get("/sessions/{session_id}/analysis")
async def get_simulation_session_analysis(session_id: str):
    return await simulation_session_service.get_analysis(session_id)


@router.get("/sessions/{session_id}/replay")
async def get_simulation_session_replay(
    session_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=180, ge=1, le=2000),
):
    return await simulation_session_service.get_replay_slice(session_id, offset=offset, limit=limit)
