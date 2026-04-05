import json
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.core.config import settings


def test_unity_ws_requires_admin_key():
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "ws-key"

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/unity/test-sim"):
            pass


def test_unity_ws_accepts_valid_admin_key():
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "ws-key"

    client = TestClient(app)
    with client.websocket_connect("/ws/unity/test-sim?admin_key=ws-key"):
        pass


def test_client_ws_rejects_write_message_without_admin_key():
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "ws-key"

    client = TestClient(app)
    with client.websocket_connect("/ws/test-sim") as ws:
        ws.send_text(json.dumps({"type": "simulation_update", "payload": {"x": 1}}))
        message = ws.receive_json()
        assert message["type"] == "error"
        assert "admin_key required" in message["message"]


def test_client_ws_allows_write_message_with_admin_key():
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "ws-key"

    client = TestClient(app)
    with client.websocket_connect("/ws/test-sim?admin_key=ws-key") as ws:
        ws.send_text(json.dumps({"type": "simulation_update", "payload": {"x": 1}}))
        message = ws.receive_json()
        assert message["type"] == "simulation_update"
