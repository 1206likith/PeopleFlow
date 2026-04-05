from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import ValidationError
from typing import Optional
import logging
from app.core.request_context import get_request_actor
from app.core.validation import SimulationFrameSchema
from app.services.frame_ingest import ingest_frame
from app.core.config import settings
from app.services.legacy_results_service import legacy_results_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/{simulation_id}/frame")
async def save_simulation_frame(
    simulation_id: str,
    request: Request,
    current_user: Optional[dict] = Depends(get_request_actor)
):
    """Save a simulation frame with production-grade validation"""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    # Parse and validate JSON body
    try:
        frame_json = await request.json()
        # Validate frame structure
        SimulationFrameSchema(**frame_json)
    except ValidationError as e:
        logger.warning(f"Invalid frame data: {e}", extra={"correlation_id": correlation_id, "simulation_id": simulation_id})
        raise HTTPException(status_code=400, detail=f"Invalid frame format: {e}")
    except Exception as e:
        logger.error(f"Error parsing frame: {e}", extra={"correlation_id": correlation_id, "simulation_id": simulation_id})
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Ingest frame (broadcast + store)
    try:
        frame_id, _ = await ingest_frame(simulation_id, frame_json)
    except Exception as e:
        logger.warning(
            f"Frame ingest failed: {e}",
            extra={"correlation_id": correlation_id, "simulation_id": simulation_id},
        )
        frame_id = None

    # Track metrics
    from app.core.metrics import websocket_messages_total
    websocket_messages_total.labels(message_type="simulation_update").inc()
    
    if simulation_id.startswith("mock-"):
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=404, detail="Simulation not found")
        return {"message": "Frame saved (demo mode)", "frame_id": "mock"}

    return {"message": "Frame saved", "frame_id": frame_id or "unknown"}

@router.get("/{simulation_id}/frames")
async def get_simulation_frames(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
    skip: int = 0,
    limit: int = 100
):
    """Get simulation frames"""
    try:
        del current_user
        return await legacy_results_service.get_frames(
            simulation_id,
            skip=skip,
            limit=limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Database unavailable for get_frames: {e}")
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return {"frames": [], "total": 0}

@router.get("/{simulation_id}/summary")
async def get_simulation_summary(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor)
):
    """Get simulation summary statistics"""
    try:
        del current_user
        return await legacy_results_service.get_summary(simulation_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Database unavailable for get_summary: {e}")
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        raise HTTPException(status_code=404, detail="Simulation not found")


