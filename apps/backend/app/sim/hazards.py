"""
Hazard field wrapper.
"""
from app.services.disaster_engine import DisasterEngine


def create_hazard(emergency_type: str):
    return DisasterEngine(emergency_type)
