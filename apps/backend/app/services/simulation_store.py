"""
In-memory stores for simulation summaries and transient frames.
Used for demo/mock runs and database-unavailable fallback.
"""

from typing import Dict, Any, Optional, Tuple, List
from copy import deepcopy
import time

SIM_SUMMARY_TTL_SECONDS = 3600
SIM_SUMMARY_MAX_ENTRIES = 1024

SIM_FRAME_TTL_SECONDS = 3600
SIM_FRAME_MAX_SIMULATIONS = 1024
SIM_FRAME_MAX_PER_SIMULATION = 4000

_SIM_SUMMARIES: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_SIM_FRAMES: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}


def _prune_summaries() -> None:
    if not _SIM_SUMMARIES:
        return
    now = time.time()
    expired = [k for k, (ts, _) in _SIM_SUMMARIES.items() if now - ts > SIM_SUMMARY_TTL_SECONDS]
    for key in expired:
        _SIM_SUMMARIES.pop(key, None)
    if len(_SIM_SUMMARIES) <= SIM_SUMMARY_MAX_ENTRIES:
        return
    ordered = sorted(_SIM_SUMMARIES.items(), key=lambda item: item[1][0])
    for key, _ in ordered[: max(0, len(_SIM_SUMMARIES) - SIM_SUMMARY_MAX_ENTRIES)]:
        _SIM_SUMMARIES.pop(key, None)


def _prune_frames() -> None:
    if not _SIM_FRAMES:
        return
    now = time.time()
    expired = [k for k, (ts, _) in _SIM_FRAMES.items() if now - ts > SIM_FRAME_TTL_SECONDS]
    for key in expired:
        _SIM_FRAMES.pop(key, None)
    if len(_SIM_FRAMES) <= SIM_FRAME_MAX_SIMULATIONS:
        return
    ordered = sorted(_SIM_FRAMES.items(), key=lambda item: item[1][0])
    for key, _ in ordered[: max(0, len(_SIM_FRAMES) - SIM_FRAME_MAX_SIMULATIONS)]:
        _SIM_FRAMES.pop(key, None)


def save_summary(simulation_id: str, summary: Dict[str, Any]) -> None:
    if not simulation_id:
        return
    _SIM_SUMMARIES[simulation_id] = (time.time(), deepcopy(summary))
    _prune_summaries()


def get_summary(simulation_id: str) -> Optional[Dict[str, Any]]:
    if not simulation_id:
        return None
    _prune_summaries()
    entry = _SIM_SUMMARIES.get(simulation_id)
    if not entry:
        return None
    _, summary = entry
    return deepcopy(summary)


def save_frame(simulation_id: str, frame: Dict[str, Any]) -> None:
    if not simulation_id or not isinstance(frame, dict):
        return
    _prune_frames()
    _, existing = _SIM_FRAMES.get(simulation_id, (time.time(), []))
    next_frames = list(existing)
    next_frames.append(deepcopy(frame))
    if len(next_frames) > SIM_FRAME_MAX_PER_SIMULATION:
        next_frames = next_frames[-SIM_FRAME_MAX_PER_SIMULATION :]
    _SIM_FRAMES[simulation_id] = (time.time(), next_frames)
    _prune_frames()


def get_latest_frame(simulation_id: str) -> Optional[Dict[str, Any]]:
    if not simulation_id:
        return None
    _prune_frames()
    entry = _SIM_FRAMES.get(simulation_id)
    if not entry:
        return None
    _, frames = entry
    if not frames:
        return None
    return deepcopy(frames[-1])


def get_frames(
    simulation_id: str,
    *,
    limit: Optional[int] = None,
    skip: int = 0,
    stride: int = 1,
    from_ts: Optional[float] = None,
    to_ts: Optional[float] = None,
) -> List[Dict[str, Any]]:
    if not simulation_id:
        return []

    _prune_frames()
    entry = _SIM_FRAMES.get(simulation_id)
    if not entry:
        return []

    _, frames = entry
    if not frames:
        return []

    items = frames
    if from_ts is not None or to_ts is not None:
        bounded: List[Dict[str, Any]] = []
        for frame in items:
            ts = frame.get("timestamp")
            try:
                ts_value = float(ts)
            except (TypeError, ValueError):
                bounded.append(frame)
                continue
            if from_ts is not None and ts_value < float(from_ts):
                continue
            if to_ts is not None and ts_value > float(to_ts):
                continue
            bounded.append(frame)
        items = bounded

    skip = max(0, int(skip))
    stride = max(1, int(stride))
    if skip > 0:
        items = items[skip:]
    if limit is not None:
        bounded_limit = max(1, int(limit))
        items = items[:bounded_limit]
    if stride > 1:
        items = items[::stride]

    return deepcopy(items)


def clear_simulation_store() -> None:
    """Clear all in-memory simulation summaries/frames (test lifecycle helper)."""
    _SIM_SUMMARIES.clear()
    _SIM_FRAMES.clear()


def clear_summary(simulation_id: str) -> None:
    if not simulation_id:
        return
    _SIM_SUMMARIES.pop(simulation_id, None)


def clear_frames(simulation_id: str) -> None:
    if not simulation_id:
        return
    _SIM_FRAMES.pop(simulation_id, None)
