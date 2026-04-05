"""
Enhanced Gap Detection with Improved Algorithms
Better wall-to-wall gap analysis, door detection, and corridor identification
"""

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
import numpy as np
import math
import hashlib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

from scipy import ndimage

logger = logging.getLogger(__name__)

@dataclass
class GapAnalysis:
    """Detailed gap analysis result"""
    gap_id: str
    position: Tuple[float, float]
    width: float
    height: float
    area: float
    gap_type: str  # "door", "corridor", "opening", "window"
    confidence: float
    connected_walls: List[str]
    walkable: bool
    door_swing_direction: Optional[str] = None

class EnhancedGapDetector:
    """
    Enhanced gap detection with improved wall-to-wall analysis
    """
    
    def __init__(self):
        self.min_gap_area = 50
        self.max_gap_area = 10000
        self.door_width_range = (50, 2000)
        self.corridor_min_length = 200
        self.wall_proximity_threshold = 20
    
    def analyze_wall_to_wall_gaps(
        self,
        walls: List[Dict],
        wall_mask: np.ndarray
    ) -> List[GapAnalysis]:
        """
        Analyze gaps between walls with improved algorithm
        
        Uses:
        - Wall proximity analysis
        - Perpendicular distance calculation
        - Gap classification based on geometry
        """
        gaps = []
        
        # Create wall distance map
        wall_distance_map = self._create_wall_distance_map(wall_mask)
        
        # Find gaps between parallel walls
        for i, wall1 in enumerate(walls):
            for wall2 in walls[i+1:]:
                if self._are_walls_parallel(wall1, wall2):
                    gap = self._analyze_parallel_wall_gap(
                        wall1, wall2, wall_distance_map, wall_mask
                    )
                    if gap:
                        gaps.append(gap)
        
        # Find gaps in wall lines (openings)
        line_gaps = self._find_line_gaps(walls, wall_mask)
        gaps.extend(line_gaps)
        
        # Classify and validate gaps
        classified_gaps = self._classify_gaps(gaps, walls)
        
        return classified_gaps
    
    def _create_wall_distance_map(self, wall_mask: np.ndarray) -> np.ndarray:
        """Create distance map from walls"""
        mask = np.asarray(wall_mask)
        if mask.size == 0:
            return np.zeros_like(mask, dtype=np.float32)

        non_zero_count = int(np.count_nonzero(mask))
        zero_count = int(mask.size - non_zero_count)

        # Support both conventions used across the codebase:
        # walls=255/open=0 and walls=0/open=255.
        if non_zero_count <= zero_count:
            open_space = (mask == 0)
        else:
            open_space = (mask != 0)

        if CV2_AVAILABLE and cv2 is not None:
            open_mask = (open_space.astype(np.uint8) * 255)
            return cv2.distanceTransform(open_mask, cv2.DIST_L2, 5)

        return ndimage.distance_transform_edt(open_space).astype(np.float32)
    
    def _are_walls_parallel(
        self,
        wall1: Dict,
        wall2: Dict,
        angle_threshold: float = 0.1
    ) -> bool:
        """Check if two walls are parallel"""
        dx1 = wall1["x2"] - wall1["x1"]
        dy1 = wall1["y2"] - wall1["y1"]
        dx2 = wall2["x2"] - wall2["x1"]
        dy2 = wall2["y2"] - wall2["y1"]
        
        angle1 = math.atan2(dy1, dx1)
        angle2 = math.atan2(dy2, dx2)
        
        angle_diff = abs(angle1 - angle2)
        return (angle_diff < angle_threshold or 
                abs(angle_diff - math.pi) < angle_threshold)
    
    def _analyze_parallel_wall_gap(
        self,
        wall1: Dict,
        wall2: Dict,
        distance_map: np.ndarray,
        wall_mask: np.ndarray
    ) -> Optional[GapAnalysis]:
        """Analyze gap between two parallel walls"""
        # Calculate perpendicular distance between walls
        # Get midpoint of wall1
        mid1_x = (wall1["x1"] + wall1["x2"]) / 2
        mid1_y = (wall1["y1"] + wall1["y2"]) / 2
        
        # Get midpoint of wall2
        mid2_x = (wall2["x1"] + wall2["x2"]) / 2
        mid2_y = (wall2["y1"] + wall2["y2"]) / 2
        
        # Distance between midpoints
        distance = math.sqrt((mid2_x - mid1_x)**2 + (mid2_y - mid1_y)**2)
        
        # Check if distance is reasonable for a gap
        if not (20 < distance < 500):
            return None
        
        # Check if gap is actually open (not blocked)
        gap_center_x = int((mid1_x + mid2_x) / 2)
        gap_center_y = int((mid1_y + mid2_y) / 2)
        
        if (0 <= gap_center_y < distance_map.shape[0] and
            0 <= gap_center_x < distance_map.shape[1]):
            gap_distance = distance_map[gap_center_y, gap_center_x]
            
            # Gap exists if distance is significant
            if gap_distance > 10:
                # Estimate gap dimensions
                wall_length = math.sqrt(
                    (wall1["x2"] - wall1["x1"])**2 + 
                    (wall1["y2"] - wall1["y1"])**2
                )
                
                gap_width = distance
                gap_length = min(wall_length, 200)  # Typical door/corridor length
                
                return GapAnalysis(
                    gap_id=self._build_parallel_gap_id(wall1, wall2, gap_center_x, gap_center_y),
                    position=(gap_center_x, gap_center_y),
                    width=gap_width,
                    height=gap_length,
                    area=gap_width * gap_length,
                    gap_type="unknown",  # Will be classified later
                    confidence=0.7,
                    connected_walls=[f"wall_{wall1.get('id', '')}", f"wall_{wall2.get('id', '')}"],
                    walkable=True
                )
        
        return None

    def _build_parallel_gap_id(
        self,
        wall1: Dict,
        wall2: Dict,
        center_x: float,
        center_y: float,
    ) -> str:
        """
        Build deterministic gap IDs without relying on outer mutable state.
        """
        wall1_sig = (
            wall1.get("id"),
            round(float(wall1.get("x1", 0.0)), 2),
            round(float(wall1.get("y1", 0.0)), 2),
            round(float(wall1.get("x2", 0.0)), 2),
            round(float(wall1.get("y2", 0.0)), 2),
        )
        wall2_sig = (
            wall2.get("id"),
            round(float(wall2.get("x1", 0.0)), 2),
            round(float(wall2.get("y1", 0.0)), 2),
            round(float(wall2.get("x2", 0.0)), 2),
            round(float(wall2.get("y2", 0.0)), 2),
        )
        payload = f"{wall1_sig}|{wall2_sig}|{round(center_x, 2)}|{round(center_y, 2)}"
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
        return f"gap_{digest}"
    
    def _find_line_gaps(
        self,
        walls: List[Dict],
        wall_mask: np.ndarray
    ) -> List[GapAnalysis]:
        """Find gaps in wall lines (openings)"""
        if not CV2_AVAILABLE or cv2 is None:
            return []

        gaps = []
        
        # Dilate walls to find where they should connect
        dilated = cv2.dilate(wall_mask, np.ones((15, 15), np.uint8), iterations=1)
        
        # Find gaps (areas that should be walls but aren't)
        gap_mask = cv2.bitwise_and(dilated, cv2.bitwise_not(wall_mask))
        
        # Find contours of gaps
        contours, _ = cv2.findContours(gap_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if self.min_gap_area < area < self.max_gap_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Find nearest walls
                nearest_walls = self._find_nearest_walls((x + w/2, y + h/2), walls)
                
                gaps.append(GapAnalysis(
                    gap_id=f"line_gap_{i}",
                    position=(x + w/2, y + h/2),
                    width=float(w),
                    height=float(h),
                    area=float(area),
                    gap_type="opening",
                    confidence=0.6,
                    connected_walls=nearest_walls,
                    walkable=True
                ))
        
        return gaps
    
    def _find_nearest_walls(
        self,
        position: Tuple[float, float],
        walls: List[Dict],
        max_distance: float = 50
    ) -> List[str]:
        """Find walls near a position"""
        px, py = position
        nearest = []
        
        for wall in walls:
            # Calculate distance from point to line segment
            dist = self._point_to_line_distance(
                position,
                (wall["x1"], wall["y1"]),
                (wall["x2"], wall["y2"])
            )
            
            if dist < max_distance:
                nearest.append(f"wall_{wall.get('id', '')}")
        
        return nearest
    
    def _point_to_line_distance(
        self,
        point: Tuple[float, float],
        line_start: Tuple[float, float],
        line_end: Tuple[float, float]
    ) -> float:
        """Calculate distance from point to line segment"""
        px, py = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Vector from line_start to line_end
        dx = x2 - x1
        dy = y2 - y1
        
        # Vector from line_start to point
        px_dx = px - x1
        py_dy = py - y1
        
        # Project point onto line
        line_length_sq = dx * dx + dy * dy
        if line_length_sq == 0:
            return math.sqrt(px_dx * px_dx + py_dy * py_dy)
        
        t = max(0, min(1, (px_dx * dx + py_dy * dy) / line_length_sq))
        
        # Closest point on line
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Distance
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    def _classify_gaps(
        self,
        gaps: List[GapAnalysis],
        walls: List[Dict]
    ) -> List[GapAnalysis]:
        """Classify gaps into doors, corridors, openings"""
        classified = []
        
        for gap in gaps:
            # Classify based on dimensions
            if self.door_width_range[0] <= gap.width <= self.door_width_range[1]:
                # Check aspect ratio (doors are typically wider than tall)
                aspect_ratio = gap.width / gap.height if gap.height > 0 else 0
                
                if 0.5 < aspect_ratio < 2.0:
                    gap.gap_type = "door"
                    gap.confidence = 0.8
                    # Detect door swing direction (if possible)
                    gap.door_swing_direction = self._detect_door_swing(gap, walls)
                else:
                    gap.gap_type = "opening"
                    gap.confidence = 0.6
            
            elif gap.width > self.corridor_min_length or gap.height > self.corridor_min_length:
                # Long gap = corridor
                gap.gap_type = "corridor"
                gap.confidence = 0.7
            
            else:
                gap.gap_type = "opening"
                gap.confidence = 0.5
            
            classified.append(gap)
        
        return classified
    
    def _detect_door_swing(
        self,
        gap: GapAnalysis,
        walls: List[Dict]
    ) -> Optional[str]:
        """Detect door swing direction from wall geometry"""
        # Simplified: check which side of gap has more wall
        # In practice, would analyze door arc symbol if available
        return "left"  # Placeholder
    
    def detect_corridors(
        self,
        open_spaces: np.ndarray,
        min_length: float = 200
    ) -> List[Dict]:
        """
        Detect corridors with improved algorithm
        
        Corridors are:
        - Elongated open spaces
        - Connect multiple rooms
        - Have consistent width
        """
        if not CV2_AVAILABLE or cv2 is None:
            return []

        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            open_spaces, connectivity=8
        )
        
        corridors = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            
            aspect_ratio = w / h if h > 0 else 0
            
            # Corridor criteria: elongated and long enough
            if (aspect_ratio > 3.0 or aspect_ratio < 0.33) and max(w, h) > min_length:
                # Check connectivity (corridors connect multiple spaces)
                connectivity = self._calculate_corridor_connectivity(
                    labels, i, (x, y, w, h)
                )
                
                if connectivity >= 2:  # Connects at least 2 spaces
                    corridors.append({
                        "x": float(x + w/2),
                        "y": float(y + h/2),
                        "width": float(min(w, h)),  # Narrow dimension
                        "length": float(max(w, h)),  # Long dimension
                        "area": float(area),
                        "connectivity": connectivity,
                        "confidence": min(1.0, connectivity / 5.0),
                        "type": "corridor"
                    })
        
        return corridors
    
    def _calculate_corridor_connectivity(
        self,
        labels: np.ndarray,
        corridor_label: int,
        bbox: Tuple[int, int, int, int]
    ) -> int:
        """Calculate how many spaces this corridor connects"""
        x, y, w, h = bbox
        
        # Count unique labels at corridor boundaries
        boundary_labels = set()
        
        # Top and bottom boundaries
        for x_pos in range(x, x + w):
            if 0 <= y < labels.shape[0] and 0 <= x_pos < labels.shape[1]:
                if labels[y, x_pos] != corridor_label and labels[y, x_pos] != 0:
                    boundary_labels.add(labels[y, x_pos])
            if 0 <= y + h < labels.shape[0] and 0 <= x_pos < labels.shape[1]:
                if labels[y + h, x_pos] != corridor_label and labels[y + h, x_pos] != 0:
                    boundary_labels.add(labels[y + h, x_pos])
        
        # Left and right boundaries
        for y_pos in range(y, y + h):
            if 0 <= y_pos < labels.shape[0] and 0 <= x < labels.shape[1]:
                if labels[y_pos, x] != corridor_label and labels[y_pos, x] != 0:
                    boundary_labels.add(labels[y_pos, x])
            if 0 <= y_pos < labels.shape[0] and 0 <= x + w < labels.shape[1]:
                if labels[y_pos, x + w] != corridor_label and labels[y_pos, x + w] != 0:
                    boundary_labels.add(labels[y_pos, x + w])
        
        return len(boundary_labels)

# Global enhanced gap detector
enhanced_gap_detector = EnhancedGapDetector()

