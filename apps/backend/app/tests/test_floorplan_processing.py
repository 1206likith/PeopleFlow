import pytest

cv2 = pytest.importorskip("cv2")
import numpy as np

from app.services.floor_plan_processor import FloorPlanProcessor
from app.services.floorplan_service import process_floor_plan_image


def _create_synthetic_floorplan(path: str) -> None:
    image = np.full((720, 960, 3), 255, dtype=np.uint8)

    # Outer boundary
    cv2.rectangle(image, (60, 60), (900, 660), (0, 0, 0), 8)

    # Interior walls (with simple door-like gaps)
    cv2.line(image, (320, 60), (320, 280), (0, 0, 0), 6)
    cv2.line(image, (320, 360), (320, 660), (0, 0, 0), 6)
    cv2.line(image, (60, 340), (420, 340), (0, 0, 0), 6)
    cv2.line(image, (500, 340), (900, 340), (0, 0, 0), 6)
    cv2.line(image, (540, 60), (540, 260), (0, 0, 0), 6)
    cv2.line(image, (540, 340), (540, 660), (0, 0, 0), 6)

    cv2.imwrite(path, image)


def test_process_floor_plan_image_uses_extension_for_generic_content_type(tmp_path):
    image_path = tmp_path / "synthetic_floorplan.png"
    _create_synthetic_floorplan(str(image_path))

    result = process_floor_plan_image(
        file_type="application/octet-stream",
        file_path=str(image_path),
        options={"use_semantic": True},
    )

    assert result.get("processed") is True
    assert int(result.get("wall_count", 0)) >= 6
    assert isinstance(result.get("boundaries"), list)
    assert result.get("building_bounds")


def test_process_floor_plan_image_retries_traditional_when_semantic_is_low_quality(monkeypatch, tmp_path):
    image_path = tmp_path / "retry_floorplan.png"
    _create_synthetic_floorplan(str(image_path))

    class StubProcessor:
        def process_floor_plan(self, image_path: str, use_semantic: bool = True, debug: bool = False, debug_dir=None):
            if use_semantic:
                return {
                    "processed": True,
                    "pipeline": "semantic",
                    "wall_count": 2,
                    "room_count": 0,
                    "exit_count": 0,
                    "quality": {"score": 0.25},
                    "walls": [],
                    "rooms": [],
                    "exits": [],
                    "pipeline_steps": [],
                }
            return {
                "processed": True,
                "pipeline": "traditional",
                "wall_count": 25,
                "room_count": 6,
                "exit_count": 3,
                "quality": {"score": 0.84},
                "walls": [{"x1": 0, "y1": 0, "x2": 20, "y2": 0}],
                "rooms": [{"x": 10, "y": 10, "width": 50, "height": 40}],
                "exits": [{"x": 5, "y": 5, "width": 10}],
                "pipeline_steps": [{"name": "traditional_mock", "duration_ms": 1}],
            }

    import app.services.floor_plan_processor as floor_plan_processor_module

    monkeypatch.setattr(floor_plan_processor_module, "floor_plan_processor", StubProcessor())

    result = process_floor_plan_image(
        file_type="image/png",
        file_path=str(image_path),
        options={"use_semantic": True},
    )

    assert result.get("processed") is True
    assert result.get("pipeline") == "traditional_retry"
    assert int(result.get("wall_count", 0)) == 25
    assert int(result.get("room_count", 0)) == 6


def test_process_floor_plan_image_auto_mode_uses_traditional_when_semantic_stack_missing(monkeypatch, tmp_path):
    image_path = tmp_path / "auto_mode_floorplan.png"
    _create_synthetic_floorplan(str(image_path))

    calls: list[bool] = []

    class StubProcessor:
        def process_floor_plan(self, image_path: str, use_semantic: bool = True, debug: bool = False, debug_dir=None):
            del image_path, debug, debug_dir
            calls.append(use_semantic)
            return {
                "processed": True,
                "pipeline": "traditional",
                "wall_count": 20,
                "room_count": 4,
                "exit_count": 2,
                "quality": {"score": 0.8, "warnings": []},
                "walls": [{"x1": 0, "y1": 0, "x2": 20, "y2": 0}],
                "rooms": [{"x": 10, "y": 10, "width": 30, "height": 30}],
                "exits": [{"id": "e1", "x": 5, "y": 5, "width": 2}],
                "pipeline_steps": [],
            }

    import app.services.floor_plan_processor as floor_plan_processor_module
    import app.services.floorplan_service as floorplan_service_module

    monkeypatch.setattr(floor_plan_processor_module, "floor_plan_processor", StubProcessor())
    monkeypatch.setattr(floorplan_service_module, "_semantic_runtime_ready", lambda: False)

    result = process_floor_plan_image(
        file_type="image/png",
        file_path=str(image_path),
        options={"mode": "auto"},
    )

    assert calls == [False]
    assert result.get("detector_mode") == "auto"
    assert result.get("fallback_reason") == "semantic_dependencies_missing"
    assert result.get("simulation_ready") is True


