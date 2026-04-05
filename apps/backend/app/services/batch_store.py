"""
In-memory batch results store for demo mode.
Provides temporary persistence when MongoDB is unavailable.
Bounded with TTL to avoid unbounded growth.
"""

from typing import Dict, Any, Optional, List, Tuple
from copy import deepcopy
from datetime import datetime, timezone
import time

BATCH_STORE_TTL_SECONDS = 86400
BATCH_STORE_MAX_ENTRIES = 256

_BATCH_STORE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _prune() -> None:
    if not _BATCH_STORE:
        return
    now = time.time()
    expired = [k for k, (ts, _) in _BATCH_STORE.items() if now - ts > BATCH_STORE_TTL_SECONDS]
    for key in expired:
        _BATCH_STORE.pop(key, None)
    if len(_BATCH_STORE) <= BATCH_STORE_MAX_ENTRIES:
        return
    ordered = sorted(_BATCH_STORE.items(), key=lambda item: item[1][0])
    for key, _ in ordered[: max(0, len(_BATCH_STORE) - BATCH_STORE_MAX_ENTRIES)]:
        _BATCH_STORE.pop(key, None)


def save_batch(batch_id: str, doc: Dict[str, Any]) -> None:
    if not batch_id:
        return
    stored = deepcopy(doc)
    stored.setdefault("created_at", datetime.now(timezone.utc))
    _BATCH_STORE[batch_id] = (time.time(), stored)
    _prune()


def get_batch(batch_id: str) -> Optional[Dict[str, Any]]:
    if not batch_id:
        return None
    _prune()
    entry = _BATCH_STORE.get(batch_id)
    if not entry:
        return None
    _, doc = entry
    return deepcopy(doc)


def list_batches(skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    _prune()
    items = [doc for _, doc in _BATCH_STORE.values()]
    items.sort(key=lambda d: d.get("created_at") or datetime.now(timezone.utc), reverse=True)
    return deepcopy(items[skip: skip + limit])
