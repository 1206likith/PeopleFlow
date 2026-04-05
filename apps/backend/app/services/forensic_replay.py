"""
Forensic Replay & Validation Engine
Timeline scrubber, agent decision replay, density evolution, death-zone heatmaps
"""
import json
import logging
from typing import Dict, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ReplayFrame:
    """Single frame in replay timeline"""
    timestamp: float
    agents: List[Dict]
    bottlenecks: List[Dict]
    density_map: Dict
    decisions: List[Dict]
    events: List[Dict]

@dataclass
class AgentDecision:
    """Agent decision record"""
    agent_id: int
    timestamp: float
    decision_type: str  # exit_choice, route_change, panic_trigger
    old_value: any
    new_value: any
    reason: str
    context: Dict

class ForensicReplayEngine:
    """
    Forensic replay system for analyzing evacuation
    Records all decisions, events, and state changes
    """
    
    def __init__(self):
        self.replay_frames: List[ReplayFrame] = []
        self.decision_log: List[AgentDecision] = []
        self.events: List[Dict] = []
        self.density_history: List[Dict] = []
        self.death_zones: List[Dict] = []
    
    def record_frame(
        self,
        timestamp: float,
        agents: List[Dict],
        bottlenecks: List[Dict],
        density_map: Dict,
        decisions: List[Dict] = None,
        events: List[Dict] = None
    ):
        """Record a frame in the replay timeline"""
        frame = ReplayFrame(
            timestamp=timestamp,
            agents=[agent.copy() for agent in agents],
            bottlenecks=[b.copy() for b in bottlenecks],
            density_map=density_map.copy(),
            decisions=decisions or [],
            events=events or []
        )
        self.replay_frames.append(frame)
        
        # Record density history
        self.density_history.append({
            "timestamp": timestamp,
            "density_map": density_map,
            "peak_density": max(density_map.values()) if density_map else 0.0
        })
    
    def record_decision(
        self,
        agent_id: int,
        timestamp: float,
        decision_type: str,
        old_value: any,
        new_value: any,
        reason: str,
        context: Dict = None
    ):
        """Record an agent decision"""
        decision = AgentDecision(
            agent_id=agent_id,
            timestamp=timestamp,
            decision_type=decision_type,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            context=context or {}
        )
        self.decision_log.append(decision)
    
    def record_event(
        self,
        event_type: str,
        timestamp: float,
        location: Dict,
        description: str,
        severity: float = 0.0
    ):
        """Record a significant event (bottleneck formation, death, etc.)"""
        event = {
            "type": event_type,
            "timestamp": timestamp,
            "location": location,
            "description": description,
            "severity": severity
        }
        self.events.append(event)
    
    def get_timeline(self, start_time: float = 0.0, end_time: float = None) -> List[ReplayFrame]:
        """Get replay frames for a time range"""
        if end_time is None:
            end_time = float('inf')
        
        return [
            frame for frame in self.replay_frames
            if start_time <= frame.timestamp <= end_time
        ]
    
    def get_agent_timeline(self, agent_id: int) -> List[Dict]:
        """Get complete timeline for a specific agent"""
        agent_frames = []
        
        for frame in self.replay_frames:
            agent = next(
                (a for a in frame.agents if a.get("agent_id") == agent_id),
                None
            )
            if agent:
                agent_frames.append({
                    "timestamp": frame.timestamp,
                    "agent": agent,
                    "density": frame.density_map.get(f"agent_{agent_id}", 0.0),
                    "bottlenecks": [
                        b for b in frame.bottlenecks
                        if abs(b.get("x", 0) - agent.get("x", 0)) < 5 and
                        abs(b.get("z", 0) - agent.get("z", 0)) < 5
                    ]
                })
        
        return agent_frames
    
    def get_density_evolution(self) -> List[Dict]:
        """Get density evolution over time"""
        return self.density_history
    
    def get_death_zones(self) -> List[Dict]:
        """Identify death zones (high casualty areas)"""
        # Analyze density history for sustained high-density areas
        death_zones = []
        
        # Find areas with sustained high density
        for density_record in self.density_history:
            for location, density in density_record["density_map"].items():
                if density > 5.0:  # Critical density threshold
                    # Check if this location has been high-density for extended period
                    sustained = sum(
                        1 for dr in self.density_history
                        if dr["timestamp"] >= density_record["timestamp"] - 10.0 and
                        dr["density_map"].get(location, 0) > 5.0
                    )
                    
                    if sustained > 5:  # High density for >5 seconds
                        death_zones.append({
                            "location": location,
                            "peak_density": density,
                            "duration": sustained,
                            "timestamp": density_record["timestamp"]
                        })
        
        return death_zones
    
    def generate_replay_report(self) -> Dict:
        """Generate comprehensive replay report"""
        return {
            "total_frames": len(self.replay_frames),
            "total_decisions": len(self.decision_log),
            "total_events": len(self.events),
            "timeline_range": {
                "start": self.replay_frames[0].timestamp if self.replay_frames else 0.0,
                "end": self.replay_frames[-1].timestamp if self.replay_frames else 0.0
            },
            "density_evolution": self.get_density_evolution(),
            "death_zones": self.get_death_zones(),
            "key_events": sorted(self.events, key=lambda e: e["timestamp"]),
            "decision_summary": self._summarize_decisions()
        }
    
    def _summarize_decisions(self) -> Dict:
        """Summarize agent decisions"""
        decision_types = {}
        
        for decision in self.decision_log:
            decision_type = decision.decision_type
            if decision_type not in decision_types:
                decision_types[decision_type] = 0
            decision_types[decision_type] += 1
        
        return decision_types
    
    def export_replay(self, filepath: str):
        """Export replay data to JSON"""
        data = {
            "frames": [asdict(frame) for frame in self.replay_frames],
            "decisions": [asdict(decision) for decision in self.decision_log],
            "events": self.events,
            "density_history": self.density_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported replay data to {filepath}")

# Global replay engine
forensic_replay = ForensicReplayEngine()

