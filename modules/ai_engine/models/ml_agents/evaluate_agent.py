"""
ML-Agents Evaluation Script
Evaluates trained models and generates performance metrics
"""

import argparse
import os
import json
from pathlib import Path
from typing import Dict, List, Any


def load_model_results(results_dir: str) -> Dict[str, Any]:
    """
    Load training results from ML-Agents output
    
    Args:
        results_dir: Directory containing training results
        
    Returns:
        Dictionary with training metrics
    """
    results = {
        "episodes": [],
        "mean_reward": [],
        "std_reward": [],
        "steps": [],
    }
    
    # Look for progress.json or similar files
    progress_file = os.path.join(results_dir, "progress.json")
    
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            data = json.load(f)
            # Extract relevant metrics
            if "Environment/CrowdAgent" in data:
                agent_data = data["Environment/CrowdAgent"]
                results["mean_reward"] = agent_data.get("Cumulative Reward", [])
                results["episodes"] = agent_data.get("Episode", [])
    
    return results


def evaluate_model(
    model_path: str,
    results_dir: str = None,
    num_episodes: int = 100
) -> Dict[str, Any]:
    """
    Evaluate a trained model
    
    Args:
        model_path: Path to trained model file
        results_dir: Directory with training results
        num_episodes: Number of episodes to evaluate
        
    Returns:
        Evaluation metrics
    """
    metrics = {
        "model_path": model_path,
        "num_episodes": num_episodes,
        "mean_reward": 0.0,
        "std_reward": 0.0,
        "success_rate": 0.0,
        "avg_evacuation_time": 0.0,
    }
    
    # Load training results if available
    if results_dir and os.path.exists(results_dir):
        training_results = load_model_results(results_dir)
        if training_results["mean_reward"]:
            metrics["mean_reward"] = sum(training_results["mean_reward"][-10:]) / min(10, len(training_results["mean_reward"]))
    
    # TODO: Actual evaluation requires Unity to be running
    # This is a placeholder structure
    print(f"Evaluating model: {model_path}")
    print(f"Note: Full evaluation requires Unity simulation to be running")
    print(f"Expected metrics: {metrics}")
    
    return metrics


def compare_models(model_paths: List[str], output_file: str = "model_comparison.json"):
    """
    Compare multiple trained models
    
    Args:
        model_paths: List of paths to model files
        output_file: Output file for comparison results
    """
    comparisons = []
    
    for model_path in model_paths:
        if os.path.exists(model_path):
            metrics = evaluate_model(model_path)
            comparisons.append(metrics)
        else:
            print(f"Warning: Model not found: {model_path}")
    
    # Save comparison
    with open(output_file, 'w') as f:
        json.dump(comparisons, f, indent=2)
    
    print(f"Comparison saved to: {output_file}")
    
    # Print summary
    print("\nModel Comparison Summary:")
    print("-" * 50)
    for i, comp in enumerate(comparisons, 1):
        print(f"Model {i}: {comp['model_path']}")
        print(f"  Mean Reward: {comp['mean_reward']:.2f}")
        print(f"  Success Rate: {comp['success_rate']:.2%}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate ML-Agents models for PeopleFlow"
    )
    parser.add_argument(
        "model_path",
        type=str,
        help="Path to trained model file"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        help="Directory containing training results"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=100,
        help="Number of episodes to evaluate"
    )
    parser.add_argument(
        "--compare",
        nargs="+",
        help="Compare multiple models (provide multiple paths)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_results.json",
        help="Output file for evaluation results"
    )
    
    args = parser.parse_args()
    
    if args.compare:
        compare_models(args.compare, args.output)
    else:
        metrics = evaluate_model(
            args.model_path,
            args.results_dir,
            args.episodes
        )
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"Evaluation results saved to: {args.output}")


if __name__ == "__main__":
    main()

