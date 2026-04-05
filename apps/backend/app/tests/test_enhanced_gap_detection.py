import numpy as np

from app.services.enhanced_gap_detection import enhanced_gap_detector


def test_parallel_wall_gap_analysis_does_not_reference_undefined_outer_state():
    wall_a = {"id": "w1", "x1": 10.0, "y1": 10.0, "x2": 10.0, "y2": 100.0}
    wall_b = {"id": "w2", "x1": 40.0, "y1": 10.0, "x2": 40.0, "y2": 100.0}
    # Wall pixels are zero, open space is 255.
    wall_mask = np.full((120, 120), 255, dtype=np.uint8)
    wall_mask[:, 10:12] = 0
    wall_mask[:, 40:42] = 0
    distance_map = enhanced_gap_detector._create_wall_distance_map(wall_mask)

    gap = enhanced_gap_detector._analyze_parallel_wall_gap(wall_a, wall_b, distance_map, wall_mask)

    # Regression check: method must not crash due to outer-state references.
    if gap is not None:
        assert isinstance(gap.gap_id, str)
        assert gap.gap_id.startswith("gap_")
        assert gap.area > 0
