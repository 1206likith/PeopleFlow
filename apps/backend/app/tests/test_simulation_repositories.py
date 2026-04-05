import pytest

from app.core.config import settings
from app.core.database import db
from app.services.simulation_record_store import clear_simulation_record_store
from app.services.simulation_repository import get_simulation_repository
from app.services.simulation_result_repository import get_simulation_result_repository
from app.services.simulation_store import clear_simulation_store, save_frame


@pytest.fixture(autouse=True)
def clear_simulation_demo_stores():
    clear_simulation_record_store()
    clear_simulation_store()
    yield
    clear_simulation_record_store()
    clear_simulation_store()


@pytest.mark.asyncio
async def test_demo_simulation_repository_round_trip():
    previous_mode = settings.APP_MODE
    previous_client = db.client
    previous_instrumented = db.instrumented
    settings.APP_MODE = "demo"
    db.client = None
    db.instrumented = None

    try:
        repository = await get_simulation_repository()
        simulation_id = await repository.create(
            {
                "tenant_id": "global",
                "status": "running",
                "num_agents": 24,
                "emergency_type": "fire",
            }
        )

        stored = await repository.get(simulation_id)
        assert stored is not None
        assert stored["id"] == simulation_id
        assert stored["num_agents"] == 24

        updated = await repository.update_fields(
            simulation_id,
            {"status": "paused", "label": "Repository Demo"},
        )
        assert updated is not None
        assert updated["status"] == "paused"
        assert updated["label"] == "Repository Demo"

        listed = await repository.list(skip=0, limit=10)
        assert len(listed) == 1
        assert listed[0]["id"] == simulation_id
    finally:
        settings.APP_MODE = previous_mode
        db.client = previous_client
        db.instrumented = previous_instrumented


@pytest.mark.asyncio
async def test_demo_simulation_result_repository_reads_in_memory_frames():
    previous_mode = settings.APP_MODE
    previous_client = db.client
    previous_instrumented = db.instrumented
    settings.APP_MODE = "demo"
    db.client = None
    db.instrumented = None

    save_frame(
        "mock-frame-repo",
        {
            "simulation_id": "mock-frame-repo",
            "timestamp": 1.5,
            "frame_id": 3,
            "agents": [],
            "bottlenecks": [],
            "hazards": [],
            "exit_usage": [],
            "exit_evac_counts": [],
            "profile_counts": [],
            "stats": {"total_agents": 10, "evacuated": 4, "remaining": 6},
        },
    )

    try:
        repository = await get_simulation_result_repository()
        latest = await repository.get_latest_frame("mock-frame-repo")
        assert latest is not None
        assert latest["frame_id"] == 3

        frames = await repository.list_frames(
            "mock-frame-repo",
            limit=10,
            skip=0,
            from_ts=None,
            to_ts=None,
        )
        assert len(frames) == 1
        assert frames[0]["simulation_id"] == "mock-frame-repo"
    finally:
        settings.APP_MODE = previous_mode
        db.client = previous_client
        db.instrumented = previous_instrumented
