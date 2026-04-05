import time

from app.services.simulation_state import SimulationStateManager


def test_state_transitions_pause_resume_stop():
    manager = SimulationStateManager()
    manager.register_simulation("sim-1", status="running")

    assert manager.get_status("sim-1") == "running"
    assert manager.pause_simulation("sim-1") is True
    assert manager.get_status("sim-1") == "paused"
    assert manager.resume_simulation("sim-1") is True
    assert manager.get_status("sim-1") == "running"
    assert manager.request_stop("sim-1") is True
    assert manager.get_status("sim-1") == "stopping"
    assert manager.stop_simulation("sim-1") is True
    assert manager.get_status("sim-1") == "stopped"
    assert manager.active_count() == 0


def test_invalid_transitions_rejected():
    manager = SimulationStateManager()
    manager.register_simulation("sim-2", status="running")

    assert manager.resume_simulation("sim-2") is False
    assert manager.pause_simulation("missing") is False
    manager.mark_completed("sim-2", final_status="completed")
    assert manager.pause_simulation("sim-2") is False
    assert manager.request_stop("sim-2") is False


def test_cleanup_terminal_records():
    manager = SimulationStateManager()
    manager.register_simulation("sim-old", status="running")
    manager.mark_completed("sim-old", final_status="completed")
    snap = manager.snapshot("sim-old")
    assert snap is not None
    snap["ended_at"] = time.time() - 10_000
    manager._simulations["sim-old"] = snap
    removed = manager.cleanup_terminal(max_age_seconds=60, max_entries=1000)
    assert removed >= 1
    assert manager.get_status("sim-old") is None


def test_mark_completed_unknown_status_normalized():
    manager = SimulationStateManager()
    manager.register_simulation("sim-3", status="running")
    manager.mark_completed("sim-3", final_status="not-a-real-status")
    assert manager.get_status("sim-3") == "completed"
