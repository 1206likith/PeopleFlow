"""
ML-Enhanced Floor Plan Recognition
Integrates U-Net, YOLOv8, and Mask-RCNN for advanced blueprint understanding
"""

from __future__ import annotations
import sys

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import ML libraries (optional dependencies)
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
    TORCH_IMPORT_ERROR = None
except ImportError:
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    TORCH_AVAILABLE = False
    TORCH_IMPORT_ERROR = "not installed in backend environment"

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    YOLO_IMPORT_ERROR = None
except ImportError:
    YOLO_AVAILABLE = False
    YOLO_IMPORT_ERROR = "not installed in backend environment"

try:
    from detectron2 import model_zoo
    from detectron2.engine import DefaultPredictor
    from detectron2.config import get_cfg
    DETECTRON_AVAILABLE = True
    DETECTRON_IMPORT_ERROR = None
except ImportError:
    DETECTRON_AVAILABLE = False
    DETECTRON_IMPORT_ERROR = "not installed or unsupported on this platform/runtime"

_ML_DEPENDENCY_SUMMARY_LOGGED = False


def get_optional_ml_dependency_status() -> Dict[str, Dict[str, Any]]:
    return {
        "opencv": {
            "available": bool(CV2_AVAILABLE and cv2 is not None),
            "error": None if (CV2_AVAILABLE and cv2 is not None) else "opencv runtime unavailable",
        },
        "torch": {
            "available": bool(TORCH_AVAILABLE and torch is not None),
            "error": TORCH_IMPORT_ERROR,
        },
        "ultralytics": {
            "available": bool(YOLO_AVAILABLE),
            "error": YOLO_IMPORT_ERROR,
        },
        "detectron2": {
            "available": bool(DETECTRON_AVAILABLE),
            "error": DETECTRON_IMPORT_ERROR,
        },
    }


def log_optional_ml_dependency_summary() -> None:
    global _ML_DEPENDENCY_SUMMARY_LOGGED
    if _ML_DEPENDENCY_SUMMARY_LOGGED:
        return

    status = get_optional_ml_dependency_status()
    missing = [name for name, details in status.items() if name != "opencv" and not bool(details.get("available"))]
    if missing:
        runtime = f"{sys.platform} / Python {sys.version_info.major}.{sys.version_info.minor}"
        logger.warning(
            "Optional ML dependencies unavailable in current backend environment (%s). "
            "PeopleFlow will use OpenCV fallbacks where possible. Missing: %s. "
            "Install apps/backend/requirements-ml.txt for PyTorch and YOLO support. "
            "Detectron2 often requires Linux/WSL or a carefully pinned toolchain.",
            runtime,
            ", ".join(missing),
        )
    _ML_DEPENDENCY_SUMMARY_LOGGED = True


log_optional_ml_dependency_summary()

