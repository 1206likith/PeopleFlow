"""
Semantic Floorplan Understanding Engine
Moves from edge detection → semantic understanding
Uses improved OpenCV + ML models (U-Net, YOLOv8, Mask-RCNN)
"""
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
import numpy as np
import logging
from typing import Dict, List, Optional
from app.services.enhanced_floorplan_recognition import gap_detector, structural_classifier
from app.services.ml_floorplan_recognition import ml_floorplan_recognizer
from app.services.enhanced_gap_detection import enhanced_gap_detector
from app.services.floorplan_validation import floorplan_validator

logger = logging.getLogger(__name__)

class SemanticFloorplanProcessor:
    """
    Advanced semantic floorplan processing
    Classifies: walls, doors, exits, stairs, elevators, furniture, rooms
    """
    
    def __init__(self):
        self.min_wall_length = 20
        self.min_exit_width = 10
        self.wall_thickness = 3
        
        # Try to load ML models (if available)
        self.unet_model = None
        self.yolo_model = None
        self.maskrcnn_model = None
        self._load_ml_models()
    
    def _load_ml_models(self):
        """Load ML models if available (optional - falls back to OpenCV)"""
        try:
            # Try to load U-Net for wall segmentation
            # unet_path = Path("apps/backend/app/models/unet_walls.pth")
            # if unet_path.exists():
            #     import torch
            #     self.unet_model = torch.load(unet_path)
            #     logger.info("Loaded U-Net model for wall segmentation")
            pass
        except Exception as e:
            logger.debug(f"ML models not available, using OpenCV: {e}")

    @staticmethod
    def _opencv_ready() -> bool:
        return bool(CV2_AVAILABLE and cv2 is not None)
    
    def process_semantic(self, image_path: str, use_ml: bool = True) -> Dict:
        """
        Process floorplan with semantic understanding
        
        Args:
            image_path: Path to floor plan image
            use_ml: Whether to use ML models (if available)
        
        Returns:
            Comprehensive semantic analysis with classified elements
        """
        try:
            if not self._opencv_ready():
                logger.warning(
                    "Semantic processing unavailable because OpenCV is not installed in the backend runtime"
                )
                return self._empty_result()

            # Use ML-enhanced recognition if available and requested
            if use_ml:
                try:
                    ml_results = ml_floorplan_recognizer.process_floor_plan(image_path)
                    
                    # Extract results from ML processing
                    processing = ml_results.get("processing", {})
                    
                    # Get walls from ML segmentation
                    walls = processing.get("wall_segmentation", {}).get("walls", [])
                    
                    # Get furniture from YOLO
                    furniture = processing.get("furniture_detection", {}).get("furniture", [])
                    
                    # Get room classifications
                    room_classifications = processing.get("room_classification", [])
                    
                    # Get gaps from enhanced detection
                    gap_data = processing.get("gap_detection", {})
                    doors = gap_data.get("doors", [])
                    corridors = gap_data.get("corridors", [])
                    
                    # Enhanced gap analysis
                    wall_mask = None  # Would come from U-Net output
                    if walls:
                        # Create wall mask for enhanced gap detection
                        img = cv2.imread(image_path)
                        if img is not None:
                            height, width = img.shape[:2]
                            wall_mask = np.zeros((height, width), dtype=np.uint8)
                            for wall in walls:
                                cv2.line(wall_mask,
                                        (int(wall["x1"]), int(wall["y1"])),
                                        (int(wall["x2"]), int(wall["y2"])),
                                        255, thickness=3)
                            
                            # Enhanced gap analysis
                            enhanced_gaps = enhanced_gap_detector.analyze_wall_to_wall_gaps(walls, wall_mask)
                            doors.extend([{
                                "x": g.position[0],
                                "y": g.position[1],
                                "width": g.width,
                                "height": g.height,
                                "confidence": g.confidence,
                                "type": g.gap_type
                            } for g in enhanced_gaps if g.gap_type == "door"])
                    
                    # Get architectural symbols
                    symbols = processing.get("architectural_symbols", [])
                    
                    # Build result
                    result = {
                        "walls": walls,
                        "doors": doors,
                        "exits": self._classify_exits_from_gaps(gap_data.get("openings", []), walls),
                        "stairs": [s for s in symbols if s.get("type") == "stairwell"],
                        "elevators": processing.get("instance_segmentation", {}).get("instances", []),
                        "furniture": furniture,
                        "rooms": room_classifications,
                        "corridors": corridors,
                        "open_spaces": gap_data.get("openings", []),
                        "topology": self._build_topology(walls, doors, [], room_classifications),
                        "scale": self._extract_scale(cv2.imread(image_path)),
                        "wall_count": len(walls),
                        "exit_count": len(self._classify_exits_from_gaps(gap_data.get("openings", []), walls)),
                        "room_count": len(room_classifications),
                        "corridor_count": len(corridors),
                        "gap_count": len(doors) + len(corridors),
                        "processed": True,
                        "ml_enhanced": True,
                        "overall_confidence": ml_results.get("overall_confidence", 0.0),
                        "validation": ml_results.get("validation", {}),
                        "image_dimensions": ml_results.get("processing", {}).get("image_dimensions", {})
                    }
                    
                    # Validate results
                    validation_metrics = floorplan_validator.validate_recognition(ml_results)
                    result["validation_metrics"] = {
                        "overall_accuracy": validation_metrics.overall_accuracy,
                        "confidence_scores": validation_metrics.confidence_scores
                    }
                    
                    logger.info(f"ML-enhanced processing: {len(walls)} walls, {len(room_classifications)} rooms, "
                              f"confidence: {ml_results.get('overall_confidence', 0.0):.2f}")
                    
                    return result
                except Exception as e:
                    logger.warning(f"ML processing failed: {e}, falling back to OpenCV")
            
            # Fallback to OpenCV-based processing
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Could not load image: {image_path}")
                return self._empty_result()
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            
            # Enhanced preprocessing
            processed = self._preprocess_enhanced(gray)
            
            # Semantic classification
            walls = self._classify_walls(processed, width, height)
            
            # Enhanced gap detection
            gaps = gap_detector.detect_gaps(processed, walls)
            
            # Classify structural elements from gaps
            structural_elements = structural_classifier.classify_structural_elements(
                processed, gaps, walls
            )
            
            # Extract classified elements
            rooms = structural_elements.get("rooms", [])
            corridors = structural_elements.get("corridors", [])
            open_spaces = structural_elements.get("open_spaces", [])
            doors = structural_elements.get("doors", [])
            stairs = structural_elements.get("stairwells", [])
            elevators = structural_elements.get("elevators", [])
            
            # Combine all spaces for rooms list
            all_spaces = rooms + corridors + open_spaces
            
            # Detect exits (enhanced)
            exits = self._classify_exits(processed, walls, doors)
            
            # Detect furniture
            furniture = self._classify_furniture(processed, walls)
            
            # Build topology graph
            topology = self._build_topology(walls, doors, exits, rooms)
            
            # Extract scale/dimensions
            scale_info = self._extract_scale(img)
            
            result = {
                "walls": walls,
                "doors": doors,
                "exits": exits,
                "stairs": stairs,
                "elevators": elevators,
                "furniture": furniture,
                "rooms": all_spaces,  # Includes rooms, corridors, open spaces
                "corridors": corridors,
                "open_spaces": open_spaces,
                "gaps": [{"x": g.x, "y": g.y, "width": g.width, "height": g.height, 
                         "area": g.area, "type": g.gap_type} for g in gaps],
                "topology": topology,
                "scale": scale_info,
                "wall_count": len(walls),
                "exit_count": len(exits),
                "room_count": len(rooms),
                "corridor_count": len(corridors),
                "gap_count": len(gaps),
                "processed": True,
                "ml_enhanced": False,
                "image_dimensions": {"width": width, "height": height}
            }
            
            logger.info(
                f"Semantic processing: {len(walls)} walls, {len(exits)} exits, "
                f"{len(rooms)} rooms, {len(doors)} doors"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in semantic processing: {e}", exc_info=True)
            return self._empty_result()
    
    def _classify_exits_from_gaps(self, openings: List[Dict], walls: List[Dict]) -> List[Dict]:
        """Classify exits from gap openings"""
        exits = []
        for opening in openings:
            # Exits are typically larger openings at building boundaries
            if opening.get("area", 0) > 2000:  # Large opening
                exits.append({
                    "x": opening.get("x", 0),
                    "y": opening.get("y", 0),
                    "z": opening.get("y", 0),
                    "width": opening.get("width", 2.0),
                    "type": "exit",
                    "confidence": opening.get("confidence", 0.6)
                })
        return exits
    
    def _preprocess_enhanced(self, gray: np.ndarray) -> np.ndarray:
        """Enhanced preprocessing with morphological operations"""
        # Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Adaptive thresholding
        adaptive = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Morphological closing to connect broken lines
        kernel = np.ones((3, 3), np.uint8)
        closed = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Remove small noise
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Combine
        combined = cv2.bitwise_or(opened, edges)
        
        return combined
    
    def _classify_walls(self, processed: np.ndarray, width: int, height: int) -> List[Dict]:
        """Classify walls with improved detection"""
        # Use HoughLinesP with better parameters
        threshold = max(50, int(min(width, height) * 0.08))
        
        lines = cv2.HoughLinesP(
            processed,
            rho=1,
            theta=np.pi/180,
            threshold=threshold,
            minLineLength=max(self.min_wall_length, min(width, height) * 0.03),
            maxLineGap=max(10, min(width, height) * 0.015)
        )
        
        walls = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                
                if length < self.min_wall_length:
                    continue
                
                # Classify as external or internal based on position
                is_external = (
                    x1 < 5 or x2 < 5 or x1 > width - 5 or x2 > width - 5 or
                    y1 < 5 or y2 < 5 or y1 > height - 5 or y2 > height - 5
                )
                
                walls.append({
                    "x1": float(x1),
                    "y1": float(y1),
                    "x2": float(x2),
                    "y2": float(y2),
                    "length": float(length),
                    "type": "external" if is_external else "internal",
                    "thickness": float(self.wall_thickness),
                    "classification": "wall"
                })
        
        return walls
    
    def _classify_doors(self, processed: np.ndarray, walls: List[Dict]) -> List[Dict]:
        """
        Classify doors and openings with improved gap detection
        Uses morphological operations to find gaps in wall lines
        """
        doors = []
        height, width = processed.shape
        
        # Create wall mask (thickened walls)
        wall_mask = np.zeros((height, width), dtype=np.uint8)
        for wall in walls:
            cv2.line(wall_mask, 
                    (int(wall["x1"]), int(wall["y1"])),
                    (int(wall["x2"]), int(wall["y2"])),
                    255, thickness=5)
        
        # Find gaps in walls (openings)
        # Dilate walls to find where they should connect but don't
        dilated = cv2.dilate(wall_mask, np.ones((15, 15), np.uint8), iterations=1)
        
        # Find contours of potential openings
        inverted = cv2.bitwise_not(dilated)
        contours, _ = cv2.findContours(inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            # Doors are typically 50-500 pixels in area
            if 50 < area < 500:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Doors are typically wider than tall (horizontal openings)
                if 1.5 < aspect_ratio < 10.0 or 0.1 < aspect_ratio < 0.67:
                    # Check if this opening connects two spaces
                    center_x = x + w / 2
                    center_y = y + h / 2
                    
                    # Verify it's actually an opening (not just noise)
                    if 0 <= int(center_x) < width and 0 <= int(center_y) < height:
                        pixel_value = processed[int(center_y), int(center_x)]
                        if pixel_value < 128:  # Open space
                            doors.append({
                                "x": float(center_x),
                                "y": float(center_y),
                                "z": 0.0,
                                "width": float(max(w, h)),
                                "height": float(min(w, h)),
                                "type": "door",
                                "classification": "door",
                                "opening_area": float(area)
                            })
        
        # Also check for gaps between parallel walls
        for i, wall1 in enumerate(walls):
            for wall2 in walls[i+1:]:
                if self._are_parallel(wall1, wall2, threshold=0.15):
                    gap = self._find_gap(wall1, wall2, processed)
                    if gap and gap["width"] < 100:  # Narrow gap = door
                        # Check if not already added
                        is_duplicate = False
                        for door in doors:
                            if abs(door["x"] - gap["x"]) < 20 and abs(door["y"] - gap["y"]) < 20:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            doors.append({
                                "x": gap["x"],
                                "y": gap["y"],
                                "z": 0.0,
                                "width": gap["width"],
                                "height": gap["width"] * 0.5,
                                "type": "door",
                                "classification": "door"
                            })
        
        return doors
    
    def _classify_exits(self, processed: np.ndarray, walls: List[Dict], doors: List[Dict]) -> List[Dict]:
        """Classify exits (larger openings, typically at boundaries)"""
        exits = []
        
        # Exits are typically larger than doors and at building boundaries
        for door in doors:
            if door["width"] >= self.min_exit_width * 2:  # Exits are wider
                # Check if near boundary
                height, width = processed.shape
                x, y = door["x"], door["y"]
                
                if (x < 20 or x > width - 20 or y < 20 or y > height - 20):
                    exits.append({
                        "x": x,
                        "y": y,
                        "z": 0.0,
                        "width": door["width"],
                        "type": "exit",
                        "classification": "exit",
                        "is_emergency": True
                    })
        
        return exits
    
    def _classify_stairs(self, processed: np.ndarray) -> List[Dict]:
        """Classify staircases (typically rectangular patterns)"""
        # Find rectangular patterns that might be stairs
        contours, _ = cv2.findContours(processed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        stairs = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 500 < area < 5000:  # Stair size range
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Stairs are typically elongated rectangles
                if 2.0 < aspect_ratio < 5.0:
                    stairs.append({
                        "x": float(x + w/2),
                        "y": float(y + h/2),
                        "z": 0.0,
                        "width": float(w),
                        "height": float(h),
                        "type": "staircase",
                        "classification": "stairs"
                    })
        
        return stairs
    
    def _classify_elevators(self, processed: np.ndarray) -> List[Dict]:
        """Classify elevators (small square/rectangular rooms)"""
        contours, _ = cv2.findContours(processed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        elevators = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 200 < area < 2000:  # Elevator size
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Elevators are typically square-ish
                if 0.7 < aspect_ratio < 1.4:
                    elevators.append({
                        "x": float(x + w/2),
                        "y": float(y + h/2),
                        "z": 0.0,
                        "width": float(w),
                        "height": float(h),
                        "type": "elevator",
                        "classification": "elevator"
                    })
        
        return elevators
    
    def _classify_furniture(self, processed: np.ndarray, walls: List[Dict]) -> List[Dict]:
        """Classify furniture/obstacles (small closed shapes)"""
        contours, _ = cv2.findContours(processed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        furniture = []
        for contour in contours:
            area = cv2.contourArea(contour)
            # Furniture is smaller than rooms but larger than noise
            if 50 < area < 2000:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Check if not a wall
                is_wall = False
                for wall in walls:
                    wall_dist = min(
                        abs(x - wall["x1"]), abs(x - wall["x2"]),
                        abs(y - wall["y1"]), abs(y - wall["y2"])
                    )
                    if wall_dist < 10:
                        is_wall = True
                        break
                
                if not is_wall:
                    furniture.append({
                        "x": float(x + w/2),
                        "y": float(y + h/2),
                        "z": float(y + h/2),
                        "width": float(w),
                        "height": float(h),
                        "type": "furniture",
                        "classification": "obstacle"
                    })
        
        return furniture
    
    def _classify_rooms(self, processed: np.ndarray, walls: List[Dict]) -> List[Dict]:
        """
        Classify rooms and open spaces with proper gap detection
        Uses flood fill to identify connected open areas
        """
        height, width = processed.shape
        
        # Create binary mask: 0 = wall, 255 = open space
        # Invert so walls are black (0) and open spaces are white (255)
        binary = cv2.bitwise_not(processed)
        
        # Clean up small noise
        kernel = np.ones((5, 5), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Find connected components (rooms/open spaces)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )
        
        rooms = []
        corridors = []
        open_spaces = []
        
        for i in range(1, num_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            
            # Skip very small areas (noise)
            if area < 500:
                continue
            
            # Classify based on shape and size
            aspect_ratio = w / h if h > 0 else 0
            compactness = 4 * np.pi * area / (w * h + 1e-6)  # How circular
            
            # Corridors: elongated, narrow spaces
            if (aspect_ratio > 3.0 or aspect_ratio < 0.33) and area < 10000:
                corridors.append({
                    "x": float(x + w/2),
                    "y": float(y + h/2),
                    "width": float(w),
                    "height": float(h),
                    "area": float(area),
                    "type": "corridor",
                    "classification": "corridor",
                    "name": f"Corridor {len(corridors) + 1}",
                    "walkable_width": min(w, h)  # Narrow dimension
                })
            # Open spaces: large, relatively open areas
            elif area > 20000 and compactness > 0.3:
                open_spaces.append({
                    "x": float(x + w/2),
                    "y": float(y + h/2),
                    "width": float(w),
                    "height": float(h),
                    "area": float(area),
                    "type": "open_space",
                    "classification": "open_space",
                    "name": f"Open Space {len(open_spaces) + 1}"
                })
            # Rooms: medium-sized enclosed spaces
            elif area > 5000:
                rooms.append({
                    "x": float(x + w/2),
                    "y": float(y + h/2),
                    "width": float(w),
                    "height": float(h),
                    "area": float(area),
                    "type": "room",
                    "classification": "room",
                    "name": f"Room {len(rooms) + 1}",
                    "compactness": float(compactness)
                })
        
        # Combine all spaces
        all_spaces = rooms + corridors + open_spaces
        
        logger.info(f"Detected {len(rooms)} rooms, {len(corridors)} corridors, {len(open_spaces)} open spaces")
        
        return all_spaces
    
    def _build_topology(self, walls: List[Dict], doors: List[Dict], exits: List[Dict], rooms: List[Dict]) -> Dict:
        """
        Build topology graph of building structure
        Identifies connectivity between rooms, corridors, and exits
        """
        # Count different space types
        room_count = sum(1 for r in rooms if r.get("type") == "room")
        corridor_count = sum(1 for r in rooms if r.get("type") == "corridor")
        open_space_count = sum(1 for r in rooms if r.get("type") == "open_space")
        
        # Calculate connectivity
        # A space is connected if it has doors or is adjacent to exits
        connected_spaces = 0
        for room in rooms:
            # Check if room is near an exit or door
            room_x, room_y = room.get("x", 0), room.get("y", 0)
            
            # Check exit proximity
            near_exit = False
            for exit_data in exits:
                exit_x, exit_y = exit_data.get("x", 0), exit_data.get("y", 0)
                dist = np.sqrt((room_x - exit_x)**2 + (room_y - exit_y)**2)
                if dist < 100:  # Within 100 pixels
                    near_exit = True
                    break
            
            # Check door proximity
            near_door = False
            for door in doors:
                door_x, door_y = door.get("x", 0), door.get("y", 0)
                dist = np.sqrt((room_x - door_x)**2 + (room_y - door_y)**2)
                if dist < 50:  # Within 50 pixels
                    near_door = True
                    break
            
            if near_exit or near_door:
                connected_spaces += 1
        
        connectivity_ratio = connected_spaces / len(rooms) if rooms else 0.0
        
        return {
            "nodes": len(rooms) + len(exits),
            "edges": len(doors),
            "connectivity": "connected" if connectivity_ratio > 0.7 else "partially_connected",
            "connectivity_ratio": connectivity_ratio,
            "room_count": room_count,
            "corridor_count": corridor_count,
            "open_space_count": open_space_count,
            "structural_types": {
                "rooms": room_count,
                "corridors": corridor_count,
                "open_spaces": open_space_count,
                "exits": len(exits),
                "doors": len(doors)
            }
        }
    
    def _extract_scale(self, img: Optional[np.ndarray]) -> Dict:
        """Extract scale/dimensions from blueprint (OCR for dimension labels)"""
        if img is None:
            return {
                "pixels_per_meter": 10.0,
                "scale_confidence": 0.0,
            }
        # Simplified - in production would use OCR
        return {
            "pixels_per_meter": 10.0,  # Default
            "scale_confidence": 0.5
        }
    
    def _are_parallel(self, wall1: Dict, wall2: Dict, threshold: float = 0.1) -> bool:
        """Check if two walls are parallel"""
        dx1 = wall1["x2"] - wall1["x1"]
        dy1 = wall1["y2"] - wall1["y1"]
        dx2 = wall2["x2"] - wall2["x1"]
        dy2 = wall2["y2"] - wall2["y1"]
        
        angle1 = np.arctan2(dy1, dx1)
        angle2 = np.arctan2(dy2, dx2)
        
        angle_diff = abs(angle1 - angle2)
        return angle_diff < threshold or abs(angle_diff - np.pi) < threshold
    
    def _find_gap(self, wall1: Dict, wall2: Dict, processed: np.ndarray) -> Optional[Dict]:
        """Find gap between parallel walls (potential door or corridor)"""
        # Calculate distance between parallel walls
        # Get perpendicular distance from wall1 to wall2
        x1, y1 = wall1["x1"], wall1["y1"]
        x2, y2 = wall1["x2"], wall1["y2"]
        x3, y3 = wall2["x1"], wall2["y1"]
        x4, y4 = wall2["x2"], wall2["y2"]
        
        # Calculate distance between wall midpoints
        mid1 = ((x1 + x2) / 2, (y1 + y2) / 2)
        mid2 = ((x3 + x4) / 2, (y3 + y4) / 2)
        distance = np.sqrt((mid1[0] - mid2[0])**2 + (mid1[1] - mid2[1])**2)
        
        # Check if there's a walkable gap (not blocked by walls)
        if 20 < distance < 500:  # Reasonable gap size
            # Sample points along the gap to check if it's open
            gap_x = (mid1[0] + mid2[0]) / 2
            gap_y = (mid1[1] + mid2[1]) / 2
            
            # Check if this point is in an open area (low pixel value = white/open)
            h, w = processed.shape
            if 0 <= int(gap_x) < w and 0 <= int(gap_y) < h:
                pixel_value = processed[int(gap_y), int(gap_x)]
                if pixel_value < 128:  # Open space (dark in inverted image)
                    return {
                        "x": gap_x,
                        "y": gap_y,
                        "width": distance,
                        "type": "corridor" if distance > 50 else "door"
                    }
        
        return None
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "walls": [],
            "doors": [],
            "exits": [],
            "stairs": [],
            "elevators": [],
            "furniture": [],
            "rooms": [],
            "topology": {},
            "scale": {},
            "wall_count": 0,
            "exit_count": 0,
            "room_count": 0,
            "processed": False,
            "image_dimensions": {"width": 0, "height": 0}
        }

# Global instance
semantic_processor = SemanticFloorplanProcessor()

