"""
API endpoints for real-time metrics and KPIs
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from pydantic import BaseModel
import logging

from app.core.request_context import get_request_actor
from app.services.metrics_engine import metrics_engine

logger = logging.getLogger(__name__)

router = APIRouter()

class FrameData(BaseModel):
    """Frame data for metrics calculation"""
    timestamp: float
    agents: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]

@router.post("/frame")
async def add_metrics_frame(
    request: Request,
    frame_data: FrameData,
    current_user: dict = Depends(get_request_actor)
):
    """Add frame to metrics calculation"""
    try:
        metrics_engine.add_frame({
            "timestamp": frame_data.timestamp,
            "agents": frame_data.agents,
            "bottlenecks": frame_data.bottlenecks
        })
        return {"message": "Frame added", "frame_count": len(metrics_engine.frame_history)}
    except Exception as e:
        logger.error(f"Error adding metrics frame: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calculate")
async def get_metrics(
    request: Request,
    current_user: dict = Depends(get_request_actor)
):
    """Get comprehensive evacuation metrics"""
    try:
        metrics = metrics_engine.calculate_metrics()
        
        return {
            "time_metrics": {
                "total_evacuation_time": metrics.total_evacuation_time,
                "average_evacuation_time": metrics.average_evacuation_time,
                "median_evacuation_time": metrics.median_evacuation_time,
                "evacuation_time_distribution": metrics.evacuation_time_distribution
            },
            "flow_metrics": {
                "flow_rate_per_exit": metrics.flow_rate_per_exit,
                "total_flow_rate": metrics.total_flow_rate,
                "peak_flow_rate": metrics.peak_flow_rate,
                "flow_rate_over_time": metrics.flow_rate_over_time
            },
            "delay_metrics": {
                "delay_time_distribution": metrics.delay_time_distribution,
                "average_delay": metrics.average_delay,
                "pre_evacuation_delays": metrics.pre_evacuation_delays
            },
            "exit_utilization": {
                "utilization": metrics.exit_utilization,
                "utilization_over_time": metrics.exit_utilization_over_time,
                "load_balance": metrics.exit_load_balance
            },
            "congestion_metrics": {
                "heatmap": metrics.congestion_heatmap,
                "peak_density": metrics.peak_congestion_density,
                "congestion_duration": metrics.congestion_duration,
                "bottleneck_locations": metrics.bottleneck_locations
            },
            "density_speed_curve": metrics.density_speed_data,
            "agent_metrics": {
                "stress_distribution": metrics.agent_stress_distribution,
                "panic_distribution": metrics.agent_panic_distribution,
                "average_stress": metrics.average_stress,
                "average_panic": metrics.average_panic
            },
            "safety_metrics": {
                "casualties": metrics.casualties,
                "near_misses": metrics.near_misses,
                "safety_score": metrics.safety_score
            }
        }
    except Exception as e:
        logger.error(f"Error calculating metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_metrics(
    request: Request,
    current_user: dict = Depends(get_request_actor)
):
    """Reset metrics engine"""
    try:
        metrics_engine.frame_history = []
        metrics_engine.agent_histories = {}
        return {"message": "Metrics reset"}
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


