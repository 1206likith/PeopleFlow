from __future__ import annotations

from typing import Dict

from fastapi import Request

from app.core.config import settings


def get_request_actor(request: Request) -> Dict[str, str]:
    """Return a synthetic actor context for single-tenant mode."""
    actor = request.headers.get("X-Actor-ID", "system")
    if not actor:
        actor = "system"
    mode = "demo" if settings.APP_MODE == "demo" else "production"
    return {
        "_id": actor,
        "id": actor,
        "tenant_id": "global",
        "mode": mode,
    }
