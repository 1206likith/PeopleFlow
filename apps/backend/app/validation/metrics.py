import numpy as np
from typing import List

def compute_rmse(simulated: List[float], expected: List[float]) -> float:
    """Compute Root Mean Square Error"""
    if not simulated or not expected or len(simulated) != len(expected):
        return float('inf')
    return float(np.sqrt(np.mean((np.array(simulated) - np.array(expected))**2)))

def theoretical_flow(density: float, free_flow_speed: float = 1.35, max_density: float = 6.0) -> float:
    """Greenshields fundamental diagram theoretical flow curve"""
    if density >= max_density:
        return 0.0
    return float(density * free_flow_speed * (1.0 - density / max_density))

def compute_flow_curve_rmse(densities: List[float], flows: List[float]) -> float:
    """Compute RMSE of simulated flows vs theoretical flows based on density"""
    if not densities or not flows:
        return float('inf')
    expected_flows = [theoretical_flow(d) for d in densities]
    return compute_rmse(flows, expected_flows)

def compute_evacuation_time_error(simulated_time: float, expected_time: float) -> float:
    """Computes percentage error in evacuation time"""
    if expected_time <= 0:
        return 0.0
    return abs(simulated_time - expected_time) / expected_time

def compute_density_distribution_error(sim_densities: List[float], expected_mean: float) -> float:
    """Computes error between simulated density mean and expected mean"""
    sim_mean = float(np.mean(sim_densities)) if sim_densities else 0.0
    return abs(sim_mean - expected_mean)
