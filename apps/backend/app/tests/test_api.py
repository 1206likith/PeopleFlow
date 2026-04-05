import json
import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services import floorplan_store


@pytest.fixture
def client():
    settings.RATE_LIMIT_ENABLED = False
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "test-admin-key"
    settings.APP_MODE = "demo"
    # Use explicit transport to avoid httpx deprecation warnings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides = {}


def _create_floor_plan(client: TestClient) -> str:
    payload = {
        "buildingName": "Test Building",
        "floors": [
            {"floorNumber": 1, "name": "Floor 1", "exits": []},
            {"floorNumber": 2, "name": "Floor 2", "exits": []},
        ],
    }
    response = client.post("/api/simulation/upload", json=payload)
    assert response.status_code == 200
    return response.json()["id"]


def _unwrap_v2(payload: dict) -> dict:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _assert_v2_error_status(body: dict, expected_status: int) -> None:
    assert body.get("error", {}).get("status_code") == expected_status


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
    }


def test_floor_plan_metadata_filters_by_floor(client: TestClient):
    plan_id = _create_floor_plan(client)

    exit_payload_floor1 = {
        "exits": [
            {"id": "exit_f1", "x": 10.0, "y": 0.0, "z": 12.0, "width": 2.5, "capacity": 100}
        ],
        "merge": True,
        "snap_to_boundary": False,
    }
    exit_payload_floor2 = {
        "exits": [
            {"id": "exit_f2", "x": 15.0, "y": 0.0, "z": 18.0, "width": 2.0, "capacity": 80}
        ],
        "merge": True,
        "snap_to_boundary": False,
    }

    resp1 = client.post(f"/api/simulation/floor-plans/{plan_id}/exits?floor_number=1", json=exit_payload_floor1)
    assert resp1.status_code == 200
    resp2 = client.post(f"/api/simulation/floor-plans/{plan_id}/exits?floor_number=2", json=exit_payload_floor2)
    assert resp2.status_code == 200

    meta = client.get(f"/api/simulation/floor-plans/{plan_id}?floor_number=1")
    assert meta.status_code == 200
    data = meta.json()

    assert data["building_name"] == "Test Building"
    assert isinstance(data["boundaries"], list)
    assert data["detected_exits"] == []
    assert len(data["manual_exits"]) == 1
    assert data["manual_exits"][0]["id"] == "exit_f1"
    assert len(data["exits"]) == 1
    assert data["exits"][0]["id"] == "exit_f1"


def test_manual_exit_delete(client: TestClient):
    plan_id = _create_floor_plan(client)
    exit_payload = {
        "exits": [
            {"id": "exit_delete", "x": 8.0, "y": 0.0, "z": 9.0, "width": 2.0, "capacity": 60}
        ],
        "merge": True,
        "snap_to_boundary": False,
    }
    add_resp = client.post(f"/api/simulation/floor-plans/{plan_id}/exits?floor_number=1", json=exit_payload)
    assert add_resp.status_code == 200

    delete_resp = client.delete(f"/api/simulation/floor-plans/{plan_id}/exits/exit_delete")
    assert delete_resp.status_code == 200

    meta = client.get(f"/api/simulation/floor-plans/{plan_id}?floor_number=1")
    assert meta.status_code == 200
    data = meta.json()
    assert all(exit_item["id"] != "exit_delete" for exit_item in data["manual_exits"])


