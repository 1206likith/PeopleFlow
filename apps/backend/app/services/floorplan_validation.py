"""
Floor Plan Validation and Refinement
Tests on diverse floor plans, parameter tuning, confidence scores
"""

import numpy as np
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ValidationMetrics:
    """Validation metrics for floor plan recognition"""
    overall_accuracy: float
    wall_detection_accuracy: float
    room_detection_accuracy: float
    door_detection_accuracy: float
    furniture_detection_accuracy: float
    confidence_scores: Dict[str, float]
    parameter_sensitivity: Dict[str, float]

class FloorPlanValidator:
    """
    Validates floor plan recognition on diverse test cases
    Tunes parameters for different building types
    """
    
    def __init__(self):
        self.test_cases: List[Dict] = []
        self.parameter_ranges = {
            "min_wall_length": (10, 50),
            "min_exit_width": (5, 20),
            "wall_thickness": (1, 5),
            "gap_detection_threshold": (0.3, 0.7),
            "furniture_confidence": (0.2, 0.5)
        }
    
    def validate_recognition(
        self,
        recognition_results: Dict,
        ground_truth: Optional[Dict] = None
    ) -> ValidationMetrics:
        """
        Validate recognition results against ground truth
        
        Args:
            recognition_results: Results from ML recognizer
            ground_truth: Optional ground truth annotations
        
        Returns:
            Validation metrics
        """
        if ground_truth is None:
            # Self-validation without ground truth
            return self._self_validate(recognition_results)
        
        # Compare with ground truth
        metrics = ValidationMetrics(
            overall_accuracy=0.0,
            wall_detection_accuracy=0.0,
            room_detection_accuracy=0.0,
            door_detection_accuracy=0.0,
            furniture_detection_accuracy=0.0,
            confidence_scores={},
            parameter_sensitivity={}
        )
        
        # Wall detection accuracy
        if "walls" in ground_truth:
            metrics.wall_detection_accuracy = self._calculate_wall_accuracy(
                recognition_results.get("processing", {}).get("wall_segmentation", {}).get("walls", []),
                ground_truth["walls"]
            )
        
        # Room detection accuracy
        if "rooms" in ground_truth:
            metrics.room_detection_accuracy = self._calculate_room_accuracy(
                recognition_results.get("processing", {}).get("room_classification", []),
                ground_truth["rooms"]
            )
        
        # Door detection accuracy
        if "doors" in ground_truth:
            metrics.door_detection_accuracy = self._calculate_door_accuracy(
                recognition_results.get("processing", {}).get("gap_detection", {}).get("doors", []),
                ground_truth["doors"]
            )
        
        # Furniture detection accuracy
        if "furniture" in ground_truth:
            metrics.furniture_detection_accuracy = self._calculate_furniture_accuracy(
                recognition_results.get("processing", {}).get("furniture_detection", {}).get("furniture", []),
                ground_truth["furniture"]
            )
        
        # Overall accuracy (weighted average)
        metrics.overall_accuracy = (
            metrics.wall_detection_accuracy * 0.3 +
            metrics.room_detection_accuracy * 0.3 +
            metrics.door_detection_accuracy * 0.2 +
            metrics.furniture_detection_accuracy * 0.2
        )
        
        # Confidence scores
        metrics.confidence_scores = {
            "overall": recognition_results.get("overall_confidence", 0.0),
            "walls": recognition_results.get("processing", {}).get("wall_segmentation", {}).get("confidence", 0.0),
            "furniture": np.mean([
                f.get("confidence", 0.0) 
                for f in recognition_results.get("processing", {}).get("furniture_detection", {}).get("furniture", [])
            ]) if recognition_results.get("processing", {}).get("furniture_detection", {}).get("furniture") else 0.0
        }
        
        return metrics
    
    def _self_validate(self, results: Dict) -> ValidationMetrics:
        """Self-validation without ground truth"""
        # Check for reasonable results
        warnings = results.get("validation", {}).get("warnings", [])
        errors = results.get("validation", {}).get("errors", [])
        
        # Calculate confidence-based accuracy estimate
        overall_conf = results.get("overall_confidence", 0.5)
        
        # Penalize for warnings/errors
        penalty = len(warnings) * 0.1 + len(errors) * 0.2
        estimated_accuracy = max(0.0, overall_conf - penalty)
        
        return ValidationMetrics(
            overall_accuracy=estimated_accuracy,
            wall_detection_accuracy=results.get("processing", {}).get("wall_segmentation", {}).get("confidence", 0.5),
            room_detection_accuracy=0.5,  # Cannot estimate without ground truth
            door_detection_accuracy=0.5,
            furniture_detection_accuracy=0.5,
            confidence_scores={"overall": overall_conf},
            parameter_sensitivity={}
        )
    
    def _calculate_wall_accuracy(
        self,
        detected_walls: List[Dict],
        ground_truth_walls: List[Dict],
        tolerance: float = 10.0
    ) -> float:
        """Calculate wall detection accuracy"""
        if not ground_truth_walls:
            return 0.0
        
        matched = 0
        for gt_wall in ground_truth_walls:
            for det_wall in detected_walls:
                # Check if walls match (similar position and angle)
                if self._walls_match(gt_wall, det_wall, tolerance):
                    matched += 1
                    break
        
        return matched / len(ground_truth_walls)
    
    def _walls_match(
        self,
        wall1: Dict,
        wall2: Dict,
        tolerance: float
    ) -> bool:
        """Check if two walls match"""
        # Check if endpoints are close
        dist1 = np.sqrt((wall1.get("x1", 0) - wall2.get("x1", 0))**2 + 
                       (wall1.get("y1", 0) - wall2.get("y1", 0))**2)
        dist2 = np.sqrt((wall1.get("x2", 0) - wall2.get("x2", 0))**2 + 
                       (wall1.get("y2", 0) - wall2.get("y2", 0))**2)
        
        return dist1 < tolerance and dist2 < tolerance
    
    def _calculate_room_accuracy(
        self,
        detected_rooms: List[Dict],
        ground_truth_rooms: List[Dict],
        iou_threshold: float = 0.5
    ) -> float:
        """Calculate room detection accuracy using IoU"""
        if not ground_truth_rooms:
            return 0.0
        
        matched = 0
        for gt_room in ground_truth_rooms:
            for det_room in detected_rooms:
                iou = self._calculate_iou(gt_room.get("bbox", []), det_room.get("bbox", []))
                if iou > iou_threshold:
                    matched += 1
                    break
        
        return matched / len(ground_truth_rooms)
    
    def _calculate_door_accuracy(
        self,
        detected_doors: List[Dict],
        ground_truth_doors: List[Dict],
        distance_threshold: float = 20.0
    ) -> float:
        """Calculate door detection accuracy"""
        if not ground_truth_doors:
            return 0.0
        
        matched = 0
        for gt_door in ground_truth_doors:
            gt_pos = (gt_door.get("x", 0), gt_door.get("y", 0))
            for det_door in detected_doors:
                det_pos = (det_door.get("x", 0), det_door.get("y", 0))
                dist = np.sqrt((gt_pos[0] - det_pos[0])**2 + (gt_pos[1] - det_pos[1])**2)
                if dist < distance_threshold:
                    matched += 1
                    break
        
        return matched / len(ground_truth_doors)
    
    def _calculate_furniture_accuracy(
        self,
        detected_furniture: List[Dict],
        ground_truth_furniture: List[Dict],
        iou_threshold: float = 0.3
    ) -> float:
        """Calculate furniture detection accuracy"""
        if not ground_truth_furniture:
            return 0.0
        
        matched = 0
        for gt_furn in ground_truth_furniture:
            for det_furn in detected_furniture:
                iou = self._calculate_iou(gt_furn.get("bbox", []), det_furn.get("bbox", []))
                if iou > iou_threshold:
                    matched += 1
                    break
        
        return matched / len(ground_truth_furniture)
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate Intersection over Union (IoU)"""
        if len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        
        x1_1, y1_1, x2_1, y2_1 = bbox1[:4]
        x1_2, y1_2, x2_2, y2_2 = bbox2[:4]
        
        # Intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def tune_parameters(
        self,
        test_images: List[str],
        ground_truths: List[Dict],
        building_type: str = "residential"
    ) -> Dict[str, float]:
        """
        Tune parameters for specific building type
        
        Args:
            test_images: List of test image paths
            ground_truths: List of ground truth annotations
            building_type: Type of building (residential, commercial, etc.)
        
        Returns:
            Optimized parameters
        """
        best_params = {}
        best_accuracy = 0.0
        
        # Grid search over parameter ranges
        for min_wall_len in range(10, 51, 10):
            for min_exit_width in range(5, 21, 5):
                # Test these parameters
                accuracy = self._test_parameters(
                    test_images, ground_truths,
                    {"min_wall_length": min_wall_len, "min_exit_width": min_exit_width}
                )
                
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_params = {
                        "min_wall_length": min_wall_len,
                        "min_exit_width": min_exit_width
                    }
        
        logger.info(f"Best parameters for {building_type}: {best_params} (accuracy: {best_accuracy:.2f})")
        return best_params
    
    def _test_parameters(
        self,
        test_images: List[str],
        ground_truths: List[Dict],
        parameters: Dict[str, float]
    ) -> float:
        """Test parameters and return average accuracy"""
        # This would run recognition with parameters and compare with ground truth
        # Simplified for now
        return 0.7  # Placeholder
    
    def generate_confidence_report(self, results: Dict) -> Dict:
        """Generate detailed confidence report"""
        report = {
            "overall_confidence": results.get("overall_confidence", 0.0),
            "component_confidences": {},
            "recommendations": []
        }
        
        # Component confidences
        processing = results.get("processing", {})
        
        if "wall_segmentation" in processing:
            report["component_confidences"]["walls"] = processing["wall_segmentation"].get("confidence", 0.0)
        
        if "furniture_detection" in processing:
            furniture = processing["furniture_detection"].get("furniture", [])
            if furniture:
                report["component_confidences"]["furniture"] = np.mean([f.get("confidence", 0.0) for f in furniture])
        
        if "room_classification" in processing:
            rooms = processing["room_classification"]
            if rooms:
                report["component_confidences"]["rooms"] = np.mean([r.get("confidence", 0.0) for r in rooms])
        
        # Recommendations
        if report["overall_confidence"] < 0.5:
            report["recommendations"].append("Low overall confidence - consider retraining models or improving image quality")
        
        if report["component_confidences"].get("walls", 0.0) < 0.6:
            report["recommendations"].append("Wall detection confidence low - check image preprocessing")
        
        if report["component_confidences"].get("furniture", 0.0) < 0.5:
            report["recommendations"].append("Furniture detection confidence low - model may need retraining")
        
        return report

# Global validator instance
floorplan_validator = FloorPlanValidator()

