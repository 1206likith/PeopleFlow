"""
Real-Time Metrics & KPI Dashboard
Research-grade metrics for evacuation analysis
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import numpy as np
import math
import logging

logger = logging.getLogger(__name__)

@dataclass
class EvacuationMetrics:
    """Comprehensive evacuation metrics"""
    # Time metrics
    total_evacuation_time: float
    average_evacuation_time: float
    median_evacuation_time: float
    evacuation_time_distribution: List[float]
    
    # Flow metrics
    flow_rate_per_exit: Dict[str, float]  # exit_id -> persons/second
    total_flow_rate: float
    peak_flow_rate: float
    flow_rate_over_time: List[Dict[str, Any]]
    
    # Delay metrics
    delay_time_distribution: List[float]
    average_delay: float
    pre_evacuation_delays: List[float]
    
    # Exit utilization
    exit_utilization: Dict[str, float]  # exit_id -> utilization percentage
    exit_utilization_over_time: Dict[str, List[float]]
    exit_load_balance: float  # 0-1, higher is more balanced
    
    # Congestion metrics
    congestion_heatmap: List[Dict[str, Any]]  # Grid-based density
    peak_congestion_density: float
    congestion_duration: float
    bottleneck_locations: List[Dict[str, Any]]
    
    # Density vs Speed curves
    density_speed_data: List[Dict[str, float]]
    
    # Agent metrics
    agent_stress_distribution: List[float]
    agent_panic_distribution: List[float]
    average_stress: float
    average_panic: float
    
    # Safety metrics
    casualties: int
    near_misses: int
    safety_score: float
    survival_probability: float  # 0-1, based on hazard exposure
    
    # Research-validated KPIs
    fundamental_diagram_data: List[Dict[str, float]]  # Flow vs density (fundamental diagram)
    exit_flow_capacity_curves: Dict[str, List[Dict[str, float]]]  # Flow rate vs capacity per exit
    optimal_exit_utilization: float  # Optimal utilization metric
    congestion_pressure_map: List[Dict[str, Any]]  # Pressure-based congestion

class MetricsEngine:
    """Engine for calculating research-grade metrics"""
    
    def __init__(self):
        self.frame_history: List[Dict] = []
        self.agent_histories: Dict[int, List[Dict]] = {}
    
    def add_frame(self, frame_data: Dict):
        """Add frame to metrics calculation"""
        self.frame_history.append(frame_data)
        
        # Track individual agent histories
        for agent in frame_data.get("agents", []):
            agent_id = agent.get("agent_id")
            if agent_id not in self.agent_histories:
                self.agent_histories[agent_id] = []
            self.agent_histories[agent_id].append({
                "timestamp": frame_data.get("timestamp", 0),
                "position": (agent.get("x", 0), agent.get("y", 0), agent.get("z", 0)),
                "status": agent.get("status"),
                "panic_level": agent.get("panic_level", 0),
                "stress_level": agent.get("stress_level", 0)
            })
    
    def calculate_metrics(self) -> EvacuationMetrics:
        """Calculate comprehensive evacuation metrics"""
        if not self.frame_history:
            return self._empty_metrics()
        
        # Time metrics
        time_metrics = self._calculate_time_metrics()
        
        # Flow metrics
        flow_metrics = self._calculate_flow_metrics()
        
        # Delay metrics
        delay_metrics = self._calculate_delay_metrics()
        
        # Exit utilization
        exit_metrics = self._calculate_exit_utilization()
        
        # Congestion metrics
        congestion_metrics = self._calculate_congestion_metrics()
        
        # Density vs Speed
        density_speed = self._calculate_density_speed_curve()
        
        # Agent metrics
        agent_metrics = self._calculate_agent_metrics()
        
        # Safety metrics
        safety_metrics = self._calculate_safety_metrics()
        
        # Research-validated KPIs
        research_kpis = self._calculate_research_kpis()
        
        return EvacuationMetrics(
            **time_metrics,
            **flow_metrics,
            **delay_metrics,
            **exit_metrics,
            **congestion_metrics,
            density_speed_data=density_speed,
            **agent_metrics,
            **safety_metrics,
            **research_kpis
        )
    
    def _calculate_time_metrics(self) -> Dict:
        """Calculate evacuation time metrics"""
        evacuation_times = []
        
        for agent_id, history in self.agent_histories.items():
            # Find when agent evacuated
            for event in history:
                if event["status"] == "evacuated":
                    evacuation_times.append(event["timestamp"])
                    break
        
        if not evacuation_times:
            return {
                "total_evacuation_time": 0.0,
                "average_evacuation_time": 0.0,
                "median_evacuation_time": 0.0,
                "evacuation_time_distribution": []
            }
        
        return {
            "total_evacuation_time": max(evacuation_times),
            "average_evacuation_time": np.mean(evacuation_times),
            "median_evacuation_time": np.median(evacuation_times),
            "evacuation_time_distribution": evacuation_times
        }
    
    def _calculate_flow_metrics(self) -> Dict:
        """Calculate flow rate metrics"""
        exit_flows = {}  # exit_id -> list of flow rates over time
        flow_over_time = []
        
        for i, frame in enumerate(self.frame_history):
            timestamp = frame.get("timestamp", 0)
            
            # Calculate flow per exit (agents passing through in time window)
            if i > 0:
                prev_frame = self.frame_history[i - 1]
                dt = timestamp - prev_frame.get("timestamp", 0)
                
                if dt > 0:
                    # Count agents that evacuated in this frame
                    prev_agents = {a.get("agent_id"): a for a in prev_frame.get("agents", [])}
                    curr_agents = {a.get("agent_id"): a for a in frame.get("agents", [])}
                    
                    for agent_id, agent in curr_agents.items():
                        if agent.get("status") == "evacuated":
                            prev_agent = prev_agents.get(agent_id)
                            if prev_agent and prev_agent.get("status") != "evacuated":
                                exit_id = agent.get("target_exit", "unknown")
                                if exit_id not in exit_flows:
                                    exit_flows[exit_id] = []
                                exit_flows[exit_id].append(1.0 / dt)  # Flow rate
                    
                    # Total flow rate
                    total_flow = sum(len(flows) for flows in exit_flows.values()) / dt if dt > 0 else 0
                    flow_over_time.append({
                        "timestamp": timestamp,
                        "total_flow": total_flow,
                        "exit_flows": {k: len(v) / dt for k, v in exit_flows.items()}
                    })
        
        # Average flow per exit
        avg_flow_per_exit = {
            exit_id: np.mean(flows) if flows else 0.0
            for exit_id, flows in exit_flows.items()
        }
        
        total_flow_rates = [f["total_flow"] for f in flow_over_time if f["total_flow"] > 0]
        
        return {
            "flow_rate_per_exit": avg_flow_per_exit,
            "total_flow_rate": np.mean(total_flow_rates) if total_flow_rates else 0.0,
            "peak_flow_rate": max(total_flow_rates) if total_flow_rates else 0.0,
            "flow_rate_over_time": flow_over_time
        }
    
    def _calculate_delay_metrics(self) -> Dict:
        """Calculate delay metrics"""
        delays = []
        pre_evacuation_delays = []
        
        for agent_id, history in self.agent_histories.items():
            if len(history) < 2:
                continue
            
            # Find when agent started moving
            start_time = None
            for event in history:
                if event["status"] == "moving" and start_time is None:
                    start_time = event["timestamp"]
                    break
            
            # Find when agent evacuated
            evacuation_time = None
            for event in history:
                if event["status"] == "evacuated":
                    evacuation_time = event["timestamp"]
                    break
            
            if start_time and evacuation_time:
                delay = evacuation_time - start_time
                delays.append(delay)
            
            # Pre-evacuation delay (time before starting to move)
            if start_time:
                pre_evacuation_delays.append(start_time)
        
        return {
            "delay_time_distribution": delays,
            "average_delay": np.mean(delays) if delays else 0.0,
            "pre_evacuation_delays": pre_evacuation_delays
        }
    
    def _calculate_exit_utilization(self) -> Dict:
        """Calculate exit utilization metrics"""
        exit_utilization = {}
        exit_utilization_over_time = {}
        
        for frame in self.frame_history:
            agents = frame.get("agents", [])
            
            # Count agents per exit
            exit_counts = {}
            for agent in agents:
                if agent.get("status") != "evacuated":
                    exit_id = agent.get("target_exit")
                    if exit_id:
                        exit_counts[exit_id] = exit_counts.get(exit_id, 0) + 1
            
            # Calculate utilization (assuming capacity from exits)
            for exit_id, count in exit_counts.items():
                # Assume capacity of 100 per exit (would come from exit data)
                utilization = min(1.0, count / 100.0)
                
                if exit_id not in exit_utilization_over_time:
                    exit_utilization_over_time[exit_id] = []
                exit_utilization_over_time[exit_id].append(utilization)
        
        # Average utilization per exit
        for exit_id, utilizations in exit_utilization_over_time.items():
            exit_utilization[exit_id] = np.mean(utilizations) if utilizations else 0.0
        
        # Load balance (coefficient of variation)
        util_values = list(exit_utilization.values())
        if util_values:
            mean_util = np.mean(util_values)
            std_util = np.std(util_values)
            load_balance = 1.0 - (std_util / mean_util) if mean_util > 0 else 0.0
        else:
            load_balance = 0.0
        
        return {
            "exit_utilization": exit_utilization,
            "exit_utilization_over_time": exit_utilization_over_time,
            "exit_load_balance": max(0.0, min(1.0, load_balance))
        }
    
    def _calculate_congestion_metrics(self) -> Dict:
        """Calculate congestion metrics"""
        max_density = 0.0
        congestion_duration = 0.0
        
        # Create density grid
        grid_size = 5.0  # 5m cells
        density_grid = {}
        
        for frame in self.frame_history:
            agents = frame.get("agents", [])
            frame_density = 0.0
            
            # Count agents in each grid cell
            for agent in agents:
                if agent.get("status") != "evacuated":
                    x, z = agent.get("x", 0), agent.get("z", agent.get("y", 0))
                    cell_x = int(x / grid_size)
                    cell_z = int(z / grid_size)
                    cell_key = (cell_x, cell_z)
                    
                    density_grid[cell_key] = density_grid.get(cell_key, 0) + 1
                    frame_density = max(frame_density, density_grid[cell_key] / (grid_size ** 2))
            
            max_density = max(max_density, frame_density)
            
            if frame_density > 2.0:  # High density threshold
                congestion_duration += 0.1  # Assuming 0.1s per frame
        
        # Create heatmap
        heatmap = []
        for (cell_x, cell_z), count in density_grid.items():
            density = count / (grid_size ** 2)
            heatmap.append({
                "x": cell_x * grid_size,
                "z": cell_z * grid_size,
                "density": density
            })
        
        # Extract bottleneck locations
        bottlenecks = [
            {"x": h["x"], "z": h["z"], "density": h["density"]}
            for h in heatmap if h["density"] > 2.0
        ]
        
        return {
            "congestion_heatmap": heatmap,
            "peak_congestion_density": max_density,
            "congestion_duration": congestion_duration,
            "bottleneck_locations": bottlenecks
        }
    
    def _calculate_density_speed_curve(self) -> List[Dict[str, float]]:
        """Calculate density vs speed relationship"""
        density_speed_pairs = []
        
        for frame in self.frame_history:
            agents = frame.get("agents", [])
            if not agents:
                continue
            
            # Calculate local density for each agent
            for agent in agents:
                if agent.get("status") != "evacuated":
                    agent_pos = (agent.get("x", 0), agent.get("z", agent.get("y", 0)))
                    
                    # Count nearby agents (within 5m)
                    nearby_count = sum(
                        1 for a in agents
                        if a.get("agent_id") != agent.get("agent_id") and
                        math.sqrt(
                            (a.get("x", 0) - agent_pos[0])**2 +
                            (a.get("z", a.get("y", 0)) - agent_pos[1])**2
                        ) < 5.0
                    )
                    
                    density = nearby_count / (math.pi * 5.0 ** 2)  # persons/m²
                    speed = agent.get("speed", 1.0)
                    
                    density_speed_pairs.append({
                        "density": density,
                        "speed": speed
                    })
        
        return density_speed_pairs
    
    def _calculate_agent_metrics(self) -> Dict:
        """Calculate agent stress and panic metrics"""
        stress_levels = []
        panic_levels = []
        
        for frame in self.frame_history:
            for agent in frame.get("agents", []):
                if agent.get("status") != "evacuated":
                    stress_levels.append(agent.get("stress_level", 0))
                    panic_levels.append(agent.get("panic_level", 0))
        
        return {
            "agent_stress_distribution": stress_levels,
            "agent_panic_distribution": panic_levels,
            "average_stress": np.mean(stress_levels) if stress_levels else 0.0,
            "average_panic": np.mean(panic_levels) if panic_levels else 0.0
        }
    
    def _calculate_safety_metrics(self) -> Dict:
        """Calculate safety metrics"""
        casualties = 0
        near_misses = 0
        
        for frame in self.frame_history:
            for agent in frame.get("agents", []):
                if agent.get("status") == "dead":
                    casualties += 1
                elif agent.get("health", 100) < 50:
                    near_misses += 1
        
        # Safety score (0-100, higher is safer)
        total_agents = len(self.agent_histories)
        if total_agents > 0:
            safety_score = 100.0 * (1.0 - (casualties / total_agents))
        else:
            safety_score = 100.0
        
        return {
            "casualties": casualties,
            "near_misses": near_misses,
            "safety_score": safety_score
        }
    
    def _calculate_research_kpis(self) -> Dict:
        """
        Calculate research-validated KPIs
        - Fundamental diagram (flow vs density)
        - Exit flow capacity curves
        - Survival probability
        - Congestion pressure maps
        """
        # Fundamental diagram: flow rate vs density
        fundamental_diagram = self._calculate_fundamental_diagram()
        
        # Exit flow capacity curves
        exit_capacity_curves = self._calculate_exit_capacity_curves()
        
        # Survival probability
        survival_prob = self._calculate_survival_probability()
        
        # Congestion pressure map
        congestion_pressure = self._calculate_congestion_pressure_map()
        
        # Optimal exit utilization
        optimal_utilization = self._calculate_optimal_exit_utilization()
        
        return {
            "fundamental_diagram_data": fundamental_diagram,
            "exit_flow_capacity_curves": exit_capacity_curves,
            "survival_probability": survival_prob,
            "congestion_pressure_map": congestion_pressure,
            "optimal_exit_utilization": optimal_utilization
        }
    
    def _calculate_fundamental_diagram(self) -> List[Dict[str, float]]:
        """
        Calculate fundamental diagram: flow rate vs density
        Research: Fundamental diagrams in pedestrian dynamics (ScienceDirect)
        """
        density_flow_pairs = []
        
        for frame in self.frame_history:
            agents = frame.get("agents", [])
            if not agents:
                continue
            
            # Calculate density and flow for each region
            grid_size = 5.0
            grid_flow = {}  # (cell_x, cell_z) -> flow rate
            
            for agent in agents:
                if agent.get("status") != "evacuated":
                    x = agent.get("x", 0)
                    z = agent.get("z", agent.get("y", 0))
                    cell_x = int(x / grid_size)
                    cell_z = int(z / grid_size)
                    cell_key = (cell_x, cell_z)
                    
                    # Count agents in cell (density)
                    if cell_key not in grid_flow:
                        grid_flow[cell_key] = {"count": 0, "speed_sum": 0.0}
                    
                    grid_flow[cell_key]["count"] += 1
                    grid_flow[cell_key]["speed_sum"] += agent.get("speed", 1.0)
            
            # Calculate flow = density * speed
            for cell_key, data in grid_flow.items():
                density = data["count"] / (grid_size ** 2)  # persons/m²
                avg_speed = data["speed_sum"] / data["count"] if data["count"] > 0 else 0.0
                flow_rate = density * avg_speed  # persons/(m²·s)
                
                density_flow_pairs.append({
                    "density": density,
                    "flow_rate": flow_rate,
                    "speed": avg_speed
                })
        
        return density_flow_pairs
    
    def _calculate_exit_capacity_curves(self) -> Dict[str, List[Dict[str, float]]]:
        """
        Calculate flow rate per exit vs capacity curves
        Research: Exit flow capacity studies (ScienceDirect)
        """
        exit_curves = {}
        
        for frame in self.frame_history:
            agents = frame.get("agents", [])
            exits = frame.get("exits", [])
            
            for exit in exits:
                exit_id = exit.get("id")
                exit_width = exit.get("width", 2.0)
                
                # Count agents at exit
                agents_at_exit = sum(
                    1 for agent in agents
                    if agent.get("target_exit") == exit_id and
                    agent.get("status") != "evacuated"
                )
                
                # Calculate utilization
                flow_capacity = 1.33 * exit_width  # persons/second (research-validated)
                utilization = min(1.0, agents_at_exit / (flow_capacity * 10))  # 10s window
                
                if exit_id not in exit_curves:
                    exit_curves[exit_id] = []
                
                exit_curves[exit_id].append({
                    "utilization": utilization,
                    "flow_rate": agents_at_exit / 10.0 if agents_at_exit > 0 else 0.0,
                    "capacity": flow_capacity,
                    "actual_flow": agents_at_exit / 10.0
                })
        
        return exit_curves
    
    def _calculate_survival_probability(self) -> float:
        """
        Calculate survival probability based on hazard exposure
        Research: Survival probability models
        """
        total_agents = len(self.agent_histories)
        if total_agents == 0:
            return 1.0
        
        survived = 0
        for agent_id, history in self.agent_histories.items():
            # Check if agent survived (evacuated without death)
            for event in reversed(history):
                if event.get("status") == "evacuated":
                    survived += 1
                    break
                elif event.get("status") == "dead":
                    break
        
        return survived / total_agents if total_agents > 0 else 1.0
    
    def _calculate_congestion_pressure_map(self) -> List[Dict[str, Any]]:
        """
        Calculate congestion pressure map
        Pressure = density * velocity gradient (research metric)
        """
        pressure_map = []
        grid_size = 5.0
        
        for frame in self.frame_history:
            agents = frame.get("agents", [])
            if not agents:
                continue
            
            # Create density and velocity grid
            grid_data = {}  # (cell_x, cell_z) -> {density, velocities}
            
            for agent in agents:
                if agent.get("status") != "evacuated":
                    x = agent.get("x", 0)
                    z = agent.get("z", agent.get("y", 0))
                    cell_x = int(x / grid_size)
                    cell_z = int(z / grid_size)
                    cell_key = (cell_x, cell_z)
                    
                    if cell_key not in grid_data:
                        grid_data[cell_key] = {"count": 0, "velocities": []}
                    
                    grid_data[cell_key]["count"] += 1
                    speed = agent.get("speed", 1.0)
                    grid_data[cell_key]["velocities"].append(speed)
            
            # Calculate pressure for each cell
            for cell_key, data in grid_data.items():
                density = data["count"] / (grid_size ** 2)
                avg_velocity = np.mean(data["velocities"]) if data["velocities"] else 0.0
                
                # Pressure = density * (desired_velocity - actual_velocity)
                desired_velocity = 1.35  # m/s (research average)
                velocity_deficit = max(0.0, desired_velocity - avg_velocity)
                pressure = density * velocity_deficit
                
                pressure_map.append({
                    "x": cell_key[0] * grid_size,
                    "z": cell_key[1] * grid_size,
                    "pressure": pressure,
                    "density": density,
                    "velocity": avg_velocity
                })
        
        return pressure_map
    
    def _calculate_optimal_exit_utilization(self) -> float:
        """
        Calculate optimal exit utilization metric
        Optimal = balanced utilization across all exits
        """
        exit_utilizations = []
        
        for frame in self.frame_history:
            agents = frame.get("agents", [])
            exits = frame.get("exits", [])
            
            for exit in exits:
                exit_id = exit.get("id")
                exit_width = exit.get("width", 2.0)
                
                agents_at_exit = sum(
                    1 for agent in agents
                    if agent.get("target_exit") == exit_id
                )
                
                flow_capacity = 1.33 * exit_width
                utilization = min(1.0, agents_at_exit / (flow_capacity * 10))
                exit_utilizations.append(utilization)
        
        if not exit_utilizations:
            return 0.0
        
        # Optimal utilization = mean utilization (balanced)
        # Penalty for high variance (unbalanced)
        mean_util = np.mean(exit_utilizations)
        std_util = np.std(exit_utilizations)
        
        # Optimal is high mean with low variance
        optimal_score = mean_util * (1.0 - std_util)
        
        return max(0.0, min(1.0, optimal_score))
    
    def _empty_metrics(self) -> EvacuationMetrics:
        """Return empty metrics structure"""
        return EvacuationMetrics(
            total_evacuation_time=0.0,
            average_evacuation_time=0.0,
            median_evacuation_time=0.0,
            evacuation_time_distribution=[],
            flow_rate_per_exit={},
            total_flow_rate=0.0,
            peak_flow_rate=0.0,
            flow_rate_over_time=[],
            delay_time_distribution=[],
            average_delay=0.0,
            pre_evacuation_delays=[],
            exit_utilization={},
            exit_utilization_over_time={},
            exit_load_balance=0.0,
            congestion_heatmap=[],
            peak_congestion_density=0.0,
            congestion_duration=0.0,
            bottleneck_locations=[],
            density_speed_data=[],
            agent_stress_distribution=[],
            agent_panic_distribution=[],
            average_stress=0.0,
            average_panic=0.0,
            casualties=0,
            near_misses=0,
            safety_score=100.0,
            survival_probability=1.0,
            fundamental_diagram_data=[],
            exit_flow_capacity_curves={},
            optimal_exit_utilization=0.0,
            congestion_pressure_map=[]
        )

# Global instance
metrics_engine = MetricsEngine()

