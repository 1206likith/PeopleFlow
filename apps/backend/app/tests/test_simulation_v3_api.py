from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.validation import SimulationFrameSchema
from app.services.simulation_session_service import simulation_session_service


def _unwrap_v3(payload: dict) -> dict:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _v3_headers() -> dict[str, str]:
    return {"X-Admin-Key": "test-admin-key", "X-Actor-ID": "test-suite"}


def _minimal_floor_plan_snapshot() -> dict:
    return {
        "pipeline": "client-snapshot",
        "building_bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100, "width": 100, "height": 100},
        "detected_walls": [
            {"x1": 0, "y1": 0, "x2": 100, "y2": 0, "length": 100, "type": "boundary"},
            {"x1": 100, "y1": 0, "x2": 100, "y2": 100, "length": 100, "type": "boundary"},
            {"x1": 100, "y1": 100, "x2": 0, "y2": 100, "length": 100, "type": "boundary"},
            {"x1": 0, "y1": 100, "x2": 0, "y2": 0, "length": 100, "type": "boundary"},
        ],
        "boundaries": [
            {"x1": 0, "y1": 0, "x2": 100, "y2": 0, "length": 100, "type": "boundary"},
            {"x1": 100, "y1": 0, "x2": 100, "y2": 100, "length": 100, "type": "boundary"},
            {"x1": 100, "y1": 100, "x2": 0, "y2": 100, "length": 100, "type": "boundary"},
            {"x1": 0, "y1": 100, "x2": 0, "y2": 0, "length": 100, "type": "boundary"},
        ],
        "exits": [
            {"id": "main-exit", "name": "Main Exit", "x": 50, "y": 0, "z": 0, "width": 3, "capacity": 100},
        ],
        "detected_obstacles": [],
        "rooms": [],
        "hazards": [],
    }


