import json
import random
import numpy as np

from app.sim.simulation import SimulationEngine
from app.services.metrics_engine import MetricsEngine
from app.experiments import OUTPUT_DIR
from app.experiments.artifact_manifests import write_research_artifact_index, write_research_artifact_record
from app.experiments.metadata import build_provenance

def run_benchmark(name: str, floor_plan_data: dict, exits: list, spawn_area: tuple, num_agents: int = 50):
    print(f"Running benchmark: {name}")
    random.seed(42)
    np.random.seed(42)
    
    metrics_engine = MetricsEngine()
    sim = SimulationEngine(
        num_agents=num_agents,
        emergency_type="fire",
        seed=42,
        engine="core" # use the new physics engine
    )
    sim.initialize_from_floor_plan(floor_plan_data)
    sim.set_exits(exits)
    sim.initialize_agents()
    
    # Overwrite agent positions to spawn in the targeted area (min_x, max_x, min_y, max_y)
    agents_list = getattr(sim.sim, "agents", [])
    if type(agents_list) is dict:
        agents_list = list(agents_list.values())
        
    for agent in agents_list:
        x = np.random.uniform(spawn_area[0], spawn_area[1])
        y = np.random.uniform(spawn_area[2], spawn_area[3])
        if hasattr(agent, "position"):
            if isinstance(agent.position, np.ndarray) and len(agent.position) == 3:
                agent.position = np.array([x, y, 0.0])
            elif isinstance(agent.position, np.ndarray) and len(agent.position) == 2:
                agent.position = np.array([x, y])
            elif type(agent.position) is dict:
                agent.position["x"] = x
                agent.position["y"] = y
    
    dt = 0.1
    steps = int(120 / dt)
    
    for step in range(steps):
        sim.update(dt)
        frame = sim.get_frame()
        metrics_engine.add_frame(frame)
        if sim.is_complete():
            print(f"Simulation completed early at step {step}")
            break
            
    metrics = metrics_engine.calculate_metrics()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"benchmark_{name}.json"
    
    result = {
        "name": name,
        "metrics": metrics.__dict__ if hasattr(metrics, "__dict__") else metrics
    }
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    config_snapshot = {
        "benchmark_name": name,
        "num_agents": num_agents,
        "spawn_area": list(spawn_area),
        "exit_count": len(exits),
        "seed": 42,
    }
    provenance = build_provenance(config_snapshot).to_dict()
    provenance["benchmark_name"] = name
    write_research_artifact_record(
        output_path=OUTPUT_DIR / f"benchmark_{name}.manifest.json",
        artifact_id=f"benchmark:{name}",
        artifact_kind="benchmark",
        artifact_type="json",
        artifact_output_path=str(out_path),
        provenance=provenance,
        metadata={
            "benchmark_name": name,
            "num_agents": num_agents,
            "output_name": out_path.name,
            "metrics_summary": result["metrics"],
        },
        extra_fields={
            "manifest_version": "peopleflow-benchmark-manifest-v1",
            "benchmark_name": name,
        },
    )
    write_research_artifact_index(
        source_dir=OUTPUT_DIR,
        output_path=OUTPUT_DIR / "artifacts_index.json",
        metadata={"artifact_scope": "experiments_output"},
    )
    
    val_queue = metrics.max_queue_length if hasattr(metrics, "max_queue_length") else "N/A"
    print(f"Benchmark {name} completed! Max queue length: {val_queue}")
    return result

def run_corridor_benchmark(num_agents: int = 60):
    # 20m long, 3m wide corridor
    floor_plan_data = {
        "building_bounds": {"min_x": 0, "max_x": 20, "min_y": 0, "max_y": 3},
        "detected_walls": [
            {"id": "w1", "x1": 0, "y1": 0, "x2": 20, "y2": 0},
            {"id": "w2", "x1": 0, "y1": 3, "x2": 20, "y2": 3},
            {"id": "w3", "x1": 0, "y1": 0, "x2": 0, "y2": 3},
        ]
    }
    exits = [
        {"id": "exit1", "x": 20, "y": 1.5, "width": 1.0}
    ]
    spawn_area = (1.0, 5.0, 0.5, 2.5)
    return run_benchmark("corridor", floor_plan_data, exits, spawn_area, num_agents=num_agents)

def run_multi_exit_benchmark(num_agents: int = 80):
    # 15x15m room with two exits on opposite sides
    floor_plan_data = {
        "building_bounds": {"min_x": 0, "max_x": 15, "min_y": 0, "max_y": 15},
        "detected_walls": [
            {"id": "w1", "x1": 0, "y1": 0, "x2": 15, "y2": 0},
            {"id": "w2", "x1": 0, "y1": 15, "x2": 15, "y2": 15},
            {"id": "w3", "x1": 0, "y1": 0, "x2": 0, "y2": 15},
            {"id": "w4", "x1": 15, "y1": 0, "x2": 15, "y2": 15},
        ]
    }
    exits = [
        {"id": "exitA", "x": 15, "y": 5.0, "width": 1.5},
        {"id": "exitB", "x": 15, "y": 10.0, "width": 1.0}
    ]
    spawn_area = (2.0, 8.0, 2.0, 13.0)
    return run_benchmark("multi_exit", floor_plan_data, exits, spawn_area, num_agents=num_agents)

if __name__ == "__main__":
    run_corridor_benchmark()
    run_multi_exit_benchmark()
    print("All benchmarks finished.")