def test_process_floor_plan_image_auto_mode_fallback_reason_on_zero_exits(monkeypatch, tmp_path):
    image_path = tmp_path / "auto_mode_zero_exits.png"
    _create_synthetic_floorplan(str(image_path))

    class StubProcessor:
        def process_floor_plan(self, image_path: str, use_semantic: bool = True, debug: bool = False, debug_dir=None):
            del image_path, debug, debug_dir
            if use_semantic:
                return {
                    "processed": True,
                    "pipeline": "semantic",
                    "wall_count": 120,
                    "room_count": 2,
                    "exit_count": 0,
                    "quality": {"score": 0.6, "warnings": []},
                    "walls": [{"x1": 0, "y1": 0, "x2": 20, "y2": 0}],
                    "rooms": [{"x": 10, "y": 10, "width": 50, "height": 40}],
                    "exits": [],
                    "pipeline_steps": [],
                }
            return {
                "processed": True,
                "pipeline": "traditional",
                "wall_count": 35,
                "room_count": 5,
                "exit_count": 3,
                "quality": {"score": 0.86, "warnings": []},
                "walls": [{"x1": 0, "y1": 0, "x2": 20, "y2": 0}],
                "rooms": [{"x": 10, "y": 10, "width": 50, "height": 40}],
                "exits": [{"id": "exit-main", "x": 5, "y": 5, "width": 2}],
                "pipeline_steps": [{"name": "traditional_mock", "duration_ms": 1}],
            }

    import app.services.floor_plan_processor as floor_plan_processor_module
    import app.services.floorplan_service as floorplan_service_module

    monkeypatch.setattr(floor_plan_processor_module, "floor_plan_processor", StubProcessor())
    monkeypatch.setattr(floorplan_service_module, "_semantic_runtime_ready", lambda: True)

    result = process_floor_plan_image(
        file_type="image/png",
        file_path=str(image_path),
        options={"mode": "auto"},
    )

    assert result.get("pipeline") == "traditional_retry"
    assert result.get("detector_mode") == "auto"
    assert result.get("fallback_reason") == "semantic_zero_exits"
    assert result.get("simulation_ready") is True


def test_wall_stabilization_prunes_isolated_short_fragments():
    processor = FloorPlanProcessor()
    width, height = 1000, 1000
    boundaries = [
        {"x1": 50.0, "y1": 50.0, "x2": 950.0, "y2": 50.0, "length": 900.0, "type": "boundary"},
        {"x1": 950.0, "y1": 50.0, "x2": 950.0, "y2": 950.0, "length": 900.0, "type": "boundary"},
        {"x1": 950.0, "y1": 950.0, "x2": 50.0, "y2": 950.0, "length": 900.0, "type": "boundary"},
        {"x1": 50.0, "y1": 950.0, "x2": 50.0, "y2": 50.0, "length": 900.0, "type": "boundary"},
    ]
    core_walls = [
        {"x1": 200.0, "y1": 200.0, "x2": 800.0, "y2": 200.0, "length": 600.0, "type": "internal"},
        {"x1": 500.0, "y1": 200.0, "x2": 500.0, "y2": 820.0, "length": 620.0, "type": "internal"},
    ]
    noise_walls = []
    for i in range(20):
        x = 150.0 + i * 22.0
        y = 600.0 + (i % 4) * 18.0
        noise_walls.append(
            {
                "x1": x,
                "y1": y,
                "x2": x + 9.0,
                "y2": y + 1.0,
                "length": 9.06,
                "type": "internal",
            }
        )

    walls = boundaries + core_walls + noise_walls
    stabilized = processor._stabilize_walls(walls, width, height, boundaries=boundaries)

    assert len(stabilized) < len(walls)
    assert len(stabilized) <= len(boundaries) + len(core_walls) + 4
    assert sum(1 for wall in stabilized if str(wall.get("type")) == "boundary") >= 4
    assert any(float(wall.get("length", 0.0)) >= 500.0 for wall in stabilized)


def test_room_cleanup_filters_fragments_and_dedupes():
    processor = FloorPlanProcessor()
    rooms = [
        {"x": 100.0, "y": 100.0, "width": 220.0, "height": 160.0, "area": 35200.0},
        {"x": 104.0, "y": 104.0, "width": 218.0, "height": 158.0, "area": 34444.0},  # duplicate overlap
        {"x": 20.0, "y": 20.0, "width": 8.0, "height": 8.0, "area": 64.0},  # tiny fragment
        {"x": 420.0, "y": 120.0, "width": 360.0, "height": 44.0, "area": 15840.0},  # corridor
        {"x": 620.0, "y": 620.0, "width": 200.0, "height": 200.0, "area": 5200.0},  # low compactness
    ]

    cleaned = processor._cleanup_rooms(rooms, width=1000, height=1000)

    assert len(cleaned) == 2
    assert any(room.get("room_type") == "room" for room in cleaned)
    assert any(room.get("room_type") == "corridor" for room in cleaned)
