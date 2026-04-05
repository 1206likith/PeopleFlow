"""
Application service for runtime simulation controls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.core.config import settings
from app.services.audit_log import record_event
from app.services.simulation_repository import get_simulation_repository


def _safe_audit(
    action: str,
    actor: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    severity: str = "info",
) -> None:
    try:
        record_event(action=action, actor=actor, metadata=metadata, severity=severity)
    except Exception:
        pass


class SimulationControlApplicationService:
    async def pause(self, simulation_id: str, current_user: dict) -> Dict[str, Any]:
        from app.services.simulation_state import simulation_state_manager
        from app.services.unity_bridge import unity_bridge

        paused = simulation_state_manager.pause_simulation(simulation_id)
        unity_dispatched = False

        if unity_bridge.has_connection(simulation_id):
            try:
                await unity_bridge.pause_simulation(simulation_id)
                unity_dispatched = True
                paused = True
            except ConnectionError as exc:
                self._warn(f"Pause dispatch to Unity failed for {simulation_id}: {exc}")

        if not paused and not simulation_id.startswith("mock-"):
            await self._update_database_status(simulation_id, "paused")

        self._audit("simulation_paused", simulation_id, current_user)
        return {
            "message": "Simulation paused",
            "simulation_id": simulation_id,
            "dispatched_to_unity": unity_dispatched,
        }

    async def resume(self, simulation_id: str, current_user: dict) -> Dict[str, Any]:
        from app.services.simulation_state import simulation_state_manager
        from app.services.unity_bridge import unity_bridge

        resumed = simulation_state_manager.resume_simulation(simulation_id)
        unity_dispatched = False

        if unity_bridge.has_connection(simulation_id):
            try:
                await unity_bridge.resume_simulation(simulation_id)
                unity_dispatched = True
                resumed = True
            except ConnectionError as exc:
                self._warn(f"Resume dispatch to Unity failed for {simulation_id}: {exc}")

        if not resumed and not simulation_id.startswith("mock-"):
            await self._update_database_status(simulation_id, "running")

        self._audit("simulation_resumed", simulation_id, current_user)
        return {
            "message": "Simulation resumed",
            "simulation_id": simulation_id,
            "dispatched_to_unity": unity_dispatched,
        }

    async def stop(self, simulation_id: str, current_user: dict) -> Dict[str, Any]:
        from app.services.simulation_state import simulation_state_manager
        from app.services.unity_bridge import unity_bridge

        simulation_state_manager.request_stop(simulation_id)
        unity_dispatched = False

        if simulation_id in unity_bridge.unity_connections:
            try:
                await unity_bridge.stop_simulation(simulation_id)
                unity_dispatched = True
            except Exception as exc:
                self._warn(f"Could not stop Unity simulation {simulation_id}: {exc}")

        if simulation_id.startswith("mock-"):
            self._audit("simulation_stopped", simulation_id, current_user, mode="mock")
            return {"message": "Simulation stopped", "dispatched_to_unity": unity_dispatched}

        try:
            await self._update_database_status(simulation_id, "stopped")
            self._audit("simulation_stopped", simulation_id, current_user, mode="db")
            return {"message": "Simulation stopped", "dispatched_to_unity": unity_dispatched}
        except HTTPException:
            raise
        except Exception:
            self._audit("simulation_stopped", simulation_id, current_user, mode="demo")
            return {"message": "Simulation stopped (demo mode)", "dispatched_to_unity": unity_dispatched}

    async def send_command(self, simulation_id: str, command: Any, current_user: dict) -> Dict[str, Any]:
        from app.services.simulation_state import simulation_state_manager
        from app.services.unity_bridge import unity_bridge

        command_data = command.model_dump(exclude_none=True)
        command_type = command.type
        sim_status = simulation_state_manager.get_status(simulation_id)

        if sim_status in {"stopping", "stopped", "completed", "error", "failed", "disconnected"}:
            raise HTTPException(status_code=409, detail=f"Simulation is not commandable in status '{sim_status}'")

        if command_type == "close_exit" and not command.exit_id:
            raise HTTPException(status_code=400, detail="exit_id is required for close_exit")
        if command_type == "redirect_crowd" and not command.target_exit:
            raise HTTPException(status_code=400, detail="target_exit is required for redirect_crowd")
        if command_type == "trigger_fire_door" and not command.door_id:
            raise HTTPException(status_code=400, detail="door_id is required for trigger_fire_door")
        if command_type == "emergency_announcement" and not command.message:
            raise HTTPException(status_code=400, detail="message is required for emergency_announcement")

        dispatched_to_unity = False
        if unity_bridge.has_connection(simulation_id):
            try:
                await unity_bridge.send_to_unity(
                    simulation_id,
                    {
                        "schema_version": 1,
                        "type": "runtime_command",
                        "simulation_id": simulation_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "command": command_data,
                    },
                )
                dispatched_to_unity = True
            except ConnectionError as exc:
                self._warn(f"Unity command dispatch failed for {simulation_id}: {exc}")

        actor = str(current_user.get("_id", current_user.get("id", "system")))
        _safe_audit(
            "simulation_command_sent",
            actor=actor,
            metadata={
                "simulation_id": simulation_id,
                "command_type": command_type,
                "dispatched_to_unity": dispatched_to_unity,
            },
        )

        return {
            "status": "accepted",
            "simulation_id": simulation_id,
            "command": command_data,
            "dispatched_to_unity": dispatched_to_unity,
            "runtime_status": sim_status or "unknown",
        }

    async def _update_database_status(self, simulation_id: str, status: str) -> None:
        try:
            if not settings.IS_DEMO_MODE:
                try:
                    ObjectId(simulation_id)
                except Exception:
                    raise RuntimeError("Simulation id is not a valid production identifier")
            repository = await get_simulation_repository()
            updated = await repository.update_fields(
                simulation_id,
                {"status": status, "updated_at": datetime.now(timezone.utc)},
            )
            if not updated:
                raise HTTPException(status_code=404, detail="Simulation not found")
        except HTTPException:
            raise
        except Exception as exc:
            self._warn(f"Database unavailable for simulation status update ({status}): {exc}")
            if not settings.IS_DEMO_MODE:
                raise HTTPException(status_code=503, detail="Database unavailable")

    @staticmethod
    def _audit(action: str, simulation_id: str, current_user: dict, mode: Optional[str] = None) -> None:
        metadata = {"simulation_id": simulation_id}
        if mode:
            metadata["mode"] = mode
        _safe_audit(
            action,
            actor=str(current_user.get("_id", current_user.get("id", "demo_user"))),
            metadata=metadata,
        )

    @staticmethod
    def _warn(message: str) -> None:
        import logging

        logging.getLogger(__name__).warning(message)


simulation_control_application_service = SimulationControlApplicationService()
