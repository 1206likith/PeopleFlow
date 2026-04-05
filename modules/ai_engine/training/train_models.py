"""
Main training script for all ML models
"""
import asyncio
import logging
from pathlib import Path
import sys
from datetime import datetime

# Add module roots to path for imports
AI_ENGINE_ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = AI_ENGINE_ROOT.parent
for path in (AI_ENGINE_ROOT, MODULES_DIR, AI_ENGINE_ROOT / "training"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from data_pipeline import SimulationDataPipeline
from congestion_predictor import CongestionPredictor
from exit_allocation_rl import ExitAllocationAgent
from ai_engine.registry import register_model
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def train_congestion_predictor():
    """Train congestion prediction model"""
    logger.info("Training congestion predictor...")
    
    pipeline = SimulationDataPipeline()
    
    # Load training data (in production, this would come from database)
    # For now, we'll create synthetic data
    logger.info("Generating training data...")
    
    # Generate synthetic features
    n_samples = 1000
    features = pd.DataFrame({
        'num_agents': np.random.randint(50, 500, n_samples),
        'evacuation_rate': np.random.uniform(0, 1, n_samples),
        'grid_density': np.random.uniform(0, 10, n_samples),
        'grid_max': np.random.uniform(0, 20, n_samples),
        'grid_std': np.random.uniform(0, 5, n_samples),
        'avg_speed': np.random.uniform(1, 3, n_samples),
        'bottleneck_count': np.random.randint(0, 10, n_samples),
        'floor_number': np.random.randint(1, 5, n_samples),
    })
    
    # Generate target (future congestion level)
    target = (
        features['grid_density'] * 0.3 +
        features['num_agents'] / 100 * 0.2 +
        (1 - features['evacuation_rate']) * 0.3 +
        features['bottleneck_count'] * 0.2 +
        np.random.normal(0, 0.1, n_samples)
    )
    
    # Train model
    predictor = CongestionPredictor()
    X = predictor.prepare_features(features)
    results = predictor.train(X, target.values)
    
    predictor.save_model()

    register_model(
        "congestion_predictor",
        str(predictor.model_path),
        {"trained_at": datetime.utcnow().isoformat() + "Z", "metrics": results},
    )
    
    logger.info(f"Congestion predictor trained: {results}")
    return predictor


async def train_exit_allocation_rl():
    """Train exit allocation RL agent"""
    logger.info("Training exit allocation RL agent...")
    
    # State: [num_agents_per_exit, distances, congestion_levels]
    state_size = 10  # Example: 3 exits * 3 features + 1 global
    action_size = 3  # Number of exits
    
    agent = ExitAllocationAgent(state_size, action_size)
    
    # Training loop (simplified - in production, use actual simulation)
    logger.info("Training RL agent (simplified)...")
    for episode in range(100):
        state = np.random.rand(state_size)
        total_reward = 0
        
        for step in range(50):
            action = agent.act(state, training=True)
            
            # Simulate reward (negative evacuation time)
            reward = -np.random.uniform(10, 100)  # Simplified
            
            next_state = np.random.rand(state_size)
            done = step == 49
            
            agent.remember(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward
            
            if len(agent.memory) > 32:
                agent.replay()
        
        if episode % 10 == 0:
            logger.info(f"Episode {episode}, Reward: {total_reward:.2f}, Epsilon: {agent.epsilon:.3f}")
    
    model_path = AI_ENGINE_ROOT / "data" / "saved_models" / "exit_allocation_rl.pth"
    agent.save(str(model_path))

    register_model(
        "exit_allocation_rl",
        str(model_path),
        {"trained_at": datetime.utcnow().isoformat() + "Z", "state_size": state_size, "action_size": action_size},
    )

    logger.info("Exit allocation RL agent trained")
    return agent


async def main():
    """Main training function"""
    logger.info("Starting model training pipeline...")
    
    # Create directories
    (AI_ENGINE_ROOT / "data" / "saved_models").mkdir(parents=True, exist_ok=True)
    (AI_ENGINE_ROOT / "data" / "training_logs").mkdir(parents=True, exist_ok=True)
    
    # Train models
    await train_congestion_predictor()
    await train_exit_allocation_rl()
    
    logger.info("Training complete!")


if __name__ == "__main__":
    asyncio.run(main())
