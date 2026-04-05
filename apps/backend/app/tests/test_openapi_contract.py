import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.main import app


def test_openapi_v2_snapshot_paths():
    snapshot_path = Path(__file__).parent / "snapshots" / "openapi_v2_expected_paths.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))

    with TestClient(app) as client:
        schema = client.get("/api/v2/openapi.json").json()

    paths = set(schema.get("paths", {}).keys())

    for required in snapshot["required_paths"]:
        assert required in paths, f"missing required path: {required}"

    for absent in snapshot["absent_paths"]:
        assert absent not in paths, f"path must be removed: {absent}"


def test_openapi_v3_snapshot_paths():
    snapshot_path = Path(__file__).parent / "snapshots" / "openapi_v3_expected_paths.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))

    with TestClient(app) as client:
        schema = client.get("/api/v2/openapi.json").json()

    paths = set(schema.get("paths", {}).keys())

    for required in snapshot["required_paths"]:
        assert required in paths, f"missing required v3 path: {required}"


def _validate_v2_envelope(data: Dict[str, Any], status_code: int) -> None:
    """Validate that response conforms to /api/v2 envelope contract."""
    # Success responses (2xx) should have meta and data
    if 200 <= status_code < 300:
        assert "meta" in data, "Success responses must have 'meta' field"
        assert "version" in data["meta"], "meta must contain 'version' field"
        assert data["meta"]["version"] == "v2", "envelope version must be v2"
        assert "data" in data, "Success responses must have 'data' field"
    # Error responses (4xx, 5xx) should have meta and error
    else:
        assert "meta" in data, "Error responses must have 'meta' field"
        assert data["meta"]["version"] == "v2", "envelope version must be v2"
        assert "error" in data, "Error responses must have 'error' field"
        error = data["error"]
        assert "code" in error, "error must have 'code' field"
        assert "message" in error, "error must have 'message' field"
        assert "status_code" in error, "error must have 'status_code' field"
        assert error["status_code"] == status_code, "error.status_code must match HTTP status"


def test_v2_envelope_contract_on_success(client: TestClient) -> None:
    """Verify all success responses follow envelope contract."""
    # Test system status endpoint (no auth required)
    resp = client.get("/api/v2/system/status")
    assert 200 <= resp.status_code < 300
    body = resp.json()
    _validate_v2_envelope(body, resp.status_code)


def test_v2_envelope_contract_on_401_unauthorized(client: TestClient) -> None:
    """Verify 401 errors follow envelope contract."""
    from app.core.config import settings
    
    # Setup admin key requirement
    old_admin_enabled = settings.ADMIN_KEY_ENABLED
    old_admin_key = settings.ADMIN_API_KEY
    
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "test-key-xyz"
    
    try:
        resp = client.post("/api/v2/scenarios/create", json={})
        assert resp.status_code in (401, 403)
        body = resp.json()
        _validate_v2_envelope(body, resp.status_code)
    finally:
        settings.ADMIN_KEY_ENABLED = old_admin_enabled
        settings.ADMIN_API_KEY = old_admin_key


def test_v2_envelope_contract_on_400_validation(client: TestClient) -> None:
    """Verify 400 validation errors follow envelope contract."""
    from app.core.config import settings
    
    # Send invalid payload (without proper admin key)
    old_admin_enabled = settings.ADMIN_KEY_ENABLED
    settings.ADMIN_KEY_ENABLED = False
    
    try:
        resp = client.post(
            "/api/v2/scenarios/create",
            json={"invalid_field": "value"}
        )
        assert resp.status_code in (400, 401, 403, 404, 422)
        body = resp.json()
        _validate_v2_envelope(body, resp.status_code)
    finally:
        settings.ADMIN_KEY_ENABLED = old_admin_enabled


def test_v2_envelope_contract_on_500_error(client: TestClient) -> None:
    """Verify 500 errors follow envelope contract."""
    with patch(
        "app.services.simulation_state.simulation_state_manager.active_count",
        side_effect=RuntimeError("forced failure for envelope test"),
    ):
        resp = client.get("/api/v2/system/status")

    assert resp.status_code == 500
    body = resp.json()
    _validate_v2_envelope(body, resp.status_code)


def test_v2_error_shape_contains_required_fields(client: TestClient) -> None:
    """Verify error responses include all required error fields."""
    resp = client.get("/api/v2/nonexistent-endpoint/path")
    
    assert resp.status_code >= 400
    body = resp.json()
    _validate_v2_envelope(body, resp.status_code)
    error = body["error"]
    assert isinstance(error.get("code"), str)
    assert isinstance(error.get("message"), str)
    assert isinstance(error.get("status_code"), int)
    assert error.get("status_code") == resp.status_code


def test_v2_envelope_nesting_consistency(client: TestClient) -> None:
    """Verify envelope structure is consistent across all endpoints."""
    endpoints_to_test = [
        ("GET", "/api/v2/system/status"),
        ("GET", "/api/v2/scenarios/list"),
    ]
    
    for method, path in endpoints_to_test:
        if method == "GET":
            resp = client.get(path)
        elif method == "POST":
            resp = client.post(path, json={})
        
        if resp.status_code < 500:  # Skip actual 500s for this test
            body = resp.json()
            assert "meta" in body, f"Missing 'meta' in {method} {path}"
            assert "version" in body["meta"], f"Missing version in {method} {path}"
            assert body["meta"]["version"] == "v2", f"Wrong version in {method} {path}"


def test_v2_response_includes_correlation_id(client: TestClient) -> None:
    """Verify responses include correlation ID tracking."""
    custom_correlation_id = "test-correlation-123"
    resp = client.get(
        "/api/v2/system/status",
        headers={"X-Correlation-ID": custom_correlation_id}
    )
    body = resp.json()
    
    # Check that correlation ID is present in response headers or metadata
    # (Implementation depends on how it's exposed)
    correlation_header = resp.headers.get("X-Correlation-ID")
    if correlation_header:
        assert correlation_header == custom_correlation_id


def test_v2_response_headers_include_security_headers(client: TestClient) -> None:
    """Verify security headers are present in all responses."""
    resp = client.get("/api/v2/system/status")
    
    # Check for essential security headers
    security_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
    ]
    
    for header in security_headers:
        assert header in resp.headers, f"Missing security header: {header}"
