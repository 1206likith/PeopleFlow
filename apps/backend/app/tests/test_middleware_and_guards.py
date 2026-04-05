from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from app.core.admin_gate import require_admin_key
from app.core.config import settings
from app.core.middleware import (
    AdminKeyMiddleware,
    ApiV1DeprecationMiddleware,
    ApiV2EnvelopeMiddleware,
    CorrelationIDMiddleware,
    HttpsOnlyMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.request_context import get_request_actor


def create_client(app: FastAPI) -> TestClient:
    """Helper to create TestClient with explicit httpx configuration."""
    return TestClient(app)


def test_admin_gate_dependency_enforced():
    app = FastAPI()

    @app.post("/mutate")
    async def mutate(_: None = Depends(require_admin_key)):
        return {"ok": True}

    client = create_client(app)
    old_enabled = settings.ADMIN_KEY_ENABLED
    old_key = settings.ADMIN_API_KEY
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "dep-key"
    try:
        assert client.post("/mutate").status_code == 401
        assert client.post("/mutate", headers={"X-Admin-Key": "bad"}).status_code == 403
        assert client.post("/mutate", headers={"X-Admin-Key": "dep-key"}).status_code == 200
    finally:
        settings.ADMIN_KEY_ENABLED = old_enabled
        settings.ADMIN_API_KEY = old_key


def test_admin_gate_dependency_can_be_disabled():
    app = FastAPI()

    @app.post("/mutate")
    async def mutate(_: None = Depends(require_admin_key)):
        return {"ok": True}

    client = create_client(app)
    old_enabled = settings.ADMIN_KEY_ENABLED
    settings.ADMIN_KEY_ENABLED = False
    try:
        assert client.post("/mutate").status_code == 200
    finally:
        settings.ADMIN_KEY_ENABLED = old_enabled


def test_request_context_uses_global_tenant_and_mode():
    app = FastAPI()

    @app.get("/ctx")
    async def context(request: Request):
        return get_request_actor(request)

    client = create_client(app)
    old_mode = settings.APP_MODE
    try:
        settings.APP_MODE = "production"
        body = client.get("/ctx").json()
        assert body["tenant_id"] == "global"
        assert body["mode"] == "production"
        assert body["id"] == "system"

        settings.APP_MODE = "demo"
        body = client.get("/ctx", headers={"X-Actor-ID": "operator-1"}).json()
        assert body["id"] == "operator-1"
        assert body["mode"] == "demo"
        body = client.get("/ctx", headers={"X-Actor-ID": ""}).json()
        assert body["id"] == "system"
    finally:
        settings.APP_MODE = old_mode


def test_admin_key_middleware_only_blocks_v2_mutations():
    app = FastAPI()
    app.add_middleware(AdminKeyMiddleware)

    @app.get("/api/v2/read")
    async def read_v2():
        return {"ok": True}

    @app.post("/api/v2/write")
    async def write_v2():
        return {"ok": True}

    @app.post("/api/v2/docs/probe")
    async def docs_probe():
        return {"ok": True}

    client = create_client(app)
    old_enabled = settings.ADMIN_KEY_ENABLED
    old_key = settings.ADMIN_API_KEY
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "mw-key"
    try:
        assert client.get("/api/v2/read").status_code == 200
        assert client.post("/api/v2/write").status_code == 401
        assert client.post("/api/v2/write", headers={"X-Admin-Key": "bad"}).status_code == 403
        assert client.post("/api/v2/write", headers={"X-Admin-Key": "mw-key"}).status_code == 200
        assert client.post("/api/v2/docs/probe").status_code == 200
        settings.ADMIN_KEY_ENABLED = False
        assert client.post("/api/v2/write").status_code == 200
    finally:
        settings.ADMIN_KEY_ENABLED = old_enabled
        settings.ADMIN_API_KEY = old_key


def test_v2_envelope_wraps_success_and_errors():
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(ApiV2EnvelopeMiddleware)

    @app.get("/api/v2/success")
    async def success():
        return {"ok": True}

    @app.get("/api/v2/error")
    async def error():
        return PlainTextResponse("bad", status_code=400)

    @app.get("/api/v2/prewrapped")
    async def prewrapped():
        return {"meta": {"version": "v2"}, "data": {"x": 1}}

    @app.get("/api/v2/invalid-json")
    async def invalid_json():
        return PlainTextResponse("{bad", media_type="application/json")

    @app.get("/api/v2/empty")
    async def empty():
        return PlainTextResponse("", media_type="application/json")

    @app.get("/api/v2/bad-gzip")
    async def bad_gzip():
        response = PlainTextResponse("{\"ok\":true}", media_type="application/json")
        response.headers["Content-Encoding"] = "gzip"
        return response

    client = create_client(app)
    success_resp = client.get("/api/v2/success")
    success_body = success_resp.json()
    assert success_body["meta"]["version"] == "v2"
    assert success_body["data"]["ok"] is True

    error_resp = client.get("/api/v2/error")
    assert error_resp.status_code == 400
    assert error_resp.text == "bad"

    prewrapped_response = client.get("/api/v2/prewrapped").json()
    assert prewrapped_response["meta"]["version"] == "v2"
    assert prewrapped_response["data"]["x"] == 1

    invalid_json_response = client.get("/api/v2/invalid-json")
    assert invalid_json_response.status_code == 200
    assert invalid_json_response.text == "{bad"

    empty_response = client.get("/api/v2/empty").json()
    assert empty_response["meta"]["version"] == "v2"
    assert empty_response["data"] is None

    bad_gzip_response = client.get("/api/v2/bad-gzip").json()
    assert bad_gzip_response["meta"]["version"] == "v2"
    assert bad_gzip_response["data"]["ok"] is True


def test_v1_deprecation_headers_applied_only_to_legacy_paths():
    app = FastAPI()
    app.add_middleware(ApiV1DeprecationMiddleware)

    @app.get("/api/system/test")
    async def legacy():
        return {"ok": True}

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    client = TestClient(app)
    legacy_resp = client.get("/api/system/test")
    assert legacy_resp.headers.get("Deprecation") == "true"
    assert legacy_resp.headers.get("Sunset") == "2026-06-30"
    assert legacy_resp.headers.get("Link") == "/api/v2/docs"

    health_resp = client.get("/api/health")
    assert "Deprecation" not in health_resp.headers


def test_request_size_limit_blocks_large_payloads():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware, max_body_size=5)

    @app.post("/ingest")
    async def ingest():
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/ingest", content="123456", headers={"content-type": "application/json"})
    assert response.status_code == 413


