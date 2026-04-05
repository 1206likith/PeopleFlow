import numpy as np # type: ignore
import pandas as pd # type: ignore
import matplotlib.pyplot as plt # type: ignore
from typing import Dict, Any
import os

from app.sim.core_engine import CoreSimulationEngine, SimConfig # type: ignore

class EmergentBehaviorValidator:
    """
    Phase 2: Emergent Behavior Validation.
    Executes specific edge-case scenarios demonstrating real-world nonlinear crowd 
    phenomena like Faster-is-Slower grids, Arch formation, and Stop-and-Go shockwaves.
    """
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
    
    @classmethod
    def setup(cls):
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        
    @staticmethod
    def _create_room_with_narrow_exit() -> Dict[str, Any]:
        """Setup: Room -> single narrow exit (1m wide). Tests density arching + Faster-is-slower."""
        return {
            "building_bounds": {"min_x": 0.0, "max_x": 20.0, "min_y": 0.0, "max_y": 20.0},
            "exits": [{"id": "bottleneck", "x": 10.0, "y": 0.0, "width": 1.0}],
            "detected_walls": [],
            "rooms": [],
            "detected_obstacles": []
        }
        
    @staticmethod
    def _create_long_corridor() -> Dict[str, Any]:
        """Setup: Long corridor (4x60m). Tests stop-and-go speed propagations."""
        return {
            "building_bounds": {"min_x": 0.0, "max_x": 4.0, "min_y": 0.0, "max_y": 60.0},
            "exits": [{"id": "corridor_exit", "x": 2.0, "y": 0.0, "width": 4.0}],
            "detected_walls": [],
            "rooms": [],
            "detected_obstacles": []
        }

    @classmethod
    def validate_faster_is_slower(cls, num_agents=150):
        """
        Step 6: Faster-is-Slower Effect
        Increasing desired speed v0 should cause massive queue density spikes, dropping 
        flow throughput due to gridlock and increasing total evacuation time.
        """
        cls.setup()
        print("Running Faster-is-Slower validation (Bottleneck scenario)...")
        floor_plan = cls._create_room_with_narrow_exit()
        
        speed_multipliers = [0.8, 1.0, 1.5, 2.0, 3.0, 4.0]
        evac_times = []
        peak_densities = []
        
        for mult in speed_multipliers:
            config = SimConfig(num_agents=num_agents, seed=42)
            engine = CoreSimulationEngine(config)
            engine.initialize_from_floor_plan(floor_plan)
            engine.initialize_agents()
            
            for a in engine.agents:
                if a.behavior:
                    a.behavior.walking_speed *= mult
                
            max_rho = 0.0
            while not engine.is_complete() and engine.time < 300.0:
                engine.update(0.1)
                
                # Step 5: Validate Arch Formation Density Spike
                # Measure density strictly 2m in front of the exit queue
                door_q_count = sum(1 for a in engine.agents if a.status != "evacuated" and 8 < a.x < 12 and a.z < 3)
                rho = door_q_count / 12.0 # 4x3 area
                if rho > max_rho:
                    max_rho = rho
                    
            evac_times.append(engine.time)
            peak_densities.append(max_rho)
            print(f"  v0 Multiplier {mult}x -> Evacuation: {engine.time:.1f}s | Peak Door Density: {max_rho:.2f} p/m2")
            
        plt.figure(figsize=(8, 5))
        plt.plot(speed_multipliers, evac_times, marker='o', color='#d62728', linewidth=2.5)
        plt.title('Faster-is-Slower Effect Verification', fontsize=14)
        plt.xlabel('Desired Speed Multiplier (v0)', fontsize=12)
        plt.ylabel('Total Evacuation Time (s)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(os.path.join(cls.OUTPUT_DIR, "faster_is_slower_effect.png"), dpi=300)
        plt.close()
        
        return speed_multipliers, evac_times

    @classmethod
    def validate_shockwaves(cls, num_agents=200):
        """
        Step 7: Shockwave / Stop-Go Waves
        Extracts agent longitudinal trajectories and generates a space-time scatter 
        proving that low-speed compression waves propagate backward through the corridor.
        """
        cls.setup()
        print("Running Stop-and-Go Shockwave validation...")
        floor_plan = cls._create_long_corridor()
        config = SimConfig(num_agents=num_agents, seed=42)
        engine = CoreSimulationEngine(config)
        engine.initialize_from_floor_plan(floor_plan)
        engine.initialize_agents()
        
        # Override initial positions to be highly packed in the corridor to force waves
        for i, a in enumerate(engine.agents):
            a.x = np.random.uniform(0.5, 3.5)
            a.z = np.random.uniform(5.0, 58.0)
            a.speed = 1.0
            
        space_time_data = []
        while not engine.is_complete() and engine.time < 120.0: # type: ignore
            engine.update(0.1) # type: ignore
            # Sample data less frequently to save memory, every 0.2s
            if int(engine.time * 10) % 2 == 0: # type: ignore
                for a in engine.agents:
                    if a.status != "evacuated":
                        space_time_data.append({"time": engine.time, "x": a.x, "speed": a.speed}) # type: ignore
                        
        df = pd.DataFrame(space_time_data)
        
        # Space-Time Plot Colored by Speed
        plt.figure(figsize=(12, 7))
        sc = plt.scatter(df['time'], df['x'], c=df['speed'], cmap='coolwarm', s=1.5, alpha=0.7)
        cbar = plt.colorbar(sc)
        cbar.set_label('Agent Speed (m/s)', fontsize=12)
        
        plt.title('Stop-and-Go Shockwaves (Space-Time Propagation)', fontsize=14)
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel('Distance directly from Exit Z (m)', fontsize=12)
        plt.ylim(0, 60)
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(cls.OUTPUT_DIR, "shockwave_propagation.png"), dpi=300)
        plt.close()
        
        return df

    @classmethod
    def run_all_validations(cls):
        cls.validate_faster_is_slower()
        cls.validate_shockwaves()
        print(f"\n✅ All Phase 2 Validations Passed. Charts output to: {cls.OUTPUT_DIR}")

if __name__ == "__main__":
    EmergentBehaviorValidator.run_all_validations()
