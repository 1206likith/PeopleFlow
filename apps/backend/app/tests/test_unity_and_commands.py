from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.simulation_state import simulation_state_manager
from app.services.unity_bridge import unity_bridge


@pytest.fixture
def client():
    settings.RATE_LIMIT_ENABLED = False
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "test-admin-key"
    settings.APP_MODE = "demo"
    with TestClient(app) as test_client:
        yield test_client


def _assert_v2_error_status(body: dict, expected_status: int) -> None:
    assert body.get("error", {}).get("status_code") == expected_status


def test_unity_status_returns_connection_diagnostics(client: TestClient):
    response = client.get("/api/v2/unity/status/sim-status")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["version"] == "v2"
    data = body["data"]
    assert data["simulation_id"] == "sim-status"
    assert "connected" in data
    assert "runtime_status" in data


def test_unity_control_returns_404_when_unity_missing(client: TestClient):
    with patch("app.api.routes.unity.unity_bridge.pause_simulation", new=AsyncMock(side_effect=ConnectionError("No Unity connection"))):
        response = client.post(
            "/api/v2/unity/control",
            json={"simulation_id": "sim-x", "command": "pause"},
            headers={"X-Admin-Key": "test-admin-key"},
        )
    assert response.status_code == 404
    body = response.json()
    _assert_v2_error_status(body, 404)
    assert body["error"]["message"] == "No Unity connection"


def test_simulation_command_validates_required_fields(client: TestClient):
    response = client.post(
        "/api/v2/simulations/sim-cmd/command",
        json={"type": "close_exit"},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert response.status_code == 400
    body = response.json()
    _assert_v2_error_status(body, 400)
    assert "exit_id is required" in body["error"]["message"]


def test_simulation_command_dispatches_to_unity_when_connected(client: TestClient):
    with patch.object(unity_bridge, "has_connection", return_value=True), patch.object(
        unity_bridge, "send_to_unity", new=AsyncMock()
    ) as send_mock:
        response = client.post(
            "/api/v2/simulations/sim-cmd/command",
            json={"type": "close_exit", "exit_id": "exit-a"},
            headers={"X-Admin-Key": "test-admin-key"},
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dispatched_to_unity"] is True
    send_mock.assert_awaited_once()


def test_simulation_command_rejects_terminal_status(client: TestClient):
    simulation_state_manager.register_simulation("sim-term", status="running")
    simulation_state_manager.mark_completed("sim-term", final_status="completed")
    response = client.post(
        "/api/v2/simulations/sim-term/command",
        json={"type": "emergency_announcement", "message": "Evacuate now"},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert response.status_code == 409
    body = response.json()
    _assert_v2_error_status(body, 409)
    assert "not commandable" in body["error"]["message"]


def test_simulation_pause_resume_stop_routes_work_for_mock_ids(client: TestClient):
    headers = {"X-Admin-Key": "test-admin-key"}

    pause_resp = client.post("/api/v2/simulations/mock-control/pause", headers=headers)
    assert pause_resp.status_code == 200
    pause_data = pause_resp.json()["data"]
    assert pause_data["message"] == "Simulation paused"

    resume_resp = client.post("/api/v2/simulations/mock-control/resume", headers=headers)
    assert resume_resp.status_code == 200
    resume_data = resume_resp.json()["data"]
    assert resume_data["message"] == "Simulation resumed"

    stop_resp = client.post("/api/v2/simulations/mock-control/stop", headers=headers)
    assert stop_resp.status_code == 200
    stop_data = stop_resp.json()["data"]
    assert stop_data["message"] == "Simulation stopped"


def test_simulation_catalog_routes_support_mock_runs(client: TestClient):
    list_resp = client.get("/api/v2/simulations/")
    assert list_resp.status_code == 200
    list_data = list_resp.json()["data"]
    assert isinstance(list_data["simulations"], list)
    assert list_data["total"] >= 1

    get_resp = client.get("/api/v2/simulations/mock-catalog")
    assert get_resp.status_code == 200
    get_data = get_resp.json()["data"]
    assert get_data["id"] == "mock-catalog"
    assert get_data["status"] in {"running", "completed"}

    metadata_resp = client.put(
        "/api/v2/simulations/mock-catalog/metadata",
        json={"label": "Catalog Mock", "tags": ["demo"]},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert metadata_resp.status_code == 200
    metadata_data = metadata_resp.json()["data"]
    assert metadata_data["simulation_id"] == "mock-catalog"
    assert metadata_data["status"] == "mock"
    assert metadata_data["updates"]["label"] == "Catalog Mock"

    get_after_resp = client.get("/api/v2/simulations/mock-catalog")
    assert get_after_resp.status_code == 200
    get_after_data = get_after_resp.json()["data"]
    assert get_after_data["label"] == "Catalog Mock"
    assert get_after_data["tags"] == ["demo"]


def test_simulation_live_update_routes_broadcast_payloads(client: TestClient):
    headers = {"X-Admin-Key": "test-admin-key"}
    with patch(
        "app.services.simulation_live_update_service.manager.broadcast_to_simulation",
        new=AsyncMock(),
    ) as broadcast_mock:
        hazards_resp = client.post(
            "/api/v2/simulations/mock-live/hazards/update",
            json={
                "hazards": [
                    {"type": "fire", "x": 12.0, "y": 8.0, "z": 0.0, "intensity": 0.7, "radius": 4.0}
                ]
            },
            headers=headers,
        )
        assert hazards_resp.status_code == 200
        hazards_data = hazards_resp.json()["data"]
        assert hazards_data["status"] == "broadcast"
        assert hazards_data["hazards"][0]["hazard_type"] == "fire"

        exits_resp = client.post(
            "/api/v2/simulations/mock-live/exits/update",
            json={
                "exits": [
                    {"id": "exit-a", "name": "Exit A", "x": 4.0, "y": 0.0, "z": 6.0, "width": 2.5}
                ]
            },
            headers=headers,
        )
        assert exits_resp.status_code == 200
        exits_data = exits_resp.json()["data"]
        assert exits_data["status"] == "broadcast"
        assert exits_data["exits"][0]["id"] == "exit-a"

        boundary_resp = client.post(
            "/api/v2/simulations/mock-live/boundary/update",
            json={
                "boundary": {
                    "points": [
                        {"x": 0.0, "y": 0.0},
                        {"x": 10.0, "y": 0.0},
                        {"x": 10.0, "y": 10.0},
                        {"x": 0.0, "y": 10.0},
                    ],
                    "min_x": 0.0,
                    "max_x": 10.0,
                    "min_z": 0.0,
                    "max_z": 10.0,
                }
            },
            headers=headers,
        )
        assert boundary_resp.status_code == 200
        boundary_data = boundary_resp.json()["data"]
        assert boundary_data["status"] == "broadcast"
        assert len(boundary_data["boundary"]["points"]) == 4

    assert broadcast_mock.await_count == 3
