"""
Movement model wrapper (SFM + kinematics).
"""
from app.services.social_force_model import social_force_model


def compute_forces(agent, neighbors, exits, obstacles):
    return social_force_model.compute_forces(agent, neighbors, exits, obstacles)
