"""
In-memory session store for v3 simulation sessions and derived artifacts.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import time

SESSION_TTL_SECONDS = 6 * 3600
SESSION_MAX_ENTRIES = 2048
SESSION_EVENT_MAX_ENTRIES = 400

_SESSIONS: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_SESSION_EVENTS: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_SESSION_ANALYSIS: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _prune() -> None:
    now = time.time()

    expired_sessions = [key for key, (ts, _) in _SESSIONS.items() if now - ts > SESSION_TTL_SECONDS]
    for key in expired_sessions:
        _SESSIONS.pop(key, None)
        _SESSION_EVENTS.pop(key, None)
        _SESSION_ANALYSIS.pop(key, None)

    if len(_SESSIONS) <= SESSION_MAX_ENTRIES:
        return

    ordered = sorted(_SESSIONS.items(), key=lambda item: item[1][0])
    overflow = len(_SESSIONS) - SESSION_MAX_ENTRIES
    for key, _ in ordered[:overflow]:
        _SESSIONS.pop(key, None)
        _SESSION_EVENTS.pop(key, None)
        _SESSION_ANALYSIS.pop(key, None)


def save_session(session_id: str, doc: Dict[str, Any]) -> None:
    if not session_id:
        return
    stored = deepcopy(doc)
    stored.setdefault("id", session_id)
    stored.setdefault("_id", session_id)
    stored.setdefault("created_at", datetime.now(timezone.utc))
    stored["updated_at"] = stored.get("updated_at") or datetime.now(timezone.utc)
    _SESSIONS[session_id] = (time.time(), stored)
    _prune()


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    if not session_id:
        return None
    _prune()
    entry = _SESSIONS.get(session_id)
    if not entry:
        return None
    _, doc = entry
    return deepcopy(doc)


def list_sessions(skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    _prune()
    docs = [doc for _, doc in _SESSIONS.values()]
    docs.sort(key=lambda item: item.get("created_at") or datetime.now(timezone.utc), reverse=True)
    return deepcopy(docs[skip : skip + limit])


def append_session_event(session_id: str, event: Dict[str, Any]) -> None:
    if not session_id:
        return
    _prune()
    _, existing = _SESSION_EVENTS.get(session_id, (time.time(), []))
    events = list(existing)
    events.append(deepcopy(event))
    if len(events) > SESSION_EVENT_MAX_ENTRIES:
        events = events[-SESSION_EVENT_MAX_ENTRIES:]
    _SESSION_EVENTS[session_id] = (time.time(), events)


def get_session_events(session_id: str) -> List[Dict[str, Any]]:
    if not session_id:
        return []
    _prune()
    entry = _SESSION_EVENTS.get(session_id)
    if not entry:
        return []
    _, events = entry
    return deepcopy(events)


def save_session_analysis(session_id: str, analysis: Dict[str, Any]) -> None:
    if not session_id:
        return
    _SESSION_ANALYSIS[session_id] = (time.time(), deepcopy(analysis))
    _prune()


def get_session_analysis(session_id: str) -> Optional[Dict[str, Any]]:
    if not session_id:
        return None
    _prune()
    entry = _SESSION_ANALYSIS.get(session_id)
    if not entry:
        return None
    _, analysis = entry
    return deepcopy(analysis)


def clear_session_runtime(session_id: str) -> None:
    if not session_id:
        return
    _SESSION_EVENTS.pop(session_id, None)
    _SESSION_ANALYSIS.pop(session_id, None)


def clear_all_session_store() -> None:
    _SESSIONS.clear()
    _SESSION_EVENTS.clear()
    _SESSION_ANALYSIS.clear()