class UNetWallSegmentation:
    """
    U-Net model for wall segmentation
    Provides pixel-level wall detection
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        default_path = Path(__file__).resolve().parents[1] / "models" / "unet_walls.pth"
        self.model_path = model_path or str(default_path)
        self.device = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """Load U-Net model for wall segmentation"""
        if not TORCH_AVAILABLE:
            return
        
        model_file = Path(self.model_path)
        if model_file.exists():
            try:
                self.model = torch.load(model_file, map_location=self.device)
                self.model.eval()
                logger.info(f"Loaded U-Net model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not load U-Net model: {e}")
        else:
            logger.info(f"U-Net model not found at {self.model_path}, using fallback")
    
    def segment_walls(self, image: np.ndarray) -> np.ndarray:
        """
        Segment walls from floor plan image
        
        Returns:
            Binary mask where 1 = wall, 0 = open space
        """
        if self.model is None:
            # Fallback to OpenCV-based detection
            return self._opencv_wall_segmentation(image)
        
        try:
            # Preprocess image
            img_tensor = self._preprocess_image(image)
            
            # Run inference
            with torch.no_grad():
                output = self.model(img_tensor)
                mask = torch.sigmoid(output).cpu().numpy()[0, 0]
                mask = (mask > 0.5).astype(np.uint8) * 255
            
            return mask
        except Exception as e:
            logger.warning(f"U-Net inference failed: {e}, using fallback")
            return self._opencv_wall_segmentation(image)
    
    def _preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess image for U-Net"""
        # Resize to model input size (typically 512x512)
        resized = cv2.resize(image, (512, 512))
        # Normalize
        normalized = resized.astype(np.float32) / 255.0
        # Convert to tensor
        tensor = torch.from_numpy(normalized).unsqueeze(0).unsqueeze(0)
        return tensor.to(self.device)
    
    def _opencv_wall_segmentation(self, image: np.ndarray) -> np.ndarray:
        """Fallback OpenCV-based wall segmentation"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate to connect wall lines
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Fill walls
        filled = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel, iterations=3)
        
        return filled

class YOLOFurnitureDetector:
    """
    YOLOv8 model for furniture and object detection
    Detects: beds, sofas, tables, chairs, appliances, etc.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        default_path = Path(__file__).resolve().parents[1] / "models" / "yolov8_floorplan.pt"
        self.model_path = model_path or str(default_path)
        self._load_model()
        
        # Furniture class mappings
        self.furniture_classes = {
            'bed': 'bedroom',
            'sofa': 'living_room',
            'table': 'dining_room',
            'chair': 'dining_room',
            'toilet': 'bathroom',
            'sink': 'bathroom',
            'bathtub': 'bathroom',
            'refrigerator': 'kitchen',
            'oven': 'kitchen',
            'stove': 'kitchen',
            'microwave': 'kitchen'
        }
    
    def _load_model(self):
        """Load YOLOv8 model"""
        if not YOLO_AVAILABLE:
            return
        
        model_file = Path(self.model_path)
        if model_file.exists():
            try:
                self.model = YOLO(self.model_path)
                logger.info(f"Loaded YOLOv8 model from {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not load YOLOv8 model: {e}")
        else:
            logger.info(f"YOLOv8 model not found at {self.model_path}, using fallback")
    
    def detect_furniture(self, image: np.ndarray) -> List[Dict]:
        """
        Detect furniture and objects in floor plan
        
        Returns:
            List of detected objects with bounding boxes and classes
        """
        if self.model is None:
            return self._opencv_furniture_detection(image)
        
        try:
            results = self.model(image, conf=0.25)
            detections = []
            
            for result in results:
                boxes = result.boxes
                for i in range(len(boxes)):
                    box = boxes[i]
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = result.names[class_id]
                    
                    detections.append({
                        "class": class_name,
                        "confidence": confidence,
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "center": [float((x1 + x2) / 2), float((y1 + y2) / 2)],
                        "room_type": self.furniture_classes.get(class_name, "unknown")
                    })
            
            return detections
        except Exception as e:
            logger.warning(f"YOLOv8 inference failed: {e}, using fallback")
            return self._opencv_furniture_detection(image)
    
    def _opencv_furniture_detection(self, image: np.ndarray) -> List[Dict]:
        """Fallback OpenCV-based furniture detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Find contours that might be furniture
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 100 < area < 5000:  # Furniture size range
                x, y, w, h = cv2.boundingRect(contour)
                detections.append({
                    "class": "furniture",
                    "confidence": 0.5,
                    "bbox": [float(x), float(y), float(x + w), float(y + h)],
                    "center": [float(x + w/2), float(y + h/2)],
                    "room_type": "unknown"
                })
        
        return detections

class MaskRCNNInstanceSegmentation:
    """
    Mask-RCNN model for instance segmentation
    Provides pixel-level segmentation of different building elements
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.predictor = None
        self.model_path = model_path
        self._load_model()
        
        # Building element classes
        self.element_classes = {
            0: 'background',
            1: 'wall',
            2: 'door',
            3: 'window',
            4: 'room',
            5: 'corridor',
            6: 'stairwell',
            7: 'elevator',
            8: 'exit'
        }
    
    def _load_model(self):
        """Load Mask-RCNN model"""
        if not DETECTRON_AVAILABLE:
            return
        
        try:
            cfg = get_cfg()
            # Use pre-trained model or custom
            if self.model_path:
                cfg.MODEL.WEIGHTS = self.model_path
            else:
                cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
            
            cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
            cfg.MODEL.DEVICE = "cuda" if TORCH_AVAILABLE and torch is not None and torch.cuda.is_available() else "cpu"
            
            self.predictor = DefaultPredictor(cfg)
            logger.info("Loaded Mask-RCNN model")
        except Exception as e:
            logger.warning(f"Could not load Mask-RCNN: {e}, using fallback")
    
    def segment_instances(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Perform instance segmentation
        
        Returns:
            Dictionary with masks, boxes, and classes for each instance
        """
        if self.predictor is None:
            return self._opencv_instance_segmentation(image)
        
        try:
            outputs = self.predictor(image)
            
            instances = []
            for i in range(len(outputs["instances"])):
                instance = outputs["instances"][i]
                mask = instance.pred_masks[0].cpu().numpy().astype(np.uint8) * 255
                bbox = instance.pred_boxes.tensor[0].cpu().numpy()
                class_id = instance.pred_classes.item()
                score = instance.scores.item()
                
                instances.append({
                    "mask": mask,
                    "bbox": bbox.tolist(),
                    "class_id": int(class_id),
                    "class_name": self.element_classes.get(class_id, "unknown"),
                    "confidence": float(score)
                })
            
            return {
                "instances": instances,
                "num_instances": len(instances)
            }
        except Exception as e:
            logger.warning(f"Mask-RCNN inference failed: {e}, using fallback")
            return self._opencv_instance_segmentation(image)
    
    def _opencv_instance_segmentation(self, image: np.ndarray) -> Dict[str, Any]:
        """Fallback OpenCV-based instance segmentation"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Simple segmentation by connected components
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        
        instances = []
        for i in range(1, num_labels):
            mask = (labels == i).astype(np.uint8) * 255
            x, y, w, h, area = stats[i]
            
            instances.append({
                "mask": mask,
                "bbox": [float(x), float(y), float(x + w), float(y + h)],
                "class_id": 4,  # room
                "class_name": "room",
                "confidence": 0.5
            })
        
        return {
            "instances": instances,
            "num_instances": len(instances)
        }

class EnhancedSemanticClassifier:
    """
    Enhanced semantic classification with room types and architectural symbols
    """
    
    def __init__(self):
        self.room_type_classifier = self._initialize_room_classifier()
    
    def classify_room_type(
        self,
        room_region: np.ndarray,
        furniture_detections: List[Dict],
        room_features: Dict
    ) -> Tuple[str, float]:
        """
        Classify room type based on furniture and features
        
        Returns:
            (room_type, confidence)
        """
        # Count furniture by type
        furniture_counts = {}
        for det in furniture_detections:
            room_type = det.get("room_type", "unknown")
            furniture_counts[room_type] = furniture_counts.get(room_type, 0) + 1
        
        # Room type heuristics
        scores = {
            "bedroom": 0.0,
            "kitchen": 0.0,
            "bathroom": 0.0,
            "living_room": 0.0,
            "dining_room": 0.0,
            "corridor": 0.0,
            "stairwell": 0.0,
            "elevator": 0.0
        }
        
        # Furniture-based scoring
        if furniture_counts.get("bedroom", 0) > 0:
            scores["bedroom"] += 0.8
        if furniture_counts.get("kitchen", 0) > 0:
            scores["kitchen"] += 0.8
        if furniture_counts.get("bathroom", 0) > 0:
            scores["bathroom"] += 0.9
        if furniture_counts.get("living_room", 0) > 0:
            scores["living_room"] += 0.7
        
        # Feature-based scoring
        area = room_features.get("area", 0)
        aspect_ratio = room_features.get("aspect_ratio", 1.0)
        
        # Corridors: elongated, narrow
        if aspect_ratio > 3.0 or aspect_ratio < 0.33:
            scores["corridor"] += 0.6
        
        # Small rooms: likely bathrooms
        if area < 2000:
            scores["bathroom"] += 0.3
        
        # Large rooms: likely living rooms
        if area > 10000:
            scores["living_room"] += 0.4
        
        # Find best match
        best_type = max(scores.items(), key=lambda x: x[1])
        return best_type[0], min(1.0, best_type[1])
    
    def detect_architectural_symbols(self, image: np.ndarray) -> List[Dict]:
        """
        Detect architectural symbols (doors, windows, stairs, etc.)
        
        Returns:
            List of detected symbols
        """
        symbols = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Detect door symbols (arc patterns)
        doors = self._detect_door_symbols(gray)
        symbols.extend(doors)
        
        # Detect window symbols (double lines)
        windows = self._detect_window_symbols(gray)
        symbols.extend(windows)
        
        # Detect stair symbols (parallel lines)
        stairs = self._detect_stair_symbols(gray)
        symbols.extend(stairs)
        
        return symbols
    
    def _detect_door_symbols(self, gray: np.ndarray) -> List[Dict]:
        """Detect door arc symbols"""
        # Use HoughCircles or arc detection
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, 1, 20,
            param1=50, param2=30, minRadius=5, maxRadius=30
        )
        
        doors = []
        if circles is not None:
            for circle in circles[0]:
                x, y, r = circle
                doors.append({
                    "type": "door",
                    "center": [float(x), float(y)],
                    "radius": float(r),
                    "confidence": 0.7
                })
        
        return doors
    
    def _detect_window_symbols(self, gray: np.ndarray) -> List[Dict]:
        """Detect window symbols (double parallel lines)"""
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=20, maxLineGap=5)
        
        windows = []
        if lines is not None:
            # Find parallel line pairs (windows)
            for i, line1 in enumerate(lines):
                for line2 in lines[i+1:]:
                    if self._are_parallel_lines(line1[0], line2[0], threshold=0.1):
                        # Check if close together (window thickness)
                        dist = self._line_distance(line1[0], line2[0])
                        if 2 < dist < 10:
                            mid_x = (line1[0][0] + line1[0][2] + line2[0][0] + line2[0][2]) / 4
                            mid_y = (line1[0][1] + line1[0][3] + line2[0][1] + line2[0][3]) / 4
                            windows.append({
                                "type": "window",
                                "center": [float(mid_x), float(mid_y)],
                                "confidence": 0.6
                            })
        
        return windows
    
    def _detect_stair_symbols(self, gray: np.ndarray) -> List[Dict]:
        """Detect stair symbols (parallel lines pattern)"""
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi/180, 100)
        
        stairs = []
        if lines is not None:
            # Group parallel lines
            parallel_groups = {}
            for line in lines:
                rho, theta = line[0]
                theta_key = int(theta * 180 / np.pi / 5) * 5  # Group by 5 degree bins
                if theta_key not in parallel_groups:
                    parallel_groups[theta_key] = []
                parallel_groups[theta_key].append((rho, theta))
            
            # Stairs have many parallel lines
            for theta_key, group in parallel_groups.items():
                if len(group) >= 5:  # Many parallel lines = stairs
                    avg_rho = np.mean([r for r, _ in group])
                    stairs.append({
                        "type": "stairwell",
                        "position": [float(avg_rho * np.cos(np.radians(theta_key))),
                                    float(avg_rho * np.sin(np.radians(theta_key)))],
                        "confidence": min(1.0, len(group) / 10.0)
                    })
        
        return stairs
    
    def _are_parallel_lines(self, line1, line2, threshold: float = 0.1) -> bool:
        """Check if two lines are parallel"""
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        
        dx1, dy1 = x2 - x1, y2 - y1
        dx2, dy2 = x4 - x3, y4 - y3
        
        angle1 = np.arctan2(dy1, dx1)
        angle2 = np.arctan2(dy2, dx2)
        
        angle_diff = abs(angle1 - angle2)
        return angle_diff < threshold or abs(angle_diff - np.pi) < threshold
    
    def _line_distance(self, line1, line2) -> float:
        """Calculate distance between two parallel lines"""
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        
        # Midpoints
        mid1 = ((x1 + x2) / 2, (y1 + y2) / 2)
        mid2 = ((x3 + x4) / 2, (y3 + y4) / 2)
        
        return np.sqrt((mid1[0] - mid2[0])**2 + (mid1[1] - mid2[1])**2)
    
    def _initialize_room_classifier(self):
        """Initialize room type classifier (could be ML model)"""
        # Placeholder for ML-based room classifier
        return None

