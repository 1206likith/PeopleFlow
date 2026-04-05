import asyncio
import pytest

from app.core.config import settings
from app.core.database import db, get_database
from app.services.floorplan_loader import merge_exits


def test_merge_exits_floor_aware():
    exits = [
        [{"id": "exit_shared", "x": 1.0, "y": 0.0, "z": 1.0, "floor_number": 1}],
        [{"id": "exit_shared", "x": 1.0, "y": 0.0, "z": 1.0, "floor_number": 2}],
    ]
    merged = merge_exits(exits)
    assert len(merged) == 2


def test_merge_exits_dedup_same_floor():
    exits = [
        [{"id": "exit_dup", "x": 1.0, "y": 0.0, "z": 1.0, "floor_number": 1}],
        [{"id": "exit_dup", "x": 1.0, "y": 0.0, "z": 1.0, "floor_number": 1}],
    ]
    merged = merge_exits(exits)
    assert len(merged) == 1


def test_get_database_requires_client_in_production_mode():
    previous_mode = settings.APP_MODE
    previous_client = db.client
    previous_instrumented = db.instrumented
    settings.APP_MODE = "production"
    db.client = None
    db.instrumented = None
    try:
        with pytest.raises(RuntimeError):
            asyncio.run(get_database())
    finally:
        settings.APP_MODE = previous_mode
        db.client = previous_client
        db.instrumented = previous_instrumented


def test_get_database_uses_mock_in_demo_mode():
    previous_mode = settings.APP_MODE
    previous_client = db.client
    previous_instrumented = db.instrumented
    settings.APP_MODE = "demo"
    db.client = None
    db.instrumented = None
    try:
        database = asyncio.run(get_database())
        assert getattr(database, "is_mock", False) is True
    finally:
        settings.APP_MODE = previous_mode
        db.client = previous_client
        db.instrumented = previous_instrumented
