"""
Structural Graph Reconstruction
Converts blueprint into walkable geometry graph
Nodes = rooms, junctions, staircases
Edges = corridors with width, length, visibility
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    import networkx as nx
except ImportError:
    class _FallbackNetworkXNoPath(Exception):
        """Fallback no-path exception for environments without networkx."""

    class _FallbackGraph:
        def __init__(self):
            self.nodes: Dict[str, Dict] = {}
            self.adjacency: Dict[str, set[str]] = {}

        def clear(self) -> None:
            self.nodes.clear()
            self.adjacency.clear()

        def add_node(self, node_key: str, **attrs) -> None:
            self.nodes[node_key] = attrs
            self.adjacency.setdefault(node_key, set())

        def add_edge(self, u_of_edge: str, v_of_edge: str, **attrs) -> None:
            del attrs
            self.adjacency.setdefault(u_of_edge, set()).add(v_of_edge)
            self.adjacency.setdefault(v_of_edge, set()).add(u_of_edge)

    class _FallbackNxModule:
        Graph = _FallbackGraph
        NetworkXNoPath = _FallbackNetworkXNoPath

        @staticmethod
        def shortest_path(graph: _FallbackGraph, from_node_id: str, to_node_id: str) -> List[str]:
            if from_node_id not in graph.adjacency or to_node_id not in graph.adjacency:
                raise _FallbackNetworkXNoPath()
            frontier: List[Tuple[str, List[str]]] = [(from_node_id, [from_node_id])]
            visited = {from_node_id}
            while frontier:
                current, path = frontier.pop(0)
                if current == to_node_id:
                    return path
                for neighbor in graph.adjacency.get(current, set()):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    frontier.append((neighbor, path + [neighbor]))
            raise _FallbackNetworkXNoPath()

    nx = _FallbackNxModule()

logger = logging.getLogger(__name__)

@dataclass
class GraphNode:
    """Node in building graph"""
    node_id: str
    node_type: str  # room, junction, staircase, elevator, exit
    x: float
    y: float
    z: float
    area: float = 0.0
    capacity: int = 0
    metadata: Dict = None

@dataclass
class GraphEdge:
    """Edge in building graph (corridor/passage)"""
    edge_id: str
    from_node: str
    to_node: str
    width: float
    length: float
    visibility: float = 1.0  # 0-1, affected by smoke/fire
    is_stairs: bool = False
    is_door: bool = False
    door_opening_time: float = 0.0  # seconds

class BuildingGraph:
    """
    Structural graph representation of building
    Enables pathfinding and flow analysis
    """
    
    def __init__(self):
        self.graph = nx.Graph()
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self.exits: List[GraphNode] = []
        self.rooms: List[GraphNode] = []
    
    def build_from_floor_plan(
        self,
        walls: List[Dict],
        exits: List[Dict],
        obstacles: List[Dict],
        rooms: List[Dict],
        image_dimensions: Dict
    ):
        """
        Build graph from detected floor plan elements
        
        Args:
            walls: Detected walls
            exits: Detected exits
            obstacles: Detected obstacles
            rooms: Detected rooms
            image_dimensions: Image width/height
        """
        self.graph.clear()
        self.nodes.clear()
        self.edges.clear()
        self.exits.clear()
        self.rooms.clear()
        
        # Create exit nodes
        for i, exit_data in enumerate(exits):
            exit_node = GraphNode(
                node_id=f"exit_{i+1}",
                node_type="exit",
                x=exit_data.get("x", 0.0),
                y=exit_data.get("y", 0.0),
                z=exit_data.get("z", 0.0),
                capacity=exit_data.get("capacity", 100),
                metadata={
                    "width": exit_data.get("width", 2.0),
                    "flow_rate": exit_data.get("flow_rate", 1.33),
                    "is_emergency": exit_data.get("is_emergency", True)
                }
            )
            self.nodes[exit_node.node_id] = exit_node
            self.exits.append(exit_node)
            self.graph.add_node(exit_node.node_id, **exit_node.__dict__)
        
        # Create room nodes
        for i, room_data in enumerate(rooms):
            room_node = GraphNode(
                node_id=f"room_{i+1}",
                node_type="room",
                x=room_data.get("x", 0.0),
                y=room_data.get("y", 0.0),
                z=0.0,
                area=room_data.get("area", 0.0),
                capacity=int(room_data.get("area", 0.0) * 0.5),  # 0.5 persons/m²
                metadata={"name": room_data.get("name", f"Room {i+1}")}
            )
            self.nodes[room_node.node_id] = room_node
            self.rooms.append(room_node)
            self.graph.add_node(room_node.node_id, **room_node.__dict__)
        
        # Create junction nodes (wall intersections, doorways)
        junctions = self._detect_junctions(walls, exits)
        for i, (x, y) in enumerate(junctions):
            junction_node = GraphNode(
                node_id=f"junction_{i+1}",
                node_type="junction",
                x=x,
                y=y,
                z=0.0
            )
            self.nodes[junction_node.node_id] = junction_node
            self.graph.add_node(junction_node.node_id, **junction_node.__dict__)
        
        # Create edges (walkable paths)
        self._create_edges(walls, obstacles, image_dimensions)
        
        logger.info(f"Built building graph: {len(self.nodes)} nodes, {len(self.edges)} edges")
    
    def _detect_junctions(self, walls: List[Dict], exits: List[Dict]) -> List[Tuple[float, float]]:
        """Detect junction points (wall intersections, doorways)"""
        junctions = []
        
        # Add exit positions as junctions
        for exit_data in exits:
            junctions.append((exit_data.get("x", 0.0), exit_data.get("y", 0.0)))
        
        # Find wall intersections
        for i, wall1 in enumerate(walls):
            for j, wall2 in enumerate(walls[i+1:], i+1):
                intersection = self._line_intersection(
                    (wall1["x1"], wall1["y1"]), (wall1["x2"], wall1["y2"]),
                    (wall2["x1"], wall2["y1"]), (wall2["x2"], wall2["y2"])
                )
                if intersection:
                    junctions.append(intersection)
        
        # Remove duplicates (within 5 pixel tolerance)
        unique_junctions = []
        for x, y in junctions:
            is_duplicate = False
            for ux, uy in unique_junctions:
                if abs(x - ux) < 5 and abs(y - uy) < 5:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_junctions.append((x, y))
        
        return unique_junctions
    
    def _line_intersection(
        self,
        p1: Tuple[float, float], p2: Tuple[float, float],
        p3: Tuple[float, float], p4: Tuple[float, float]
    ) -> Optional[Tuple[float, float]]:
        """Find intersection point of two line segments"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None  # Parallel lines
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        if 0 <= t <= 1 and 0 <= u <= 1:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return (x, y)
        
        return None
    
    def _create_edges(self, walls: List[Dict], obstacles: List[Dict], image_dimensions: Dict):
        """Create walkable edges between nodes"""
        # Connect rooms to nearest exits via junctions
        for room_node in self.rooms:
            # Find nearest exit
            min_dist = float('inf')
            nearest_exit = None
            
            for exit_node in self.exits:
                dist = ((room_node.x - exit_node.x)**2 + (room_node.y - exit_node.y)**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest_exit = exit_node
            
            if nearest_exit:
                # Create edge (simplified - in reality would use pathfinding around walls)
                edge = GraphEdge(
                    edge_id=f"edge_{room_node.node_id}_{nearest_exit.node_id}",
                    from_node=room_node.node_id,
                    to_node=nearest_exit.node_id,
                    width=2.0,  # Default corridor width
                    length=min_dist,
                    visibility=1.0
                )
                self.edges[edge.edge_id] = edge
                self.graph.add_edge(
                    room_node.node_id,
                    nearest_exit.node_id,
                    **edge.__dict__
                )
    
    def find_path(self, from_node_id: str, to_node_id: str) -> List[str]:
        """Find shortest path between nodes"""
        try:
            path = nx.shortest_path(self.graph, from_node_id, to_node_id)
            return path
        except nx.NetworkXNoPath:
            return []
    
    def get_exit_capacity(self, exit_id: str) -> int:
        """Get capacity of an exit"""
        if exit_id in self.nodes:
            return self.nodes[exit_id].capacity
        return 100  # Default
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID"""
        return self.nodes.get(node_id)

