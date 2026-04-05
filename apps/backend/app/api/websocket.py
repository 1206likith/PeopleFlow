import json
import logging
from typing import Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

    _WS_CONNECTION_ERRORS = (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK)
except Exception:
    _WS_CONNECTION_ERRORS = ()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.simulation_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, simulation_id: Optional[str] = None, already_accepted: bool = False):
        """Accept a new WebSocket connection or add to existing connections."""
        if not already_accepted:
            await websocket.accept()

        if websocket not in self.active_connections:
            self.active_connections.append(websocket)

        if simulation_id:
            if simulation_id not in self.simulation_connections:
                self.simulation_connections[simulation_id] = []
            if websocket not in self.simulation_connections[simulation_id]:
                self.simulation_connections[simulation_id].append(websocket)

    def disconnect(self, websocket: WebSocket, simulation_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        if simulation_id and simulation_id in self.simulation_connections:
            if websocket in self.simulation_connections[simulation_id]:
                self.simulation_connections[simulation_id].remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection."""
        await websocket.send_json(message)

    async def broadcast_to_simulation(self, message: dict, simulation_id: str):
        """Broadcast message to all connections for a simulation."""
        if simulation_id in self.simulation_connections:
            disconnected = []
            for connection in self.simulation_connections[simulation_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

            for conn in disconnected:
                self.disconnect(conn, simulation_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


def _is_normal_websocket_disconnect(error: BaseException) -> bool:
    if isinstance(error, (WebSocketDisconnect, ConnectionResetError, ConnectionAbortedError)):
        return True
    if _WS_CONNECTION_ERRORS and isinstance(error, _WS_CONNECTION_ERRORS):
        return True
    message = str(error).lower()
    return "no close frame received or sent" in message or "connection closed" in message


async def websocket_endpoint(websocket: WebSocket, simulation_id: Optional[str] = None):
    """WebSocket endpoint for real-time simulation updates."""
    admin_key = websocket.query_params.get("admin_key")
    is_admin = bool(settings.ADMIN_KEY_ENABLED) and admin_key == settings.ADMIN_API_KEY

    try:
        await manager.connect(websocket, simulation_id, already_accepted=False)
    except Exception as e:
        logger.error("WebSocket connection error: %s", e)
        try:
            await websocket.close(code=1008, reason="Connection failed")
        except Exception:
            pass
        return

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON payload"},
                    websocket,
                )
                continue

            message_type = message.get("type")

            if message_type == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)
                continue

            if message_type == "simulation_update":
                if settings.ADMIN_KEY_ENABLED and not is_admin:
                    await manager.send_personal_message(
                        {"type": "error", "message": "admin_key required for write operations"},
                        websocket,
                    )
                    continue
                if simulation_id:
                    await manager.broadcast_to_simulation(message, simulation_id)
                continue

            if message_type == "subscribe":
                new_sim_id = message.get("simulation_id")
                if new_sim_id and new_sim_id != simulation_id:
                    if simulation_id and simulation_id in manager.simulation_connections:
                        if websocket in manager.simulation_connections[simulation_id]:
                            manager.simulation_connections[simulation_id].remove(websocket)

                    if new_sim_id not in manager.simulation_connections:
                        manager.simulation_connections[new_sim_id] = []
                    if websocket not in manager.simulation_connections[new_sim_id]:
                        manager.simulation_connections[new_sim_id].append(websocket)

                    simulation_id = new_sim_id
                    await manager.send_personal_message(
                        {"type": "subscribed", "simulation_id": simulation_id},
                        websocket,
                    )

    except WebSocketDisconnect:
        manager.disconnect(websocket, simulation_id)
    except Exception as e:
        if _is_normal_websocket_disconnect(e):
            manager.disconnect(websocket, simulation_id)
            return
        logger.error("WebSocket error: %s", e, exc_info=True)
        manager.disconnect(websocket, simulation_id)
