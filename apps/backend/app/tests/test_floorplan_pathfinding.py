from app.services.floorplan_pathfinding import FloorPlanPathfinder


def test_pathfinder_dedupes_walls_and_inflates_occupancy():
    pathfinder = FloorPlanPathfinder()
    walls = [
        {"x1": 20, "y1": 10, "x2": 20, "y2": 90, "thickness": 2},
        {"x1": 20.1, "y1": 10.0, "x2": 20.0, "y2": 90.0, "thickness": 2},  # near-duplicate
    ]
    bounds = {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 100}
    pathfinder.initialize_from_floor_plan(
        walls=walls,
        obstacles=[],
        rooms=[],
        corridors=[],
        building_bounds=bounds,
        grid_resolution=1.0,
        boundaries=[],
    )

    assert len(pathfinder.walls) == 1
    assert pathfinder.is_walkable(20, 50) is False
    assert pathfinder.is_walkable(5, 5) is True


def test_pathfinder_returns_nearest_walkable_for_blocked_point():
    pathfinder = FloorPlanPathfinder()
    bounds = {"min_x": 0, "min_y": 0, "max_x": 40, "max_y": 40}
    pathfinder.initialize_from_floor_plan(
        walls=[{"x1": 5, "y1": 5, "x2": 35, "y2": 5}],
        obstacles=[{"x": 20, "y": 20, "width": 8, "height": 8}],
        rooms=[],
        corridors=[],
        building_bounds=bounds,
        grid_resolution=1.0,
        boundaries=[],
    )

    x, z = pathfinder.get_nearest_walkable(20, 20, search_radius=10.0)
    assert pathfinder.is_walkable(x, z) is True
