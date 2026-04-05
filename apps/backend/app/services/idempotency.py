"""
In-memory idempotency store for POST requests.
Used to prevent duplicate side effects when clients retry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Any
import hashlib
import json
import threading
import time

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.config import settings


@dataclass
class IdempotencyRecord:
    created_at: float
    status_code: int
    payload: Dict[str, Any]
    headers: Dict[str, str]
    metadata: Dict[str, Any]


_STORE: Dict[str, IdempotencyRecord] = {}
_LOCK = threading.Lock()


def _prune() -> None:
    if not _STORE:
        return
    now = time.time()
    ttl = max(1, int(settings.IDEMPOTENCY_TTL_SECONDS))
    expired = [k for k, v in _STORE.items() if now - v.created_at > ttl]
    for key in expired:
        _STORE.pop(key, None)
    max_entries = max(1, int(settings.IDEMPOTENCY_MAX_ENTRIES))
    if len(_STORE) <= max_entries:
        return
    ordered = sorted(_STORE.items(), key=lambda item: item[1].created_at)
    for key, _ in ordered[: max(0, len(_STORE) - max_entries)]:
        _STORE.pop(key, None)


def _normalize_key(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) > 200:
        value = value[:200]
    return value


def build_idempotency_key(request: Request, user_id: str) -> Optional[str]:
    raw_key = _normalize_key(request.headers.get("Idempotency-Key", ""))
    if not raw_key:
        return None
    base = {
        "user_id": str(user_id or "anonymous"),
        "method": request.method,
        "path": request.url.path,
        "key": raw_key,
    }
    encoded = json.dumps(base, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"idemp:{digest}"


def get_cached_response(key: str) -> Optional[IdempotencyRecord]:
    if not key:
        return None
    with _LOCK:
        _prune()
        record = _STORE.get(key)
        return record


def store_response(
    key: str,
    status_code: int,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if not key:
        return
    encoded = jsonable_encoder(payload)
    record = IdempotencyRecord(
        created_at=time.time(),
        status_code=int(status_code or 200),
        payload=encoded,
        headers={k: str(v) for k, v in (headers or {}).items()},
        metadata=metadata or {},
    )
    with _LOCK:
        _STORE[key] = record
        _prune()


def build_replay_response(record: IdempotencyRecord) -> JSONResponse:
    headers = dict(record.headers or {})
    headers["Idempotency-Replay"] = "true"
    try:
        from app.core.metrics import idempotency_replays_total
        endpoint = str(record.metadata.get("path") or "unknown")
        idempotency_replays_total.labels(endpoint=endpoint).inc()
    except Exception:
        pass
    return JSONResponse(
        status_code=record.status_code,
        content=record.payload,
        headers=headers,
    )
