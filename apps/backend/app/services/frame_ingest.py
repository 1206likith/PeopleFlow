"""
Unified frame ingestion for simulation updates.
Validates, broadcasts, and stores frames with consistent logic.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple

from app.api.websocket import manager
from app.core.validation import SimulationFrameSchema
from app.services.simulation_result_repository import get_simulation_result_repository

logger = logging.getLogger(__name__)


async def ingest_frame(
    simulation_id: str,
    frame_data: Dict[str, Any],
    broadcast: bool = True,
) -> Tuple[Optional[str], SimulationFrameSchema]:
    """
    Validate and ingest a simulation frame.

    Returns:
        (inserted_id, validated_frame)
    """
    validated_frame = SimulationFrameSchema(**frame_data)
    try:
        from app.core.metrics import simulation_frames_ingested_total
        simulation_frames_ingested_total.labels(status="validated").inc()
    except Exception:
        pass

    if broadcast:
        payload = {
            "schema_version": 1,
            "type": "simulation_update",
            "simulation_id": simulation_id,
            "timestamp": validated_frame.timestamp,
            "agents": [
                a.model_dump() if hasattr(a, "model_dump") else a.dict()
                for a in validated_frame.agents
            ],
            "bottlenecks": [
                b.model_dump() if hasattr(b, "model_dump") else b.dict()
                for b in validated_frame.bottlenecks
            ],
            "hazards": [
                h.model_dump() if hasattr(h, "model_dump") else h.dict()
                for h in validated_frame.hazards
            ],
            "exit_usage": [
                e.model_dump() if hasattr(e, "model_dump") else e.dict()
                for e in validated_frame.exit_usage
            ],
            "exit_evac_counts": [
                e.model_dump() if hasattr(e, "model_dump") else e.dict()
                for e in validated_frame.exit_evac_counts
            ],
            "profile_counts": [
                p.model_dump() if hasattr(p, "model_dump") else p.dict()
                for p in validated_frame.profile_counts
            ],
            "stats": validated_frame.stats,
        }

        # Pass through optional fields if present (e.g., walls, exits)
        for key in ("walls", "exits", "obstacles", "frame_id", "seed", "hazard_state", "replay_id", "building_bounds", "session_id", "mode", "emergency_type"):
            if key in frame_data:
                payload[key] = frame_data.get(key)

        await manager.broadcast_to_simulation(payload, simulation_id)

    frame_doc = {
        "simulation_id": simulation_id,
        "timestamp": validated_frame.timestamp,
        "floor_number": validated_frame.floor_number,
        "agents": [
            a.model_dump() if hasattr(a, "model_dump") else a.dict()
            for a in validated_frame.agents
        ],
        "bottlenecks": [
            b.model_dump() if hasattr(b, "model_dump") else b.dict()
            for b in validated_frame.bottlenecks
        ],
        "hazards": [
            h.model_dump() if hasattr(h, "model_dump") else h.dict()
            for h in validated_frame.hazards
        ],
        "exit_usage": [
            e.model_dump() if hasattr(e, "model_dump") else e.dict()
            for e in validated_frame.exit_usage
        ],
        "exit_evac_counts": [
            e.model_dump() if hasattr(e, "model_dump") else e.dict()
            for e in validated_frame.exit_evac_counts
        ],
        "profile_counts": [
            p.model_dump() if hasattr(p, "model_dump") else p.dict()
            for p in validated_frame.profile_counts
        ],
        "stats": validated_frame.stats,
        "walls": frame_data.get("walls", []),
        "exits": frame_data.get("exits", []),
        "obstacles": frame_data.get("obstacles", []),
        "building_bounds": frame_data.get("building_bounds"),
        "frame_id": frame_data.get("frame_id"),
        "seed": frame_data.get("seed"),
        "hazard_state": frame_data.get("hazard_state"),
        "replay_id": frame_data.get("replay_id"),
        "session_id": frame_data.get("session_id"),
        "mode": frame_data.get("mode"),
        "emergency_type": frame_data.get("emergency_type"),
    }
    try:
        from app.services.simulation_store import save_frame

        save_frame(simulation_id, frame_doc)
    except Exception:
        pass

    if simulation_id.startswith("mock-"):
        try:
            from app.core.metrics import simulation_frames_ingested_total
            simulation_frames_ingested_total.labels(status="mock").inc()
        except Exception:
            pass
        return "mock", validated_frame

    inserted_id = None
    try:
        doc = {**frame_doc, "created_at": datetime.now(timezone.utc)}
        repository = await get_simulation_result_repository()
        inserted_id = await repository.insert_frame(doc)
        try:
            from app.core.metrics import simulation_frames_ingested_total
            simulation_frames_ingested_total.labels(status="stored").inc()
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Failed to persist frame: {e}")
        try:
            from app.core.metrics import simulation_frames_ingested_total
            simulation_frames_ingested_total.labels(status="failed").inc()
        except Exception:
            pass

    return inserted_id, validated_frame
