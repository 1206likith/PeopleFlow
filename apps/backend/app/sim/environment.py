"""
Environment graph wrapper for semantic floor plans.
"""
from typing import Dict


def build_environment(floor_plan_data: Dict) -> Dict:
    return {
        "walls": floor_plan_data.get("detected_walls", []),
        "exits": floor_plan_data.get("exits", []),
        "obstacles": floor_plan_data.get("detected_obstacles", []),
        "rooms": floor_plan_data.get("rooms", []),
        "corridors": floor_plan_data.get("corridors", []),
        "bounds": floor_plan_data.get("building_bounds", None),
    }