def test_request_size_limit_passthrough_with_zero_limit():
    app = FastAPI()
    app.add_middleware(RequestSizeLimitMiddleware, max_body_size=0)

    @app.post("/ingest")
    async def ingest():
        return {"ok": True}

    client = TestClient(app)
    response = client.post("/ingest", content="123456", headers={"content-type": "application/json"})
    assert response.status_code == 200


def test_https_only_middleware_enforces_scheme():
    app = FastAPI()
    app.add_middleware(HttpsOnlyMiddleware, enabled=True)

    @app.get("/probe")
    async def probe():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/probe")
    assert response.status_code == 400


def test_https_only_middleware_allows_options_preflight():
    app = FastAPI()
    app.add_middleware(HttpsOnlyMiddleware, enabled=True)

    @app.options("/probe")
    async def probe_options():
        return {"ok": True}

    client = TestClient(app)
    response = client.options("/probe")
    assert response.status_code == 200


def test_cors_preflight_allows_localhost_any_port_for_upload_shape():
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/api/v2/simulations/upload")
    async def upload_probe():
        return {"ok": True}

    client = TestClient(app)
    origin = "http://localhost:4173"
    response = client.options(
        "/api/v2/simulations/upload",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-actor-id,x-admin-key,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


def test_https_only_middleware_trusts_forwarded_proto_header():
    app = FastAPI()
    app.add_middleware(HttpsOnlyMiddleware, enabled=True)

    @app.get("/probe")
    async def probe():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/probe", headers={"x-forwarded-proto": "https"})
    assert response.status_code == 200


def test_security_headers_and_correlation_id_middleware():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIDMiddleware)

    @app.get("/probe")
    async def probe():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/probe", headers={"X-Correlation-ID": "cid-123"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "cid-123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"

    https_client = TestClient(app, base_url="https://testserver")
    https_response = https_client.get("/probe")
    assert "Strict-Transport-Security" in https_response.headers


def test_structured_logging_middleware_handles_exceptions():
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    from app.core.middleware import StructuredLoggingMiddleware

    app.add_middleware(StructuredLoggingMiddleware)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
