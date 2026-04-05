from app.sim.core_engine import CoreSimulationEngine, SimConfig # type: ignore

class BenchmarkValidator:
    """
    Step 13: Dataset Benchmarking
    Verifies that native spatial capacities strictly output error variances < 15% 
    compared to the globally accepted SFPE Handbook empirical norms.
    """
    @classmethod
    def evaluate_sfpe_flow_error(cls):
        print("Running strict <15% dataset benchmark validation...")
        floor_plan = {
            "building_bounds": {"min_x": 0.0, "max_x": 10.0, "min_y": 0.0, "max_y": 10.0},
            "exits": [{"id": "bottleneck", "x": 5.0, "y": 0.0, "width": 1.0}],
            "detected_walls": [], "rooms": [], "detected_obstacles": []
        }
        
        # We spawn a huge crowd directly at a 1m exit.
        config = SimConfig(num_agents=80, seed=42, enable_hazards=False)
        engine = CoreSimulationEngine(config)
        engine.initialize_from_floor_plan(floor_plan)
        engine.initialize_agents()
        
        # Suppress artificial panic/haste that triggers Faster-is-Slower
        for a in engine.agents:
            if a.behavior:
                a.behavior.walking_speed = min(1.2, a.behavior.walking_speed)
                a.behavior.panic_level = 0.0
                
        while not engine.is_complete() and engine.time < 300.0:
            engine.update(0.1)
            
        # SFPE Standard for doors is physically limited to exactly 1.32 persons/sec/meter.
        expected_evac_time = 80 / (1.0 * 1.32)
        actual_evac_time = engine.time
        
        error_pct = abs(expected_evac_time - actual_evac_time) / expected_evac_time * 100
        
        print(f"Expected Minimum Clearance: {expected_evac_time:.1f}s")
        print(f"Simulation Clearance:       {actual_evac_time:.1f}s")
        print(f"Validation Error Variance:  {error_pct:.2f}%")
        
        if error_pct <= 15.0:
            print("✅ Status: PASSED (Error < 15% Strict Tolerance)")
        else:
            print("❌ Status: FAILED (Tolerance limits exceeded)")

if __name__ == "__main__":
    BenchmarkValidator.evaluate_sfpe_flow_error()
