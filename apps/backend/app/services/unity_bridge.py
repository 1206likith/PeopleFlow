"""
Unity Bridge Service
Handles communication between Unity simulation and FastAPI backend
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect

from app.api.websocket import manager
from app.services.floor_plan_document_service import fetch_floor_plan_doc
from app.services.frame_ingest import ingest_frame
from app.services.simulation_repository import get_simulation_repository
from app.services.simulation_state import simulation_state_manager

logger = logging.getLogger(__name__)


class UnityBridge:
    """
    Manages connection and communication with Unity simulation.
    """

    def __init__(self):
        self.unity_connections: Dict[str, WebSocket] = {}
        self.simulation_status: Dict[str, str] = {}
        self.last_seen: Dict[str, str] = {}

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _set_status(self, simulation_id: str, status: str) -> None:
        self.simulation_status[simulation_id] = status
        self.last_seen[simulation_id] = self._utc_now_iso()

    def connection_count(self) -> int:
        return len(self.unity_connections)

    def has_connection(self, simulation_id: str) -> bool:
        return simulation_id in self.unity_connections

    def get_status(self, simulation_id: str) -> str:
        """Get Unity connection status for simulation."""
        if simulation_id in self.unity_connections:
            return self.simulation_status.get(simulation_id, "connected")
        return self.simulation_status.get(simulation_id, "not_connected")

    def get_connection_status(self, simulation_id: str) -> Dict[str, Any]:
        """Get richer status details for diagnostics and API responses."""
        return {
            "simulation_id": simulation_id,
            "status": self.get_status(simulation_id),
            "connected": self.has_connection(simulation_id),
            "last_seen": self.last_seen.get(simulation_id),
            "runtime_status": simulation_state_manager.get_status(simulation_id),
        }

    async def _handle_unity_message(self, simulation_id: str, data: Dict[str, Any]) -> None:
        """
        Handle message from Unity.

        Args:
            simulation_id: Simulation identifier
            data: Message data from Unity
        """
        message_type = str(data.get("type") or "")
        self.last_seen[simulation_id] = self._utc_now_iso()

        if message_type == "simulation_update":
            self._set_status(simulation_id, "running")
            try:
                await ingest_frame(simulation_id, data)
            except Exception as exc:
                logger.warning("Frame ingest failed for Unity simulation %s: %s", simulation_id, exc)
            return

        if message_type == "simulation_complete":
            self._set_status(simulation_id, "completed")
            simulation_state_manager.mark_completed(simulation_id, final_status="completed")
            await manager.broadcast_to_simulation(
                {
                    "schema_version": 1,
                    "type": "simulation_complete",
                    "simulation_id": simulation_id,
                    "timestamp": self._utc_now_iso(),
                },
                simulation_id,
            )
            return

        if message_type == "request_floor_plan":
            await self._send_floor_plan_to_unity(simulation_id)
            return

        if message_type == "error":
            logger.error("Unity error for simulation %s: %s", simulation_id, data.get("message"))
            self._set_status(simulation_id, "error")
            simulation_state_manager.mark_completed(simulation_id, final_status="error")
            return

        if message_type in {"heartbeat", "status"}:
            self._set_status(simulation_id, "connected")
            return

        logger.warning("Unknown Unity message type for simulation %s: %s", simulation_id, message_type)

    async def _send_floor_plan_to_unity(self, simulation_id: str) -> None:
        """Send floor plan data to Unity."""
        if simulation_id.startswith("mock-"):
            return

        try:
            simulation_repository = await get_simulation_repository()
            simulation = await simulation_repository.get(simulation_id)
            if not simulation:
                logger.warning("Simulation not found for floor plan request: %s", simulation_id)
                return

            floor_plan_id = simulation.get("floor_plan_id")
            if not floor_plan_id:
                logger.warning("No floor_plan_id on simulation %s", simulation_id)
                return

            floor_plan = await fetch_floor_plan_doc(
                str(floor_plan_id),
                str(simulation.get("user_id") or "system"),
            )
            if not floor_plan:
                logger.warning("Floor plan %s not found for simulation %s", floor_plan_id, simulation_id)
                return

            await self.send_to_unity(
                simulation_id,
                {
                    "schema_version": 1,
                    "type": "floor_plan_data",
                    "simulation_id": simulation_id,
                    "building_name": floor_plan.get("building_name", "Building"),
                    "floors": floor_plan.get("floors", []),
                    "file_path": floor_plan.get("file_path"),
                    "floor_number": simulation.get("floor_number", 1),
                    "detected_walls": floor_plan.get("detected_walls", []),
                    "boundaries": floor_plan.get("boundaries", []),
                    "boundary_polygon": floor_plan.get("boundary_polygon", []),
                    "building_bounds": floor_plan.get("building_bounds", {}),
                    "detected_obstacles": floor_plan.get("detected_obstacles", []),
                    "rooms": floor_plan.get("rooms", []),
                    "corridors": floor_plan.get("corridors", []),
                    "open_spaces": floor_plan.get("open_spaces", []),
                    "doors": floor_plan.get("doors", []),
                    "quality": floor_plan.get("quality", {}),
                },
            )
            logger.info("Sent floor plan data to Unity for simulation %s", simulation_id)
        except Exception as exc:
            logger.warning("Error sending floor plan to Unity for %s: %s", simulation_id, exc)

    async def send_to_unity(self, simulation_id: str, message: Dict[str, Any]) -> None:
        """
        Send message to Unity simulation.
        """
        ws = self.unity_connections.get(simulation_id)
        if not ws:
            raise ConnectionError(f"No Unity connection for simulation {simulation_id}")
        try:
            await ws.send_json(message)
            self.last_seen[simulation_id] = self._utc_now_iso()
        except Exception as exc:
            self.unity_connections.pop(simulation_id, None)
            self._set_status(simulation_id, "disconnected")
            raise ConnectionError(f"Failed to send Unity message for {simulation_id}") from exc

    async def _send_control_message(self, simulation_id: str, message_type: str, config: Dict[str, Any] | None = None) -> None:
        payload: Dict[str, Any] = {
            "schema_version": 1,
            "type": message_type,
            "simulation_id": simulation_id,
            "timestamp": self._utc_now_iso(),
        }
        if config is not None:
            payload["config"] = config
        await self.send_to_unity(simulation_id, payload)

    async def start_simulation(self, simulation_id: str, config: Dict[str, Any]) -> None:
        """Send start command to Unity."""
        await self._send_control_message(simulation_id, "start_simulation", config=config)
        self._set_status(simulation_id, "running")

    async def pause_simulation(self, simulation_id: str) -> None:
        """Pause simulation in Unity."""
        await self._send_control_message(simulation_id, "pause_simulation")
        self._set_status(simulation_id, "paused")

    async def resume_simulation(self, simulation_id: str) -> None:
        """Resume simulation in Unity."""
        await self._send_control_message(simulation_id, "resume_simulation")
        self._set_status(simulation_id, "running")

    async def stop_simulation(self, simulation_id: str) -> None:
        """Stop simulation in Unity and clean up connection."""
        ws = self.unity_connections.get(simulation_id)
        if ws:
            try:
                await self._send_control_message(simulation_id, "stop_simulation")
            except Exception as exc:
                logger.warning("Could not send stop command to Unity %s: %s", simulation_id, exc)
            try:
                await ws.close()
            except Exception:
                pass
            self.unity_connections.pop(simulation_id, None)
        self._set_status(simulation_id, "stopped")
        simulation_state_manager.stop_simulation(simulation_id)

    async def _save_simulation_frame(self, simulation_id: str, data: Dict[str, Any]) -> None:
        """Deprecated: use ingest_frame instead."""
        await ingest_frame(simulation_id, data)

    async def handle_unity_connection(self, websocket: WebSocket, simulation_id: str) -> None:
        """Handle incoming Unity WebSocket connection."""
        await websocket.accept()

        existing = self.unity_connections.get(simulation_id)
        if existing and existing is not websocket:
            try:
                await existing.close(code=1000, reason="Replaced by new Unity connection")
            except Exception:
                pass

        self.unity_connections[simulation_id] = websocket
        self._set_status(simulation_id, "connected")

        if simulation_state_manager.get_status(simulation_id) is None:
            simulation_state_manager.register_simulation(
                simulation_id,
                status="running",
                metadata={"source": "unity"},
            )

        logger.info("Unity connected via WebSocket: %s", simulation_id)

        try:
            while True:
                data = await websocket.receive_json()
                if not isinstance(data, dict):
                    logger.warning("Ignoring non-object Unity message for simulation %s", simulation_id)
                    continue
                await self._handle_unity_message(simulation_id, data)
        except WebSocketDisconnect:
            logger.info("Unity disconnected: %s", simulation_id)
            self._set_status(simulation_id, "disconnected")
            if simulation_state_manager.get_status(simulation_id) not in {"completed", "stopped"}:
                simulation_state_manager.mark_completed(simulation_id, final_status="disconnected")
        except Exception as exc:
            logger.error("Error in Unity WebSocket handler for %s: %s", simulation_id, exc, exc_info=True)
            self._set_status(simulation_id, "error")
            simulation_state_manager.mark_completed(simulation_id, final_status="error")
        finally:
            current = self.unity_connections.get(simulation_id)
            if current is websocket:
                self.unity_connections.pop(simulation_id, None)


# Global instance
unity_bridge = UnityBridge()
