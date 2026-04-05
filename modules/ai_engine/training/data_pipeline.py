"""
Production-grade data pipeline for AI/ML training
Extracts, transforms, and loads simulation data for model training
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Ensure parquet support
try:
    import pyarrow
except ImportError:
    logger.warning("pyarrow not installed. Parquet support unavailable. Install with: pip install pyarrow")


class SimulationDataPipeline:
    """Extract and transform simulation data for ML training"""
    
    def __init__(self, data_dir: str = None):
        base_dir = Path(__file__).resolve().parents[1]
        self.data_dir = Path(data_dir) if data_dir else base_dir / "data" / "simulation_runs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_simulation_data(self, simulation_id: str, db_collection) -> pd.DataFrame:
        """Extract all frames for a simulation"""
        frames = []
        
        try:
            cursor = db_collection.find({"simulation_id": simulation_id}).sort("timestamp", 1)
            
            for frame in cursor:
                frames.append({
                    "simulation_id": simulation_id,
                    "timestamp": frame.get("timestamp", 0),
                    "floor_number": frame.get("floor_number", 1),
                    "num_agents": len(frame.get("agents", [])),
                    "num_evacuated": sum(1 for a in frame.get("agents", []) if a.get("status") == "evacuated"),
                    "num_bottlenecks": len(frame.get("bottlenecks", [])),
                    "agents": frame.get("agents", []),
                    "bottlenecks": frame.get("bottlenecks", []),
                })
            
            return pd.DataFrame(frames)
            
        except Exception as e:
            logger.error(f"Error extracting simulation data: {e}")
            return pd.DataFrame()
    
    def create_occupancy_grid(self, agents: List[Dict], grid_size: float = 5.0, 
                              bounds: Dict[str, float] = None) -> np.ndarray:
        """Create occupancy grid from agent positions"""
        if not agents:
            return np.zeros((10, 10))
        
        # Determine bounds
        if bounds is None:
            xs = [a.get("x", 0) for a in agents]
            zs = [a.get("z", 0) for a in agents]
            bounds = {
                "min_x": min(xs) if xs else -50,
                "max_x": max(xs) if xs else 50,
                "min_z": min(zs) if zs else -50,
                "max_z": max(zs) if zs else 50,
            }
        
        # Create grid
        width = int((bounds["max_x"] - bounds["min_x"]) / grid_size) + 1
        height = int((bounds["max_z"] - bounds["min_z"]) / grid_size) + 1
        grid = np.zeros((height, width))
        
        # Populate grid
        for agent in agents:
            if agent.get("status") != "evacuated":
                x_idx = int((agent.get("x", 0) - bounds["min_x"]) / grid_size)
                z_idx = int((agent.get("z", 0) - bounds["min_z"]) / grid_size)
                if 0 <= x_idx < width and 0 <= z_idx < height:
                    grid[z_idx, x_idx] += 1
        
        return grid
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract ML features from simulation data"""
        features = []
        
        for idx, row in df.iterrows():
            agents = row.get("agents", [])
            bottlenecks = row.get("bottlenecks", [])
            
            # Occupancy grid features
            occupancy_grid = self.create_occupancy_grid(agents)
            grid_density = np.mean(occupancy_grid)
            grid_max = np.max(occupancy_grid)
            grid_std = np.std(occupancy_grid)
            
            # Agent features
            agent_speeds = [a.get("speed", 0) for a in agents if a.get("status") != "evacuated"]
            avg_speed = np.mean(agent_speeds) if agent_speeds else 0
            max_speed = np.max(agent_speeds) if agent_speeds else 0
            
            # Flow features
            evacuation_rate = row.get("num_evacuated", 0) / max(row.get("num_agents", 1), 1)
            bottleneck_density = len(bottlenecks)
            
            # Time features
            elapsed_time = row.get("timestamp", 0)
            
            features.append({
                "timestamp": elapsed_time,
                "num_agents": row.get("num_agents", 0),
                "num_evacuated": row.get("num_evacuated", 0),
                "evacuation_rate": evacuation_rate,
                "grid_density": grid_density,
                "grid_max": grid_max,
                "grid_std": grid_std,
                "avg_speed": avg_speed,
                "max_speed": max_speed,
                "bottleneck_count": bottleneck_density,
                "floor_number": row.get("floor_number", 1),
            })
        
        return pd.DataFrame(features)
    
    def save_training_data(self, df: pd.DataFrame, filename: str):
        """Save processed data for training"""
        filepath = self.data_dir / filename
        df.to_parquet(filepath, compression='snappy')
        logger.info(f"Saved training data to {filepath}")
    
    def load_training_data(self, filename: str) -> pd.DataFrame:
        """Load processed training data"""
        filepath = self.data_dir / filename
        return pd.read_parquet(filepath)

