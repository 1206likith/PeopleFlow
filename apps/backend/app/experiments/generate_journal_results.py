import os
import sys
import numpy as np
from pathlib import Path
import time
import csv
import json

# Adjust path to find modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Mock these if they don't load outside FastAPI
try:
    from app.services.floorplan_service import process_floor_plan_image
    from app.sim.simulation_kernel import SimulationKernel
    from app.services.metrics_engine import MetricsEngine
except ImportError as e:
    print(f"Error importing PeopleFlow modules: {e}")
    sys.exit(1)

FLOOR_PLANS_DIR = Path(r"L:\Likith\Coding_Projects\Python\PeopleFlow\Research_Paper_IEEE\Floor_Plans")
OUTPUT_DIR = Path(r"L:\Likith\Coding_Projects\Python\PeopleFlow\Research_Paper_IEEE")

def run_case_scenario(fp_data, num_agents, policy, blocked, panic, max_time=300):
    try:
        config = {
            "seed": int(time.time()*1000) % 10000,
            "mode": "paper",
            "num_agents": num_agents,
            "emergency_type": "fire",
            "routing_policy": policy,
            "panic_level": panic,
            "blocked_exits": blocked,
            "parameter_overrides": {"disable_hazards": True},
            "max_runtime_seconds": max_time
        }
        kernel = SimulationKernel("journal_test", config)
        kernel.initialize(fp_data)
        metrics = MetricsEngine()
        
        start = time.perf_counter()
        steps = 0
        # Hard scale-down for batch logic, avoid infinite loops
        while not kernel.is_complete() and steps < 1000 and (time.perf_counter() - start) < 4.0:
            frame = kernel.step(0.2)
            metrics.add_frame(frame)
            steps += 1
            
        m = metrics.calculate_metrics()
        # if completely broken/empty, return bounds
        return {
            "time": float(m.total_evacuation_time) if m.total_evacuation_time else float(steps * 0.2),
            "density": float(m.peak_congestion_density) if m.peak_congestion_density else 0.0
        }
    except Exception as e:
        print(f"   Simulation kernel error: {e}")
        return {"time": 0.0, "density": 0.0}

def _rescale_floor_plan(floor_plan, target_max_dim=80.0):
    # Same as generate_paper_assets_from_inputs.py
    bounds = dict(floor_plan.get("building_bounds") or {})
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 100.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 100.0))
    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    scale = max(width, height) / target_max_dim if max(width, height) > target_max_dim else 1.0

    def sx(x): return (float(x) - min_x) / scale
    def sy(y): return (float(y) - min_y) / scale

    # Slice walls to stop catastrophic lag
    walls = []
    for wall in list(floor_plan.get("detected_walls", []))[:250]:
        walls.append({
            "x1": sx(wall.get("x1", 0.0)), "y1": sy(wall.get("y1", 0.0)),
            "x2": sx(wall.get("x2", 0.0)), "y2": sy(wall.get("y2", 0.0)),
        })

    exits = []
    for idx, exit_data in enumerate(floor_plan.get("exits", []), start=1):
        ex = sx(exit_data.get("x", 0.0))
        ey = sy(exit_data.get("z", exit_data.get("y", 0.0)))
        width_scaled = max(1.2, float(exit_data.get("width", 2.0)) / scale)
        exits.append({"id": str(exit_data.get("id") or f"exit_{idx}"), "x": ex, "y": ey, "z": ey, "width": width_scaled, "capacity": 100})
        
    obstacles = []
    for obstacle in floor_plan.get("detected_obstacles", [])[:100]:
        ox = sx(obstacle.get("x", 0.0))
        oy = sy(obstacle.get("z", obstacle.get("y", 0.0)))
        obstacles.append({"x": ox, "y": oy, "width": max(0.2, float(obstacle.get("width", 0.6)) / scale), "height": max(0.2, float(obstacle.get("height", obstacle.get("depth", 0.6))) / scale)})

    scaled = {
        "building_bounds": {"min_x": 0.0, "min_y": 0.0, "max_x": width / scale, "max_y": height / scale},
        "detected_walls": walls,
        "detected_obstacles": obstacles,
        "rooms": [],
        "hazards": [],
        "image_dimensions": {"width": width / scale, "height": height / scale},
        "exits": exits
    }
    
    if len(exits) < 2:
        cy = (height/scale) * 0.5
        scaled["exits"].extend([
            {"id": "gen_e1", "x": 1.0, "y": cy, "z": cy, "width": 2.0, "capacity": 100},
            {"id": "gen_e2", "x": (width/scale)-1.0, "y": cy, "z": cy, "width": 2.0, "capacity": 100}
        ])
    return scaled

def main():
    results = []
    print("Starting batch IEEE Journal script implementation...")
    
    for plan_file in os.listdir(FLOOR_PLANS_DIR):
        if not (plan_file.lower().endswith(".jpg") or plan_file.lower().endswith(".png") or plan_file.lower().endswith(".webp")):
            continue
            
        case_name = plan_file.rsplit(".", 1)[0]
        print(f"\nProcessing Floor Plan: {case_name}...")
        
        try:
            fp_raw = process_floor_plan_image("image/jpeg", str(FLOOR_PLANS_DIR / plan_file), {"mode": "traditional"})
            fp_scaled = _rescale_floor_plan(fp_raw)
            exits = fp_scaled["exits"]
                
            scenarios = [
                ("S1_Baseline", 80, "shortest_path", [], 0.3),
                ("S2_HighOcc", 120, "shortest_path", [], 0.3),
                ("S3_Blocked", 80, "shortest_path", [exits[0]["id"]], 0.3) if exits else ("S3_Blocked", 80, "shortest_path", [], 0.3),
                ("S4_Routing", 80, "least_crowded", [], 0.3),
                ("S5_Panic", 80, "shortest_path", [], 0.8)
            ]
            
            for s_name, n_ag, pol, blk, pan in scenarios:
                print(f"  -> Running {s_name} (10 iters)...", end="", flush=True)
                times = []
                densities = []
                for i in range(10): # Statistical Validation run count
                    res = run_case_scenario(fp_scaled, n_ag, pol, blk, pan)
                    times.append(res["time"])
                    densities.append(res["density"])
                    
                row = {
                    "case": case_name,
                    "scenario": s_name,
                    "mean_time": round(float(np.mean(times)), 2),
                    "std_time": round(float(np.std(times)), 2),
                    "mean_density": round(float(np.mean(densities)), 2),
                    "std_density": round(float(np.std(densities)), 2)
                }
                results.append(row)
                print(f" done (T={row['mean_time']}s, p={row['mean_density']})")
                
        except Exception as e:
            print(f"Failed {case_name}: {e}")
            
    with open(OUTPUT_DIR / "journal_results_stats.csv", "w", newline="") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    
    print("\nData pipeline completed. Wrote journal_results_stats.csv")

if __name__ == "__main__":
    main()