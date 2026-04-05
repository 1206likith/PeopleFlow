"""
Live runtime update service for simulation hazards, exits, and boundaries.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from app.api.websocket import manager
from app.services.audit_log import record_event
from app.services.unity_bridge import unity_bridge

logger = logging.getLogger(__name__)


def _safe_audit(
    action: str,
    actor: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    severity: str = "info",
) -> None:
    try:
        record_event(action=action, actor=actor, metadata=metadata, severity=severity)
    except Exception:
        pass


class SimulationLiveUpdateService:
    @staticmethod
    def _user_id(current_user: dict) -> str:
        return str(current_user.get("_id", current_user.get("id", "demo_user")))

    async def _dispatch(self, simulation_id: str, message: Dict[str, Any]) -> str:
        unity_connected = simulation_id in unity_bridge.unity_connections
        if unity_connected:
            try:
                await unity_bridge.send_to_unity(simulation_id, message)
            except Exception as exc:
                logger.warning("Failed to send update to Unity: %s", exc)
                unity_connected = False

        await manager.broadcast_to_simulation(message, simulation_id)
        return "sent" if unity_connected else "broadcast"

    async def update_hazards(self, simulation_id: str, hazards: List[Any], *, current_user: dict) -> Dict[str, Any]:
        hazards_payload = []
        for hazard in hazards:
            hazard_dict = hazard.model_dump() if hasattr(hazard, "model_dump") else hazard.dict()
            metadata = hazard_dict.get("metadata") or {}
            hazard_type = hazard_dict.get("type")
            hazards_payload.append(
                {
                    "id": hazard_dict.get("id") or f"hazard-{uuid.uuid4().hex[:8]}",
                    "hazard_type": hazard_type,
                    "x": hazard_dict.get("x", 0.0),
                    "y": hazard_dict.get("y", 0.0),
                    "z": hazard_dict.get("z", 0.0),
                    "radius": hazard_dict.get("radius", 10.0),
                    "intensity": hazard_dict.get("intensity", 0.5),
                    "growth_rate": metadata.get("growth_rate", 0.0),
                    "smoke_density": metadata.get("smoke_density", 0.0),
                    "blocks_exits": hazard_type == "blocked_exit" or bool(metadata.get("blocks_exits")),
                    "is_active": True,
                    "start_time": hazard_dict.get("start_time", 0.0),
                    "duration": hazard_dict.get("duration") or 0.0,
                }
            )

        message = {
            "schema_version": 1,
            "type": "update_hazards",
            "simulation_id": simulation_id,
            "hazards": hazards_payload,
        }
        status = await self._dispatch(simulation_id, message)
        _safe_audit(
            "simulation_hazards_updated",
            actor=self._user_id(current_user),
            metadata={"simulation_id": simulation_id, "hazard_count": len(hazards_payload)},
        )
        return {"status": status, "hazards": hazards_payload}

    async def update_exits(self, simulation_id: str, exits: List[Any], *, current_user: dict) -> Dict[str, Any]:
        exits_payload = []
        for exit_item in exits:
            exit_dict = exit_item.model_dump() if hasattr(exit_item, "model_dump") else exit_item.dict()
            exits_payload.append(
                {
                    "id": exit_dict.get("id") or f"exit-{uuid.uuid4().hex[:8]}",
                    "label": exit_dict.get("name") or "Exit",
                    "x": exit_dict.get("x", 0.0),
                    "y": exit_dict.get("y", 0.0),
                    "z": exit_dict.get("z", 0.0) or 0.0,
                    "width": exit_dict.get("width", 2.0),
                    "capacity": exit_dict.get("capacity") or 100.0,
                    "is_emergency": exit_dict.get("is_emergency", True),
                    "is_accessible": exit_dict.get("is_accessible", True),
                    "is_blocked": False,
                    "preference_weight": 1.0,
                    "queue_radius": 4.0,
                }
            )

        message = {
            "schema_version": 1,
            "type": "update_exits",
            "simulation_id": simulation_id,
            "exits": exits_payload,
        }
        status = await self._dispatch(simulation_id, message)
        _safe_audit(
            "simulation_exits_updated",
            actor=self._user_id(current_user),
            metadata={"simulation_id": simulation_id, "exit_count": len(exits_payload)},
        )
        return {"status": status, "exits": exits_payload}

    async def update_boundary(self, simulation_id: str, boundary: Any, *, current_user: dict) -> Dict[str, Any]:
        boundary_payload = boundary.model_dump() if hasattr(boundary, "model_dump") else boundary.dict()
        message = {
            "schema_version": 1,
            "type": "update_boundary",
            "simulation_id": simulation_id,
            "boundary": boundary_payload,
        }
        status = await self._dispatch(simulation_id, message)
        _safe_audit(
            "simulation_boundary_updated",
            actor=self._user_id(current_user),
            metadata={
                "simulation_id": simulation_id,
                "boundary_points": len(boundary_payload.get("points", []) if isinstance(boundary_payload, dict) else []),
            },
        )
        return {"status": status, "boundary": boundary_payload}


simulation_live_update_service = SimulationLiveUpdateService()
