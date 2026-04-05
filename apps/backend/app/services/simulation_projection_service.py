"""
Projection service for canonical session frames, replay slices, and analysis snapshots.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional
import math

from app.services.metrics_engine import MetricsEngine


class SimulationProjectionService:
    def build_frame(
        self,
        session_id: str,
        session_doc: Dict[str, Any],
        raw_frame: Dict[str, Any],
        *,
        previous_frame: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        config = dict(session_doc.get("config") or {})
        hazards = list(raw_frame.get("hazard_state", {}).get("active", []) or [])
        walls = self._normalize_walls(raw_frame.get("walls") or [])
        obstacles = self._normalize_obstacles(raw_frame.get("obstacles") or [])
        exits = self._normalize_exits(raw_frame.get("exits") or [])
        agents = self._normalize_agents(raw_frame.get("agents") or [])
        building_bounds = self._derive_bounds(config, walls, exits, obstacles, agents)
        density_grid = self._density_grid(agents, building_bounds, size=14)
        peak_density = max((max(row) for row in density_grid), default=0.0)
        exit_counts = self._exit_evac_counts(agents)
        exit_usage = self._exit_usage(agents, exits)
        profile_counts = self._profile_counts(config, agents)
        bottlenecks = self._bottlenecks(exit_usage, exits)

        evacuated = sum(1 for agent in agents if agent.get("status") == "evacuated")
        total_agents = max(int(config.get("num_agents") or len(agents) or 0), len(agents))
        remaining = max(0, total_agents - evacuated)
        timestamp = float(raw_frame.get("timestamp") or 0.0)
        previous_evacuated = 0
        previous_timestamp = timestamp
        if previous_frame:
            prev_stats = dict(previous_frame.get("stats") or {})
            previous_evacuated = int(prev_stats.get("evacuated") or 0)
            previous_timestamp = float(previous_frame.get("timestamp") or timestamp)
        dt = max(0.0001, timestamp - previous_timestamp)
        flow_rate = max(0.0, float(evacuated - previous_evacuated) / dt)

        stats = dict(raw_frame.get("stats") or {})
        stats.update(
            {
                "total_agents": total_agents,
                "evacuated": evacuated,
                "remaining": remaining,
                "completion_percentage": (evacuated / total_agents * 100.0) if total_agents else 0.0,
                "flow_rate": flow_rate,
                "peak_density": peak_density,
                "density_grid": density_grid,
                "routing_policy": config.get("routing_policy"),
                "emergency_type": config.get("emergency_type"),
                "mode": config.get("mode"),
                "blocked_exit_count": sum(1 for exit_data in exits if exit_data.get("blocked")),
                "active_hazard_count": len(hazards),
            }
        )

        return {
            "type": "simulation_update",
            "schema_version": 3,
            "session_id": session_id,
            "simulation_id": session_id,
            "frame_id": raw_frame.get("frame_id"),
            "timestamp": timestamp,
            "simulation_time": timestamp,
            "floor_number": raw_frame.get("floor_number") or config.get("floor_number"),
            "agents": agents,
            "exits": exits,
            "walls": walls,
            "obstacles": obstacles,
            "building_bounds": building_bounds,
            "hazards": hazards,
            "hazard_state": raw_frame.get("hazard_state") or {},
            "bottlenecks": bottlenecks,
            "exit_usage": exit_usage,
            "exit_evac_counts": exit_counts,
            "profile_counts": profile_counts,
            "stats": stats,
            "seed": config.get("seed"),
            "mode": config.get("mode"),
            "emergency_type": config.get("emergency_type"),
        }

    def build_analysis_snapshot(
        self,
        session_doc: Dict[str, Any],
        frames: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        session_id = str(session_doc.get("id") or session_doc.get("_id") or "")
        config = dict(session_doc.get("config") or {})
        state = dict(session_doc.get("state") or {})
        latest = frames[-1] if frames else None
        metrics_payload: Dict[str, Any] = {}
        if frames:
            engine = MetricsEngine()
            for frame in frames:
                engine.add_frame(frame)
            try:
                metrics_payload = asdict(engine.calculate_metrics())
            except Exception:
                metrics_payload = {}

        latest_stats = dict((latest or {}).get("stats") or {})
        timeline = [
            {
                "t": float(frame.get("timestamp") or 0.0),
                "frame_id": int(frame.get("frame_id") or 0),
                "evacuated": int(dict(frame.get("stats") or {}).get("evacuated") or 0),
                "remaining": int(dict(frame.get("stats") or {}).get("remaining") or 0),
                "flow_rate": float(dict(frame.get("stats") or {}).get("flow_rate") or 0.0),
                "peak_density": float(dict(frame.get("stats") or {}).get("peak_density") or 0.0),
            }
            for frame in frames[-240:]
        ]
        density_heatmap = latest_stats.get("density_grid")
        if not isinstance(density_heatmap, list):
            density_heatmap = []

        final_summary = {
            "session_id": session_id,
            "mode": config.get("mode"),
            "emergency_type": config.get("emergency_type"),
            "routing_policy": config.get("routing_policy"),
            "seed": config.get("seed"),
            "metrics": metrics_payload,
        }

        return {
            "session_id": session_id,
            "status": state.get("status") or "draft",
            "simulation_time": float((latest or {}).get("timestamp") or 0.0),
            "frame_count": len(frames),
            "total_agents": int(latest_stats.get("total_agents") or config.get("num_agents") or 0),
            "evacuated": int(latest_stats.get("evacuated") or 0),
            "remaining": int(latest_stats.get("remaining") or 0),
            "completion_percentage": float(latest_stats.get("completion_percentage") or 0.0),
            "flow_rate": float(latest_stats.get("flow_rate") or 0.0),
            "peak_density": float(latest_stats.get("peak_density") or 0.0),
            "exit_usage": self._map_counts((latest or {}).get("exit_evac_counts"), "exit_id"),
            "profile_counts": self._map_counts((latest or {}).get("profile_counts"), "profile_id"),
            "timeline": timeline,
            "event_markers": [
                {
                    "event_id": event.get("event_id"),
                    "type": event.get("type"),
                    "timestamp": event.get("timestamp"),
                    "frame_id": event.get("frame_id"),
                    "title": event.get("title"),
                    "severity": event.get("severity"),
                }
                for event in events[-120:]
            ],
            "density_heatmap": density_heatmap,
            "final_summary": final_summary,
        }

    def build_replay_slice(
        self,
        session_id: str,
        frames: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        *,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        safe_offset = max(0, int(offset))
        safe_limit = max(1, min(int(limit), 2000))
        slice_frames = frames[safe_offset : safe_offset + safe_limit]
        return {
            "session_id": session_id,
            "offset": safe_offset,
            "limit": safe_limit,
            "count": len(slice_frames),
            "frames": slice_frames,
            "events": events[-min(len(events), safe_limit) :],
        }

    def _normalize_agents(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                **dict(agent),
                "x": float(agent.get("x", 0.0) or 0.0),
                "y": float(agent.get("y", 0.0) or 0.0),
                "z": float(agent.get("z", agent.get("y", 0.0)) or 0.0),
                "status": str(agent.get("status") or "moving"),
                "target_exit": agent.get("target_exit"),
            }
            for agent in agents
        ]

    def _normalize_exits(self, exits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for index, exit_data in enumerate(exits):
            normalized.append(
                {
                    **dict(exit_data),
                    "id": str(exit_data.get("id") or f"exit-{index + 1}"),
                    "x": float(exit_data.get("x", 0.0) or 0.0),
                    "y": float(exit_data.get("y", 0.0) or 0.0),
                    "z": float(exit_data.get("z", exit_data.get("y", 0.0)) or 0.0),
                    "width": float(exit_data.get("width", 2.0) or 2.0),
                    "capacity": int(exit_data.get("capacity", 100) or 100),
                    "blocked": bool(exit_data.get("blocked") or exit_data.get("is_blocked")),
                }
            )
        return normalized

    def _normalize_walls(self, walls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for wall in walls:
            if not isinstance(wall, dict):
                continue
            try:
                x1 = float(wall.get("x1", 0.0) or 0.0)
                y1 = float(wall.get("y1", 0.0) or 0.0)
                x2 = float(wall.get("x2", 0.0) or 0.0)
                y2 = float(wall.get("y2", 0.0) or 0.0)
            except Exception:
                continue
            normalized.append(
                {
                    **dict(wall),
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "type": str(wall.get("type") or "wall"),
                }
            )
        return normalized

    def _normalize_obstacles(self, obstacles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for obstacle in obstacles:
            if not isinstance(obstacle, dict):
                continue
            x = float(obstacle.get("x", 0.0) or 0.0)
            y = float(obstacle.get("z", obstacle.get("y", 0.0)) or 0.0)
            width = float(obstacle.get("width", obstacle.get("w", 0.0)) or 0.0)
            height = float(obstacle.get("depth", obstacle.get("height", obstacle.get("h", 0.0))) or 0.0)
            if width <= 0 and "x1" in obstacle and "x2" in obstacle:
                width = abs(float(obstacle.get("x2", 0.0) or 0.0) - float(obstacle.get("x1", 0.0) or 0.0))
            if height <= 0 and "y1" in obstacle and "y2" in obstacle:
                height = abs(float(obstacle.get("y2", 0.0) or 0.0) - float(obstacle.get("y1", 0.0) or 0.0))
            normalized.append({**dict(obstacle), "x": x, "y": y, "width": width, "height": height})
        return normalized

    def _derive_bounds(
        self,
        config: Dict[str, Any],
        walls: List[Dict[str, Any]],
        exits: List[Dict[str, Any]],
        obstacles: List[Dict[str, Any]],
        agents: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        snapshot = dict(config.get("floor_plan_snapshot") or {})
        raw = dict(snapshot.get("building_bounds") or {})
        min_x = raw.get("min_x")
        max_x = raw.get("max_x")
        min_y = raw.get("min_y")
        max_y = raw.get("max_y")
        if all(value is not None for value in (min_x, max_x, min_y, max_y)):
            return {
                "min_x": float(min_x),
                "max_x": float(max_x),
                "min_y": float(min_y),
                "max_y": float(max_y),
            }

        xs: List[float] = []
        ys: List[float] = []
        for wall in walls:
            xs.extend([float(wall.get("x1", 0.0)), float(wall.get("x2", 0.0))])
            ys.extend([float(wall.get("y1", 0.0)), float(wall.get("y2", 0.0))])
        for exit_data in exits:
            xs.append(float(exit_data.get("x", 0.0)))
            ys.append(float(exit_data.get("z", exit_data.get("y", 0.0)) or 0.0))
        for obstacle in obstacles:
            x = float(obstacle.get("x", 0.0) or 0.0)
            y = float(obstacle.get("y", 0.0) or 0.0)
            xs.extend([x, x + float(obstacle.get("width", 0.0) or 0.0)])
            ys.extend([y, y + float(obstacle.get("height", 0.0) or 0.0)])
        for agent in agents:
            xs.append(float(agent.get("x", 0.0) or 0.0))
            ys.append(float(agent.get("z", agent.get("y", 0.0)) or 0.0))

        if not xs or not ys:
            return {"min_x": 0.0, "max_x": 100.0, "min_y": 0.0, "max_y": 100.0}
        return {"min_x": min(xs), "max_x": max(xs), "min_y": min(ys), "max_y": max(ys)}

    def _density_grid(self, agents: List[Dict[str, Any]], bounds: Dict[str, float], *, size: int) -> List[List[float]]:
        width = max(1.0, float(bounds.get("max_x", 100.0)) - float(bounds.get("min_x", 0.0)))
        height = max(1.0, float(bounds.get("max_y", 100.0)) - float(bounds.get("min_y", 0.0)))
        cell_width = width / size
        cell_height = height / size
        grid = [[0.0 for _ in range(size)] for _ in range(size)]

        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            x = float(agent.get("x", 0.0) or 0.0)
            y = float(agent.get("z", agent.get("y", 0.0)) or 0.0)
            col = min(size - 1, max(0, int((x - float(bounds.get("min_x", 0.0))) / cell_width)))
            row = min(size - 1, max(0, int((y - float(bounds.get("min_y", 0.0))) / cell_height)))
            grid[row][col] += 1.0

        cell_area = max(1.0, cell_width * cell_height)
        for row_index, row in enumerate(grid):
            for col_index, value in enumerate(row):
                grid[row_index][col_index] = round(value / cell_area, 3)
        return grid

    def _exit_evac_counts(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for agent in agents:
            if agent.get("status") != "evacuated":
                continue
            exit_id = str(agent.get("target_exit") or "")
            if not exit_id:
                continue
            counts[exit_id] = counts.get(exit_id, 0) + 1
        return [{"exit_id": exit_id, "count": count} for exit_id, count in counts.items()]

    def _exit_usage(self, agents: List[Dict[str, Any]], exits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        queue_lengths: Dict[str, int] = {}
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            exit_id = str(agent.get("target_exit") or "")
            if not exit_id:
                continue
            queue_lengths[exit_id] = queue_lengths.get(exit_id, 0) + 1

        rows = []
        for exit_data in exits:
            exit_id = str(exit_data.get("id") or "")
            rows.append(
                {
                    "exit_id": exit_id,
                    "x": float(exit_data.get("x", 0.0) or 0.0),
                    "y": float(exit_data.get("y", 0.0) or 0.0),
                    "z": float(exit_data.get("z", exit_data.get("y", 0.0)) or 0.0),
                    "width": float(exit_data.get("width", 2.0) or 2.0),
                    "capacity": float(exit_data.get("capacity", 100) or 100),
                    "queue_length": queue_lengths.get(exit_id, 0),
                    "is_blocked": bool(exit_data.get("blocked")),
                    "estimated_wait": round(queue_lengths.get(exit_id, 0) / max(1.0, float(exit_data.get("capacity", 100) or 100)), 3),
                }
            )
        return rows

    def _profile_counts(self, config: Dict[str, Any], agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if config.get("agent_profiles"):
            total = max(1, len(agents))
            rows = []
            for profile in config.get("agent_profiles") or []:
                profile_data = dict(profile if isinstance(profile, dict) else {})
                profile_id = str(profile_data.get("name") or profile_data.get("profile_id") or "profile")
                if profile_data.get("count") is not None:
                    count = int(profile_data.get("count") or 0)
                else:
                    ratio = float(profile_data.get("ratio", 0.0) or 0.0)
                    count = int(round(total * ratio))
                rows.append({"profile_id": profile_id, "count": max(0, count)})
            return rows

        status_counts: Dict[str, int] = {}
        for agent in agents:
            status = str(agent.get("status") or "moving")
            status_counts[status] = status_counts.get(status, 0) + 1
        return [{"profile_id": key, "count": value} for key, value in status_counts.items()]

    def _bottlenecks(self, exit_usage: List[Dict[str, Any]], exits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        exit_map = {str(exit_data.get("id") or ""): exit_data for exit_data in exits}
        for entry in exit_usage:
            queue = int(entry.get("queue_length") or 0)
            if queue < 6:
                continue
            exit_data = exit_map.get(str(entry.get("exit_id") or ""), {})
            rows.append(
                {
                    "x": float(exit_data.get("x", 0.0) or 0.0),
                    "y": float(exit_data.get("y", 0.0) or 0.0),
                    "z": float(exit_data.get("z", exit_data.get("y", 0.0)) or 0.0),
                    "density": round(queue / max(1.0, float(exit_data.get("width", 2.0) or 2.0)), 3),
                }
            )
        return rows

    def _map_counts(self, rows: Any, key_name: str) -> Dict[str, int]:
        if not isinstance(rows, list):
            return {}
        mapped: Dict[str, int] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            item_key = str(row.get(key_name) or "")
            if not item_key:
                continue
            mapped[item_key] = int(row.get("count") or 0)
        return mapped
