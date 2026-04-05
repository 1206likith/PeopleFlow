"""
Catalog and metadata routes extracted from the main simulation router.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.request_context import get_request_actor
from app.services.simulation_catalog_service import simulation_catalog_service

router = APIRouter()


class SimulationMetadataUpdateRequest(BaseModel):
    tags: Optional[List[str]] = Field(default=None, max_length=20)
    notes: Optional[str] = Field(default=None, max_length=2000)
    label: Optional[str] = Field(default=None, max_length=200)
    priority: Optional[int] = Field(default=None, ge=1, le=10)


@router.get("/")
async def list_simulations(
    current_user: dict = Depends(get_request_actor),
    skip: int = 0,
    limit: int = 10,
):
    """List user's simulations."""
    del current_user
    return await simulation_catalog_service.list_simulations(skip=skip, limit=limit)


@router.put("/{simulation_id}/metadata")
async def update_simulation_metadata(
    simulation_id: str,
    payload: SimulationMetadataUpdateRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Update tags/notes/labels on a simulation."""
    del current_user
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    return await simulation_catalog_service.update_metadata(simulation_id, updates)


@router.get("/{simulation_id}")
async def get_simulation(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Get simulation details."""
    del current_user
    return await simulation_catalog_service.get_simulation(simulation_id)