class MLFloorPlanRecognizer:
    """
    Main ML-enhanced floor plan recognition system
    Combines all ML models for comprehensive blueprint understanding
    """
    
    def __init__(self):
        self.unet = UNetWallSegmentation()
        self.yolo = YOLOFurnitureDetector()
        self.maskrcnn = MaskRCNNInstanceSegmentation()
        self.semantic_classifier = EnhancedSemanticClassifier()
    
    def process_floor_plan(
        self,
        image_path: str,
        confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Process floor plan with all ML models
        
        Returns:
            Comprehensive recognition results with confidence scores
        """
        if not CV2_AVAILABLE or cv2 is None:
            logger.warning(
                "ML floor plan recognition unavailable because OpenCV is not installed in the backend runtime"
            )
            result = self._empty_result()
            result["image_path"] = image_path
            result["confidence_threshold"] = confidence_threshold
            result["validation"]["warnings"].append("opencv_unavailable")
            return result

        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Could not load image: {image_path}")
            result = self._empty_result()
            result["image_path"] = image_path
            result["confidence_threshold"] = confidence_threshold
            result["validation"]["errors"].append("image_load_failed")
            return result
        
        results = {
            "image_path": image_path,
            "confidence_threshold": confidence_threshold,
            "processing": {}
        }
        
        # 1. Wall segmentation (U-Net)
        logger.info("Segmenting walls with U-Net...")
        wall_mask = self.unet.segment_walls(image)
        walls = self._extract_walls_from_mask(wall_mask, confidence_threshold)
        results["processing"]["wall_segmentation"] = {
            "walls": walls,
            "confidence": self._calculate_wall_confidence(wall_mask),
            "method": "U-Net" if self.unet.model else "OpenCV",
            "wall_mask": wall_mask  # Store for later use
        }
        
        # 2. Furniture detection (YOLOv8)
        logger.info("Detecting furniture with YOLOv8...")
        furniture = self.yolo.detect_furniture(image)
        results["processing"]["furniture_detection"] = {
            "furniture": furniture,
            "count": len(furniture),
            "method": "YOLOv8" if self.yolo.model else "OpenCV"
        }
        
        # 3. Instance segmentation (Mask-RCNN)
        logger.info("Performing instance segmentation with Mask-RCNN...")
        instances = self.maskrcnn.segment_instances(image)
        results["processing"]["instance_segmentation"] = instances
        
        # 4. Semantic classification
        logger.info("Classifying room types...")
        room_classifications = self._classify_rooms_from_instances(
            instances, furniture, walls
        )
        results["processing"]["room_classification"] = room_classifications
        
        # 5. Architectural symbols
        logger.info("Detecting architectural symbols...")
        symbols = self.semantic_classifier.detect_architectural_symbols(image)
        results["processing"]["architectural_symbols"] = symbols
        
        # 6. Enhanced gap detection
        logger.info("Detecting gaps and openings...")
        # Get wall mask from segmentation (or create from walls if not available)
        wall_mask_for_gaps = results["processing"]["wall_segmentation"].get("wall_mask")
        if wall_mask_for_gaps is None:
            # Create wall mask from detected walls
            height, width = image.shape[:2]
            wall_mask_for_gaps = np.zeros((height, width), dtype=np.uint8)
            for wall in walls:
                cv2.line(wall_mask_for_gaps,
                        (int(wall["x1"]), int(wall["y1"])),
                        (int(wall["x2"]), int(wall["y2"])),
                        255, thickness=3)
        
        gap_detection_results = self._detect_enhanced_gaps(wall_mask_for_gaps, walls, symbols)
        results["processing"]["gap_detection"] = gap_detection_results
        
        # 7. Overall confidence
        results["overall_confidence"] = self._calculate_overall_confidence(results)
        
        # 8. Validation metrics
        results["validation"] = self._validate_results(results)
        
        return results
    
    def _extract_walls_from_mask(
        self,
        mask: np.ndarray,
        confidence_threshold: float
    ) -> List[Dict]:
        """Extract wall lines from segmentation mask"""
        # Use HoughLinesP on mask
        lines = cv2.HoughLinesP(
            mask, 1, np.pi/180, 50,
            minLineLength=20, maxLineGap=10
        )
        
        walls = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                
                walls.append({
                    "x1": float(x1),
                    "y1": float(y1),
                    "x2": float(x2),
                    "y2": float(y2),
                    "length": float(length),
                    "confidence": 0.8,  # From U-Net
                    "type": "wall"
                })
        
        return walls
    
    def _calculate_wall_confidence(self, mask: np.ndarray) -> float:
        """Calculate confidence in wall segmentation"""
        # Higher confidence if mask is clear and well-defined
        edge_strength = np.mean(cv2.Canny(mask, 50, 150))
        return min(1.0, edge_strength / 100.0)
    
    def _classify_rooms_from_instances(
        self,
        instances: Dict,
        furniture: List[Dict],
        walls: List[Dict]
    ) -> List[Dict]:
        """Classify room types from instances and furniture"""
        room_classifications = []
        
        for instance in instances.get("instances", []):
            if instance["class_name"] == "room":
                # Get furniture in this room
                room_bbox = instance["bbox"]
                room_furniture = [
                    f for f in furniture
                    if self._is_inside_bbox(f["center"], room_bbox)
                ]
                
                # Calculate room features
                x1, y1, x2, y2 = room_bbox
                area = (x2 - x1) * (y2 - y1)
                aspect_ratio = (x2 - x1) / (y2 - y1) if (y2 - y1) > 0 else 1.0
                
                room_features = {
                    "area": area,
                    "aspect_ratio": aspect_ratio
                }
                
                # Classify room type
                room_type, confidence = self.semantic_classifier.classify_room_type(
                    instance["mask"], room_furniture, room_features
                )
                
                room_classifications.append({
                    "room_id": len(room_classifications),
                    "bbox": room_bbox,
                    "room_type": room_type,
                    "confidence": confidence,
                    "furniture_count": len(room_furniture),
                    "area": area
                })
        
        return room_classifications
    
    def _is_inside_bbox(self, point: List[float], bbox: List[float]) -> bool:
        """Check if point is inside bounding box"""
        x, y = point
        x1, y1, x2, y2 = bbox
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def _detect_enhanced_gaps(
        self,
        wall_mask: np.ndarray,
        walls: List[Dict],
        symbols: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """Enhanced gap detection with better analysis"""
        gaps = {
            "doors": [],
            "corridors": [],
            "openings": []
        }
        
        # Invert wall mask to get open spaces
        open_spaces = cv2.bitwise_not(wall_mask)
        
        # Find connected components (gaps)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            open_spaces, connectivity=8
        )
        
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            
            aspect_ratio = w / h if h > 0 else 0
            
            # Classify gap type
            if 50 < area < 2000:  # Door size
                # Check if near door symbol
                near_door = any(
                    np.sqrt((x + w/2 - sym["center"][0])**2 + 
                           (y + h/2 - sym["center"][1])**2) < 20
                    for sym in symbols if sym["type"] == "door"
                )
                
                gaps["doors"].append({
                    "x": float(x + w/2),
                    "y": float(y + h/2),
                    "width": float(max(w, h)),
                    "height": float(min(w, h)),
                    "area": float(area),
                    "confidence": 0.8 if near_door else 0.6,
                    "type": "door"
                })
            elif aspect_ratio > 3.0 or aspect_ratio < 0.33:  # Corridor
                gaps["corridors"].append({
                    "x": float(x + w/2),
                    "y": float(y + h/2),
                    "width": float(w),
                    "height": float(h),
                    "area": float(area),
                    "confidence": 0.7,
                    "type": "corridor"
                })
            else:  # General opening
                gaps["openings"].append({
                    "x": float(x + w/2),
                    "y": float(y + h/2),
                    "width": float(w),
                    "height": float(h),
                    "area": float(area),
                    "confidence": 0.5,
                    "type": "opening"
                })
        
        return gaps
    
    def _calculate_overall_confidence(self, results: Dict) -> float:
        """Calculate overall confidence score"""
        confidences = []
        
        # Wall segmentation confidence
        if "wall_segmentation" in results["processing"]:
            confidences.append(results["processing"]["wall_segmentation"]["confidence"])
        
        # Furniture detection confidence (average)
        if "furniture_detection" in results["processing"]:
            furniture = results["processing"]["furniture_detection"]["furniture"]
            if furniture:
                avg_conf = np.mean([f["confidence"] for f in furniture])
                confidences.append(avg_conf)
        
        # Instance segmentation confidence (average)
        if "instance_segmentation" in results["processing"]:
            instances = results["processing"]["instance_segmentation"]["instances"]
            if instances:
                avg_conf = np.mean([i["confidence"] for i in instances])
                confidences.append(avg_conf)
        
        # Room classification confidence (average)
        if "room_classification" in results["processing"]:
            rooms = results["processing"]["room_classification"]
            if rooms:
                avg_conf = np.mean([r["confidence"] for r in rooms])
                confidences.append(avg_conf)
        
        return np.mean(confidences) if confidences else 0.5
    
    def _validate_results(self, results: Dict) -> Dict:
        """Validate recognition results"""
        validation = {
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        # Check for missing elements
        if not results["processing"].get("wall_segmentation", {}).get("walls"):
            validation["warnings"].append("No walls detected")
        
        if not results["processing"].get("furniture_detection", {}).get("furniture"):
            validation["warnings"].append("No furniture detected")
        
        # Check confidence levels
        overall_conf = results.get("overall_confidence", 0.5)
        if overall_conf < 0.5:
            validation["warnings"].append(f"Low overall confidence: {overall_conf:.2f}")
        
        # Check for reasonable counts
        wall_count = len(results["processing"].get("wall_segmentation", {}).get("walls", []))
        if wall_count < 10:
            validation["warnings"].append(f"Very few walls detected: {wall_count}")
        
        return validation
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "image_path": "",
            "confidence_threshold": 0.5,
            "processing": {},
            "overall_confidence": 0.0,
            "validation": {"warnings": [], "errors": [], "suggestions": []}
        }

# Global ML recognizer instance
ml_floorplan_recognizer = MLFloorPlanRecognizer()

