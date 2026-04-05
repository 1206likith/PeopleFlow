"""
In-memory cache for floor plan processing results.
Avoids repeating expensive image processing.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, Tuple
from copy import deepcopy
import json
import time

from app.core.config import settings

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _prune() -> None:
    if not _CACHE:
        return
    now = time.time()
    ttl = max(1, int(settings.FLOORPLAN_CACHE_TTL_SECONDS))
    expired = [k for k, (ts, _) in _CACHE.items() if now - ts > ttl]
    for key in expired:
        _CACHE.pop(key, None)
    max_entries = max(1, int(settings.FLOORPLAN_CACHE_MAX_ENTRIES))
    if len(_CACHE) <= max_entries:
        return
    ordered = sorted(_CACHE.items(), key=lambda item: item[1][0])
    for key, _ in ordered[: max(0, len(_CACHE) - max_entries)]:
        _CACHE.pop(key, None)


def make_cache_key(file_hash: Optional[str], processing_options: Optional[Dict[str, Any]]) -> Optional[str]:
    if not file_hash:
        return None
    options = processing_options or {}
    try:
        options_key = json.dumps(options, sort_keys=True, default=str)
    except Exception:
        options_key = str(options)
    return f"fp:{file_hash}:{options_key}"


def get_cached_processing(cache_key: Optional[str]) -> Optional[Dict[str, Any]]:
    if not cache_key:
        return None
    _prune()
    entry = _CACHE.get(cache_key)
    if not entry:
        try:
            from app.core.metrics import floorplan_processing_cache_total
            floorplan_processing_cache_total.labels(source="memory", status="miss").inc()
        except Exception:
            pass
        return None
    try:
        from app.core.metrics import floorplan_processing_cache_total
        floorplan_processing_cache_total.labels(source="memory", status="hit").inc()
    except Exception:
        pass
    _, payload = entry
    return deepcopy(payload)


def store_cached_processing(cache_key: Optional[str], payload: Dict[str, Any]) -> None:
    if not cache_key or not payload:
        return
    _CACHE[cache_key] = (time.time(), deepcopy(payload))
    _prune()
