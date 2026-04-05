"""
ML-Agents Training Script
Trains reinforcement learning agents for evacuation behavior
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from mlagents.trainers.trainer_util import load_config
from mlagents.trainers import learn


def create_config_file(output_path: str = "config.yaml"):
    """Create default ML-Agents training configuration"""
    config_content = """
behaviors:
  CrowdAgent:
    trainer_type: ppo
    hyperparameters:
      batch_size: 1024
      buffer_size: 10240
      learning_rate: 3.0e-4
      learning_rate_schedule: linear
      beta: 5.0e-3
      epsilon: 0.2
      lambd: 0.95
      num_epoch: 3
    network_settings:
      normalize: false
      hidden_units: 128
      num_layers: 2
      vis_encode_type: simple
    reward_signals:
      extrinsic:
        gamma: 0.99
        strength: 1.0
    behavioral_cloning:
      demo_path: null
      strength: 0.0
      steps: 0
    max_steps: 500000
    time_horizon: 64
    summary_freq: 10000
    threaded: false
"""
    with open(output_path, 'w') as f:
        f.write(config_content)
    print(f"Created config file: {output_path}")


def train_agent(
    config_path: str = "config.yaml",
    run_id: str = "peopleflow-training",
    resume: bool = False,
    force: bool = False
):
    """
    Train ML-Agents model
    
    Args:
        config_path: Path to training configuration YAML
        run_id: Unique identifier for this training run
        resume: Whether to resume from previous checkpoint
        force: Whether to overwrite existing results
    """
    # Check if config exists
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        print("Creating default config...")
        create_config_file(config_path)
    
    # Prepare arguments for mlagents-learn
    args = [
        config_path,
        "--run-id", run_id,
        "--force" if force else "",
    ]
    
    if resume:
        args.append("--resume")
    
    # Filter out empty strings
    args = [arg for arg in args if arg]
    
    print(f"Starting training with config: {config_path}")
    print(f"Run ID: {run_id}")
    print("=" * 50)
    print("Press Play in Unity to start training...")
    print("=" * 50)
    
    # Start training
    # Note: This requires Unity to be running with the simulation scene
    try:
        learn.main(args)
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
    except Exception as e:
        print(f"Training error: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Train ML-Agents for PeopleFlow evacuation simulation"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to training configuration YAML file"
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default="peopleflow-training",
        help="Unique identifier for this training run"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume training from previous checkpoint"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing results"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default config file and exit"
    )
    
    args = parser.parse_args()
    
    if args.create_config:
        create_config_file(args.config)
        return
    
    train_agent(
        config_path=args.config,
        run_id=args.run_id,
        resume=args.resume,
        force=args.force
    )


if __name__ == "__main__":
    main()

