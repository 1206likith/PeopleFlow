"""
In-memory simulation record store for demo mode and database-unavailable fallback.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import time

SIM_RECORD_TTL_SECONDS = 6 * 3600
SIM_RECORD_MAX_ENTRIES = 2048

_SIM_RECORDS: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _prune() -> None:
    if not _SIM_RECORDS:
        return
    now = time.time()
    expired = [key for key, (ts, _) in _SIM_RECORDS.items() if now - ts > SIM_RECORD_TTL_SECONDS]
    for key in expired:
        _SIM_RECORDS.pop(key, None)
    if len(_SIM_RECORDS) <= SIM_RECORD_MAX_ENTRIES:
        return
    ordered = sorted(_SIM_RECORDS.items(), key=lambda item: item[1][0])
    for key, _ in ordered[: max(0, len(_SIM_RECORDS) - SIM_RECORD_MAX_ENTRIES)]:
        _SIM_RECORDS.pop(key, None)


def save_simulation_record(simulation_id: str, doc: Dict[str, Any]) -> None:
    if not simulation_id:
        return
    stored = deepcopy(doc)
    stored.setdefault("id", simulation_id)
    stored.setdefault("_id", simulation_id)
    stored.setdefault("tenant_id", "global")
    stored.setdefault("created_at", datetime.now(timezone.utc))
    stored["updated_at"] = stored.get("updated_at") or datetime.now(timezone.utc)
    _SIM_RECORDS[simulation_id] = (time.time(), stored)
    _prune()


def get_simulation_record(simulation_id: str) -> Optional[Dict[str, Any]]:
    if not simulation_id:
        return None
    _prune()
    entry = _SIM_RECORDS.get(simulation_id)
    if not entry:
        return None
    _, doc = entry
    return deepcopy(doc)


def list_simulation_records(skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    _prune()
    items = [doc for _, doc in _SIM_RECORDS.values()]
    items.sort(key=lambda d: d.get("created_at") or datetime.now(timezone.utc), reverse=True)
    return deepcopy(items[skip : skip + limit])


def clear_simulation_record_store() -> None:
    _SIM_RECORDS.clear()
