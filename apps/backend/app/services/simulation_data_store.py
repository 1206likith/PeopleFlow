"""
In-memory simulation data store for demo mode.
Provides lightweight persistence for legacy simulation metadata records.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid

_SIMULATION_DATA_STORE: Dict[str, List[Dict[str, Any]]] = {}


def save_simulation_data_record(simulation_id: str, doc: Dict[str, Any]) -> str:
    if not simulation_id:
        simulation_id = f"mock-sim-{uuid.uuid4().hex[:12]}"

    stored = deepcopy(doc)
    stored.setdefault("id", f"mock-data-{uuid.uuid4().hex[:12]}")
    stored.setdefault("simulation_id", simulation_id)
    stored.setdefault("created_at", datetime.now(timezone.utc))
    _SIMULATION_DATA_STORE.setdefault(simulation_id, []).append(stored)
    return str(stored["id"])


def list_simulation_data_records(simulation_id: str) -> List[Dict[str, Any]]:
    items = [deepcopy(item) for item in _SIMULATION_DATA_STORE.get(simulation_id, [])]
    items.sort(key=lambda item: item.get("created_at") or datetime.now(timezone.utc))
    return items


def clear_simulation_data_store() -> None:
    _SIMULATION_DATA_STORE.clear()
