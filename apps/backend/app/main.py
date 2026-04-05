from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
import logging
import sys
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import WebSocket
from app.api.routes import simulation_upload, simulation_start, simulation_batches, simulation_scenarios, simulation_controls, simulation_runtime_data, simulation_catalog, simulation_live_updates, floor_plans_read, floor_plans_mutation, results, reports, predictions, replay, metrics, scenarios, validation, optimization, system, models, experiment_artifacts, experiment_execution, simulation_v3
from app.api.websocket import websocket_endpoint
from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.middleware import (
    CorrelationIDMiddleware,
    StructuredLoggingMiddleware,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    HttpsOnlyMiddleware,
    AdminKeyMiddleware,
    ApiV1DeprecationMiddleware,
    ApiV2EnvelopeMiddleware,
)
from app.core.rate_limit import RateLimitMiddleware
from app.core.metrics import MetricsMiddleware, get_metrics

# Configure logging with custom formatter that handles missing correlation_id
class SafeFormatter(logging.Formatter):
    """Formatter that safely handles missing extra fields"""
    def format(self, record):
        # Add default correlation_id if missing
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = getattr(record, 'correlation_id', 'system')
        return super().format(record)

# Set up logging
log_format = (
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(name)s", "correlation_id": "%(correlation_id)s"}'
    if settings.LOG_FORMAT == "json"
    else '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SafeFormatter(log_format))

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, "INFO"),
    handlers=[handler]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (environment=%s, app_mode=%s)",
        settings.APP_NAME,
        settings.ENVIRONMENT,
        settings.APP_MODE,
    )
    app.state.start_time = time.time()
    await init_db()

    # Load ML models if enabled
    if settings.ENVIRONMENT == "production":
        try:
            from app.services.ml_service import ml_service
            ml_service.load_models()
            logger.info("ML models loaded")
        except Exception as e:
            logger.warning(f"Could not load ML models: {e}")

    logger.info("Application startup complete")
    yield
    logger.info("Shutting down application")
    await close_db()


app = FastAPI(
    title="PeopleFlow API",
    description="AI-Powered Emergency Evacuation Simulator Backend",
    version="2.0.0",
    docs_url="/api/v2/docs",
    redoc_url="/api/v2/redoc",
    openapi_url="/api/v2/openapi.json",
    lifespan=lifespan,
)

# Add middleware in order (last added is first executed)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=settings.GZIP_MINIMUM_SIZE, compresslevel=settings.GZIP_LEVEL)
app.add_middleware(StructuredLoggingMiddleware)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)
if settings.ENABLE_METRICS:
    app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_body_size=settings.MAX_REQUEST_SIZE)
