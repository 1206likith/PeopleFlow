import os
import sys
import numpy as np
from pathlib import Path
import time
import csv

# Adjust path to find modules
sys.path.insert(0, 'L:/Likith/Coding_Projects/Python/PeopleFlow')

try:
    from app.services.floorplan_service import process_floor_plan_image
    from app.sim.simulation_kernel import SimulationKernel
    from app.services.metrics_engine import MetricsEngine
except ImportError as e:
    print(f"Error importing PeopleFlow modules: {e}")
    sys.exit(1)

FLOOR_PLANS_DIR = Path(r"L:\Likith\Coding_Projects\Python\PeopleFlow\Research_Paper_IEEE\Floor_Plans")
OUTPUT_DIR = Path(r"L:\Likith\Coding_Projects\Python\PeopleFlow\Research_Paper_IEEE")

def run_sim(fp_data, num_agents, policy, blocked, panic, max_time=300):
    try:
        config = {
            "seed": int(time.time()*1000) % 10000, "mode": "paper", "num_agents": num_agents,
            "emergency_type": "fire", "routing_policy": policy, "panic_level": panic,
            "blocked_exits": blocked, "parameter_overrides": {"disable_hazards": True},
            "max_runtime_seconds": max_time
        }
        kernel = SimulationKernel("ablation_test", config)
        kernel.initialize(fp_data)
        metrics_engine = MetricsEngine()
        
        start_time = time.perf_counter()
        steps = 0
        while not kernel.is_complete() and steps < 1000 and (time.perf_counter() - start_time) < 4.0:
            frame = kernel.step(0.2)
            metrics_engine.add_frame(frame)
            steps += 1
            
        m = metrics_engine.calculate_metrics()
        return {
            "time": float(m.total_evacuation_time) if m.total_evacuation_time else float(steps * 0.2),
            "density": float(m.peak_congestion_density) if m.peak_congestion_density else 0.0
        }
    except Exception as e:
        return {"time": 0.0, "density": 0.0}

def _rescale_floor_plan(floor_plan, target_max_dim=80.0):
    bounds = dict(floor_plan.get("building_bounds") or {})
    min_x, max_x = float(bounds.get("min_x", 0.0)), float(bounds.get("max_x", 100.0))
    min_y, max_y = float(bounds.get("min_y", 0.0)), float(bounds.get("max_y", 100.0))
    width, height = max(1.0, max_x - min_x), max(1.0, max_y - min_y)
    scale = max(width, height) / target_max_dim if max(width, height) > target_max_dim else 1.0
    sx = lambda x: (float(x) - min_x) / scale
    sy = lambda y: (float(y) - min_y) / scale
    walls = [{"x1": sx(w.get("x1",0)), "y1": sy(w.get("y1",0)), "x2": sx(w.get("x2",0)), "y2": sy(w.get("y2",0))} for w in list(floor_plan.get("detected_walls", []))[:250]]
    exits = [{"id": str(e.get("id") or f"e_{i}") , "x": sx(e.get("x",0)), "y": sy(e.get("z", e.get("y",0))), "z": sy(e.get("z", e.get("y",0))), "width": max(1.2, float(e.get("width",2.0))/scale), "capacity": 100} for i, e in enumerate(floor_plan.get("exits",[]))]
    if len(exits) < 2:
        cy = (height/scale) * 0.5
        exits.extend([{"id":"gen_e1", "x":1.0, "y":cy, "z":cy, "width":2.0, "capacity":100}, {"id":"gen_e2", "x":(width/scale)-1.0, "y":cy, "z":cy, "width":2.0, "capacity":100}])
    return {"building_bounds": {"min_x":0,"min_y":0,"max_x":width/scale,"max_y":height/scale}, "detected_walls": walls, "exits": exits, "detected_obstacles":[]}

def main():
    print("Starting Ablation Study simulations...")
    academic_plan_path = FLOOR_PLANS_DIR / "Academic_Plan.jpg"
    if not academic_plan_path.exists():
        print("Error: Academic_Plan.jpg not found.")
        return

    fp_raw = process_floor_plan_image("image/jpeg", str(academic_plan_path), {"mode": "traditional"})
    fp_scaled = _rescale_floor_plan(fp_raw)
    
    # Define scenarios for ablation study
    scenarios = {
        "Full Model (S4)": {"policy": "least_crowded", "panic": 0.3},
        "No Congestion Routing": {"policy": "shortest_path", "panic": 0.3},
        "No Panic Variation": {"policy": "least_crowded", "panic": 0.1},
    }
    
    results = []
    for name, params in scenarios.items():
        print(f"  -> Running: {name} (10 iters)...", end="", flush=True)
        times, densities = [], []
        for _ in range(10):
            res = run_sim(fp_scaled, num_agents=80, policy=params["policy"], blocked=[], panic=params["panic"])
            times.append(res["time"])
            densities.append(res["density"])
        
        row = {
            "Configuration": name,
            "Mean Time (s)": round(float(np.mean(times)), 2),
            "Mean Density": round(float(np.mean(densities)), 2)
        }
        results.append(row)
        print(f" done (T={row['Mean Time (s)']}s)")

    # Write results to CSV
    output_csv = OUTPUT_DIR / "ablation_study_results.csv"
    with open(output_csv, "w", newline="", encoding='utf-8') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    print(f"\nAblation study completed. Results written to {output_csv}")

if __name__ == "__main__":
    main()
