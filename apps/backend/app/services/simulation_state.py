"""
Simulation State Manager
Tracks running simulations and their pause/resume state
"""

from threading import RLock
from typing import Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)


ACTIVE_STATUSES = {"running", "paused", "stopping"}
TERMINAL_STATUSES = {"completed", "stopped", "failed", "error", "time_limit", "max_iterations", "disconnected"}


class SimulationStateManager:
    """Manages state for all running simulations"""
    
    def __init__(self):
        self._simulations: Dict[str, Dict] = {}
        self._lock = RLock()

    @staticmethod
    def _now() -> float:
        return time.time()

    def _record_state(
        self,
        simulation_id: str,
        status: str,
        paused: bool = False,
        stop_requested: bool = False,
        metadata: Optional[Dict] = None,
        preserve_started_at: bool = True,
    ) -> None:
        existing = self._simulations.get(simulation_id, {})
        started_at = existing.get("started_at", self._now()) if preserve_started_at else self._now()
        state = {
            "status": status,
            "paused": paused,
            "stop_requested": stop_requested,
            "started_at": started_at,
            "updated_at": self._now(),
            "metadata": metadata if metadata is not None else existing.get("metadata", {}),
        }
        if status in TERMINAL_STATUSES:
            state["ended_at"] = self._now()
        self._simulations[simulation_id] = state
    
    def register_simulation(self, simulation_id: str, status: str = "running", metadata: Optional[Dict] = None):
        """Register a new simulation"""
        with self._lock:
            self._record_state(
                simulation_id,
                status=status,
                paused=(status == "paused"),
                stop_requested=(status == "stopping"),
                metadata=metadata or {},
                preserve_started_at=False,
            )
        logger.info(f"Registered simulation {simulation_id} with status {status}")
        self.cleanup_terminal(max_age_seconds=3600, max_entries=2000)

    def active_count(self) -> int:
        """Count simulations considered active."""
        with self._lock:
            return sum(
                1 for sim in self._simulations.values()
                if sim.get("status") in ACTIVE_STATUSES
            )

    def can_start(self, max_concurrent: Optional[int]) -> bool:
        """Check if a new simulation can be started under concurrency limit."""
        if not max_concurrent or max_concurrent <= 0:
            return True
        return self.active_count() < max_concurrent
    
    def pause_simulation(self, simulation_id: str) -> bool:
        """Pause a simulation"""
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim and sim.get("status") == "running":
                sim["paused"] = True
                sim["status"] = "paused"
                sim["updated_at"] = self._now()
                logger.info(f"Paused simulation {simulation_id}")
                return True
        logger.warning(f"Simulation {simulation_id} not found for pause")
        return False
    
    def resume_simulation(self, simulation_id: str) -> bool:
        """Resume a paused simulation"""
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim and sim.get("status") == "paused":
                sim["paused"] = False
                sim["status"] = "running"
                sim["updated_at"] = self._now()
                logger.info(f"Resumed simulation {simulation_id}")
                return True
        logger.warning(f"Simulation {simulation_id} not found for resume")
        return False
    
    def stop_simulation(self, simulation_id: str):
        """Stop and remove a simulation"""
        with self._lock:
            self._record_state(
                simulation_id,
                status="stopped",
                paused=False,
                stop_requested=True,
            )
        logger.info(f"Stopped simulation {simulation_id}")
        return True

    def request_stop(self, simulation_id: str) -> bool:
        """Request a running simulation to stop"""
        with self._lock:
            sim = self._simulations.get(simulation_id)
            if sim and sim.get("status") in {"running", "paused"}:
                sim["stop_requested"] = True
                sim["paused"] = False
                sim["status"] = "stopping"
                sim["updated_at"] = self._now()
                logger.info(f"Stop requested for simulation {simulation_id}")
                return True
        logger.warning(f"Simulation {simulation_id} not found for stop request")
        return False

    def mark_completed(self, simulation_id: str, final_status: str = "completed") -> None:
        """Mark simulation as terminal while retaining status for observability."""
        if final_status not in TERMINAL_STATUSES:
            final_status = "completed"
        with self._lock:
            self._record_state(
                simulation_id,
                status=final_status,
                paused=False,
                stop_requested=final_status in {"stopped", "failed", "error"},
            )
        logger.info("Marked simulation %s as %s", simulation_id, final_status)

    def cleanup_terminal(self, max_age_seconds: int = 3600, max_entries: int = 2000) -> int:
        """Purge terminal simulation records to keep memory bounded."""
        removed = 0
        now = self._now()
        with self._lock:
            keys = list(self._simulations.keys())
            for simulation_id in keys:
                sim = self._simulations.get(simulation_id, {})
                status = sim.get("status")
                ended_at = sim.get("ended_at")
                if status in TERMINAL_STATUSES and ended_at and (now - float(ended_at)) > max_age_seconds:
                    del self._simulations[simulation_id]
                    removed += 1
            if len(self._simulations) > max_entries:
                terminal_items = sorted(
                    (
                        (sid, sim.get("ended_at", sim.get("updated_at", 0.0)))
                        for sid, sim in self._simulations.items()
                        if sim.get("status") in TERMINAL_STATUSES
                    ),
                    key=lambda item: item[1],
                )
                overflow = len(self._simulations) - max_entries
                for sid, _ in terminal_items[:overflow]:
                    if sid in self._simulations:
                        del self._simulations[sid]
                        removed += 1
        return removed
    
    def is_paused(self, simulation_id: str) -> bool:
        """Check if a simulation is paused"""
        with self._lock:
            sim = self._simulations.get(simulation_id)
            return bool(sim and sim.get("paused", False))

    def is_stop_requested(self, simulation_id: str) -> bool:
        """Check if a stop has been requested"""
        with self._lock:
            sim = self._simulations.get(simulation_id)
            return bool(sim and sim.get("stop_requested", False))
    
    def get_status(self, simulation_id: str) -> Optional[str]:
        """Get simulation status"""
        with self._lock:
            if simulation_id in self._simulations:
                return self._simulations[simulation_id].get("status", "unknown")
            return None

    def snapshot(self, simulation_id: str) -> Optional[Dict]:
        """Return a shallow copy of simulation state for diagnostics."""
        with self._lock:
            sim = self._simulations.get(simulation_id)
            return dict(sim) if sim else None

# Global instance
simulation_state_manager = SimulationStateManager()

