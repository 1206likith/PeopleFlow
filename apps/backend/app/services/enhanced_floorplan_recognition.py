"""
Enhanced Floor Plan Recognition with Gap Detection
Properly detects open spaces, gaps, corridors, and structural elements
Addresses issues with missing gap detection and poor floor plan recognition
"""

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GapRegion:
    """Represents a detected gap/open space"""
    x: float
    y: float
    width: float
    height: float
    area: float
    gap_type: str  # "corridor", "room", "open_space", "door"
    connectivity: List[str]  # Connected space IDs

class EnhancedGapDetector:
    """
    Advanced gap detection for floor plans
    Properly identifies open spaces, corridors, and gaps between structural elements
    """
    
    def __init__(self):
        self.min_gap_area = 500  # Minimum gap area in pixels
        self.corridor_aspect_ratio_threshold = 3.0
        self.wall_thickness = 5
    
    def detect_gaps(
        self,
        processed_image: np.ndarray,
        walls: List[Dict],
        min_area: Optional[int] = None
    ) -> List[GapRegion]:
        """
        Detect all gaps and open spaces in floor plan
        
        Args:
            processed_image: Preprocessed binary image (walls = white, open = black)
            walls: List of detected walls
            min_area: Minimum area for gap detection
        
        Returns:
            List of detected gap regions
        """
        if min_area is None:
            min_area = self.min_gap_area
        
        height, width = processed_image.shape
        
        # Create wall mask
        wall_mask = np.zeros((height, width), dtype=np.uint8)
        for wall in walls:
            cv2.line(wall_mask,
                    (int(wall["x1"]), int(wall["y1"])),
                    (int(wall["x2"]), int(wall["y2"])),
                    255, thickness=self.wall_thickness)
        
        # Dilate walls to ensure they block paths
        dilated_walls = cv2.dilate(wall_mask, np.ones((7, 7), np.uint8), iterations=2)
        
        # Invert to get open spaces (gaps)
        open_spaces = cv2.bitwise_not(dilated_walls)
        
        # Clean up noise
        kernel = np.ones((5, 5), np.uint8)
        open_spaces = cv2.morphologyEx(open_spaces, cv2.MORPH_OPEN, kernel)
        open_spaces = cv2.morphologyEx(open_spaces, cv2.MORPH_CLOSE, kernel)
        
        # Find connected components (gaps)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            open_spaces, connectivity=8
        )
        
        gaps = []
        for i in range(1, num_labels):  # Skip background
            area = stats[i, cv2.CC_STAT_AREA]
            if area < min_area:
                continue
            
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            
            # Classify gap type
            gap_type = self._classify_gap_type(w, h, area)
            
            gap = GapRegion(
                x=float(x + w/2),
                y=float(y + h/2),
                width=float(w),
                height=float(h),
                area=float(area),
                gap_type=gap_type,
                connectivity=[]
            )
            gaps.append(gap)
        
        # Analyze connectivity between gaps
        self._analyze_gap_connectivity(gaps, walls)
        
        return gaps
    
    def _classify_gap_type(self, width: float, height: float, area: float) -> str:
        """Classify gap type based on shape and size"""
        aspect_ratio = width / height if height > 0 else 0
        compactness = 4 * np.pi * area / (width * height + 1e-6)
        
        # Corridors: elongated, narrow
        if (aspect_ratio > self.corridor_aspect_ratio_threshold or 
            aspect_ratio < 1.0 / self.corridor_aspect_ratio_threshold):
            if area < 15000:
                return "corridor"
        
        # Large open spaces
        if area > 20000 and compactness > 0.4:
            return "open_space"
        
        # Small gaps (doors)
        if area < 2000:
            return "door"
        
        # Regular rooms
        return "room"
    
    def _analyze_gap_connectivity(
        self,
        gaps: List[GapRegion],
        walls: List[Dict]
    ):
        """Analyze which gaps are connected (adjacent without walls between)"""
        for i, gap1 in enumerate(gaps):
            for gap2 in gaps[i+1:]:
                # Check if gaps are close
                distance = np.sqrt(
                    (gap1.x - gap2.x)**2 + (gap1.y - gap2.y)**2
                )
                
                # Check if there's a wall blocking the connection
                # (simplified - would need proper line-of-sight check)
                max_dimension = max(gap1.width, gap1.height, gap2.width, gap2.height)
                
                if distance < max_dimension * 1.5:
                    # Check if path is blocked by wall
                    is_blocked = self._is_path_blocked(
                        (gap1.x, gap1.y),
                        (gap2.x, gap2.y),
                        walls
                    )
                    
                    if not is_blocked:
                        gap1.connectivity.append(f"gap_{gaps.index(gap2)}")
                        gap2.connectivity.append(f"gap_{gaps.index(gap1)}")
    
    def _is_path_blocked(
        self,
        point1: Tuple[float, float],
        point2: Tuple[float, float],
        walls: List[Dict]
    ) -> bool:
        """Check if path between two points is blocked by a wall"""
        x1, y1 = point1
        x2, y2 = point2
        
        # Check intersection with each wall
        for wall in walls:
            wall_p1 = (wall["x1"], wall["y1"])
            wall_p2 = (wall["x2"], wall["y2"])
            
            if self._line_segments_intersect(point1, point2, wall_p1, wall_p2):
                return True
        
        return False
    
    def _line_segments_intersect(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        p4: Tuple[float, float]
    ) -> bool:
        """Check if two line segments intersect"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return False  # Parallel
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        return 0 <= t <= 1 and 0 <= u <= 1

class StructuralElementClassifier:
    """
    Classifies structural elements with proper recognition
    Distinguishes between rooms, corridors, open spaces, stairwells, etc.
    """
    
    def __init__(self):
        self.room_min_area = 5000
        self.corridor_min_length = 100
        self.stairwell_size_range = (500, 5000)
    
    def classify_structural_elements(
        self,
        processed_image: np.ndarray,
        gaps: List[GapRegion],
        walls: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        Classify all structural elements with proper recognition
        
        Returns:
            Dictionary with classified elements by type
        """
        classified = {
            "rooms": [],
            "corridors": [],
            "open_spaces": [],
            "stairwells": [],
            "elevators": [],
            "doors": []
        }
        
        for gap in gaps:
            element = {
                "x": gap.x,
                "y": gap.y,
                "z": 0.0,
                "width": gap.width,
                "height": gap.height,
                "area": gap.area,
                "type": gap.gap_type,
                "connectivity": gap.connectivity
            }
            
            if gap.gap_type == "room":
                classified["rooms"].append(element)
            elif gap.gap_type == "corridor":
                classified["corridors"].append(element)
            elif gap.gap_type == "open_space":
                classified["open_spaces"].append(element)
            elif gap.gap_type == "door":
                classified["doors"].append(element)
        
        # Detect stairwells (typically have specific patterns)
        stairwells = self._detect_stairwells(processed_image, walls)
        classified["stairwells"] = stairwells
        
        # Detect elevators (small square rooms)
        elevators = self._detect_elevators(processed_image, gaps)
        classified["elevators"] = elevators
        
        return classified
    
    def _detect_stairwells(
        self,
        processed_image: np.ndarray,
        walls: List[Dict]
    ) -> List[Dict]:
        """Detect stairwells (typically have parallel lines pattern)"""
        # Use HoughLines to find parallel lines (stair steps)
        lines = cv2.HoughLines(processed_image, 1, np.pi/180, 100)
        
        stairwells = []
        if lines is not None:
            # Group parallel lines
            parallel_groups = []
            for line in lines:
                rho, theta = line[0]
                # Find similar lines (parallel)
                found_group = False
                for group in parallel_groups:
                    if abs(group["theta"] - theta) < 0.1:
                        group["lines"].append((rho, theta))
                        found_group = True
                        break
                
                if not found_group:
                    parallel_groups.append({"theta": theta, "lines": [(rho, theta)]})
            
            # Stairwells have many parallel lines
            for group in parallel_groups:
                if len(group["lines"]) >= 5:  # Many parallel lines = stairs
                    # Find bounding box
                    min_rho = min(r[0] for r in group["lines"])
                    max_rho = max(r[0] for r in group["lines"])
                    
                    # Estimate position (simplified)
                    avg_rho = (min_rho + max_rho) / 2
                    theta = group["theta"]
                    
                    height, width = processed_image.shape
                    x = avg_rho * np.cos(theta)
                    y = avg_rho * np.sin(theta)
                    
                    stairwells.append({
                        "x": float(x),
                        "y": float(y),
                        "z": 0.0,
                        "width": float(abs(max_rho - min_rho)),
                        "height": float(abs(max_rho - min_rho)),
                        "type": "stairwell",
                        "classification": "stairs"
                    })
        
        return stairwells
    
    def _detect_elevators(
        self,
        processed_image: np.ndarray,
        gaps: List[GapRegion]
    ) -> List[Dict]:
        """Detect elevators (small, square enclosed spaces)"""
        elevators = []
        
        for gap in gaps:
            if gap.area < 2000:  # Small area
                aspect_ratio = gap.width / gap.height if gap.height > 0 else 0
                compactness = 4 * np.pi * gap.area / (gap.width * gap.height + 1e-6)
                
                # Elevators are typically square-ish and compact
                if 0.7 < aspect_ratio < 1.4 and compactness > 0.6:
                    elevators.append({
                        "x": gap.x,
                        "y": gap.y,
                        "z": 0.0,
                        "width": gap.width,
                        "height": gap.height,
                        "area": gap.area,
                        "type": "elevator",
                        "classification": "elevator"
                    })
        
        return elevators

# Global instances
gap_detector = EnhancedGapDetector()
structural_classifier = StructuralElementClassifier()

