"""
Forensic Evacuation Replay System
Frame-by-frame replay with timeline scrubber and death analysis
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ReplayFrame:
    """Single frame in replay"""
    timestamp: float
    agents: List[Dict]
    bottlenecks: List[Dict]
    deaths: List[Dict]
    panic_events: List[Dict]
    decisions: List[Dict]

@dataclass
class AgentDeath:
    """Record of agent death"""
    agent_id: int
    timestamp: float
    location: Dict[str, float]
    cause: str  # "trampling", "smoke", "crush", "disaster"
    nearby_agents: int
    panic_level: float
    decision_history: List[Dict]

@dataclass
class PanicEvent:
    """Panic propagation event"""
    timestamp: float
    location: Dict[str, float]
    trigger: str  # "disaster", "bottleneck", "death", "rumor"
    affected_agents: List[int]
    propagation_rate: float

class ReplayEngine:
    """Manages simulation replay and forensic analysis"""
    
    def __init__(self):
        self.frames: List[ReplayFrame] = []
        self.deaths: List[AgentDeath] = []
        self.panic_events: List[PanicEvent] = []
        self.decision_audit: Dict[int, List[Dict]] = {}  # agent_id -> decisions
    
    def add_frame(
        self,
        timestamp: float,
        agents: List[Dict],
        bottlenecks: List[Dict]
    ):
        """Add a frame to replay"""
        # Detect deaths (agents that disappeared or status changed to "dead")
        deaths = self._detect_deaths(agents, timestamp)
        self.deaths.extend(deaths)
        
        # Detect panic events
        panic_events = self._detect_panic_events(agents, timestamp)
        self.panic_events.extend(panic_events)
        
        # Track decisions
        self._track_decisions(agents, timestamp)
        
        frame = ReplayFrame(
            timestamp=timestamp,
            agents=agents,
            bottlenecks=bottlenecks,
            deaths=[self._death_to_dict(d) for d in deaths],
            panic_events=[self._panic_to_dict(p) for p in panic_events],
            decisions=self._get_recent_decisions(timestamp)
        )
        
        self.frames.append(frame)
    
    def get_frame(self, timestamp: float) -> Optional[ReplayFrame]:
        """Get frame at specific timestamp"""
        for frame in self.frames:
            if abs(frame.timestamp - timestamp) < 0.1:
                return frame
        return None
    
    def get_frame_range(self, start_time: float, end_time: float) -> List[ReplayFrame]:
        """Get frames in time range"""
        return [
            f for f in self.frames
            if start_time <= f.timestamp <= end_time
        ]
    
    def get_death_replay(self, death_id: int) -> Dict:
        """Get replay of specific death"""
        death = next((d for d in self.deaths if d.agent_id == death_id), None)
        if not death:
            return {}
        
        # Get frames leading up to death
        frames_before = [
            f for f in self.frames
            if death.timestamp - 10.0 <= f.timestamp <= death.timestamp
        ]
        
        # Get agent's decision history
        decisions = self.decision_audit.get(death.agent_id, [])
        
        return {
            "death": self._death_to_dict(death),
            "frames_before": [self._frame_to_dict(f) for f in frames_before],
            "decision_history": decisions,
            "timeline": self._create_death_timeline(death, frames_before)
        }
    
    def get_panic_propagation(self) -> Dict:
        """Analyze panic propagation"""
        if not self.panic_events:
            return {"events": [], "propagation_map": {}}
        
        # Create propagation map
        propagation_map = {}
        for event in self.panic_events:
            key = f"{event.location['x']:.1f},{event.location['z']:.1f}"
            if key not in propagation_map:
                propagation_map[key] = []
            propagation_map[key].append({
                "timestamp": event.timestamp,
                "trigger": event.trigger,
                "affected_count": len(event.affected_agents),
                "propagation_rate": event.propagation_rate
            })
        
        return {
            "events": [self._panic_to_dict(e) for e in self.panic_events],
            "propagation_map": propagation_map,
            "total_events": len(self.panic_events),
            "peak_panic_time": max([e.timestamp for e in self.panic_events]) if self.panic_events else 0
        }
    
    def get_decision_audit_trail(self, agent_id: int) -> List[Dict]:
        """Get complete decision audit trail for agent"""
        return self.decision_audit.get(agent_id, [])
    
    def _detect_deaths(self, agents: List[Dict], timestamp: float) -> List[AgentDeath]:
        """Detect agent deaths in current frame"""
        deaths = []
        
        for agent in agents:
            # Check if agent died (status is "dead" or health is 0)
            if agent.get("status") == "dead" or agent.get("health", 100) <= 0:
                # Check if we already recorded this death
                existing = next(
                    (d for d in self.deaths if d.agent_id == agent.get("agent_id")),
                    None
                )
                if not existing:
                    # Determine cause
                    cause = self._determine_death_cause(agent)
                    
                    # Get nearby agents
                    nearby = self._count_nearby_agents(agents, agent)
                    
                    death = AgentDeath(
                        agent_id=agent.get("agent_id"),
                        timestamp=timestamp,
                        location={"x": agent.get("x", 0), "y": agent.get("y", 0), "z": agent.get("z", 0)},
                        cause=cause,
                        nearby_agents=nearby,
                        panic_level=agent.get("panic_level", 0),
                        decision_history=self.decision_audit.get(agent.get("agent_id"), [])
                    )
                    deaths.append(death)
        
        return deaths
    
    def _determine_death_cause(self, agent: Dict) -> str:
        """Determine cause of death"""
        # Check various factors
        if agent.get("health", 100) <= 0:
            if agent.get("smoke_exposure", 0) > 0.8:
                return "smoke"
            elif agent.get("crush_damage", 0) > 0.5:
                return "crush"
            elif agent.get("disaster_damage", 0) > 0.7:
                return "disaster"
            else:
                return "trampling"
        return "unknown"
    
    def _count_nearby_agents(self, agents: List[Dict], agent: Dict, radius: float = 5.0) -> int:
        """Count agents near given agent"""
        count = 0
        agent_pos = (agent.get("x", 0), agent.get("z", agent.get("y", 0)))
        
        for other in agents:
            if other.get("agent_id") == agent.get("agent_id"):
                continue
            other_pos = (other.get("x", 0), other.get("z", other.get("y", 0)))
            distance = ((agent_pos[0] - other_pos[0])**2 + (agent_pos[1] - other_pos[1])**2)**0.5
            if distance <= radius:
                count += 1
        
        return count
    
    def _detect_panic_events(self, agents: List[Dict], timestamp: float) -> List[PanicEvent]:
        """Detect panic propagation events"""
        events = []
        
        # Find clusters of panicked agents
        panicked_agents = [a for a in agents if a.get("panic_level", 0) > 0.7]
        
        if len(panicked_agents) > 5:
            # Group by location
            clusters = self._cluster_agents(panicked_agents, radius=10.0)
            
            for cluster in clusters:
                if len(cluster) > 5:
                    # Calculate average location
                    avg_x = sum(a.get("x", 0) for a in cluster) / len(cluster)
                    avg_z = sum(a.get("z", a.get("y", 0)) for a in cluster) / len(cluster)
                    
                    # Determine trigger
                    trigger = self._determine_panic_trigger(cluster, timestamp)
                    
                    event = PanicEvent(
                        timestamp=timestamp,
                        location={"x": avg_x, "y": 0, "z": avg_z},
                        trigger=trigger,
                        affected_agents=[a.get("agent_id") for a in cluster],
                        propagation_rate=len(cluster) / 10.0  # agents per 10 seconds
                    )
                    events.append(event)
        
        return events
    
    def _cluster_agents(self, agents: List[Dict], radius: float) -> List[List[Dict]]:
        """Cluster agents by proximity"""
        clusters = []
        used = set()
        
        for agent in agents:
            if agent.get("agent_id") in used:
                continue
            
            cluster = [agent]
            used.add(agent.get("agent_id"))
            agent_pos = (agent.get("x", 0), agent.get("z", agent.get("y", 0)))
            
            for other in agents:
                if other.get("agent_id") in used:
                    continue
                other_pos = (other.get("x", 0), other.get("z", other.get("y", 0)))
                distance = ((agent_pos[0] - other_pos[0])**2 + (agent_pos[1] - other_pos[1])**2)**0.5
                if distance <= radius:
                    cluster.append(other)
                    used.add(other.get("agent_id"))
            
            if len(cluster) > 1:
                clusters.append(cluster)
        
        return clusters
    
    def _determine_panic_trigger(self, agents: List[Dict], timestamp: float) -> str:
        """Determine what triggered panic"""
        # Check for recent deaths nearby
        recent_deaths = [
            d for d in self.deaths
            if abs(d.timestamp - timestamp) < 5.0
        ]
        if recent_deaths:
            return "death"
        
        # Check for bottlenecks
        if any(a.get("status") == "stuck" for a in agents):
            return "bottleneck"
        
        # Check for disaster proximity
        if any(a.get("disaster_proximity", 0) > 0.5 for a in agents):
            return "disaster"
        
        return "rumor"  # Default to rumor/spontaneous
    
    def _track_decisions(self, agents: List[Dict], timestamp: float):
        """Track agent decisions"""
        for agent in agents:
            agent_id = agent.get("agent_id")
            if agent_id is None:
                continue
            
            if agent_id not in self.decision_audit:
                self.decision_audit[agent_id] = []
            
            # Record decision if target exit changed
            current_exit = agent.get("target_exit")
            if self.decision_audit[agent_id]:
                last_decision = self.decision_audit[agent_id][-1]
                if last_decision.get("target_exit") != current_exit:
                    # New decision made
                    self.decision_audit[agent_id].append({
                        "timestamp": timestamp,
                        "target_exit": current_exit,
                        "location": {"x": agent.get("x", 0), "y": agent.get("y", 0), "z": agent.get("z", 0)},
                        "panic_level": agent.get("panic_level", 0),
                        "reason": "exit_change"
                    })
            else:
                # First decision
                self.decision_audit[agent_id].append({
                    "timestamp": timestamp,
                    "target_exit": current_exit,
                    "location": {"x": agent.get("x", 0), "y": agent.get("y", 0), "z": agent.get("z", 0)},
                    "panic_level": agent.get("panic_level", 0),
                    "reason": "initial"
                })
    
    def _get_recent_decisions(self, timestamp: float, window: float = 1.0) -> List[Dict]:
        """Get recent decisions across all agents"""
        decisions = []
        for agent_id, agent_decisions in self.decision_audit.items():
            recent = [
                d for d in agent_decisions
                if abs(d["timestamp"] - timestamp) <= window
            ]
            decisions.extend(recent)
        return decisions
    
    def _create_death_timeline(self, death: AgentDeath, frames: List[ReplayFrame]) -> List[Dict]:
        """Create timeline leading to death"""
        timeline = []
        
        for frame in frames:
            # Find agent in frame
            agent = next(
                (a for a in frame.agents if a.get("agent_id") == death.agent_id),
                None
            )
            if agent:
                timeline.append({
                    "timestamp": frame.timestamp,
                    "location": {"x": agent.get("x", 0), "y": agent.get("y", 0), "z": agent.get("z", 0)},
                    "health": agent.get("health", 100),
                    "panic_level": agent.get("panic_level", 0),
                    "status": agent.get("status", "moving")
                })
        
        return timeline
    
    def _death_to_dict(self, death: AgentDeath) -> Dict:
        """Convert death to dictionary"""
        return {
            "agent_id": death.agent_id,
            "timestamp": death.timestamp,
            "location": death.location,
            "cause": death.cause,
            "nearby_agents": death.nearby_agents,
            "panic_level": death.panic_level
        }
    
    def _panic_to_dict(self, panic: PanicEvent) -> Dict:
        """Convert panic event to dictionary"""
        return {
            "timestamp": panic.timestamp,
            "location": panic.location,
            "trigger": panic.trigger,
            "affected_agents": panic.affected_agents,
            "propagation_rate": panic.propagation_rate
        }
    
    def _frame_to_dict(self, frame: ReplayFrame) -> Dict:
        """Convert frame to dictionary"""
        return {
            "timestamp": frame.timestamp,
            "agent_count": len(frame.agents),
            "bottleneck_count": len(frame.bottlenecks),
            "deaths": frame.deaths,
            "panic_events": frame.panic_events
        }

# Global instance (would be per-simulation in production)
replay_engines: Dict[str, "ReplayEngine"] = {}

def get_replay_engine(simulation_id: str) -> ReplayEngine:
    """Get or create replay engine for simulation"""
    if simulation_id not in replay_engines:
        replay_engines[simulation_id] = ReplayEngine()
    return replay_engines[simulation_id]

