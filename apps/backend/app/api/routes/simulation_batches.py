"""
Batch simulation routes extracted from the main simulation router.
Public paths stay the same; implementation is isolated behind a dedicated service.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.api.contracts.simulation_contracts import BatchSimulationRequest
from app.core.request_context import get_request_actor
from app.services.idempotency import (
    build_idempotency_key,
    build_replay_response,
    get_cached_response,
    store_response,
)
from app.services.simulation_batch_service import simulation_batch_application_service

router = APIRouter()


@router.post("/start-batch")
async def start_batch_simulation(
    request: Request,
    batch: BatchSimulationRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Run a batch of simulations (ensemble) and return variance statistics."""
    user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
    raw_idempotency_key = request.headers.get("Idempotency-Key")
    idempotency_key = build_idempotency_key(request, user_id)
    if idempotency_key:
        cached = get_cached_response(idempotency_key)
        if cached:
            return build_replay_response(cached)

    batch_doc = await simulation_batch_application_service.run_batch_simulation(batch, user_id)

    if idempotency_key:
        store_response(
            idempotency_key,
            200,
            batch_doc,
            {"Idempotency-Key": raw_idempotency_key or idempotency_key},
            {"path": request.url.path},
        )

    return batch_doc


@router.get("/batches")
async def list_simulation_batches(
    current_user: dict = Depends(get_request_actor),
    skip: int = 0,
    limit: int = 20,
):
    """List batch simulation runs for the current user."""
    del current_user
    batches = await simulation_batch_application_service.list_batch_docs(skip=skip, limit=limit)
    normalized = [
        simulation_batch_application_service.normalize_batch_doc(batch_doc) or {}
        for batch_doc in batches
    ]
    return {"batches": normalized, "total": len(normalized)}


@router.get("/batches/{batch_id}")
async def get_simulation_batch(
    batch_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Get a batch simulation run by batch_id."""
    del current_user
    return await simulation_batch_application_service.get_batch_doc_or_404(batch_id)


@router.get("/batches/{batch_id}/export")
async def export_simulation_batch(
    batch_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Export batch results as CSV."""
    del current_user
    batch_doc = await simulation_batch_application_service.get_batch_doc_or_404(batch_id)
    return Response(
        content=simulation_batch_application_service.build_batch_csv(batch_doc),
        media_type="text/csv",
    )
