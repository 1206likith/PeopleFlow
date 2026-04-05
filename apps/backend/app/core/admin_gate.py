from __future__ import annotations

from fastapi import HTTPException, Request

from app.core.config import settings


async def require_admin_key(request: Request) -> None:
    """Dependency form of v2 admin-key validation."""
    if not settings.ADMIN_KEY_ENABLED:
        return

    key = request.headers.get("X-Admin-Key")
    if not key:
        raise HTTPException(status_code=401, detail="Missing X-Admin-Key")
    if key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid X-Admin-Key")
