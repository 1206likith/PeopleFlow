from pathlib import Path

from PIL import Image


def _create_basic_image(path: Path, *, width: int = 320, height: int = 240) -> None:
    Image.new("RGB", (width, height), color="white").save(path)


def test_floor_plan_processor_returns_structured_error_when_opencv_missing(tmp_path, monkeypatch):
    from app.services.floor_plan_processor import FloorPlanProcessor
    import app.services.floor_plan_processor as floor_plan_processor_module

    image_path = tmp_path / "opencv-missing.png"
    _create_basic_image(image_path)

    monkeypatch.setattr(floor_plan_processor_module, "CV2_AVAILABLE", False)
    monkeypatch.setattr(floor_plan_processor_module, "cv2", None)

    processor = FloorPlanProcessor()
    result = processor.process_floor_plan(str(image_path), use_semantic=False)

    assert result["processed"] is False
    assert result["pipeline"] == "opencv_unavailable"
    assert result["processing_error"] == "opencv_unavailable"
    assert result["image_dimensions"] == {"width": 320, "height": 240}


def test_process_floor_plan_image_surfaces_opencv_unavailable_reason(tmp_path, monkeypatch):
    import app.services.floor_plan_processor as floor_plan_processor_module
    from app.services.floorplan_service import process_floor_plan_image

    image_path = tmp_path / "opencv-missing-service.png"
    _create_basic_image(image_path, width=640, height=480)

    monkeypatch.setattr(floor_plan_processor_module, "CV2_AVAILABLE", False)
    monkeypatch.setattr(floor_plan_processor_module, "cv2", None)

    result = process_floor_plan_image(
        file_type="image/png",
        file_path=str(image_path),
        options={"mode": "auto"},
    )

    assert result["processed"] is False
    assert result["fallback_reason"] == "opencv_unavailable"
    assert result["simulation_ready"] is False
    assert result["image_dimensions"] == {"width": 640, "height": 480}


def test_normalize_detected_obstacles_handles_ml_bbox_payloads():
    from app.services.floor_plan_document_service import normalize_detected_obstacles

    normalized = normalize_detected_obstacles(
        [
            {
                "class": "furniture",
                "confidence": 0.5,
                "bbox": [10, 20, 34, 68],
                "center": [22, 44],
                "room_type": "unknown",
            }
        ]
    )

    assert len(normalized) == 1
    assert normalized[0]["x"] == 22.0
    assert normalized[0]["z"] == 44.0
    assert normalized[0]["width"] == 24.0
    assert normalized[0]["height"] == 48.0
    assert normalized[0]["depth"] == 48.0


def test_mock_simulation_obstacle_collision_accepts_bbox_style_obstacles():
    from app.services.floor_plan_document_service import normalize_detected_obstacles
    from app.services.mock_simulation import MockSimulation

    sim = MockSimulation()
    sim.obstacles = normalize_detected_obstacles(
        [
            {
                "bbox": [12, 20, 28, 40],
                "center": [20, 30],
                "class": "furniture",
            }
        ]
    )

    assert sim._check_obstacle_collision(20.0, 30.0, agent_radius=0.1) is True
