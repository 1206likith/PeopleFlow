import platform
import sys
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.services import feature_flags
from app.core.request_context import get_request_actor
from app.services.audit_log import list_events
from app.core.database import db as db_state

router = APIRouter()

PROCESS_START = time.time()


@router.get("/info")
async def get_system_info(request: Request):
    start_time = getattr(request.app.state, "start_time", PROCESS_START)
    uptime = max(0.0, time.time() - start_time)
    return {
        "service_name": settings.SERVICE_NAME,
        "service_version": settings.SERVICE_VERSION,
        "build_sha": settings.BUILD_SHA,
        "build_time": settings.BUILD_TIME,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime, 3),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "hostname": platform.node(),
    }


@router.get("/config")
async def get_system_config():
    """Return safe, non-secret configuration values."""
    return {
        "environment": settings.ENVIRONMENT,
        "app_mode": settings.APP_MODE,
        "debug": settings.DEBUG,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "enable_metrics": settings.ENABLE_METRICS,
        "unity_enabled": settings.UNITY_ENABLED,
        "redis_enabled": settings.REDIS_ENABLED,
        "require_https": settings.REQUIRE_HTTPS,
        "admin_key_enabled": settings.ADMIN_KEY_ENABLED,
        "allow_feature_mutation": settings.ALLOW_FEATURE_MUTATION,
    }


@router.get("/status")
async def get_system_status():
    """Operational status snapshot for monitoring."""
    from app.services.simulation_state import simulation_state_manager
    from app.services.unity_bridge import unity_bridge

    return {
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_state.client else "demo",
        "active_simulations": simulation_state_manager.active_count(),
        "max_concurrent_simulations": settings.MAX_CONCURRENT_SIMULATIONS,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "metrics_enabled": settings.ENABLE_METRICS,
        "unity_enabled": settings.UNITY_ENABLED,
        "unity_connections": unity_bridge.connection_count(),
    }


@router.get("/capabilities")
async def list_capabilities(
    category: Optional[str] = None,
    enabled: Optional[bool] = None,
):
    flags = feature_flags.list_flags(category=category, enabled=enabled)
    return {
        "count": len(flags),
        "capabilities": flags,
    }


@router.get("/capabilities/active")
async def list_active_capabilities():
    active = feature_flags.active_flags()
    return {
        "count": len(active),
        "capabilities": active,
    }


@router.get("/capabilities/categories")
async def list_capability_categories():
    return feature_flags.category_summary()


@router.get("/capabilities/{capability_id}")
async def get_capability(capability_id: str):
    try:
        return feature_flags.get_flag(capability_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Capability not found")


@router.post("/capabilities/{capability_id}")
async def update_capability(
    capability_id: str,
    payload: dict,
    current_user: dict = Depends(get_request_actor)
):
    if not settings.ALLOW_FEATURE_MUTATION:
        raise HTTPException(status_code=403, detail="Feature mutation disabled")
    enabled = payload.get("enabled")
    if enabled is None:
        raise HTTPException(status_code=400, detail="enabled required")
    source = payload.get("source") or "api"
    actor = str(current_user.get("_id", "system"))
    try:
        event = feature_flags.set_flag(capability_id, bool(enabled), source=source, actor=actor)
    except KeyError:
        raise HTTPException(status_code=404, detail="Capability not found")
    return {"status": "updated", "event": event}


@router.get("/audit")
async def get_audit_log(limit: int = 100):
    limit = max(1, min(limit, 1000))
    events = list_events(limit=limit)
    return {
        "events": events,
        "count": len(events),
    }