def test_detected_exit_delete_hides_exit_from_metadata_and_loader(client: TestClient):
    plan_id = "mock-detected-delete"
    floorplan_store.save_floor_plan(
        plan_id,
        {
            "id": plan_id,
            "building_name": "Detected Delete Plan",
            "detected_walls": [],
            "detected_exits": [
                {"id": "detected-a", "name": "Detected A", "x": 10.0, "y": 0.0, "z": 15.0, "width": 2.0, "capacity": 90}
            ],
            "manual_exits": [],
            "removed_detected_exit_ids": [],
            "detected_obstacles": [],
            "boundaries": [],
            "building_bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100, "width": 100, "height": 100},
            "processing_metadata": {"processed": True, "pipeline": "semantic"},
            "revision": 1,
        },
    )

    delete_resp = client.delete(
        f"/api/v2/simulations/floor-plans/{plan_id}/exits/detected-a",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert delete_resp.status_code == 200
    delete_data = _unwrap_v2(delete_resp.json())
    assert "detected-a" in delete_data["removed_detected_exit_ids"]

    exits_resp = client.get(f"/api/v2/simulations/floor-plans/{plan_id}/exits")
    assert exits_resp.status_code == 200
    exits_data = _unwrap_v2(exits_resp.json())
    assert all(exit_item["id"] != "detected-a" for exit_item in exits_data["detected_exits"])
    assert all(exit_item["id"] != "detected-a" for exit_item in exits_data["exits"])

    meta_resp = client.get(f"/api/v2/simulations/floor-plans/{plan_id}")
    assert meta_resp.status_code == 200
    meta_data = _unwrap_v2(meta_resp.json())
    assert all(exit_item["id"] != "detected-a" for exit_item in meta_data["detected_exits"])
    assert all(exit_item["id"] != "detected-a" for exit_item in meta_data["exits"])


def test_v2_floor_plan_quality_report_and_annotations_round_trip(client: TestClient):
    plan_id = _create_floor_plan(client)

    quality_resp = client.get(f"/api/v2/simulations/floor-plans/{plan_id}/quality-report")
    assert quality_resp.status_code == 200
    quality_data = _unwrap_v2(quality_resp.json())
    assert quality_data["floor_plan_id"] == plan_id
    assert "quality_report" in quality_data

    save_resp = client.post(
        f"/api/v2/simulations/floor-plans/{plan_id}/annotations",
        json={
            "status": "in_review",
            "walls": [{"x1": 0, "y1": 0, "x2": 10, "y2": 0}],
            "doors": [{"x": 5, "y": 0, "width": 2}],
            "exits": [{"x": 0, "y": 5, "width": 2}],
            "rooms": [{"name": "Room A", "polygon": [{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}]}],
            "notes": "reviewing fixture",
        },
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert save_resp.status_code == 200
    save_data = _unwrap_v2(save_resp.json())
    assert save_data["annotations"]["status"] == "in_review"

    get_resp = client.get(f"/api/v2/simulations/floor-plans/{plan_id}/annotations")
    assert get_resp.status_code == 200
    get_data = _unwrap_v2(get_resp.json())
    assert get_data["status"] == "in_review"
    assert len(get_data["walls"]) == 1


def test_v2_floorplan_train_job_force_path(client: TestClient):
    insufficient = client.post(
        "/api/v2/models/floorplan/train",
        json={"min_batch_size": 5, "force": False},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert insufficient.status_code == 422

    forced = client.post(
        "/api/v2/models/floorplan/train",
        json={"min_batch_size": 5, "force": True},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert forced.status_code == 200
    forced_data = _unwrap_v2(forced.json())
    assert forced_data["status"] in {"completed", "failed"}
    assert forced_data["job_id"].startswith("fptrain-")

    status_resp = client.get(f"/api/v2/models/floorplan/train/{forced_data['job_id']}")
    assert status_resp.status_code == 200
    status_data = _unwrap_v2(status_resp.json())
    assert status_data["job_id"] == forced_data["job_id"]


def test_v2_mock_floor_plan_fallback_after_store_reset(client: TestClient):
    plan_id = _create_floor_plan(client)
    assert plan_id.startswith("mock-")

    floorplan_store._FLOOR_PLAN_STORE.clear()

    meta_resp = client.get(f"/api/v2/simulations/floor-plans/{plan_id}")
    assert meta_resp.status_code == 200
    meta_data = _unwrap_v2(meta_resp.json())
    assert meta_data["id"] == plan_id

    exits_resp = client.get(f"/api/v2/simulations/floor-plans/{plan_id}/exits")
    assert exits_resp.status_code == 200
    exits_data = _unwrap_v2(exits_resp.json())
    assert exits_data["floor_plan_id"] == plan_id

    update_payload = {
        "exits": [
            {"id": "fallback_exit", "x": 10.0, "y": 0.0, "z": 10.0, "width": 2.0, "capacity": 50}
        ],
        "merge": True,
        "snap_to_boundary": False,
    }
    add_resp = client.post(
        f"/api/v2/simulations/floor-plans/{plan_id}/exits",
        json=update_payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert add_resp.status_code == 200
    add_data = _unwrap_v2(add_resp.json())
    assert any(exit_item["id"] == "fallback_exit" for exit_item in add_data["manual_exits"])


def test_v2_mock_simulation_endpoints_return_synthetic_data(client: TestClient):
    simulation_id = "mock-synthetic-check"

    latest_resp = client.get(f"/api/v2/simulations/{simulation_id}/frames/latest")
    assert latest_resp.status_code == 200
    latest_data = _unwrap_v2(latest_resp.json())
    assert latest_data["simulation_id"] == simulation_id
    assert isinstance(latest_data.get("agents"), list)
    assert isinstance(latest_data.get("stats"), dict)

    summary_resp = client.get(f"/api/v2/simulations/{simulation_id}/summary")
    assert summary_resp.status_code == 200
    summary_data = _unwrap_v2(summary_resp.json())
    assert summary_data["simulation_id"] == simulation_id
    assert "final_stats" in summary_data

    metrics_resp = client.get(f"/api/v2/simulations/{simulation_id}/metrics")
    assert metrics_resp.status_code == 200
    metrics_data = _unwrap_v2(metrics_resp.json())
    assert metrics_data["simulation_id"] == simulation_id
    assert "metrics" in metrics_data

    timeline_resp = client.get(f"/api/v2/simulations/{simulation_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline_data = _unwrap_v2(timeline_resp.json())
    assert isinstance(timeline_data.get("points"), list)
    assert timeline_data.get("count", 0) >= 1


def test_v2_validation_endpoint_returns_summary_and_checks(client: TestClient):
    response = client.post(
        "/api/v2/validation/validate/mock-validation-endpoint",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert response.status_code == 200
    data = _unwrap_v2(response.json())
    assert data["summary"]["schema_version"] == "peopleflow-validation-summary-v1"
    assert data["summary"]["source"] == "runtime_validation"
    assert isinstance(data["checks"], dict)
    assert data["provenance"]["simulation_id"] == "mock-validation-endpoint"


def test_v2_validation_benchmarks_endpoint_returns_canonical_catalog(client: TestClient):
    response = client.get("/api/v2/validation/benchmarks")
    assert response.status_code == 200
    data = _unwrap_v2(response.json())
    assert data["catalog_version"] == "peopleflow-validation-benchmarks-v1"
    assert [benchmark["name"] for benchmark in data["benchmarks"]] == [
        "corridor_flow_rate",
        "density_speed_curve",
        "pre_evacuation_delay",
    ]
    assert any(benchmark["id"] == "corridor_flow_rate" for benchmark in data["runtime_benchmarks"])
    assert any(benchmark["id"] == "standard_corridor" for benchmark in data["suite_benchmarks"])
    assert data["targets"]["fundamental"]["rmse_tolerance"] == pytest.approx(0.5)


def test_v2_start_simulation_uses_client_floor_plan_snapshot(client: TestClient):
    payload = {
        "floor_plan_id": "mock-client-snapshot",
        "num_agents": 12,
        "panic_level": 0.35,
        "emergency_type": "fire",
        "floor_plan_snapshot": {
            "pipeline": "client-snapshot",
            "building_bounds": {"min_x": 10, "min_y": 20, "max_x": 210, "max_y": 220, "width": 200, "height": 200},
            "detected_walls": [
                {"x1": 10, "y1": 20, "x2": 210, "y2": 20, "length": 200, "type": "boundary"},
                {"x1": 10, "y1": 220, "x2": 210, "y2": 220, "length": 200, "type": "boundary"},
                {"x1": 10, "y1": 20, "x2": 10, "y2": 220, "length": 200, "type": "boundary"},
                {"x1": 210, "y1": 20, "x2": 210, "y2": 220, "length": 200, "type": "boundary"},
            ],
            "boundaries": [
                {"x1": 10, "y1": 20, "x2": 210, "y2": 20, "length": 200, "type": "boundary"},
                {"x1": 210, "y1": 20, "x2": 210, "y2": 220, "length": 200, "type": "boundary"},
                {"x1": 210, "y1": 220, "x2": 10, "y2": 220, "length": 200, "type": "boundary"},
                {"x1": 10, "y1": 220, "x2": 10, "y2": 20, "length": 200, "type": "boundary"},
            ],
            "exits": [
                {"id": "snapshot-main", "name": "Snapshot Main Exit", "x": 110, "y": 20, "z": 20, "width": 4, "capacity": 180},
            ],
        },
    }
    start_resp = client.post(
        "/api/v2/simulations/start",
        json=payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert start_resp.status_code == 200
    simulation_id = _unwrap_v2(start_resp.json())["id"]

    latest_resp = client.get(f"/api/v2/simulations/{simulation_id}/frames/latest")
    assert latest_resp.status_code == 200
    latest_data = _unwrap_v2(latest_resp.json())
    assert latest_data["simulation_id"] == simulation_id
    assert any(exit_item.get("id") == "snapshot-main" for exit_item in latest_data.get("exits", []))
    assert len(latest_data.get("walls", [])) >= 4


def test_v2_mock_frame_endpoints_prefer_ingested_frames(client: TestClient):
    simulation_id = "mock-ingested-frames"
    frame_payload = {
        "timestamp": 12.5,
        "floor_number": 1,
        "agents": [
            {
                "agent_id": 1,
                "x": 22.0,
                "y": 14.0,
                "z": 14.0,
                "speed": 1.3,
                "status": "moving",
                "panic_level": 0.25,
            }
        ],
        "bottlenecks": [],
        "hazards": [],
        "exit_usage": [],
        "exit_evac_counts": [{"exit_id": "manual-exit", "count": 1}],
        "profile_counts": [{"profile_id": "staff", "count": 1}],
        "stats": {
            "total_agents": 1,
            "evacuated": 0,
            "remaining": 1,
            "completion_percentage": 0.0,
            "total_time": 12.5,
        },
        "walls": [{"x1": 0, "y1": 0, "x2": 10, "y2": 0, "length": 10, "type": "boundary"}],
        "exits": [{"id": "manual-exit", "x": 10, "y": 10, "z": 10, "width": 2, "capacity": 50}],
    }

    save_resp = client.post(
        f"/api/v2/results/{simulation_id}/frame",
        json=frame_payload,
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert save_resp.status_code == 200

    latest_resp = client.get(f"/api/v2/simulations/{simulation_id}/frames/latest")
    assert latest_resp.status_code == 200
    latest_data = _unwrap_v2(latest_resp.json())
    assert latest_data["timestamp"] == pytest.approx(12.5)
    assert latest_data["agents"][0]["z"] == pytest.approx(14.0)
    assert latest_data["exits"][0]["id"] == "manual-exit"

    frames_resp = client.get(f"/api/v2/simulations/{simulation_id}/frames?limit=10")
    assert frames_resp.status_code == 200
    frames_data = _unwrap_v2(frames_resp.json())
    assert frames_data["count"] >= 1
    assert frames_data["frames"][0]["timestamp"] == pytest.approx(12.5)

    legacy_summary_resp = client.get(f"/api/v2/results/{simulation_id}/summary")
    assert legacy_summary_resp.status_code == 200
    legacy_summary = _unwrap_v2(legacy_summary_resp.json())
    assert legacy_summary["simulation_id"] == simulation_id
    assert legacy_summary["frames_count"] >= 1
    assert legacy_summary["total_time"] == pytest.approx(12.5)


def test_batch_persistence(client: TestClient):
    payload = {
        "config": {
            "num_agents": 5,
            "emergency_type": "fire",
            "panic_level": 0.2,
        },
        "runs": 2,
        "realtime": False,
        "max_iterations": 5,
        "seed_start": 10,
    }
    resp = client.post("/api/simulation/start-batch", json=payload)
    assert resp.status_code == 200
    batch_payload = resp.json()
    batch_id = batch_payload["batch_id"]
    assert batch_payload["record_version"] == "peopleflow-batch-run-v1"
    assert batch_payload["provenance"]["batch_id"] == batch_id
    assert batch_payload["provenance"]["config_hash"]
    assert batch_payload["validation"]["summary"]["source"] == "batch_execution"
    assert isinstance(batch_payload["run_manifest"], list)
    assert len(batch_payload["run_manifest"]) == 2

    get_resp = client.get(f"/api/simulation/batches/{batch_id}")
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["batch_id"] == batch_id
    assert fetched["validation"]["summary"]["source"] == "batch_execution"

    list_resp = client.get("/api/simulation/batches")
    assert list_resp.status_code == 200
    batches = list_resp.json().get("batches", [])
    assert any(b.get("batch_id") == batch_id for b in batches)


def test_start_scenario_launches_multiple_runs(client: TestClient):
    payload = {
        "name": "Demo Scenario",
        "base_config": {
            "num_agents": 4,
            "panic_level": 0.3,
            "emergency_type": "fire",
            "floor_plan_snapshot": _minimal_floor_plan_snapshot(),
        },
        "runs": [
            {"floor_plan_id": "mock-default-floor-plan", "floor_number": 1, "seed": 11},
            {"floor_plan_id": "mock-default-floor-plan", "floor_number": 2, "seed": 12},
        ],
    }
    resp = client.post("/api/simulation/start-scenario", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["scenario_id"].startswith("scenario-")
    assert body["runs"] == 2
    assert len(body["simulations"]) == 2
    assert body["simulations"][0]["simulation_id"]
    assert body["simulations"][1]["simulation_id"]


def test_start_simulation_idempotency(client: TestClient):
    payload = {
        "num_agents": 5,
        "panic_level": 0.2,
        "floor_plan_snapshot": _minimal_floor_plan_snapshot(),
    }
    headers = {"Idempotency-Key": "test-idempotency-key"}
    resp1 = client.post("/api/simulation/start", json=payload, headers=headers)
    assert resp1.status_code == 200
    resp2 = client.post("/api/simulation/start", json=payload, headers=headers)
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]


def test_auth_routes_removed(client: TestClient):
    assert client.post("/api/auth/demo-login").status_code == 404
    assert client.post("/api/auth/token").status_code == 404
    assert client.post("/api/auth/register").status_code == 404


def test_v2_get_without_auth(client: TestClient):
    response = client.get("/api/v2/system/info")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["version"] == "v2"
    assert body["meta"]["mode"] == "demo"
    assert "data" in body


def test_v2_mutation_requires_admin_key(client: TestClient):
    payload = {
        "num_agents": 5,
        "panic_level": 0.2,
        "floor_plan_snapshot": _minimal_floor_plan_snapshot(),
    }
    response = client.post("/api/v2/simulations/start", json=payload)
    assert response.status_code == 401
    missing = response.json()
    assert missing["meta"]["version"] == "v2"
    assert missing["error"]["code"] == "admin_key_missing"
    assert missing["error"]["status_code"] == 401
    assert missing["meta"]["correlation_id"]

    bad = client.post("/api/v2/simulations/start", json=payload, headers={"X-Admin-Key": "wrong"})
    assert bad.status_code == 403
    bad_body = bad.json()
    assert bad_body["error"]["code"] == "admin_key_invalid"
    assert bad_body["error"]["status_code"] == 403

    good = client.post("/api/v2/simulations/start", json=payload, headers={"X-Admin-Key": "test-admin-key"})
    assert good.status_code == 200


def test_v2_start_simulation_rejects_missing_geometry(client: TestClient):
    response = client.post(
        "/api/v2/simulations/start",
        json={"num_agents": 15, "panic_level": 0.3, "emergency_type": "fire"},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body.get("error", {}).get("status_code") == 422
    detail = body.get("error", {}).get("details", {})
    assert detail.get("code") == "floor_plan_geometry_invalid"


def test_v2_mode_flag_changes_with_app_mode(client: TestClient):
    settings.APP_MODE = "production"
    response = client.get("/api/v2/system/info")
    assert response.status_code == 200
    assert response.json()["meta"]["mode"] == "production"
    settings.APP_MODE = "demo"


def test_v2_openapi_location(client: TestClient):
    assert client.get("/api/v2/openapi.json").status_code == 200
    assert client.get("/openapi.json").status_code == 404


def test_production_mode_rejects_demo_fallback_paths(client: TestClient):
    old_mode = settings.APP_MODE
    settings.APP_MODE = "production"
    try:
        stop_resp = client.post(
            "/api/v2/simulations/not-an-object-id/stop",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert stop_resp.status_code == 503
        _assert_v2_error_status(stop_resp.json(), 503)

        report_resp = client.get("/api/v2/reports/demo-1/pdf")
        assert report_resp.status_code == 404
        _assert_v2_error_status(report_resp.json(), 404)

        heatmap_resp = client.get("/api/v2/reports/demo-1/heatmap")
        assert heatmap_resp.status_code == 404
        _assert_v2_error_status(heatmap_resp.json(), 404)

        summary_resp = client.get("/api/v2/results/demo-1/summary")
        assert summary_resp.status_code == 404
        _assert_v2_error_status(summary_resp.json(), 404)
    finally:
        settings.APP_MODE = old_mode


def test_v2_report_generation_mock_mode_returns_pdf(client: TestClient):
    response = client.get("/api/v2/reports/mock-report-fixture/pdf")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/pdf")
    assert len(response.content) > 100


def test_v2_report_heatmap_mock_mode_returns_points(client: TestClient):
    response = client.get("/api/v2/reports/mock-report-fixture/heatmap")
    assert response.status_code == 200
    data = _unwrap_v2(response.json())
    assert data["simulation_id"] == "mock-report-fixture"
    assert data["total_points"] == len(data["heatmap_data"])
    assert data["total_points"] > 0
    assert data["report_summary"]["artifact_type"] == "heatmap"
    assert data["provenance"]["simulation_id"] == "mock-report-fixture"
    assert data["validation"]["summary"]["source"] == "report_generation"


def test_v2_report_artifacts_catalog_returns_index(client: TestClient):
    client.get("/api/v2/reports/mock-report-fixture/pdf")
    client.get("/api/v2/reports/mock-report-fixture/heatmap")

    response = client.get("/api/v2/reports/mock-report-fixture/artifacts")
    assert response.status_code == 200
    data = _unwrap_v2(response.json())
    assert data["catalog_version"] == "peopleflow-report-index-v1"
    assert data["simulation_id"] == "mock-report-fixture"
    assert data["artifact_count"] >= 2
    assert any(artifact["artifact_type"] == "pdf" for artifact in data["artifacts"])
    assert any(artifact["artifact_type"] == "heatmap" for artifact in data["artifacts"])


def test_v2_experiment_artifact_catalog_returns_indexes_and_bundles(client: TestClient, tmp_path, monkeypatch):
    from app.services.experiment_artifact_service import experiment_artifact_service

    output_dir = tmp_path / "research-output"
    artifact_dir = tmp_path / "artifact-output"
    paper_results_dir = tmp_path / "paper-results"

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (paper_results_dir / "paper_suite_20260403T000000Z" / "metadata").mkdir(parents=True, exist_ok=True)

    run_record = {
        "record_version": "peopleflow-experiment-run-v1",
        "config": {
            "name": "baseline-run",
            "seed": 42,
            "num_agents": 50,
            "emergency_type": "fire",
        },
        "config_hash": "hash-baseline-run",
        "metrics": {
            "total_evacuation_time": 88.0,
            "average_evacuation_time": 44.0,
        },
        "metadata": {"generated_at": "2026-04-03T00:00:00Z"},
        "provenance": {
            "generated_at": "2026-04-03T00:00:00Z",
            "seed": 42,
            "engine_version": "peopleflow-sim-v1",
        },
    }
    suite_manifest = {
        "summary_version": "peopleflow-experiment-suite-v1",
        "suite_type": "ablation",
        "generated_at": "2026-04-03T00:00:00Z",
        "run_count": 1,
        "source_config_path": "research/experiments/ablation.json",
        "output_path": str(output_dir / "ablation_summary.json"),
        "provenance": {"suite_type": "ablation"},
        "results": [],
        "metadata": {"trials": 1},
    }
    research_artifact = {
        "record_version": "peopleflow-research-artifact-v1",
        "artifact_id": "benchmark:corridor",
        "artifact_kind": "benchmark",
        "artifact_type": "json",
        "generated_at": "2026-04-03T00:00:00Z",
        "output_path": str(output_dir / "benchmark_corridor.json"),
        "metadata": {"benchmark_name": "corridor"},
        "provenance": {"generated_at": "2026-04-03T00:00:00Z"},
    }
    publication_manifest = {
        "manifest_version": "peopleflow-publication-bundle-v1",
        "run_record_version": "peopleflow-experiment-run-v1",
        "layout_version": "1.0",
        "suite_name": "paper_suite",
        "generated_at": "2026-04-03T00:00:00Z",
        "run_count": 2,
        "validation_enabled": True,
        "copy_run_outputs": True,
        "copied_run_count": 2,
        "missing_run_outputs": [],
        "seeds": [11, 12],
        "variants": ["baseline"],
        "paths": {"manifests_dir": str(paper_results_dir / "paper_suite_20260403T000000Z" / "manifests")},
        "runs": [],
    }

    (output_dir / "baseline-run.json").write_text(json.dumps(run_record), encoding="utf-8")
    (output_dir / "ablation_summary.json").write_text(json.dumps(suite_manifest), encoding="utf-8")
    (output_dir / "benchmark_corridor.manifest.json").write_text(json.dumps(research_artifact), encoding="utf-8")
    (
        paper_results_dir / "paper_suite_20260403T000000Z" / "metadata" / "publication_manifest.json"
    ).write_text(json.dumps(publication_manifest), encoding="utf-8")

    monkeypatch.setattr(experiment_artifact_service, "output_dir", output_dir)
    monkeypatch.setattr(experiment_artifact_service, "artifact_dir", artifact_dir)
    monkeypatch.setattr(experiment_artifact_service, "paper_results_dir", paper_results_dir)

    response = client.get("/api/v2/experiments/artifacts")
    assert response.status_code == 200
    data = _unwrap_v2(response.json())
    assert data["catalog_version"] == "peopleflow-experiment-artifact-catalog-v1"
    assert data["experiments_output"]["run_index"]["result_count"] == 1
    assert data["experiments_output"]["metrics_export"]["row_count"] == 1
    assert data["experiments_output"]["artifact_index"]["artifact_count"] == 1
    assert data["experiments_output"]["suite_manifests"][0]["suite_type"] == "ablation"
    assert data["publication_bundles"]["artifact_count"] == 1
    assert data["publication_bundles"]["artifacts"][0]["artifact_kind"] == "publication_bundle"


def test_v2_publication_bundle_detail_returns_manifest_and_record(client: TestClient, tmp_path, monkeypatch):
    from app.services.experiment_artifact_service import experiment_artifact_service

    paper_results_dir = tmp_path / "paper-results"
    bundle_id = "paper_suite_20260403T000000Z"
    manifest_dir = paper_results_dir / bundle_id / "metadata"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    publication_manifest = {
        "manifest_version": "peopleflow-publication-bundle-v1",
        "run_record_version": "peopleflow-experiment-run-v1",
        "layout_version": "1.0",
        "suite_name": "paper_suite",
        "generated_at": "2026-04-03T00:00:00Z",
        "run_count": 2,
        "validation_enabled": True,
        "copy_run_outputs": True,
        "copied_run_count": 2,
        "missing_run_outputs": [],
        "seeds": [11, 12],
        "variants": ["baseline"],
        "paths": {"metadata_dir": str(manifest_dir)},
        "runs": [],
    }
    (manifest_dir / "publication_manifest.json").write_text(json.dumps(publication_manifest), encoding="utf-8")

    monkeypatch.setattr(experiment_artifact_service, "paper_results_dir", paper_results_dir)

    response = client.get(f"/api/v2/experiments/publication-bundles/{bundle_id}")
    assert response.status_code == 200
    data = _unwrap_v2(response.json())
    assert data["bundle_id"] == bundle_id
    assert data["record"]["artifact_kind"] == "publication_bundle"
    assert data["record"]["metadata"]["suite_name"] == "paper_suite"
    assert data["manifest"]["manifest_version"] == "peopleflow-publication-bundle-v1"
    assert data["download_path"].endswith(f"/api/v2/experiments/publication-bundles/{bundle_id}/download")

    download_response = client.get(f"/api/v2/experiments/publication-bundles/{bundle_id}/download")
    assert download_response.status_code == 200
    assert download_response.content == (manifest_dir / "publication_manifest.json").read_bytes()


def test_v2_experiment_artifact_record_routes_support_summary_detail_and_download(client: TestClient, tmp_path, monkeypatch):
    from app.services.experiment_artifact_service import experiment_artifact_service

    output_dir = tmp_path / "output"
    artifact_dir = tmp_path / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    artifact_payload = {
        "name": "benchmark-corridor",
        "metrics": {"total_evacuation_time": 44.0},
    }
    artifact_file = output_dir / "benchmark_corridor.json"
    artifact_file.write_text(json.dumps(artifact_payload), encoding="utf-8")

    research_artifact = {
        "record_version": "peopleflow-research-artifact-v1",
        "artifact_id": "benchmark:corridor",
        "artifact_kind": "benchmark",
        "artifact_type": "json",
        "generated_at": "2026-04-03T00:00:00Z",
        "output_path": str(artifact_file),
        "metadata": {
            "benchmark_name": "corridor",
            "metrics_summary": {"total_evacuation_time": 44.0, "peak_density": 1.8},
        },
        "provenance": {"generated_at": "2026-04-03T00:00:00Z", "benchmark_name": "corridor"},
    }
    manifest_file = output_dir / "benchmark_corridor.manifest.json"
    manifest_file.write_text(json.dumps(research_artifact), encoding="utf-8")

    monkeypatch.setattr(experiment_artifact_service, "output_dir", output_dir)
    monkeypatch.setattr(experiment_artifact_service, "artifact_dir", artifact_dir)

    list_response = client.get("/api/v2/experiments/artifacts/records")
    assert list_response.status_code == 200
    list_data = _unwrap_v2(list_response.json())
    assert list_data["artifact_count"] == 1
    assert list_data["artifacts"][0]["artifact_id"] == "benchmark:corridor"
    assert list_data["artifacts"][0]["metadata"]["benchmark_name"] == "corridor"
    assert "metrics_summary" not in list_data["artifacts"][0]["metadata"]

    detail_response = client.get("/api/v2/experiments/artifacts/records/benchmark:corridor")
    assert detail_response.status_code == 200
    detail_data = _unwrap_v2(detail_response.json())
    assert detail_data["artifact_id"] == "benchmark:corridor"
    assert detail_data["record"]["metadata"]["metrics_summary"]["peak_density"] == 1.8

    download_response = client.get("/api/v2/experiments/artifacts/records/benchmark:corridor/download?kind=artifact")
    assert download_response.status_code == 200
    assert download_response.content == artifact_file.read_bytes()

    manifest_response = client.get("/api/v2/experiments/artifacts/records/benchmark:corridor/download?kind=manifest")
    assert manifest_response.status_code == 200
    assert manifest_response.content == manifest_file.read_bytes()


def test_v2_experiment_execution_endpoints_delegate_to_service(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_execution_service.run_experiment",
        lambda config, validate=False: {
            "execution_type": "single_run",
            "result": {"config": config.model_dump(), "validation_enabled": validate},
        },
    )
    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_execution_service.run_ablation",
        lambda base_config, validate=False: {
            "execution_type": "ablation",
            "summary": {"suite_type": "ablation", "base_name": base_config.name, "validation_enabled": validate},
        },
    )
    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_execution_service.run_calibration",
        lambda base_config, calibration_config=None, calibration_config_path=None: {
            "execution_type": "calibration",
            "summary": {
                "suite_type": "calibration",
                "base_name": base_config.name,
                "has_inline_config": calibration_config is not None,
                "config_path": calibration_config_path,
            },
        },
    )
    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_execution_service.run_optimization",
        lambda base_config, optimization_config=None, optimization_config_path=None: {
            "execution_type": "optimization",
            "summary": {
                "suite_type": "optimization",
                "base_name": base_config.name,
                "has_inline_config": optimization_config is not None,
                "config_path": optimization_config_path,
            },
        },
    )
    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_execution_service.run_publication_bundle",
        lambda batch_config=None, batch_config_path=None, validate=True, artifacts_root=None, copy_run_outputs=True: {
            "execution_type": "publication_bundle",
            "bundle": {
                "has_inline_config": batch_config is not None,
                "batch_config_path": batch_config_path,
                "validate": validate,
                "artifacts_root": artifacts_root,
                "copy_run_outputs": copy_run_outputs,
            },
        },
    )
    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_execution_service.run_benchmark",
        lambda benchmark_name, num_agents=None: {
            "execution_type": "benchmark",
            "benchmark": benchmark_name,
            "num_agents": num_agents,
        },
    )

    run_resp = client.post(
        "/api/v2/experiments/runs",
        json={"config": {"name": "api-run", "num_agents": 20}, "validate": True},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert run_resp.status_code == 200
    run_data = _unwrap_v2(run_resp.json())
    assert run_data["execution_type"] == "single_run"
    assert run_data["result"]["config"]["name"] == "api-run"
    assert run_data["result"]["validation_enabled"] is True

    ablation_resp = client.post(
        "/api/v2/experiments/ablations",
        json={"base_config": {"name": "api-abl", "num_agents": 10}, "validate": True},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert ablation_resp.status_code == 200
    ablation_data = _unwrap_v2(ablation_resp.json())
    assert ablation_data["summary"]["suite_type"] == "ablation"
    assert ablation_data["summary"]["validation_enabled"] is True

    calibration_resp = client.post(
        "/api/v2/experiments/calibrations",
        json={
            "base_config": {"name": "api-calib", "num_agents": 10},
            "calibration_config": {"trials": 2},
        },
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert calibration_resp.status_code == 200
    calibration_data = _unwrap_v2(calibration_resp.json())
    assert calibration_data["summary"]["suite_type"] == "calibration"
    assert calibration_data["summary"]["has_inline_config"] is True

    optimization_resp = client.post(
        "/api/v2/experiments/optimizations",
        json={
            "base_config": {"name": "api-opt", "num_agents": 10},
            "optimization_config_path": "research/experiments/optimization.json",
        },
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert optimization_resp.status_code == 200
    optimization_data = _unwrap_v2(optimization_resp.json())
    assert optimization_data["summary"]["suite_type"] == "optimization"
    assert optimization_data["summary"]["config_path"] == "research/experiments/optimization.json"

    bundle_resp = client.post(
        "/api/v2/experiments/publication-bundles",
        json={
            "batch_config": {
                "name": "paper-suite",
                "base_config": "research/experiments/baseline.json",
                "seeds": [11],
                "variants": [{"id": "baseline", "overrides": {}}],
            },
            "validate": False,
            "copy_run_outputs": False,
        },
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert bundle_resp.status_code == 200
    bundle_data = _unwrap_v2(bundle_resp.json())
    assert bundle_data["bundle"]["has_inline_config"] is True
    assert bundle_data["bundle"]["validate"] is False
    assert bundle_data["bundle"]["copy_run_outputs"] is False

    benchmark_resp = client.post(
        "/api/v2/experiments/benchmarks/corridor/run",
        json={"num_agents": 144},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert benchmark_resp.status_code == 200
    benchmark_data = _unwrap_v2(benchmark_resp.json())
    assert benchmark_data["execution_type"] == "benchmark"
    assert benchmark_data["benchmark"] == "corridor"
    assert benchmark_data["num_agents"] == 144


def test_v2_experiment_execution_background_job_endpoints(client: TestClient, monkeypatch):
    submitted_jobs = []

    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_job_service.submit_job",
        lambda **kwargs: submitted_jobs.append(kwargs) or {
            "job_schema_version": "peopleflow-experiment-job-v1",
            "job_id": "expjob-queued",
            "execution_type": kwargs["execution_type"],
            "status": "queued",
            "background": True,
            "requested_by": kwargs["requested_by"],
            "input_summary": kwargs["input_summary"],
            "submitted_at": "2026-04-03T00:00:00Z",
            "updated_at": "2026-04-03T00:00:00Z",
            "started_at": None,
            "completed_at": None,
            "result_summary": None,
            "error": None,
        },
    )
    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_job_service.list_jobs",
        lambda limit=12, status=None: {
            "job_schema_version": "peopleflow-experiment-job-v1",
            "job_count": 1,
            "active_count": 1,
            "jobs": [
                {
                    "job_schema_version": "peopleflow-experiment-job-v1",
                    "job_id": "expjob-queued",
                    "execution_type": "benchmark",
                    "status": status or "running",
                    "background": True,
                    "requested_by": "demo_user",
                    "input_summary": {"benchmark": "corridor", "num_agents": 60},
                    "submitted_at": "2026-04-03T00:00:00Z",
                    "updated_at": "2026-04-03T00:00:02Z",
                    "started_at": "2026-04-03T00:00:01Z",
                    "completed_at": None,
                    "result_summary": None,
                    "error": None,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.api.routes.experiment_execution.experiment_job_service.get_job",
        lambda job_id: {
            "job_schema_version": "peopleflow-experiment-job-v1",
            "job_id": job_id,
            "execution_type": "benchmark",
            "status": "completed",
            "background": True,
            "requested_by": "demo_user",
            "input_summary": {"benchmark": "corridor", "num_agents": 60},
            "submitted_at": "2026-04-03T00:00:00Z",
            "updated_at": "2026-04-03T00:00:05Z",
            "started_at": "2026-04-03T00:00:01Z",
            "completed_at": "2026-04-03T00:00:05Z",
            "result_summary": {"title": "Benchmark corridor", "detail": "done"},
            "result": {"execution_type": "benchmark", "benchmark": "corridor", "description": "done"},
            "error": None,
        },
    )

    submit_resp = client.post(
        "/api/v2/experiments/benchmarks/corridor/run",
        json={"background": True},
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert submit_resp.status_code == 202
    submit_data = _unwrap_v2(submit_resp.json())
    assert submit_data["job_id"] == "expjob-queued"
    assert submit_data["execution_type"] == "benchmark"
    assert submit_data["status"] == "queued"
    assert submitted_jobs[0]["execution_type"] == "benchmark"
    assert submitted_jobs[0]["input_summary"]["benchmark"] == "corridor"

    list_resp = client.get("/api/v2/experiments/jobs?limit=5&status=running")
    assert list_resp.status_code == 200
    list_data = _unwrap_v2(list_resp.json())
    assert list_data["job_count"] == 1
    assert list_data["jobs"][0]["job_id"] == "expjob-queued"
    assert list_data["jobs"][0]["status"] == "running"

    detail_resp = client.get("/api/v2/experiments/jobs/expjob-queued")
    assert detail_resp.status_code == 200
    detail_data = _unwrap_v2(detail_resp.json())
    assert detail_data["job_id"] == "expjob-queued"
    assert detail_data["status"] == "completed"
    assert detail_data["result"]["benchmark"] == "corridor"


def test_v2_experiment_benchmarks_listing_returns_catalog(client: TestClient):
    response = client.get("/api/v2/experiments/benchmarks")
    assert response.status_code == 200
    data = _unwrap_v2(response.json())
    assert data["catalog_version"] == "peopleflow-executable-benchmarks-v1"
    assert any(benchmark["name"] == "corridor" for benchmark in data["benchmarks"])
    assert any(benchmark["name"] == "multi_exit" for benchmark in data["benchmarks"])


def test_v2_start_simulation_rejects_mock_floor_plan_in_production(client: TestClient):
    old_mode = settings.APP_MODE
    settings.APP_MODE = "production"
    try:
        response = client.post(
            "/api/v2/simulations/start",
            json={
                "floor_plan_id": "mock-prod-reject",
                "num_agents": 12,
                "panic_level": 0.3,
                "emergency_type": "fire",
            },
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert response.status_code == 422
        _assert_v2_error_status(response.json(), 422)
    finally:
        settings.APP_MODE = old_mode


def test_v2_start_simulation_rejects_not_ready_floor_plan_in_production(client: TestClient):
    old_mode = settings.APP_MODE
    settings.APP_MODE = "production"
    floorplan_store.save_floor_plan(
        "fp-prod-not-ready",
        {
            "id": "fp-prod-not-ready",
            "building_name": "Prod Not Ready",
            "detected_walls": [{"x1": 0, "y1": 0, "x2": 100, "y2": 0}],
            "detected_exits": [],
            "manual_exits": [],
            "detected_obstacles": [],
            "boundaries": [{"x1": 0, "y1": 0, "x2": 100, "y2": 0}],
            "building_bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100, "width": 100, "height": 100},
            "pipeline": "traditional",
            "quality": {"score": 0.9, "warnings": []},
            "processing_metadata": {"processed": True, "pipeline": "traditional"},
            "revision": 1,
        },
    )
    try:
        response = client.post(
            "/api/v2/simulations/start",
            json={
                "floor_plan_id": "fp-prod-not-ready",
                "num_agents": 12,
                "panic_level": 0.3,
                "emergency_type": "fire",
            },
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert response.status_code == 422
        body = response.json()
        _assert_v2_error_status(body, 422)
        detail = body.get("error", {}).get("details", {})
        assert detail.get("code") == "floor_plan_not_ready"
    finally:
        settings.APP_MODE = old_mode


def test_v1_deprecation_headers_present(client: TestClient):
    response = client.get("/api/system/info")
    assert response.status_code == 200
    assert response.headers.get("Deprecation") == "true"
    assert response.headers.get("Sunset") == "2026-06-30"
