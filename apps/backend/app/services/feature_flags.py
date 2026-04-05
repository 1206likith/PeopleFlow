import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.core.capabilities import CAPABILITIES, CAPABILITY_INDEX
from app.core.config import settings
from app.services.audit_log import record_event

logger = logging.getLogger(__name__)

_FLAGS_LOADED = False
_FLAG_OVERRIDES: Dict[str, bool] = {}


def _flags_file() -> Path:
    return Path(settings.FEATURE_FLAGS_FILE)


def _load_flags_from_disk() -> None:
    global _FLAGS_LOADED, _FLAG_OVERRIDES
    if _FLAGS_LOADED:
        return
    _FLAGS_LOADED = True
    path = _flags_file()
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        overrides = data.get("overrides", {})
        if isinstance(overrides, dict):
            _FLAG_OVERRIDES = {str(k): bool(v) for k, v in overrides.items()}
    except Exception as exc:
        logger.warning("Failed to load feature flags: %s", exc)


def _persist_flags() -> None:
    path = _flags_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "overrides": _FLAG_OVERRIDES,
            "updated_at": record_event(
                "feature_flags_persist",
                actor="system",
                metadata={"count": len(_FLAG_OVERRIDES)},
            )["timestamp"],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to persist feature flags: %s", exc)


def _default_flags() -> Dict[str, bool]:
    return {cap.id: cap.default_enabled for cap in CAPABILITIES}


def _update_metrics() -> None:
    try:
        from app.core.metrics import feature_flags_active_total
    except Exception:
        return
    counts: Dict[str, int] = {}
    for cap in CAPABILITIES:
        enabled = is_enabled(cap.id)
        if enabled:
            counts[cap.category] = counts.get(cap.category, 0) + 1
    for category, count in counts.items():
        feature_flags_active_total.labels(category=category).set(count)


def get_all_flags() -> Dict[str, bool]:
    _load_flags_from_disk()
    flags = _default_flags()
    flags.update(_FLAG_OVERRIDES)
    _update_metrics()
    return flags


def is_enabled(flag_id: str) -> bool:
    _load_flags_from_disk()
    if flag_id in _FLAG_OVERRIDES:
        return _FLAG_OVERRIDES[flag_id]
    cap = CAPABILITY_INDEX.get(flag_id)
    if not cap:
        return False
    return cap.default_enabled


def set_flag(flag_id: str, enabled: bool, source: str = "api", actor: Optional[str] = None) -> Dict[str, object]:
    _load_flags_from_disk()
    if flag_id not in CAPABILITY_INDEX:
        raise KeyError(f"Unknown capability: {flag_id}")
    _FLAG_OVERRIDES[flag_id] = bool(enabled)
    _persist_flags()
    _update_metrics()

    event = record_event(
        "feature_flag_update",
        actor=actor or "api",
        metadata={"flag_id": flag_id, "enabled": bool(enabled), "source": source},
    )
    try:
        from app.core.metrics import feature_flags_changes_total
        feature_flags_changes_total.labels(
            flag=flag_id,
            enabled=str(bool(enabled)).lower(),
            source=source,
        ).inc()
    except Exception:
        pass
    return event


def list_flags(category: Optional[str] = None, enabled: Optional[bool] = None) -> List[Dict[str, object]]:
    flags = get_all_flags()
    results = []
    for cap in CAPABILITIES:
        if category and cap.category != category:
            continue
        is_on = flags.get(cap.id, cap.default_enabled)
        if enabled is not None and is_on != enabled:
            continue
        source = "override" if cap.id in _FLAG_OVERRIDES else "default"
        results.append({
            "id": cap.id,
            "category": cap.category,
            "description": cap.description,
            "enabled": is_on,
            "default_enabled": cap.default_enabled,
            "source": source,
        })
    return results


def get_flag(flag_id: str) -> Dict[str, object]:
    flags = get_all_flags()
    cap = CAPABILITY_INDEX.get(flag_id)
    if not cap:
        raise KeyError(f"Unknown capability: {flag_id}")
    return {
        "id": cap.id,
        "category": cap.category,
        "description": cap.description,
        "enabled": flags.get(cap.id, cap.default_enabled),
        "default_enabled": cap.default_enabled,
        "source": "override" if cap.id in _FLAG_OVERRIDES else "default",
    }


def active_flags() -> List[str]:
    flags = get_all_flags()
    return [cap_id for cap_id, enabled in flags.items() if enabled]


def category_summary() -> Dict[str, Dict[str, int]]:
    flags = get_all_flags()
    summary: Dict[str, Dict[str, int]] = {}
    for cap in CAPABILITIES:
        cat = cap.category
        entry = summary.setdefault(cat, {"enabled": 0, "total": 0})
        entry["total"] += 1
        if flags.get(cap.id, cap.default_enabled):
            entry["enabled"] += 1
    return summary
