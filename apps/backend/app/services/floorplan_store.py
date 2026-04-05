"""
In-memory floor plan store for demo mode.
Provides temporary persistence when MongoDB is unavailable.
"""

from typing import Dict, Any, Optional, List
from copy import deepcopy
from datetime import datetime, timezone

_FLOOR_PLAN_STORE: Dict[str, Dict[str, Any]] = {}


def save_floor_plan(plan_id: str, doc: Dict[str, Any]) -> None:
    if not plan_id:
        return
    stored = deepcopy(doc)
    stored.setdefault("created_at", datetime.now(timezone.utc))
    stored.setdefault("updated_at", stored.get("created_at"))
    _FLOOR_PLAN_STORE[plan_id] = stored


def get_floor_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    if not plan_id:
        return None
    doc = _FLOOR_PLAN_STORE.get(plan_id)
    return deepcopy(doc) if doc else None


def update_floor_plan(plan_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not plan_id or plan_id not in _FLOOR_PLAN_STORE:
        return None
    updated = deepcopy(updates)
    updated.setdefault("updated_at", datetime.now(timezone.utc))
    _FLOOR_PLAN_STORE[plan_id].update(updated)
    return deepcopy(_FLOOR_PLAN_STORE[plan_id])


def list_floor_plans(skip: int = 0, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    items = [deepcopy(doc) for doc in _FLOOR_PLAN_STORE.values()]
    items.sort(key=lambda doc: doc.get("created_at") or datetime.now(timezone.utc), reverse=True)
    if limit is None:
        return items[skip:]
    return items[skip : skip + limit]


def find_floor_plan_by_hash(file_hash: str, processing_options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not file_hash:
        return None
    for doc in _FLOOR_PLAN_STORE.values():
        if doc.get("file_hash") != file_hash:
            continue
        if dict(doc.get("processing_options") or {}) != dict(processing_options or {}):
            continue
        return deepcopy(doc)
    return None


def append_manual_exits(plan_id: str, exits: list) -> Optional[Dict[str, Any]]:
    if not plan_id or plan_id not in _FLOOR_PLAN_STORE:
        return None
    doc = _FLOOR_PLAN_STORE[plan_id]
    manual_exits = doc.get("manual_exits", [])
    manual_exits.extend(deepcopy(exits))
    doc["manual_exits"] = manual_exits
    doc["updated_at"] = datetime.now(timezone.utc)
    _FLOOR_PLAN_STORE[plan_id] = doc
    return deepcopy(doc)


def clear_floor_plans() -> None:
    """Clear in-memory floor plan cache (test/demo lifecycle helper)."""
    _FLOOR_PLAN_STORE.clear()
