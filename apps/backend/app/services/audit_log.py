import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings

_EVENTS: List[Dict[str, object]] = []


def _prune() -> None:
    now = time.time()
    ttl = settings.AUDIT_LOG_TTL_SECONDS
    if ttl and ttl > 0:
        _EVENTS[:] = [e for e in _EVENTS if (now - float(e.get("ts", now))) <= ttl]
    max_entries = settings.AUDIT_LOG_MAX_ENTRIES
    if max_entries and len(_EVENTS) > max_entries:
        _EVENTS[:] = _EVENTS[-max_entries:]


def _append_to_file(event: Dict[str, object]) -> None:
    path = Path(settings.AUDIT_LOG_FILE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
    except Exception:
        pass


def record_event(
    action: str,
    actor: Optional[str] = None,
    metadata: Optional[Dict[str, object]] = None,
    severity: str = "info",
) -> Dict[str, object]:
    now = time.time()
    event = {
        "ts": now,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "action": action,
        "actor": actor or "system",
        "severity": severity,
        "metadata": metadata or {},
    }
    _EVENTS.append(event)
    _prune()
    _append_to_file(event)
    try:
        from app.core.metrics import audit_events_total
        audit_events_total.labels(action=action, severity=severity).inc()
    except Exception:
        pass
    return event


def list_events(limit: int = 100) -> List[Dict[str, object]]:
    _prune()
    if limit <= 0:
        return []
    return list(_EVENTS[-limit:])
