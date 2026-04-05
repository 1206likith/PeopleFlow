"""
Congestion Prediction Model
Predicts future congestion levels based on current simulation state
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CongestionPredictor:
    """Predict congestion levels in evacuation scenarios"""
    
    def __init__(self, model_path: str = None):
        base_dir = Path(__file__).resolve().parents[1]
        self.model_path = Path(model_path) if model_path else base_dir / "data" / "saved_models" / "congestion_predictor.pkl"
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'num_agents', 'evacuation_rate', 'grid_density', 'grid_max',
            'grid_std', 'avg_speed', 'bottleneck_count', 'floor_number'
        ]
    
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare features for model"""
        X = df[self.feature_columns].values
        return self.scaler.fit_transform(X)
    
    def train(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.2):
        """Train the congestion prediction model"""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Train model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        logger.info(f"Model trained - Train R^2: {train_score:.4f}, Test R^2: {test_score:.4f}")
        
        return {
            "train_score": train_score,
            "test_score": test_score,
            "feature_importance": dict(zip(self.feature_columns, self.model.feature_importances_))
        }
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict congestion levels"""
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        features_scaled = self.scaler.transform(features)
        return self.model.predict(features_scaled)
    
    def save_model(self):
        """Save trained model"""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns
        }, self.model_path)
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self):
        """Load trained model"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        
        data = joblib.load(self.model_path)
        self.model = data['model']
        self.scaler = data['scaler']
        self.feature_columns = data['feature_columns']
        logger.info(f"Model loaded from {self.model_path}")


