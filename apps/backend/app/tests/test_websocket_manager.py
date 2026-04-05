import asyncio
import json

from fastapi.testclient import TestClient

import app.api.websocket as websocket_module
from app.api.websocket import ConnectionManager, websocket_endpoint
from app.core.config import settings
from app.main import app


class _DummyWebSocket:
    def __init__(self, fail_on_send: bool = False):
        self.fail_on_send = fail_on_send
        self.accepted = False
        self.messages = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message):
        if self.fail_on_send:
            raise RuntimeError("send failed")
        self.messages.append(message)


def test_connection_manager_connect_disconnect_and_personal_message():
    manager = ConnectionManager()
    ws = _DummyWebSocket()

    asyncio.run(manager.connect(ws, simulation_id="sim-1"))
    assert ws.accepted is True
    assert ws in manager.active_connections
    assert ws in manager.simulation_connections["sim-1"]

    asyncio.run(manager.send_personal_message({"type": "hello"}, ws))
    assert ws.messages[-1]["type"] == "hello"

    manager.disconnect(ws, simulation_id="sim-1")
    assert ws not in manager.active_connections
    assert ws not in manager.simulation_connections["sim-1"]


def test_connection_manager_broadcast_removes_disconnected():
    manager = ConnectionManager()
    ok_ws = _DummyWebSocket()
    failing_ws = _DummyWebSocket(fail_on_send=True)

    asyncio.run(manager.connect(ok_ws, simulation_id="sim-2"))
    asyncio.run(manager.connect(failing_ws, simulation_id="sim-2"))

    asyncio.run(manager.broadcast_to_simulation({"type": "update"}, "sim-2"))
    assert ok_ws.messages[-1]["type"] == "update"
    assert failing_ws not in manager.simulation_connections["sim-2"]

    # Re-add failing socket to exercise global broadcast disconnect path.
    asyncio.run(manager.connect(failing_ws, simulation_id=None, already_accepted=True))
    asyncio.run(manager.broadcast({"type": "global"}))
    assert ok_ws.messages[-1]["type"] == "global"
    assert failing_ws not in manager.active_connections


def test_websocket_endpoint_ping_invalid_json_and_subscribe():
    old_enabled = settings.ADMIN_KEY_ENABLED
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "ws-key"
    client = TestClient(app)
    try:
        with client.websocket_connect("/ws") as ws:
            ws.send_text("not-json")
            invalid = ws.receive_json()
            assert invalid["type"] == "error"

            ws.send_text(json.dumps({"type": "ping"}))
            pong = ws.receive_json()
            assert pong["type"] == "pong"

            ws.send_text(json.dumps({"type": "subscribe", "simulation_id": "sim-abc"}))
            subscribed = ws.receive_json()
            assert subscribed["type"] == "subscribed"
            assert subscribed["simulation_id"] == "sim-abc"
    finally:
        settings.ADMIN_KEY_ENABLED = old_enabled


class _FailingConnectManager:
    async def connect(self, *_args, **_kwargs):
        raise RuntimeError("connect failed")


class _NoopManager:
    async def connect(self, *_args, **_kwargs):
        return None

    async def send_personal_message(self, *_args, **_kwargs):
        return None

    async def broadcast_to_simulation(self, *_args, **_kwargs):
        return None

    def disconnect(self, *_args, **_kwargs):
        return None


class _FailingWebSocket:
    def __init__(self):
        self.query_params = {}
        self.closed = False

    async def close(self, code: int, reason: str):
        self.closed = True


class _ExplodingReceiveWebSocket:
    def __init__(self):
        self.query_params = {}

    async def receive_text(self):
        raise RuntimeError("receive failed")


def test_websocket_endpoint_handles_connect_failure():
    original_manager = websocket_module.manager
    websocket_module.manager = _FailingConnectManager()
    try:
        ws = _FailingWebSocket()
        asyncio.run(websocket_endpoint(ws, "sim-x"))
        assert ws.closed is True
    finally:
        websocket_module.manager = original_manager


def test_websocket_endpoint_handles_unexpected_runtime_error():
    original_manager = websocket_module.manager
    websocket_module.manager = _NoopManager()
    try:
        ws = _ExplodingReceiveWebSocket()
        asyncio.run(websocket_endpoint(ws, "sim-x"))
    finally:
        websocket_module.manager = original_manager


def test_websocket_subscribe_reassigns_existing_simulation_membership():
    old_enabled = settings.ADMIN_KEY_ENABLED
    settings.ADMIN_KEY_ENABLED = False
    client = TestClient(app)
    try:
        with client.websocket_connect("/ws/sim-one") as ws:
            ws.send_text(json.dumps({"type": "subscribe", "simulation_id": "sim-two"}))
            response = ws.receive_json()
            assert response["type"] == "subscribed"
            assert response["simulation_id"] == "sim-two"
    finally:
        settings.ADMIN_KEY_ENABLED = old_enabled
