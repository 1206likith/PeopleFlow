import optuna
from typing import Dict, Any
from app.sim.core_engine import CoreSimulationEngine, SimConfig

class OptunaCalibrationEngine:
    """
    Phase 1: Scientfic Calibration Layer
    Auto-tunes base mathematical traits using Optuna to minimize residual errors 
    against known literature standards (e.g. SFPE maximum specific flow rates).
    """

    @staticmethod
    def objective(trial: optuna.Trial, floor_plan: Dict[str, Any]) -> float:
        # Tuning mathematical behavioral vectors
        speed_scaler = trial.suggest_float('speed_scaler', 0.8, 1.3)
        panic_factor = trial.suggest_float('panic_factor', 0.2, 1.0)
        
        config = SimConfig(num_agents=100, routing_policy="nearest", seed=42)
        engine = CoreSimulationEngine(config)
        engine.initialize_from_floor_plan(floor_plan)
        engine.initialize_agents()
        
        # Override agents with suggested baseline multipliers
        for agent in engine.agents:
            if agent.behavior:
                agent.behavior.walking_speed *= speed_scaler
                agent.behavior.panic_level *= panic_factor
            
        while not engine.is_complete() and engine.time < 300.0:
            engine.update(0.1)
            
        # Evaluate optimization function: Distance to SFPE typical max flow (1.32 per meter)
        exit_width = sum([e.get("width", 2.0) for e in engine.exits]) if engine.exits else 2.0
        target_flow_rate = 1.32 * exit_width
        
        actual_flow_rate = (100 / engine.time) if engine.time > 0 else 0
        
        # RMSE objective
        return abs(target_flow_rate - actual_flow_rate)

    @staticmethod
    def run_calibration(floor_plan: Dict[str, Any], n_trials: int = 15) -> Dict[str, float]:
        print(f"Starting auto-tune calibration... Budget={n_trials} trials")
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="minimize")
        study.optimize(lambda trial: OptunaCalibrationEngine.objective(trial, floor_plan), n_trials=n_trials)
        
        print("\n=== Best Calibrated Parameters ===")
        for key, val in study.best_params.items():
            print(f"  {key}: {val:.3f}")
            
        return study.best_params

if __name__ == "__main__":
    dummy_floor_plan = {
        "building_bounds": {"min_x": 0.0, "max_x": 100.0, "min_y": 0.0, "max_y": 100.0},
        "exits": [{"id": "main_exit", "x": 50, "y": 0, "width": 4.0}],
        "detected_walls": [],
        "rooms": [],
        "detected_obstacles": []
    }
    OptunaCalibrationEngine.run_calibration(dummy_floor_plan, n_trials=5)
