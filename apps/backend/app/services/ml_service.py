"""
ML Model Serving Service
Loads and serves ML models for real-time inference
"""
import numpy as np
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import settings

from ai_engine.registry import get_model

logger = logging.getLogger(__name__)


class MLService:
    """Service for ML model inference"""
    
    def __init__(self):
        self.congestion_model = None
        self.exit_allocation_model = None
        self.models_loaded = False
    
    def _resolve_model_path(self, name: str, fallback: str) -> Path:
        entry = get_model(name)
        if entry and entry.get("path"):
            return Path(entry["path"])
        return Path(fallback)

    def load_models(self):
        """Load ML models"""
        try:
            # Load congestion predictor
            try:
                from ai_engine.training.congestion_predictor import CongestionPredictor
                model_path = self._resolve_model_path(
                    "congestion_predictor",
                    settings.AI_CONGESTION_MODEL_PATH,
                )
                self.congestion_model = CongestionPredictor(model_path=str(model_path))
                if self.congestion_model.model_path.exists():
                    self.congestion_model.load_model()
                    logger.info("Congestion predictor loaded")
                else:
                    logger.warning("Congestion predictor model file not found. Train model first.")
            except ImportError as e:
                logger.warning(f"Could not import congestion predictor: {e}")
            except Exception as e:
                logger.warning(f"Could not load congestion predictor: {e}")
            
            # Load exit allocation RL
            try:
                from ai_engine.training.exit_allocation_rl import ExitAllocationAgent
                model_path = self._resolve_model_path(
                    "exit_allocation_rl",
                    settings.AI_EXIT_RL_MODEL_PATH,
                )
                if model_path.exists():
                    self.exit_allocation_model = ExitAllocationAgent(state_size=10, action_size=3)
                    self.exit_allocation_model.load(str(model_path))
                    logger.info("Exit allocation RL agent loaded")
                else:
                    logger.warning("Exit allocation RL model file not found. Train model first.")
            except ImportError as e:
                logger.warning(f"Could not import exit allocation RL: {e}")
            except Exception as e:
                logger.warning(f"Could not load exit allocation RL: {e}")
            
            # Mark as loaded if at least one model loaded
            self.models_loaded = self.congestion_model is not None or self.exit_allocation_model is not None
            
        except Exception as e:
            logger.error(f"Error loading ML models: {e}", exc_info=True)
            self.models_loaded = False
    
    def predict_congestion(self, features: Dict[str, Any]) -> Optional[float]:
        """Predict future congestion level"""
        if not self.congestion_model:
            return None
        
        try:
            # Prepare features
            feature_df = pd.DataFrame([features])
            X = self.congestion_model.prepare_features(feature_df)
            prediction = self.congestion_model.predict(X)[0]
            return float(prediction)
        except Exception as e:
            logger.error(f"Error predicting congestion: {e}")
            return None
    
    def allocate_exits(self, state: np.ndarray) -> Optional[int]:
        """Get optimal exit allocation using RL"""
        if not self.exit_allocation_model:
            return None
        
        try:
            action = self.exit_allocation_model.act(state, training=False)
            return int(action)
        except Exception as e:
            logger.error(f"Error allocating exits: {e}")
            return None
    
    def get_recommendations(self, simulation_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get ML-based recommendations for simulation"""
        recommendations = {
            "congestion_prediction": None,
            "exit_allocation": None,
            "optimization_suggestions": []
        }
        
        # Predict congestion
        if "features" in simulation_state:
            congestion = self.predict_congestion(simulation_state["features"])
            recommendations["congestion_prediction"] = congestion
            
            if congestion and congestion > 0.7:
                recommendations["optimization_suggestions"].append(
                    "High congestion predicted. Consider opening additional exits."
                )
        
        # Get exit allocation
        if "state_vector" in simulation_state:
            exit_action = self.allocate_exits(np.array(simulation_state["state_vector"]))
            recommendations["exit_allocation"] = exit_action
        
        return recommendations


# Global instance
ml_service = MLService()