def _wait_for(predicate, timeout: float = 4.0, interval: float = 0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return None


def _get_replay_if_ready(client: TestClient, session_id: str):
    payload = _unwrap_v3(client.get(f"/api/v3/simulation/sessions/{session_id}/replay?limit=25").json())
    return payload if payload.get("count", 0) > 0 else None


def _get_session_if_status(client: TestClient, session_id: str, status: str):
    payload = _unwrap_v3(client.get(f"/api/v3/simulation/sessions/{session_id}").json())
    return payload if payload.get("state", {}).get("status") == status else None


def _create_session(client: TestClient) -> dict:
    response = client.post(
        "/api/v3/simulation/sessions",
        json={
            "floor_plan_snapshot": _minimal_floor_plan_snapshot(),
            "mode": "studio",
            "num_agents": 18,
            "emergency_type": "fire",
            "routing_policy": "guided_evacuation",
            "panic_level": 0.52,
            "seed": 20260403,
            "hazards": [],
            "agent_profiles": [],
            "blocked_exits": [],
            "storage_policy": {"record_frames": True, "max_frames": 320, "frame_stride": 1, "persist_frames": True},
            "max_runtime_seconds": 12,
        },
        headers=_v3_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["version"] == "v3"
    return _unwrap_v3(body)


def test_v3_simulation_session_create_list_and_detail(client: TestClient):
    settings.RATE_LIMIT_ENABLED = False
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "test-admin-key"
    settings.APP_MODE = "demo"

    session = _create_session(client)
    assert session["state"]["status"] == "draft"
    assert session["config"]["seed"] == 20260403

    list_response = client.get("/api/v3/simulation/sessions?limit=10")
    assert list_response.status_code == 200
    listed = _unwrap_v3(list_response.json())
    assert listed["total"] >= 1
    assert any(row["id"] == session["id"] for row in listed["sessions"])

    detail_response = client.get(f"/api/v3/simulation/sessions/{session['id']}")
    assert detail_response.status_code == 200
    detail = _unwrap_v3(detail_response.json())
    assert detail["id"] == session["id"]
    assert detail["config"]["routing_policy"] == "guided_evacuation"


def test_v3_create_session_preserves_canonical_id_when_repository_returns_storage_identifier(client: TestClient, monkeypatch):
    settings.RATE_LIMIT_ENABLED = False
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "test-admin-key"
    settings.APP_MODE = "demo"

    class FakeRepository:
        async def create(self, doc):
            self.created = dict(doc)
            return "db-row-123"

    repository = FakeRepository()

    async def fake_get_repository():
        return repository

    monkeypatch.setattr(
        "app.services.simulation_session_service.get_simulation_session_repository",
        fake_get_repository,
    )

    session = _create_session(client)
    assert session["id"].startswith("session-")
    assert session["id"] == repository.created["id"]


def test_v3_session_start_failure_returns_controlled_error_and_marks_session(client: TestClient, monkeypatch):
    settings.RATE_LIMIT_ENABLED = False
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "test-admin-key"
    settings.APP_MODE = "demo"

    session = _create_session(client)
    session_id = session["id"]

    async def fake_load_floor_plan_data(_config):
        raise RuntimeError("floor plan bootstrap failed")

    monkeypatch.setattr(simulation_session_service, "_load_floor_plan_data", fake_load_floor_plan_data)

    start_response = client.post(
        f"/api/v3/simulation/sessions/{session_id}/control",
        json={"action": "start"},
        headers=_v3_headers(),
    )
    assert start_response.status_code == 200

    detail = _wait_for(lambda: _get_session_if_status(client, session_id, "error"))
    assert detail is not None
    assert detail["state"]["status"] == "error"
    assert "bootstrap failed" in str(detail["state"].get("latest_error") or "")


def test_simulation_frame_schema_accepts_collapsed_agent_status():
    frame = SimulationFrameSchema(
        timestamp=1.0,
        floor_number=1,
        agents=[
            {
                "agent_id": 15,
                "x": 10.0,
                "y": 0.0,
                "z": 12.0,
                "speed": 0.0,
                "status": "collapsed",
                "panic_level": 0.9,
                "stress_level": 0.95,
                "target_exit": "main-exit",
            }
        ],
        bottlenecks=[],
        hazards=[],
        exit_usage=[],
        exit_evac_counts=[],
        profile_counts=[],
        stats={"total_agents": 1, "evacuated": 0, "remaining": 1},
    )
    assert frame.agents[0].status == "collapsed"


def test_simulation_frame_schema_accepts_large_exit_usage_widths():
    frame = SimulationFrameSchema(
        timestamp=1.0,
        floor_number=1,
        agents=[],
        bottlenecks=[],
        hazards=[],
        exit_usage=[
            {
                "exit_id": "main-exit",
                "x": 960.0,
                "y": 512.0,
                "z": 0.0,
                "width": 1920.0,
                "capacity": 100.0,
                "queue_length": 0,
                "estimated_wait": 0.0,
            }
        ],
        exit_evac_counts=[],
        profile_counts=[],
        stats={"total_agents": 0, "evacuated": 0, "remaining": 0},
    )
    assert frame.exit_usage[0].width == 1920.0


def test_v3_simulation_session_start_stream_analysis_replay_and_reset(client: TestClient):
    settings.RATE_LIMIT_ENABLED = False
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "test-admin-key"
    settings.APP_MODE = "demo"

    session = _create_session(client)
    session_id = session["id"]

    start_response = client.post(
        f"/api/v3/simulation/sessions/{session_id}/control",
        json={"action": "start"},
        headers=_v3_headers(),
    )
    assert start_response.status_code == 200
    started = _unwrap_v3(start_response.json())
    assert started["id"] == session_id
    assert started["state"]["status"] in {"starting", "running", "completed"}

    stream_payload = _wait_for(
        lambda: _unwrap_v3(client.get(f"/api/v3/simulation/sessions/{session_id}/stream").json()),
    )
    assert stream_payload is not None
    assert stream_payload["session_id"] == session_id
    assert stream_payload["websocket_path"] == f"/ws/{session_id}"

    replay_payload = _wait_for(lambda: _get_replay_if_ready(client, session_id))
    assert replay_payload is not None
    assert replay_payload["session_id"] == session_id
    assert replay_payload["count"] >= 1
    assert replay_payload["frames"][0]["simulation_id"] == session_id

    analysis_response = client.get(f"/api/v3/simulation/sessions/{session_id}/analysis")
    assert analysis_response.status_code == 200
    analysis = _unwrap_v3(analysis_response.json())
    assert analysis["session_id"] == session_id
    assert analysis["total_agents"] == 18
    assert "final_summary" in analysis

    pause_response = client.post(
        f"/api/v3/simulation/sessions/{session_id}/control",
        json={"action": "pause"},
        headers=_v3_headers(),
    )
    assert pause_response.status_code == 200

    reset_response = client.post(
        f"/api/v3/simulation/sessions/{session_id}/control",
        json={"action": "reset"},
        headers=_v3_headers(),
    )
    assert reset_response.status_code == 200
    reset = _unwrap_v3(reset_response.json())
    assert reset["state"]["status"] == "draft"
    assert reset["analysis_available"] is False
    assert reset["replay_available"] is False
