"""
ML Inference API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
import numpy as np
import logging
from app.core.request_context import get_request_actor
from app.services.ml_service import ml_service

logger = logging.getLogger(__name__)
router = APIRouter()


class CongestionPredictionRequest(BaseModel):
    """Request for congestion prediction"""
    num_agents: int
    evacuation_rate: float
    grid_density: float
    grid_max: float
    grid_std: float
    avg_speed: float
    bottleneck_count: int
    floor_number: int = 1


class ExitAllocationRequest(BaseModel):
    """Request for exit allocation"""
    state_vector: list  # State representation


@router.post("/predict/congestion")
async def predict_congestion(
    request: Request,
    data: CongestionPredictionRequest,
    current_user: Optional[dict] = Depends(get_request_actor)
):
    """Predict future congestion level"""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    if not ml_service.models_loaded:
        raise HTTPException(status_code=503, detail="ML models not loaded")
    
    try:
        features = data.model_dump() if hasattr(data, 'model_dump') else data.dict()
        prediction = ml_service.predict_congestion(features)
        
        if prediction is None:
            raise HTTPException(status_code=500, detail="Prediction failed")
        
        logger.info(
            f"Congestion prediction: {prediction:.4f}",
            extra={"correlation_id": correlation_id, "features": features}
        )
        
        return {
            "congestion_level": prediction,
            "interpretation": "high" if prediction > 0.7 else "medium" if prediction > 0.4 else "low"
        }
        
    except Exception as e:
        logger.error(f"Error in congestion prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/exits")
async def recommend_exits(
    request: Request,
    data: ExitAllocationRequest,
    current_user: Optional[dict] = Depends(get_request_actor)
):
    """Get exit allocation recommendation"""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    if not ml_service.models_loaded:
        raise HTTPException(status_code=503, detail="ML models not loaded")
    
    try:
        state = np.array(data.state_vector)
        exit_allocation = ml_service.allocate_exits(state)
        
        if exit_allocation is None:
            raise HTTPException(status_code=500, detail="Allocation failed")
        
        logger.info(
            f"Exit allocation: {exit_allocation}",
            extra={"correlation_id": correlation_id}
        )
        
        return {
            "recommended_exit": exit_allocation,
            "confidence": 0.85  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error in exit allocation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations")
async def get_recommendations(
    request: Request,
    simulation_state: Dict[str, Any],
    current_user: Optional[dict] = Depends(get_request_actor)
):
    """Get comprehensive ML recommendations"""
    if not ml_service.models_loaded:
        return {
            "congestion_prediction": None,
            "exit_allocation": None,
            "optimization_suggestions": ["ML models not available"]
        }
    
    try:
        recommendations = ml_service.get_recommendations(simulation_state)
        return recommendations
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}", exc_info=True)
        return {
            "congestion_prediction": None,
            "exit_allocation": None,
            "optimization_suggestions": [f"Error: {str(e)}"]
        }


