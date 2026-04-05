"""
API endpoints for bottleneck prediction and safety analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.core.request_context import get_request_actor
from app.services.bottleneck_predictor import bottleneck_predictor
from app.services.survival_score import survival_score_engine
from app.services.safety_blueprint import safety_blueprint_optimizer

logger = logging.getLogger(__name__)

router = APIRouter()

class PredictionRequest(BaseModel):
    """Request for bottleneck prediction"""
    agents: List[Dict[str, Any]]
    exits: List[Dict[str, Any]]
    time_horizon: float = 30.0
    disaster_origin: Optional[Dict[str, float]] = None

class SafetyAnalysisRequest(BaseModel):
    """Request for safety analysis"""
    simulation_id: str
    agents: List[Dict[str, Any]]
    exits: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    disaster_type: str = "fire"

class OptimizationRequest(BaseModel):
    """Request for building optimization"""
    exits: List[Dict[str, Any]]
    building_bounds: Dict[str, float]
    agent_positions: List[Dict[str, Any]]
    current_score: float
    budget: Optional[float] = None

@router.post("/bottlenecks")
async def predict_bottlenecks(
    request: Request,
    prediction_data: PredictionRequest,
    current_user: dict = Depends(get_request_actor)
):
    """Predict bottlenecks and congestion areas"""
    try:
        bottlenecks = bottleneck_predictor.predict_bottlenecks(
            prediction_data.agents,
            prediction_data.exits,
            prediction_data.time_horizon
        )
        
        return {
            "bottlenecks": [
                {
                    "x": b.x,
                    "y": b.y,
                    "z": b.z,
                    "severity": b.severity,
                    "density": b.density,
                    "predicted_time": b.predicted_time,
                    "risk_level": b.risk_level
                }
                for b in bottlenecks
            ]
        }
    except Exception as e:
        logger.error(f"Error predicting bottlenecks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/death-zones")
async def predict_death_zones(
    request: Request,
    prediction_data: PredictionRequest,
    current_user: dict = Depends(get_request_actor)
):
    """Predict death zones and high-risk areas"""
    try:
        disaster_origin = None
        if prediction_data.disaster_origin:
            disaster_origin = (
                prediction_data.disaster_origin.get("x", 0),
                prediction_data.disaster_origin.get("y", 0),
                prediction_data.disaster_origin.get("z", 0)
            )
        
        # Get current bottlenecks
        bottlenecks = bottleneck_predictor.predict_bottlenecks(
            prediction_data.agents,
            prediction_data.exits,
            prediction_data.time_horizon
        )
        
        death_zones = bottleneck_predictor.predict_death_zones(
            prediction_data.agents,
            prediction_data.exits,
            [{"x": b.x, "y": b.y, "z": b.z, "density": b.density} for b in bottlenecks],
            disaster_origin
        )
        
        return {
            "death_zones": [
                {
                    "x": dz.x,
                    "y": dz.y,
                    "z": dz.z,
                    "radius": dz.radius,
                    "risk_score": dz.risk_score,
                    "predicted_casualties": dz.predicted_casualties,
                    "factors": dz.factors
                }
                for dz in death_zones
            ]
        }
    except Exception as e:
        logger.error(f"Error predicting death zones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exit-collapse")
async def predict_exit_collapse(
    request: Request,
    prediction_data: PredictionRequest,
    current_user: dict = Depends(get_request_actor)
):
    """Predict exit collapse risk"""
    try:
        at_risk_exits = bottleneck_predictor.predict_exit_collapse_chain(
            prediction_data.exits,
            prediction_data.agents,
            0.0  # Current time
        )
        
        return {
            "at_risk_exits": at_risk_exits
        }
    except Exception as e:
        logger.error(f"Error predicting exit collapse: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/survival-score")
async def calculate_survival_score(
    request: Request,
    analysis_data: SafetyAnalysisRequest,
    current_user: dict = Depends(get_request_actor)
):
    """Calculate survival score for building"""
    try:
        simulation_data = {
            "total_time": 120.0,  # Would come from actual simulation
            "num_agents": len(analysis_data.agents)
        }
        
        score = survival_score_engine.calculate_score(
            simulation_data,
            analysis_data.agents,
            analysis_data.exits,
            analysis_data.bottlenecks,
            analysis_data.disaster_type
        )
        
        return {
            "total_score": score.total_score,
            "grade": score.grade,
            "component_scores": {
                "evacuation_time": score.evacuation_time_score,
                "exit_capacity": score.exit_capacity_score,
                "bottleneck": score.bottleneck_score,
                "disaster_resilience": score.disaster_resilience_score,
                "accessibility": score.accessibility_score
            },
            "factors": score.factors,
            "recommendations": score.recommendations
        }
    except Exception as e:
        logger.error(f"Error calculating survival score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize")
async def optimize_building(
    request: Request,
    optimization_data: OptimizationRequest,
    current_user: dict = Depends(get_request_actor)
):
    """Optimize building layout for safety"""
    try:
        result = safety_blueprint_optimizer.optimize_building(
            optimization_data.exits,
            optimization_data.building_bounds,
            optimization_data.agent_positions,
            optimization_data.current_score,
            optimization_data.budget
        )
        
        return {
            "original_score": result.original_score,
            "optimized_score": result.optimized_score,
            "improvement_percentage": result.improvement_percentage,
            "suggested_exits": result.suggested_exits,
            "suggested_modifications": [
                {
                    "type": m["type"],
                    "location": m["location"],
                    "description": m["description"],
                    "estimated_cost": m["estimated_cost"],
                    "survival_increase": m["survival_increase"],
                    "priority": m["priority"]
                }
                for m in result.suggested_modifications
            ],
            "estimated_cost": result.estimated_cost,
            "estimated_survival_increase": result.estimated_survival_increase
        }
    except Exception as e:
        logger.error(f"Error optimizing building: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


