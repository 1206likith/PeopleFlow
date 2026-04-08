from __future__ import annotations

import re
from typing import Dict

from fastapi import Request

from app.core.config import settings


_ACTOR_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


def _sanitize_actor(value: str | None) -> str | None:
    candidate = (value or "").strip()
    if not candidate:
        return None
    if not _ACTOR_ID_RE.fullmatch(candidate):
        return None
    return candidate


def _extract_bearer_actor(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:].strip()
    if not token:
        return None

    # Compatibility mode: accept opaque actor subjects from internal trusted clients.
    if token.lower().startswith("actor:"):
        token = token[6:]

    return _sanitize_actor(token)


def get_request_actor(request: Request) -> Dict[str, str]:
    """Return a synthetic actor context for single-tenant mode."""
    actor = _extract_bearer_actor(request)
    if actor is None:
        can_use_actor_header = settings.APP_MODE == "demo" or settings.ACTOR_HEADER_ALLOWED_IN_PRODUCTION
        if can_use_actor_header:
            actor = _sanitize_actor(request.headers.get("X-Actor-ID"))

    if actor is None:
        actor = "system"

    mode = "demo" if settings.APP_MODE == "demo" else "production"
    return {
        "_id": actor,
        "id": actor,
        "tenant_id": "global",
        "mode": mode,
    }