app.add_middleware(HttpsOnlyMiddleware, enabled=settings.REQUIRE_HTTPS)
app.add_middleware(ApiV1DeprecationMiddleware)
app.add_middleware(AdminKeyMiddleware)
app.add_middleware(ApiV2EnvelopeMiddleware)
app.add_middleware(CorrelationIDMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Global exception handler
def _build_versioned_meta(request: Request, correlation_id: str) -> dict:
    version = "v3" if request.url.path.startswith("/api/v3") else "v2"
    return {
        "version": version,
        "mode": "demo" if settings.IS_DEMO_MODE else "production",
        "path": request.url.path,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    detail = exc.detail
    if request.url.path.startswith("/api/v2") or request.url.path.startswith("/api/v3"):
        code = f"http_{exc.status_code}"
        message = "Request failed"
        details = detail
        if isinstance(detail, dict):
            code = str(detail.get("code") or code)
            message = str(detail.get("message") or detail.get("detail") or message)
        elif isinstance(detail, str):
            message = detail
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "meta": _build_versioned_meta(request, correlation_id),
                "error": {
                    "code": code,
                    "message": message,
                    "status_code": exc.status_code,
                    "details": details,
                },
            },
        )
    payload = {
        "detail": detail,
        "correlation_id": correlation_id,
        "path": request.url.path,
        "error_type": "http_error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    if request.url.path.startswith("/api/v2") or request.url.path.startswith("/api/v3"):
        return JSONResponse(
            status_code=422,
            content={
                "meta": _build_versioned_meta(request, correlation_id),
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "status_code": 422,
                    "details": exc.errors(),
                },
            },
        )
    payload = {
        "detail": "Request validation failed",
        "errors": exc.errors(),
        "correlation_id": correlation_id,
        "path": request.url.path,
        "error_type": "validation_error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(status_code=422, content=payload)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    logger.error(
        "Unhandled exception",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "error": str(exc),
            "error_type": type(exc).__name__,
        },
        exc_info=True
    )
    if request.url.path.startswith("/api/v2") or request.url.path.startswith("/api/v3"):
        return JSONResponse(
            status_code=500,
            content={
                "meta": _build_versioned_meta(request, correlation_id),
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "status_code": 500,
                    "details": str(exc) if settings.DEBUG else None,
                },
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "correlation_id": correlation_id,
            "message": "An unexpected error occurred" if not settings.DEBUG else str(exc),
            "path": request.url.path,
            "error_type": type(exc).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

# Include Legacy v1 Routers (deprecated)
app.include_router(simulation_upload.router, prefix="/api/simulation", tags=["Simulation Upload"])
app.include_router(simulation_start.router, prefix="/api/simulation", tags=["Simulation Start"])
app.include_router(simulation_batches.router, prefix="/api/simulation", tags=["Simulation Batches"])
app.include_router(simulation_scenarios.router, prefix="/api/simulation", tags=["Simulation Scenarios"])
app.include_router(simulation_controls.router, prefix="/api/simulation", tags=["Simulation Controls"])
app.include_router(simulation_runtime_data.router, prefix="/api/simulation", tags=["Simulation Runtime Data"])
app.include_router(simulation_live_updates.router, prefix="/api/simulation", tags=["Simulation Live Updates"])
app.include_router(simulation_catalog.router, prefix="/api/simulation", tags=["Simulation Catalog"])
app.include_router(floor_plans_read.router, prefix="/api/simulation", tags=["Floor Plans"])
app.include_router(floor_plans_mutation.router, prefix="/api/simulation", tags=["Floor Plan Mutations"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(replay.router, prefix="/api/replay", tags=["Replay"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(scenarios.router, prefix="/api/scenarios", tags=["Scenarios"])
app.include_router(validation.router, prefix="/api/validation", tags=["Validation"])
app.include_router(experiment_execution.router, prefix="/api/experiments", tags=["Experiment Execution"])
app.include_router(experiment_artifacts.router, prefix="/api/experiments", tags=["Experiments"])
app.include_router(optimization.router, prefix="/api/optimization", tags=["Optimization"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(models.router, prefix="/api/models", tags=["Models"])

# Include v2 Routers (primary)
app.include_router(simulation_upload.router, prefix="/api/v2/simulations", tags=["Simulation Upload V2"])
app.include_router(simulation_start.router, prefix="/api/v2/simulations", tags=["Simulation Start V2"])
app.include_router(simulation_batches.router, prefix="/api/v2/simulations", tags=["Simulation Batches V2"])
app.include_router(simulation_scenarios.router, prefix="/api/v2/simulations", tags=["Simulation Scenarios V2"])
app.include_router(simulation_controls.router, prefix="/api/v2/simulations", tags=["Simulation Controls V2"])
app.include_router(simulation_runtime_data.router, prefix="/api/v2/simulations", tags=["Simulation Runtime Data V2"])
app.include_router(simulation_live_updates.router, prefix="/api/v2/simulations", tags=["Simulation Live Updates V2"])
app.include_router(simulation_catalog.router, prefix="/api/v2/simulations", tags=["Simulation Catalog V2"])
app.include_router(floor_plans_read.router, prefix="/api/v2/simulations", tags=["Floor Plans V2"])
app.include_router(floor_plans_mutation.router, prefix="/api/v2/simulations", tags=["Floor Plan Mutations V2"])
app.include_router(results.router, prefix="/api/v2/results", tags=["Results V2"])
app.include_router(reports.router, prefix="/api/v2/reports", tags=["Reports V2"])
app.include_router(predictions.router, prefix="/api/v2/predictions", tags=["Predictions V2"])
app.include_router(replay.router, prefix="/api/v2/replay", tags=["Replay V2"])
app.include_router(metrics.router, prefix="/api/v2/metrics", tags=["Metrics V2"])
app.include_router(scenarios.router, prefix="/api/v2/scenarios", tags=["Scenarios V2"])
app.include_router(validation.router, prefix="/api/v2/validation", tags=["Validation V2"])
app.include_router(experiment_execution.router, prefix="/api/v2/experiments", tags=["Experiment Execution V2"])
app.include_router(experiment_artifacts.router, prefix="/api/v2/experiments", tags=["Experiments V2"])
app.include_router(optimization.router, prefix="/api/v2/optimization", tags=["Optimization V2"])
app.include_router(system.router, prefix="/api/v2/system", tags=["System V2"])
app.include_router(models.router, prefix="/api/v2/models", tags=["Models V2"])

# Include v3 Routers (canonical simulation sessions)
app.include_router(simulation_v3.router, prefix="/api/v3/simulation", tags=["Simulation Sessions V3"])

# Unity integration router
try:
    from app.api.routes import unity
    app.include_router(unity.router, prefix="/api/unity", tags=["Unity"])
    app.include_router(unity.router, prefix="/api/v2/unity", tags=["Unity V2"])
except ImportError:
    logger.warning("Unity routes not available")

# ML inference router
try:
    from app.api.routes import ml
    app.include_router(ml.router, prefix="/api/ml", tags=["ML"])
    app.include_router(ml.router, prefix="/api/v2/ml", tags=["ML V2"])
except ImportError:
    logger.warning("ML routes not available")

# WebSocket endpoints
@app.websocket("/ws/{simulation_id}")
async def websocket_route(websocket: WebSocket, simulation_id: str):
    """WebSocket endpoint for client tools"""
    await websocket_endpoint(websocket, simulation_id)

@app.websocket("/ws")
async def websocket_route_no_id(websocket: WebSocket):
    """WebSocket endpoint without simulation ID"""
    await websocket_endpoint(websocket, None)

# Unity WebSocket endpoint
@app.websocket("/ws/unity/{simulation_id}")
async def unity_websocket_route(websocket: WebSocket, simulation_id: str):
    """WebSocket endpoint for Unity simulation clients"""
    if settings.ADMIN_KEY_ENABLED:
        admin_key = websocket.query_params.get("admin_key")
        if not admin_key:
            await websocket.close(code=1008, reason="Missing admin_key")
            return
        if admin_key != settings.ADMIN_API_KEY:
            await websocket.close(code=1008, reason="Invalid admin_key")
            return
    from app.services.unity_bridge import unity_bridge
    await unity_bridge.handle_unity_connection(websocket, simulation_id)

@app.get("/")
async def root():
    return {
        "message": "PeopleFlow API",
        "version": "2.0.0",
        "status": "running"
    }

@app.get("/api/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}

@app.get("/api/ready")
async def readiness_check():
    """Readiness check with database connectivity"""
    from app.core.database import db
    
    health_status = {
        "status": "ready",
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": "unknown",
            "websocket": "ok"
        }
    }
    
    # Check database
    try:
        if db.client:
            await db.client.admin.command('ping')
            health_status["checks"]["database"] = "ok"
        else:
            health_status["checks"]["database"] = "not_connected"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "ready" else 503
    return JSONResponse(content=health_status, status_code=status_code)

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    if not settings.ENABLE_METRICS:
        return JSONResponse(content={"error": "Metrics disabled"}, status_code=404)
    return Response(content=get_metrics(), media_type="text/plain")


def _append_query(url: str, request: Request) -> str:
    query = str(request.query_params)
    if query:
        return f"{url}?{query}"
    return url


@app.get("/api/v2/floor-plans")
async def v2_floor_plan_alias_root_get(request: Request):
    target = "/api/v2/simulations/floor-plans"
    return RedirectResponse(_append_query(target, request), status_code=307)


@app.api_route("/api/v2/floor-plans", methods=["POST", "PUT", "DELETE"], include_in_schema=False)
async def v2_floor_plan_alias_root_mutation(request: Request):
    target = "/api/v2/simulations/floor-plans"
    return RedirectResponse(_append_query(target, request), status_code=307)


@app.get("/api/v2/floor-plans/{subpath:path}")
async def v2_floor_plan_alias_get(request: Request, subpath: str):
    if subpath == "upload":
        target = "/api/v2/simulations/upload"
    else:
        target = f"/api/v2/simulations/floor-plans/{subpath}"
    return RedirectResponse(_append_query(target, request), status_code=307)


@app.api_route("/api/v2/floor-plans/{subpath:path}", methods=["POST", "PUT", "DELETE"], include_in_schema=False)
async def v2_floor_plan_alias_mutation(request: Request, subpath: str):
    if subpath == "upload":
        target = "/api/v2/simulations/upload"
    else:
        target = f"/api/v2/simulations/floor-plans/{subpath}"
    return RedirectResponse(_append_query(target, request), status_code=307)


@app.api_route("/api/v2/batches", methods=["GET"])
async def v2_batches_alias_root(request: Request):
    target = "/api/v2/simulations/batches"
    return RedirectResponse(_append_query(target, request), status_code=307)


@app.api_route("/api/v2/batches/{subpath:path}", methods=["GET"])
async def v2_batches_alias(request: Request, subpath: str):
    target = f"/api/v2/simulations/batches/{subpath}"
    return RedirectResponse(_append_query(target, request), status_code=307)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
