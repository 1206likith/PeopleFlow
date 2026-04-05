"""
Advanced Floor Plan Processor
Uses OpenCV and computer vision to detect walls, exits, obstacles, and boundaries
Now integrates with semantic understanding engine
"""
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
import numpy as np
import logging
import json
import time
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
try:
    from PIL import Image
except ImportError:
    Image = None
from app.services.floor_plan_document_service import normalize_detected_obstacles
from app.services.semantic_floorplan import semantic_processor

logger = logging.getLogger(__name__)


class FloorPlanProcessor:
    """Advanced floor plan image processing with improved recognition"""
    
    def __init__(self):
        self.min_wall_length = 28  # Minimum wall length in pixels
        self.min_exit_width = 10   # Minimum exit width in pixels
        self.wall_thickness = 3    # Expected wall thickness in pixels
        self.angle_snap_tolerance_deg = 7.0
        self.wall_merge_gap = 8.0
        self.wall_merge_axis_tolerance = 4.0
        self.enable_angle_snap = True
        self.enable_multiscale = True
        self.max_exit_width_ratio = 0.12
        self.max_exit_count = 24
        self.endpoint_cluster_tolerance = 6.0
        self.short_wall_ratio_limit = 0.04

    def _init_debug(self, enabled: bool, debug_dir: Optional[str], image_path: str) -> Optional[Dict]:
        if not enabled:
            return None
        base_dir = Path(debug_dir) if debug_dir else Path("artifacts") / "floorplan_debug"
        run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{Path(image_path).stem}"
        out_dir = base_dir / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        return {"dir": out_dir, "steps": []}

    def _save_debug_image(self, debug: Optional[Dict], name: str, image: np.ndarray) -> None:
        if not debug:
            return
        out_path = debug["dir"] / f"{name}.png"
        try:
            cv2.imwrite(str(out_path), image)
            debug["steps"].append({"name": name, "path": str(out_path)})
        except Exception as e:
            logger.warning(f"Failed to write debug image {name}: {e}")

    def _save_debug_json(self, debug: Optional[Dict], payload: Dict) -> None:
        if not debug:
            return
        out_path = debug["dir"] / "debug.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write debug json: {e}")

    @staticmethod
    def _opencv_ready() -> bool:
        return bool(CV2_AVAILABLE and cv2 is not None)

    @staticmethod
    def _load_image_dimensions_fallback(image_path: str) -> Dict[str, int]:
        if Image is None:
            return {}
        try:
            with Image.open(image_path) as image:
                return {"width": int(image.width), "height": int(image.height)}
        except Exception:
            return {}

    def _enhance_contrast(self, gray: np.ndarray) -> np.ndarray:
        """Improve contrast for faint blueprint lines."""
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(gray)
        except Exception:
            return gray

    def _filter_small_components(
        self,
        binary_mask: np.ndarray,
        min_area: int,
        min_span: int,
    ) -> np.ndarray:
        """Remove tiny connected components (text speckles/noise) while preserving long wall strokes."""
        if binary_mask is None or binary_mask.size == 0:
            return binary_mask

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
        cleaned = np.zeros_like(binary_mask)
        for label in range(1, num_labels):
            area = int(stats[label, cv2.CC_STAT_AREA])
            width = int(stats[label, cv2.CC_STAT_WIDTH])
            height = int(stats[label, cv2.CC_STAT_HEIGHT])
            longest = max(width, height)
            shortest = max(1, min(width, height))

            # Keep plausible wall components and remove tiny textual fragments.
            if area < min_area and longest < min_span:
                continue
            if area < max(10, min_area // 2) and longest < min_span * 1.5 and shortest < 3:
                continue
            cleaned[labels == label] = 255
        return cleaned

    def _preprocess_pipeline(self, gray: np.ndarray) -> Dict[str, np.ndarray]:
        """Preprocess image and return intermediate results."""
        contrast = self._enhance_contrast(gray)
        blurred = cv2.GaussianBlur(contrast, (5, 5), 0)

        # Adaptive + Otsu thresholds to capture linework
        adaptive = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        _, otsu = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        ink_raw = cv2.bitwise_or(adaptive, otsu)

        # Morphological cleanup to connect walls
        kernel = np.ones((3, 3), np.uint8)
        ink = cv2.morphologyEx(ink_raw, cv2.MORPH_CLOSE, kernel, iterations=2)
        ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel, iterations=1)

        height, width = gray.shape
        min_component_area = max(14, int((width * height) * 0.00001))
        min_component_span = max(9, int(min(width, height) * 0.015))
        ink = self._filter_small_components(
            ink,
            min_area=min_component_area,
            min_span=min_component_span,
        )

        # Extract structural linework; this aggressively suppresses text/furniture clutter.
        structural_scale = max(12, int(min(width, height) * 0.022))
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (structural_scale, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, structural_scale))
        horizontal_lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, vertical_kernel)
        structure = cv2.bitwise_or(horizontal_lines, vertical_lines)
        structure = cv2.morphologyEx(structure, cv2.MORPH_CLOSE, kernel, iterations=1)
        structure = cv2.dilate(structure, np.ones((2, 2), np.uint8), iterations=1)

        edges = cv2.Canny(blurred, 50, 150)
        combined = cv2.bitwise_or(structure, cv2.bitwise_and(ink, edges))
        combined = cv2.bitwise_or(combined, structure)

        return {
            "contrast": contrast,
            "blurred": blurred,
            "adaptive": adaptive,
            "otsu": otsu,
            "ink_raw": ink_raw,
            "ink": ink,
            "horizontal_lines": horizontal_lines,
            "vertical_lines": vertical_lines,
            "structure": structure,
            "edges": edges,
            "combined": combined,
        }

    def _hough_lines(
        self,
        processed: np.ndarray,
        scale: float = 1.0,
    ) -> List[Tuple[int, int, int, int]]:
        height, width = processed.shape
        threshold = max(40, int(min(width, height) * 0.08))
        min_line_length = max(self.min_wall_length * scale, min(width, height) * 0.03)
        max_line_gap = max(6, min(width, height) * 0.015)

        lines = cv2.HoughLinesP(
            processed,
            rho=1,
            theta=np.pi / 180,
            threshold=threshold,
            minLineLength=int(min_line_length),
            maxLineGap=int(max_line_gap),
        )
        if lines is None:
            return []
        return [tuple(line[0]) for line in lines]

    def _detect_lines_multiscale(self, processed: np.ndarray) -> List[Tuple[int, int, int, int]]:
        height, width = processed.shape
        lines: List[Tuple[int, int, int, int]] = []
        lines.extend(self._hough_lines(processed, scale=1.0))

        if self.enable_multiscale and min(width, height) > 600:
            scale = 0.5
            scaled = cv2.resize(processed, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
            scaled_lines = self._hough_lines(scaled, scale=scale)
            for x1, y1, x2, y2 in scaled_lines:
                lines.append((int(x1 / scale), int(y1 / scale), int(x2 / scale), int(y2 / scale)))

        return lines

    def _line_confidence(
        self,
        ink_mask: Optional[np.ndarray],
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> Optional[float]:
        if ink_mask is None:
            return None
        height, width = ink_mask.shape
        length = max(1.0, np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
        samples = max(8, int(length / 6))
        hits = 0
        total = 0
        for i in range(samples + 1):
            t = i / samples
            x = int(round(x1 + (x2 - x1) * t))
            y = int(round(y1 + (y2 - y1) * t))
            if 0 <= x < width and 0 <= y < height:
                total += 1
                if ink_mask[y, x] > 0:
                    hits += 1
        if total == 0:
            return None
        return round(hits / total, 3)

    def _snap_walls_to_axes(self, walls: List[Dict]) -> List[Dict]:
        if not walls or not self.enable_angle_snap:
            return walls

        snapped = []
        targets = [0.0, 45.0, 90.0, 135.0]

        def angle_diff(a: float, b: float) -> float:
            diff = abs(a - b)
            return min(diff, 180 - diff)

        for wall in walls:
            x1, y1, x2, y2 = wall["x1"], wall["y1"], wall["x2"], wall["y2"]
            dx = x2 - x1
            dy = y2 - y1
            angle = (np.degrees(np.arctan2(dy, dx)) + 180) % 180
            snapped_angle = None
            for target in targets:
                if angle_diff(angle, target) <= self.angle_snap_tolerance_deg:
                    snapped_angle = target
                    break

            if snapped_angle is None:
                wall["angle"] = float(angle)
                wall["orientation"] = "diagonal"
                snapped.append(wall)
                continue

            length = float(np.sqrt(dx * dx + dy * dy))
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2

            if snapped_angle in (0.0, 180.0):
                y1 = y2 = my
                wall["orientation"] = "horizontal"
                wall["angle"] = 0.0
            elif snapped_angle == 90.0:
                x1 = x2 = mx
                wall["orientation"] = "vertical"
                wall["angle"] = 90.0
            else:
                rad = np.radians(snapped_angle)
                half = length / 2
                dxs = np.cos(rad) * half
                dys = np.sin(rad) * half
                x1 = mx - dxs
                y1 = my - dys
                x2 = mx + dxs
                y2 = my + dys
                wall["orientation"] = "diagonal"
                wall["angle"] = float(snapped_angle)

            wall["x1"] = float(x1)
            wall["y1"] = float(y1)
            wall["x2"] = float(x2)
            wall["y2"] = float(y2)
            wall["length"] = float(length)
            snapped.append(wall)

        return snapped

    def _merge_axis_walls(self, walls: List[Dict]) -> List[Dict]:
        if not walls:
            return []

        merged: List[Dict] = []
        horizontals = [w for w in walls if w.get("orientation") == "horizontal"]
        verticals = [w for w in walls if w.get("orientation") == "vertical"]
        others = [w for w in walls if w.get("orientation") not in ("horizontal", "vertical")]

        def merge_group(group: List[Dict], axis: str) -> List[Dict]:
            if not group:
                return []
            tol = self.wall_merge_axis_tolerance
            gap = self.wall_merge_gap
            buckets: Dict[float, List[Dict]] = {}
            for wall in group:
                coord = float(wall["y1"] if axis == "y" else wall["x1"])
                key = round(coord / tol) * tol
                buckets.setdefault(key, []).append(wall)

            merged_group: List[Dict] = []
            for key, walls_in_bucket in buckets.items():
                if axis == "y":
                    walls_in_bucket.sort(key=lambda w: min(w["x1"], w["x2"]))
                else:
                    walls_in_bucket.sort(key=lambda w: min(w["y1"], w["y2"]))

                current = None
                for wall in walls_in_bucket:
                    if axis == "y":
                        start = min(wall["x1"], wall["x2"])
                        end = max(wall["x1"], wall["x2"])
                    else:
                        start = min(wall["y1"], wall["y2"])
                        end = max(wall["y1"], wall["y2"])

                    if current is None:
                        current = {
                            "start": start,
                            "end": end,
                            "coord": key,
                            "type": wall.get("type", "internal"),
                            "thickness": wall.get("thickness", self.wall_thickness),
                            "confidence": wall.get("confidence"),
                        }
                        continue

                    if start <= current["end"] + gap:
                        current["end"] = max(current["end"], end)
                        if wall.get("type") == "boundary":
                            current["type"] = "boundary"
                        if wall.get("confidence") is not None:
                            if current.get("confidence") is None:
                                current["confidence"] = wall.get("confidence")
                            else:
                                current["confidence"] = max(current["confidence"], wall.get("confidence"))
                    else:
                        merged_group.append(current)
                        current = {
                            "start": start,
                            "end": end,
                            "coord": key,
                            "type": wall.get("type", "internal"),
                            "thickness": wall.get("thickness", self.wall_thickness),
                            "confidence": wall.get("confidence"),
                        }

                if current:
                    merged_group.append(current)

            final: List[Dict] = []
            for segment in merged_group:
                if axis == "y":
                    x1, x2 = segment["start"], segment["end"]
                    y1 = y2 = segment["coord"]
                else:
                    y1, y2 = segment["start"], segment["end"]
                    x1 = x2 = segment["coord"]

                length = float(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
                final.append({
                    "x1": float(x1),
                    "y1": float(y1),
                    "x2": float(x2),
                    "y2": float(y2),
                    "length": length,
                    "type": segment.get("type", "internal"),
                    "thickness": float(segment.get("thickness", self.wall_thickness)),
                    "orientation": "horizontal" if axis == "y" else "vertical",
                    "angle": 0.0 if axis == "y" else 90.0,
                    "confidence": segment.get("confidence"),
                })

            return final

        merged.extend(merge_group(horizontals, axis="y"))
        merged.extend(merge_group(verticals, axis="x"))
        merged.extend(others)
        return merged

    def _compute_boundary_polygon(self, boundaries: List[Dict]) -> Tuple[List[Dict], float]:
        points: List[Tuple[float, float]] = []
        for boundary in boundaries or []:
            points.append((float(boundary.get("x1", 0.0)), float(boundary.get("y1", 0.0))))
            points.append((float(boundary.get("x2", 0.0)), float(boundary.get("y2", 0.0))))
        if not points:
            return [], 0.0
        pts = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
        hull = cv2.convexHull(pts)
        area = float(cv2.contourArea(hull))
        polygon = [{"x": float(p[0][0]), "y": float(p[0][1])} for p in hull]
        return polygon, area

    def _wall_angle_deg(self, wall: Dict) -> float:
        dx = float(wall.get("x2", 0.0)) - float(wall.get("x1", 0.0))
        dy = float(wall.get("y2", 0.0)) - float(wall.get("y1", 0.0))
        angle = abs(np.degrees(np.arctan2(dy, dx))) % 180
        if angle > 90:
            angle = 180 - angle
        return float(angle)

    def _is_near_orthogonal(self, wall: Dict, tolerance: float = 12.0) -> bool:
        angle = self._wall_angle_deg(wall)
        return min(abs(angle), abs(90.0 - angle)) <= tolerance

    def _wall_midpoint(self, wall: Dict) -> Tuple[float, float]:
        return (
            (float(wall.get("x1", 0.0)) + float(wall.get("x2", 0.0))) * 0.5,
            (float(wall.get("y1", 0.0)) + float(wall.get("y2", 0.0))) * 0.5,
        )

    def _is_boundary_type(self, wall: Dict) -> bool:
        wall_type = str(wall.get("type", "")).lower()
        return "boundary" in wall_type or wall_type in {"top", "bottom", "left", "right"}

    def _remove_isolated_internal_walls(
        self,
        walls: List[Dict],
        boundaries: List[Dict],
        width: int,
        height: int,
    ) -> List[Dict]:
        """Drop short isolated internal segments likely caused by furniture/text linework."""
        if not walls:
            return []

        min_span = float(max(1.0, min(width, height)))
        endpoint_tol = max(2.0, min_span * 0.006)
        endpoint_bins: Dict[Tuple[int, int], int] = {}

        def endpoint_key(x: float, y: float) -> Tuple[int, int]:
            return (int(round(x / endpoint_tol)), int(round(y / endpoint_tol)))

        for wall in walls:
            x1, y1 = float(wall.get("x1", 0.0)), float(wall.get("y1", 0.0))
            x2, y2 = float(wall.get("x2", 0.0)), float(wall.get("y2", 0.0))
            endpoint_bins[endpoint_key(x1, y1)] = endpoint_bins.get(endpoint_key(x1, y1), 0) + 1
            endpoint_bins[endpoint_key(x2, y2)] = endpoint_bins.get(endpoint_key(x2, y2), 0) + 1

        min_keep_len = max(14.0, min_span * self.short_wall_ratio_limit)
        boundary_keep_dist = max(6.0, min_span * 0.025)
        cleaned: List[Dict] = []

        for wall in walls:
            if self._is_boundary_type(wall):
                cleaned.append(wall)
                continue

            length = float(wall.get("length", 0.0))
            confidence = wall.get("confidence")
            confidence_value = float(confidence) if confidence is not None else None

            # Always keep long walls even if isolated.
            if length >= max(min_keep_len * 2.2, min_span * 0.09):
                cleaned.append(wall)
                continue

            x1, y1 = float(wall.get("x1", 0.0)), float(wall.get("y1", 0.0))
            x2, y2 = float(wall.get("x2", 0.0)), float(wall.get("y2", 0.0))
            degree = endpoint_bins.get(endpoint_key(x1, y1), 0) + endpoint_bins.get(endpoint_key(x2, y2), 0)
            if degree >= 5:
                cleaned.append(wall)
                continue

            mx, my = self._wall_midpoint(wall)
            dist_boundary, _ = self._distance_to_boundaries(mx, my, boundaries)
            near_boundary = dist_boundary is not None and dist_boundary <= boundary_keep_dist

            if near_boundary and length >= min_keep_len * 0.75:
                cleaned.append(wall)
                continue

            if confidence_value is not None and confidence_value >= 0.74 and length >= min_keep_len:
                cleaned.append(wall)
                continue

        return cleaned

    def _stabilize_walls(
        self,
        walls: List[Dict],
        width: int,
        height: int,
        boundaries: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        if not walls:
            return []

        min_span = float(max(1.0, min(width, height)))
        orth_count = 0
        diagonal_count = 0
        for wall in walls:
            angle = self._wall_angle_deg(wall)
            if "angle" not in wall:
                wall["angle"] = float(angle)
            if "orientation" not in wall:
                wall["orientation"] = "horizontal" if abs(angle) <= 8 else ("vertical" if abs(90 - angle) <= 8 else "diagonal")
            if self._is_near_orthogonal(wall):
                orth_count += 1
            else:
                diagonal_count += 1

        # Suppress line storms from screenshots/noisy scans that generate many long diagonals.
        if len(walls) > 260 and diagonal_count > orth_count * 0.55:
            filtered: List[Dict] = []
            for wall in walls:
                wall_type = str(wall.get("type", "internal"))
                is_boundary = wall_type in {"boundary", "external_boundary", "top", "bottom", "left", "right"}
                length = float(wall.get("length", 0.0))
                confidence = wall.get("confidence")
                confidence_value = float(confidence) if confidence is not None else None
                near_orth = self._is_near_orthogonal(wall)

                if is_boundary:
                    filtered.append(wall)
                    continue

                if near_orth:
                    if length >= max(16.0, min_span * 0.03):
                        if confidence_value is None or confidence_value >= 0.35 or length >= min_span * 0.1:
                            filtered.append(wall)
                    continue

                if length <= min_span * 0.1 and (confidence_value is None or confidence_value >= 0.7):
                    filtered.append(wall)

            walls = filtered
            if len(walls) > 520:
                walls.sort(
                    key=lambda wall: (
                        1 if str(wall.get("type", "")) in {"boundary", "external_boundary"} else 0,
                        1 if self._is_near_orthogonal(wall) else 0,
                        float(wall.get("confidence", 0.0) or 0.0),
                        float(wall.get("length", 0.0)),
                    ),
                    reverse=True,
                )
                walls = walls[:520]

        walls = self._remove_isolated_internal_walls(
            walls,
            boundaries or [],
            width,
            height,
        )

        # Final sort/cap by geometric usefulness.
        if len(walls) > 900:
            walls.sort(
                key=lambda wall: (
                    1 if str(wall.get("type", "")) in {"boundary", "external_boundary"} else 0,
                    1 if self._is_near_orthogonal(wall) else 0,
                    float(wall.get("confidence", 0.0) or 0.0),
                    float(wall.get("length", 0.0)),
                ),
                reverse=True,
            )
            walls = walls[:900]

        return walls
        
    def process_floor_plan(
        self,
        image_path: str,
        use_semantic: bool = True,
        debug: bool = False,
        debug_dir: Optional[str] = None,
    ) -> Dict:
        """
        Process floor plan image to detect:
        - Walls (boundaries and internal walls)
        - Exits (openings, doors)
        - Obstacles (furniture, columns)
        - Building boundaries
        - Room boundaries
        
        Returns comprehensive detection results
        """
        debug_ctx = self._init_debug(debug, debug_dir, image_path)
        start_time = time.time()
        pipeline_mode = "traditional"
        pipeline_steps: List[Dict[str, Any]] = []

        def record_step(name: str, step_start: float, **extra) -> None:
            pipeline_steps.append({
                "name": name,
                "duration_ms": int((time.perf_counter() - step_start) * 1000),
                **extra,
            })

        try:
            if not self._opencv_ready():
                runtime_start = time.perf_counter()
                image_dimensions = self._load_image_dimensions_fallback(image_path)
                record_step("opencv_runtime", runtime_start, success=False)
                logger.error(
                    "OpenCV runtime unavailable for floor plan processing; install opencv-python-headless in the backend environment"
                )
                result = self._empty_result()
                result["pipeline"] = "opencv_unavailable"
                result["processing_error"] = "opencv_unavailable"
                result["image_dimensions"] = image_dimensions
                result["processing_time_ms"] = int((time.time() - start_time) * 1000)
                result["pipeline_steps"] = pipeline_steps
                return result

            # Use semantic processor if available and requested
            if use_semantic:
                try:
                    semantic_start = time.perf_counter()
                    semantic_result = semantic_processor.process_semantic(image_path, use_ml=True)
                    record_step(
                        "semantic_processing",
                        semantic_start,
                        processed=bool(semantic_result.get("processed")),
                    )
                    if semantic_result.get("processed"):
                        logger.info("Using semantic floorplan processing")
                        # Convert semantic results to floor plan processor format
                        result = self._convert_semantic_results(semantic_result)
                        pipeline_mode = "semantic"
                        # Quality assessment (best-effort without raw pipeline)
                        dims = result.get("image_dimensions", {})
                        width = int(dims.get("width", 0)) if dims else 0
                        height = int(dims.get("height", 0)) if dims else 0
                        quality_start = time.perf_counter()
                        result["quality"] = self._assess_quality(result, None, width, height)
                        record_step(
                            "quality_assessment",
                            quality_start,
                            score=result.get("quality", {}).get("score"),
                        )
                        result["pipeline"] = pipeline_mode
                        result["processing_time_ms"] = int((time.time() - start_time) * 1000)
                        result["pipeline_steps"] = pipeline_steps
                        if debug_ctx:
                            debug_payload = {
                                "mode": "semantic",
                                "image_path": image_path,
                                "summary": {
                                    "wall_count": result.get("wall_count", 0),
                                    "exit_count": result.get("exit_count", 0),
                                    "obstacle_count": result.get("obstacle_count", 0),
                                    "room_count": result.get("room_count", 0),
                                },
                                "quality": result.get("quality", {}),
                            }
                            self._save_debug_json(debug_ctx, debug_payload)
                            result["debug"] = {
                                "dir": str(debug_ctx["dir"]),
                                "steps": debug_ctx["steps"],
                                "mode": "semantic",
                            }
                        return result
                except Exception as e:
                    logger.warning(f"Semantic processing failed, falling back to traditional: {e}")
            
            # Traditional OpenCV-based processing (fallback)
            # Load image
            load_start = time.perf_counter()
            img = cv2.imread(image_path)
            record_step("load_image", load_start, success=img is not None)
            if img is None:
                logger.error(f"Could not load image: {image_path}")
                result = self._empty_result()
                result["image_dimensions"] = self._load_image_dimensions_fallback(image_path)
                result["pipeline"] = "image_load_failed"
                result["processing_error"] = "image_load_failed"
                result["processing_time_ms"] = int((time.time() - start_time) * 1000)
                result["pipeline_steps"] = pipeline_steps
                return result
            
            if debug_ctx:
                self._save_debug_image(debug_ctx, "01_input", img)

            # Convert to grayscale
            gray_start = time.perf_counter()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            record_step("grayscale", gray_start, width=width, height=height)
            if debug_ctx:
                self._save_debug_image(debug_ctx, "02_gray", gray)

            # Enhanced preprocessing
            preprocess_start = time.perf_counter()
            pipeline = self._preprocess_pipeline(gray)
            processed = pipeline["combined"]
            record_step("preprocess", preprocess_start)
            if debug_ctx:
                self._save_debug_image(debug_ctx, "03_contrast", pipeline["contrast"])
                self._save_debug_image(debug_ctx, "04_blurred", pipeline["blurred"])
                self._save_debug_image(debug_ctx, "05_adaptive", pipeline["adaptive"])
                self._save_debug_image(debug_ctx, "06_otsu", pipeline["otsu"])
                self._save_debug_image(debug_ctx, "07_ink_raw", pipeline["ink_raw"])
                self._save_debug_image(debug_ctx, "08_ink_clean", pipeline["ink"])
                self._save_debug_image(debug_ctx, "09_horizontal_lines", pipeline["horizontal_lines"])
                self._save_debug_image(debug_ctx, "10_vertical_lines", pipeline["vertical_lines"])
                self._save_debug_image(debug_ctx, "11_structure", pipeline["structure"])
                self._save_debug_image(debug_ctx, "12_edges", pipeline["edges"])
                self._save_debug_image(debug_ctx, "13_combined", pipeline["combined"])
            
            # Detect building boundaries
            boundaries_start = time.perf_counter()
            boundaries = self._detect_boundaries(processed, width, height, debug_ctx)
            record_step("detect_boundaries", boundaries_start, count=len(boundaries))
            boundary_polygon, boundary_area = self._compute_boundary_polygon(boundaries)
            
            # Detect walls (both external and internal)
            walls_start = time.perf_counter()
            walls = self._detect_walls(processed, boundaries, pipeline)
            record_step("detect_walls", walls_start, count=len(walls))

            # Detect gaps/open spaces (corridors, rooms, doors)
            gaps = []
            corridors = []
            open_spaces = []
            doors = []
            try:
                gaps_start = time.perf_counter()
                from app.services.enhanced_floorplan_recognition import gap_detector
                gaps = gap_detector.detect_gaps(pipeline["ink"], walls)
                for gap in gaps:
                    gap_dict = {
                        "x": gap.x,
                        "y": gap.y,
                        "width": gap.width,
                        "height": gap.height,
                        "area": gap.area,
                        "gap_type": gap.gap_type,
                        "connectivity": gap.connectivity,
                    }
                    if gap.gap_type == "corridor":
                        corridors.append(gap_dict)
                    elif gap.gap_type == "open_space":
                        open_spaces.append(gap_dict)
                    elif gap.gap_type == "door":
                        doors.append(gap_dict)
                record_step(
                    "detect_gaps",
                    gaps_start,
                    count=len(gaps),
                    corridors=len(corridors),
                    open_spaces=len(open_spaces),
                    doors=len(doors),
                )
            except Exception as e:
                logger.debug(f"Gap detection skipped: {e}")
            
            # Detect exits (openings in walls)
            exits_start = time.perf_counter()
            exits = self._detect_exits(processed, walls, boundaries, pipeline, doors)
            record_step("detect_exits", exits_start, count=len(exits))
            
            # Detect obstacles (furniture, columns, etc.)
            obstacles_start = time.perf_counter()
            obstacles = self._detect_obstacles(processed, walls)
            record_step("detect_obstacles", obstacles_start, count=len(obstacles))
            
            # Detect rooms/spaces
            rooms_start = time.perf_counter()
            rooms = self._detect_rooms(processed, walls)
            if not rooms and gaps:
                rooms = [
                    {
                        "x": g.x - g.width / 2,
                        "y": g.y - g.height / 2,
                        "width": g.width,
                        "height": g.height,
                        "area": g.area,
                        "name": f"Room {idx + 1}",
                        "source": "gap_detector",
                    }
                    for idx, g in enumerate(gaps)
                    if g.gap_type == "room"
                ]
            record_step("detect_rooms", rooms_start, count=len(rooms))
            
            # Calculate building dimensions
            bounds_start = time.perf_counter()
            building_bounds = self._calculate_building_bounds(boundaries, width, height)
            record_step("calculate_bounds", bounds_start)

            if debug_ctx:
                overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                for b in boundaries:
                    cv2.line(
                        overlay,
                        (int(b["x1"]), int(b["y1"])),
                        (int(b["x2"]), int(b["y2"])),
                        (0, 255, 0),
                        2,
                    )
                self._save_debug_image(debug_ctx, "10_boundaries_overlay", overlay)

                walls_overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                for w in walls:
                    cv2.line(
                        walls_overlay,
                        (int(w["x1"]), int(w["y1"])),
                        (int(w["x2"]), int(w["y2"])),
                        (255, 0, 0),
                        1,
                    )
                self._save_debug_image(debug_ctx, "11_walls_overlay", walls_overlay)

                exits_overlay = walls_overlay.copy()
                for e in exits:
                    x = int(e.get("x", 0))
                    y = int(e.get("y", 0))
                    cv2.circle(exits_overlay, (x, y), 6, (0, 0, 255), 2)
                self._save_debug_image(debug_ctx, "12_exits_overlay", exits_overlay)

                obstacles_overlay = exits_overlay.copy()
                for o in obstacles:
                    x = int(o.get("x", 0))
                    z = int(o.get("z", o.get("y", 0)))
                    cv2.rectangle(
                        obstacles_overlay,
                        (x - 4, z - 4),
                        (x + 4, z + 4),
                        (255, 255, 0),
                        1,
                    )
                self._save_debug_image(debug_ctx, "13_obstacles_overlay", obstacles_overlay)
            
            result = {
                "walls": walls,
                "exits": exits,
                "obstacles": obstacles,
                "boundaries": boundaries,
                "boundary_polygon": boundary_polygon,
                "boundary_area": boundary_area,
                "rooms": rooms,
                "corridors": corridors,
                "open_spaces": open_spaces,
                "doors": doors,
                "building_bounds": building_bounds,
                "wall_count": len(walls),
                "exit_count": len(exits),
                "obstacle_count": len(obstacles),
                "room_count": len(rooms),
                "corridor_count": len(corridors),
                "open_space_count": len(open_spaces),
                "door_count": len(doors),
                "processed": True,
                "image_dimensions": {"width": width, "height": height},
                "pipeline": pipeline_mode,
            }
            
            logger.info(
                f"Processed floor plan: {len(walls)} walls, {len(exits)} exits, "
                f"{len(obstacles)} obstacles, {len(rooms)} rooms"
            )

            quality_start = time.perf_counter()
            result["quality"] = self._assess_quality(result, pipeline, width, height)
            record_step(
                "quality_assessment",
                quality_start,
                score=result.get("quality", {}).get("score"),
            )
            result["processing_time_ms"] = int((time.time() - start_time) * 1000)
            result["pipeline_steps"] = pipeline_steps
            
            if debug_ctx:
                debug_payload = {
                    "mode": "traditional",
                    "image_path": image_path,
                    "summary": {
                        "wall_count": result.get("wall_count", 0),
                        "exit_count": result.get("exit_count", 0),
                        "obstacle_count": result.get("obstacle_count", 0),
                        "room_count": result.get("room_count", 0),
                    },
                    "building_bounds": result.get("building_bounds", {}),
                    "quality": result.get("quality", {}),
                }
                self._save_debug_json(debug_ctx, debug_payload)
                result["debug"] = {
                    "dir": str(debug_ctx["dir"]),
                    "steps": debug_ctx["steps"],
                    "mode": "traditional",
                }

            return result
            
        except Exception as e:
            logger.error(f"Error processing floor plan: {e}", exc_info=True)
            return self._empty_result()
    
    def _preprocess_image(self, gray: np.ndarray) -> np.ndarray:
        """Enhanced image preprocessing for better detection"""
        pipeline = self._preprocess_pipeline(gray)
        return pipeline["combined"]

    def _assess_quality(
        self,
        result: Dict,
        pipeline: Optional[Dict[str, np.ndarray]],
        width: int,
        height: int,
    ) -> Dict:
        """Heuristic quality assessment for detected floor plan."""
        warnings = []
        score = 1.0

        wall_count = result.get("wall_count", 0)
        exit_count = result.get("exit_count", 0)
        room_count = int(result.get("room_count", len(result.get("rooms", []) or [])) or 0)
        bounds = result.get("building_bounds", {}) or {}
        walls = result.get("walls", []) or []

        if not result.get("processed", False):
            warnings.append("processing_failed")
            score -= 0.4

        if wall_count < 10:
            warnings.append("low_wall_count")
            score -= 0.1
        if exit_count == 0:
            warnings.append("no_exits_detected")
            score -= 0.15
        if room_count == 0 and wall_count >= 35:
            warnings.append("no_rooms_detected")
            score -= 0.08
        if room_count > 180:
            warnings.append("room_fragmentation")
            score -= 0.05

        wall_length_total = None
        wall_density = None
        avg_confidence = None
        orthogonal_ratio = None
        short_internal_ratio = None
        if width > 0 and height > 0 and walls:
            wall_length_total = float(sum(w.get("length", 0.0) for w in walls))
            wall_density = wall_length_total / float(width * height)
            if wall_density < 0.002:
                warnings.append("low_wall_density")
                score -= 0.08
            elif wall_density > 0.25:
                warnings.append("very_dense_walls")
                score -= 0.08

            confidences = [w.get("confidence") for w in walls if w.get("confidence") is not None]
            if confidences:
                avg_confidence = float(sum(confidences) / max(1, len(confidences)))
                if avg_confidence < 0.4:
                    warnings.append("low_wall_confidence")
                    score -= 0.08

            orthogonal_count = 0
            for w in walls:
                angle = w.get("angle")
                if angle is None:
                    dx = w.get("x2", 0.0) - w.get("x1", 0.0)
                    dy = w.get("y2", 0.0) - w.get("y1", 0.0)
                    angle = (np.degrees(np.arctan2(dy, dx)) + 180) % 180
                if min(abs(angle), abs(angle - 90), abs(angle - 180)) <= 10:
                    orthogonal_count += 1
            orthogonal_ratio = orthogonal_count / max(1, len(walls))
            if wall_count > 20 and orthogonal_ratio < 0.45:
                warnings.append("low_orthogonal_ratio")
                score -= 0.06
            if wall_count > 260 and orthogonal_ratio < 0.6 and (wall_density or 0.0) > 0.03:
                warnings.append("line_storm_artifact")
                score -= 0.18
            if wall_count > 900 and orthogonal_ratio < 0.4:
                warnings.append("excessive_diagonal_walls")
                score -= 0.22
            elif wall_count > 1400:
                warnings.append("high_wall_count")
                score -= 0.08

            short_internal = 0
            internal_total = 0
            min_short_len = max(14.0, min(width, height) * self.short_wall_ratio_limit)
            for w in walls:
                if self._is_boundary_type(w):
                    continue
                internal_total += 1
                if float(w.get("length", 0.0)) < min_short_len:
                    short_internal += 1
            if internal_total > 0:
                short_internal_ratio = short_internal / float(internal_total)
                if internal_total > 60 and short_internal_ratio > 0.58:
                    warnings.append("wall_fragmentation")
                    score -= 0.12

        bounds_ratio = None
        if width > 0 and height > 0 and bounds:
            bw = float(bounds.get("width", 0)) if "width" in bounds else float(bounds.get("max_x", 0) - bounds.get("min_x", 0))
            bh = float(bounds.get("height", 0)) if "height" in bounds else float(bounds.get("max_y", 0) - bounds.get("min_y", 0))
            if bw > 0 and bh > 0:
                bounds_ratio = (bw * bh) / float(width * height)
                if bounds_ratio < 0.05:
                    warnings.append("small_bounds_ratio")
                    score -= 0.1
                elif bounds_ratio > 0.98 and wall_count < 20:
                    warnings.append("bounds_cover_entire_image")
                    score -= 0.05

        ink_ratio = None
        if pipeline and width > 0 and height > 0:
            ink = pipeline.get("ink")
            if ink is not None:
                ink_ratio = float(np.count_nonzero(ink)) / float(width * height)
                if ink_ratio < 0.01:
                    warnings.append("very_sparse_lines")
                    score -= 0.1
                elif ink_ratio > 0.6:
                    warnings.append("very_dense_lines")
                    score -= 0.1

        score = max(0.0, min(1.0, score))

        return {
            "score": round(score, 3),
            "warnings": warnings,
            "bounds_ratio": bounds_ratio,
            "ink_ratio": ink_ratio,
            "wall_length_total": wall_length_total,
            "wall_density": wall_density,
            "avg_confidence": avg_confidence,
            "orthogonal_ratio": orthogonal_ratio,
            "short_internal_ratio": short_internal_ratio,
        }
    
    def _detect_boundaries(
        self,
        processed: np.ndarray,
        width: int,
        height: int,
        debug: Optional[Dict] = None,
    ) -> List[Dict]:
        """Detect building external boundaries with robust fallback."""
        # Strengthen mask to connect outer boundary
        kernel = np.ones((7, 7), np.uint8)
        closed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel, iterations=2)
        dilated = cv2.dilate(closed, kernel, iterations=1)

        if debug:
            self._save_debug_image(debug, "09a_boundary_closed", closed)
            self._save_debug_image(debug, "09b_boundary_dilated", dilated)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boundaries: List[Dict] = []
        if contours:
            min_area = 0.02 * width * height
            best_contour = None
            best_score = 0.0

            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                x, y, w, h = cv2.boundingRect(contour)
                rect_area = max(1.0, float(w * h))
                fill_ratio = area / rect_area
                score = area * (0.5 + 0.5 * fill_ratio)
                if score > best_score:
                    best_score = score
                    best_contour = contour

            if best_contour is None:
                best_contour = max(contours, key=cv2.contourArea)

            perimeter = cv2.arcLength(best_contour, True)
            epsilon = 0.01 * perimeter
            approx = cv2.approxPolyDP(best_contour, epsilon, True)

            # If too complex, use convex hull for stability
            if len(approx) > 12:
                hull = cv2.convexHull(best_contour)
                hull_perimeter = cv2.arcLength(hull, True)
                approx = cv2.approxPolyDP(hull, 0.02 * hull_perimeter, True)

            for i in range(len(approx)):
                pt1 = approx[i][0]
                pt2 = approx[(i + 1) % len(approx)][0]
                length = np.sqrt((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)
                if length >= self.min_wall_length:
                    boundaries.append({
                        "x1": float(pt1[0]),
                        "y1": float(pt1[1]),
                        "x2": float(pt2[0]),
                        "y2": float(pt2[1]),
                        "length": float(length),
                        "type": "external_boundary",
                    })

        if not boundaries:
            # Fallback to content bounds if any pixels are present
            non_zero = cv2.findNonZero(dilated)
            if non_zero is not None:
                x, y, w, h = cv2.boundingRect(non_zero)
                boundaries = [
                    {"x1": x, "y1": y, "x2": x + w, "y2": y, "length": w, "type": "top"},
                    {"x1": x + w, "y1": y, "x2": x + w, "y2": y + h, "length": h, "type": "right"},
                    {"x1": x + w, "y1": y + h, "x2": x, "y2": y + h, "length": w, "type": "bottom"},
                    {"x1": x, "y1": y + h, "x2": x, "y2": y, "length": h, "type": "left"},
                ]
            else:
                # Final fallback: full image bounds
                boundaries = [
                    {"x1": 0, "y1": 0, "x2": width, "y2": 0, "length": width, "type": "top"},
                    {"x1": width, "y1": 0, "x2": width, "y2": height, "length": height, "type": "right"},
                    {"x1": width, "y1": height, "x2": 0, "y2": height, "length": width, "type": "bottom"},
                    {"x1": 0, "y1": height, "x2": 0, "y2": 0, "length": height, "type": "left"},
                ]

        return boundaries
    
    def _detect_walls(
        self,
        processed: np.ndarray,
        boundaries: List[Dict],
        pipeline: Optional[Dict[str, np.ndarray]] = None,
    ) -> List[Dict]:
        """Detect all walls (external and internal) with improved algorithm"""
        height, width = processed.shape
        min_wall_length_px = max(float(self.min_wall_length), min(width, height) * 0.018)
        max_wall_length_px = np.hypot(width, height) * 1.05

        # Prefer structural mask over raw edge mask to avoid line storms from text/furniture.
        detection_mask = processed
        if pipeline and isinstance(pipeline.get("structure"), np.ndarray):
            structure_mask = pipeline.get("structure")
            if structure_mask is not None and np.count_nonzero(structure_mask) > max(64, int(width * height * 0.0004)):
                detection_mask = structure_mask

        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(detection_mask, kernel, iterations=1)
        lines = self._detect_lines_multiscale(dilated)

        # Fallback to broader mask if structural extraction was too sparse.
        if len(lines) < 8 and pipeline and isinstance(pipeline.get("combined"), np.ndarray):
            broader = cv2.dilate(pipeline.get("combined"), kernel, iterations=1)
            lines = self._detect_lines_multiscale(broader)
        
        walls = []
        min_span = float(max(1, min(width, height)))
        for line in lines:
            x1, y1, x2, y2 = line
            length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

            # Filter out very short lines
            if length < min_wall_length_px or length > max_wall_length_px:
                continue

            # Check if this is a boundary wall
            is_boundary = self._is_boundary_wall(x1, y1, x2, y2, boundaries)

            confidence = None
            if pipeline:
                confidence = self._line_confidence(pipeline.get("ink"), x1, y1, x2, y2)
                if confidence is not None and confidence < 0.22 and not is_boundary:
                    continue

            # Suppress short noisy diagonals unless they are very confident.
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1))) % 180
            if angle > 90:
                angle = 180 - angle
            near_orthogonal = min(abs(angle), abs(90.0 - angle)) <= 11.0
            if (
                not near_orthogonal
                and not is_boundary
                and length < min_span * 0.22
                and (confidence is None or confidence < 0.75)
            ):
                continue

            walls.append({
                "x1": float(x1),
                "y1": float(y1),
                "x2": float(x2),
                "y2": float(y2),
                "length": float(length),
                "type": "boundary" if is_boundary else "internal",
                "thickness": float(self.wall_thickness),
                "confidence": confidence,
            })
        
        # Remove duplicate walls (same endpoints with tolerance)
        unique_walls = []
        seen = set()
        tolerance = 2.0  # Pixel tolerance for duplicate detection
        
        for wall in walls:
            x1, y1, x2, y2 = wall["x1"], wall["y1"], wall["x2"], wall["y2"]
            # Normalize endpoints
            if x1 > x2 or (x1 == x2 and y1 > y2):
                x1, y1, x2, y2 = x2, y2, x1, y1
            
            # Round to tolerance level
            key = (round(x1 / tolerance) * tolerance, 
                   round(y1 / tolerance) * tolerance,
                   round(x2 / tolerance) * tolerance,
                   round(y2 / tolerance) * tolerance)
            
            if key not in seen:
                seen.add(key)
                unique_walls.append(wall)
        
        # Snap to axis and merge colinear walls
        unique_walls = self._snap_walls_to_axes(unique_walls)
        unique_walls = self._merge_axis_walls(unique_walls)

        # Merge nearby parallel walls (more aggressive merging)
        walls = self._merge_parallel_walls(unique_walls)

        filtered_walls = []
        for wall in walls:
            length = float(wall.get("length", 0.0))
            if length < min_wall_length_px * 0.8 or length > max_wall_length_px:
                continue
            filtered_walls.append(wall)
        walls = self._stabilize_walls(
            filtered_walls,
            width,
            height,
            boundaries=boundaries,
        )

        if len(walls) > 2200:
            walls.sort(
                key=lambda wall: (
                    1 if str(wall.get("type", "")) in {"boundary", "external_boundary"} else 0,
                    float(wall.get("confidence", 0.0) or 0.0),
                    float(wall.get("length", 0.0)),
                ),
                reverse=True,
            )
            walls = walls[:2200]
            logger.warning("Limited walls to 2200 after stabilization")
        
        return walls
    
    def _detect_exits(
        self,
        processed: np.ndarray,
        walls: List[Dict],
        boundaries: List[Dict],
        pipeline: Optional[Dict[str, np.ndarray]] = None,
        doors: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """Detect exits (openings, doors) in walls"""
        exits = []

        # Prefer cleaner ink mask when available
        base_mask = pipeline.get("ink") if pipeline else processed
        open_mask = cv2.bitwise_not(base_mask)
        kernel = np.ones((5, 5), np.uint8)
        open_mask = cv2.morphologyEx(open_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        open_mask = cv2.morphologyEx(open_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        height, width = open_mask.shape
        img_area = float(width * height)
        min_exit_width_px = max(float(self.min_exit_width), min(width, height) * 0.008)
        max_exit_width_px = max(24.0, min(width, height) * self.max_exit_width_ratio)
        min_area = max(60.0, img_area * 0.00002)
        max_area = max(max_exit_width_px * max_exit_width_px * 1.8, img_area * 0.0025)

        # Find openings in open space mask
        contours, _ = cv2.findContours(open_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            long_side = float(max(w, h))
            short_side = float(min(w, h))
            if long_side < min_exit_width_px or long_side > max_exit_width_px:
                continue
            if short_side > max_exit_width_px * 0.72:
                continue

            cx = x + w / 2
            cy = y + h / 2

            near_wall = self._is_near_wall(cx, cy, walls, threshold=9)
            dist_boundary, _ = self._distance_to_boundaries(cx, cy, boundaries)
            near_boundary = dist_boundary is not None and dist_boundary < 9

            if not (near_wall or near_boundary):
                continue

            exit_width = long_side
            exit_height = short_side
            exit_type = "main_entrance" if near_boundary else "door"

            exits.append({
                "x": float(cx),
                "y": float(cy),
                "z": float(cy),
                "width": float(exit_width),
                "height": float(exit_height),
                "name": f"Exit {len(exits) + 1}",
                "type": exit_type,
                "capacity": int(exit_width * 1.33),
                "is_emergency": True,
                "is_accessible": True,
                "source": "opening_contour",
            })

        # Add door gaps from gap detector if provided
        for door in doors or []:
            cx = float(door.get("x", 0.0))
            cy = float(door.get("y", 0.0))
            near_wall = self._is_near_wall(cx, cy, walls, threshold=9)
            dist_boundary, _ = self._distance_to_boundaries(cx, cy, boundaries)
            near_boundary = dist_boundary is not None and dist_boundary < 9
            if not (near_wall or near_boundary):
                continue

            width_px = float(max(door.get("width", 0.0), door.get("height", 0.0)))
            if width_px < min_exit_width_px or width_px > max_exit_width_px:
                continue

            exits.append({
                "x": cx,
                "y": cy,
                "z": cy,
                "width": width_px,
                "height": float(min(door.get("width", 0.0), door.get("height", 0.0))),
                "name": f"Exit {len(exits) + 1}",
                "type": "main_entrance" if near_boundary else "door",
                "capacity": int(width_px * 1.33),
                "is_emergency": True,
                "is_accessible": True,
                "source": "gap_detector",
            })

        # Detect exits at boundary edges (main entrances)
        exits.extend(self._detect_boundary_exits(boundaries, open_mask))

        # Snap exits to nearest wall/boundary and dedupe
        exits = [self._snap_exit(exit, walls, boundaries) for exit in exits]
        exits = self._dedupe_exits(exits, min_dist=15.0)
        exits = [
            exit_data
            for exit_data in exits
            if min_exit_width_px <= float(exit_data.get("width", 0.0)) <= max_exit_width_px
        ]

        if len(exits) > self.max_exit_count:
            source_priority = {"gap_detector": 3, "opening_contour": 2, "boundary_gap": 1, "boundary_fallback": 0}
            exits.sort(
                key=lambda item: (
                    1 if item.get("type") == "main_entrance" else 0,
                    source_priority.get(str(item.get("source")), 0),
                    float(item.get("width", 0.0)),
                ),
                reverse=True,
            )
            exits = exits[: self.max_exit_count]

        # Final normalization
        for i, exit_data in enumerate(exits):
            exit_data["id"] = exit_data.get("id", f"exit_{i+1}")
            exit_data["name"] = exit_data.get("name", f"Exit {i+1}")
            normalized_width = float(exit_data.get("width", min_exit_width_px))
            exit_data["width"] = float(min(max_exit_width_px, max(min_exit_width_px, normalized_width)))
            if "z" not in exit_data:
                exit_data["z"] = float(exit_data.get("y", 0.0))

        # Fallback: infer exits from longest boundary segments if none detected
        if not exits and boundaries:
            sorted_bounds = sorted(boundaries, key=lambda b: b.get("length", 0), reverse=True)
            for idx, b in enumerate(sorted_bounds[:2]):
                mx = (b["x1"] + b["x2"]) / 2
                my = (b["y1"] + b["y2"]) / 2
                fallback_width = max(min_exit_width_px, min(max_exit_width_px, 24.0))
                exits.append({
                    "id": f"exit_{idx+1}",
                    "name": f"Inferred Exit {idx+1}",
                    "x": float(mx),
                    "y": float(my),
                    "z": float(my),
                    "width": float(fallback_width),
                    "height": float(self.wall_thickness * 2),
                    "type": "main_entrance",
                    "capacity": int(fallback_width * 1.33),
                    "is_emergency": True,
                    "is_accessible": True,
                    "source": "boundary_fallback",
                })

        return exits
    
    def _detect_obstacles(self, processed: np.ndarray, walls: List[Dict]) -> List[Dict]:
        """Detect obstacles (furniture, columns, etc.)"""
        # Find contours that are not walls
        contours, _ = cv2.findContours(processed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        obstacles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            # Obstacles are typically smaller closed shapes
            if 1200 < area < 18000:  # Reasonable obstacle size
                # Check if it's not a wall
                if not self._is_wall_contour(contour, walls):
                    # Get bounding box
                    x, y, w, h = cv2.boundingRect(contour)
                    if min(w, h) < 8:
                        continue
                    aspect = max(w, h) / max(1.0, float(min(w, h)))
                    if aspect > 4.0:
                        continue
                    solidity = area / max(1.0, float(w * h))
                    if solidity < 0.32:
                        continue
                    
                    # Calculate center
                    center_x = x + w/2
                    center_y = y + h/2
                    
                    obstacles.append({
                        "x": float(center_x),
                        "y": 0.0,
                        "z": float(center_y),
                        "width": float(w),
                        "height": float(h),
                        "depth": float(min(w, h)),
                        "type": "obstacle",
                        "area": float(area)
                    })

        if len(obstacles) > 120:
            obstacles.sort(key=lambda obstacle: float(obstacle.get("area", 0.0)), reverse=True)
            obstacles = obstacles[:120]

        return obstacles

    def _room_iou(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        ax1, ay1 = float(a.get("x", 0.0)), float(a.get("y", 0.0))
        ax2 = ax1 + float(a.get("width", 0.0))
        ay2 = ay1 + float(a.get("height", 0.0))
        bx1, by1 = float(b.get("x", 0.0)), float(b.get("y", 0.0))
        bx2 = bx1 + float(b.get("width", 0.0))
        by2 = by1 + float(b.get("height", 0.0))

        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
        intersection = iw * ih
        if intersection <= 0:
            return 0.0
        a_area = max(1.0, float(a.get("area", float(a.get("width", 0.0)) * float(a.get("height", 0.0)))))
        b_area = max(1.0, float(b.get("area", float(b.get("width", 0.0)) * float(b.get("height", 0.0)))))
        union = max(1.0, a_area + b_area - intersection)
        return float(intersection / union)

    def _cleanup_rooms(self, rooms: List[Dict], width: int, height: int) -> List[Dict]:
        if not rooms:
            return []

        image_area = float(max(1, width * height))
        min_area = max(900.0, image_area * 0.0008)
        max_area = image_area * 0.72
        min_span = max(8.0, min(width, height) * 0.012)

        filtered: List[Dict] = []
        for room in rooms:
            x = float(room.get("x", 0.0))
            y = float(room.get("y", 0.0))
            w = float(room.get("width", 0.0))
            h = float(room.get("height", 0.0))
            area = float(room.get("area", max(0.0, w * h)))
            if w <= 0 or h <= 0:
                continue
            if area < min_area or area > max_area:
                continue
            if min(w, h) < min_span * 0.45:
                continue

            bbox_area = max(1.0, w * h)
            compactness = area / bbox_area
            if compactness < 0.26:
                continue

            aspect = w / max(1.0, h)
            if aspect > 12.0 or aspect < 0.08:
                continue

            room_type = "corridor" if aspect > 3.8 or aspect < 0.26 else "room"
            if area > image_area * 0.22 and room_type == "room":
                room_type = "open_space"

            filtered.append({
                **room,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "area": area,
                "room_type": room_type,
            })

        filtered.sort(key=lambda item: float(item.get("area", 0.0)), reverse=True)

        deduped: List[Dict] = []
        for candidate in filtered:
            duplicate = False
            for existing in deduped:
                if self._room_iou(candidate, existing) >= 0.82:
                    duplicate = True
                    break
            if not duplicate:
                deduped.append(candidate)

        final_rooms: List[Dict] = []
        for idx, room in enumerate(deduped[:160], start=1):
            room_type = str(room.get("room_type", "room"))
            if room_type == "corridor":
                name = f"Corridor {idx}"
            elif room_type == "open_space":
                name = f"Open Space {idx}"
            else:
                name = f"Room {idx}"
            final_rooms.append({
                **room,
                "name": str(room.get("name") or name),
            })

        return final_rooms
    
    def _detect_rooms(self, processed: np.ndarray, walls: List[Dict]) -> List[Dict]:
        """Detect enclosed rooms via wall-mask connected components."""
        height, width = processed.shape

        wall_mask = np.zeros((height, width), dtype=np.uint8)
        wall_thickness = max(3, int(round(self.wall_thickness * 2)))
        for wall in walls:
            cv2.line(
                wall_mask,
                (int(wall.get("x1", 0)), int(wall.get("y1", 0))),
                (int(wall.get("x2", 0)), int(wall.get("y2", 0))),
                255,
                thickness=wall_thickness,
            )

        kernel = np.ones((3, 3), np.uint8)
        wall_mask = cv2.morphologyEx(wall_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        wall_mask = cv2.dilate(wall_mask, kernel, iterations=1)

        open_mask = cv2.bitwise_not(wall_mask)
        open_mask = cv2.morphologyEx(open_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Remove exterior open space by flood-filling from image corners.
        interior_mask = open_mask.copy()
        flood_fill_mask = np.zeros((height + 2, width + 2), dtype=np.uint8)
        for seed in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
            if interior_mask[seed[1], seed[0]] > 0:
                cv2.floodFill(interior_mask, flood_fill_mask, seedPoint=seed, newVal=0)

        num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(interior_mask, connectivity=8)
        min_area = max(900, int(width * height * 0.0008))

        rooms = []
        for label in range(1, num_labels):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area < min_area:
                continue

            x = int(stats[label, cv2.CC_STAT_LEFT])
            y = int(stats[label, cv2.CC_STAT_TOP])
            w = int(stats[label, cv2.CC_STAT_WIDTH])
            h = int(stats[label, cv2.CC_STAT_HEIGHT])
            if x <= 1 or y <= 1 or (x + w) >= (width - 1) or (y + h) >= (height - 1):
                # Likely still connected to outside or not properly enclosed.
                continue

            cx = float(centroids[label][0])
            cy = float(centroids[label][1])
            aspect = w / max(1.0, float(h))
            room_type = "corridor" if aspect > 3.2 or aspect < 0.31 else "room"
            if area > width * height * 0.18 and room_type == "room":
                room_type = "open_space"

            rooms.append({
                "x": float(x),
                "y": float(y),
                "width": float(w),
                "height": float(h),
                "area": float(area),
                "center_x": cx,
                "center_y": cy,
                "room_type": room_type,
                "name": f"{'Corridor' if room_type == 'corridor' else 'Room'} {len(rooms) + 1}",
            })

        rooms = self._cleanup_rooms(rooms, width, height)

        if rooms:
            return rooms

        # Fallback: derive enclosed spaces directly from the processed line mask.
        alt_kernel = np.ones((3, 3), np.uint8)
        alt_wall_mask = cv2.dilate(processed, alt_kernel, iterations=1)
        alt_wall_mask = cv2.morphologyEx(alt_wall_mask, cv2.MORPH_CLOSE, alt_kernel, iterations=1)
        alt_open_mask = cv2.bitwise_not(alt_wall_mask)
        alt_open_mask = cv2.morphologyEx(alt_open_mask, cv2.MORPH_OPEN, alt_kernel, iterations=1)

        flood_fill_mask = np.zeros((height + 2, width + 2), dtype=np.uint8)
        interior_mask = alt_open_mask.copy()
        for seed in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
            if interior_mask[seed[1], seed[0]] > 0:
                cv2.floodFill(interior_mask, flood_fill_mask, seedPoint=seed, newVal=0)

        num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(interior_mask, connectivity=8)
        min_area = max(1200, int(width * height * 0.001))
        fallback_rooms = []
        for label in range(1, num_labels):
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area < min_area:
                continue

            x = int(stats[label, cv2.CC_STAT_LEFT])
            y = int(stats[label, cv2.CC_STAT_TOP])
            w = int(stats[label, cv2.CC_STAT_WIDTH])
            h = int(stats[label, cv2.CC_STAT_HEIGHT])
            if x <= 1 or y <= 1 or (x + w) >= (width - 1) or (y + h) >= (height - 1):
                continue

            cx = float(centroids[label][0])
            cy = float(centroids[label][1])
            aspect = w / max(1.0, float(h))
            room_type = "corridor" if aspect > 3.2 or aspect < 0.31 else "room"
            if area > width * height * 0.18 and room_type == "room":
                room_type = "open_space"

            fallback_rooms.append({
                "x": float(x),
                "y": float(y),
                "width": float(w),
                "height": float(h),
                "area": float(area),
                "center_x": cx,
                "center_y": cy,
                "room_type": room_type,
                "name": f"{'Corridor' if room_type == 'corridor' else 'Room'} {len(fallback_rooms) + 1}",
            })

        fallback_rooms = self._cleanup_rooms(fallback_rooms, width, height)
        return fallback_rooms

        return rooms
    
    def _calculate_building_bounds(self, boundaries: List[Dict], width: int, height: int) -> Dict:
        """Calculate building bounding box"""
        if not boundaries:
            return {
                "min_x": 0,
                "min_y": 0,
                "max_x": width,
                "max_y": height,
                "width": width,
                "height": height
            }
        
        all_x = [b["x1"] for b in boundaries] + [b["x2"] for b in boundaries]
        all_y = [b["y1"] for b in boundaries] + [b["y2"] for b in boundaries]
        
        return {
            "min_x": float(min(all_x)),
            "min_y": float(min(all_y)),
            "max_x": float(max(all_x)),
            "max_y": float(max(all_y)),
            "width": float(max(all_x) - min(all_x)),
            "height": float(max(all_y) - min(all_y))
        }
    
    def _is_boundary_wall(self, x1: float, y1: float, x2: float, y2: float, boundaries: List[Dict]) -> bool:
        """Check if a wall is part of the building boundary"""
        for boundary in boundaries:
            # Check if wall endpoints are close to boundary
            dist1 = min(
                np.sqrt((x1 - boundary["x1"])**2 + (y1 - boundary["y1"])**2),
                np.sqrt((x1 - boundary["x2"])**2 + (y1 - boundary["y2"])**2)
            )
            dist2 = min(
                np.sqrt((x2 - boundary["x1"])**2 + (y2 - boundary["y1"])**2),
                np.sqrt((x2 - boundary["x2"])**2 + (y2 - boundary["y2"])**2)
            )
            
            if dist1 < 10 or dist2 < 10:
                return True
        return False
    
    def _merge_parallel_walls(self, walls: List[Dict]) -> List[Dict]:
        """Merge nearby parallel walls"""
        if len(walls) < 2:
            return walls
        
        merged = []
        used = set()
        
        for i, wall1 in enumerate(walls):
            if i in used:
                continue
            
            group = [wall1]
            used.add(i)
            
            # Find parallel walls nearby
            for j, wall2 in enumerate(walls[i+1:], i+1):
                if j in used:
                    continue
                
                if self._are_parallel(wall1, wall2) and self._are_nearby(wall1, wall2):
                    group.append(wall2)
                    used.add(j)
            
            # Merge group into single wall
            if len(group) > 1:
                merged_wall = self._merge_wall_group(group)
                merged.append(merged_wall)
            else:
                merged.append(wall1)
        
        return merged
    
    def _are_parallel(self, wall1: Dict, wall2: Dict) -> bool:
        """Check if two walls are parallel"""
        # Calculate angles
        angle1 = np.arctan2(wall1["y2"] - wall1["y1"], wall1["x2"] - wall1["x1"])
        angle2 = np.arctan2(wall2["y2"] - wall2["y1"], wall2["x2"] - wall2["x1"])
        
        # Check if angles are similar (within 10 degrees)
        angle_diff = abs(angle1 - angle2)
        return angle_diff < np.pi/18 or abs(angle_diff - np.pi) < np.pi/18
    
    def _are_nearby(self, wall1: Dict, wall2: Dict, threshold: float = 20) -> bool:
        """Check if two walls are nearby"""
        # Calculate distance between wall midpoints
        mid1_x = (wall1["x1"] + wall1["x2"]) / 2
        mid1_y = (wall1["y1"] + wall1["y2"]) / 2
        mid2_x = (wall2["x1"] + wall2["x2"]) / 2
        mid2_y = (wall2["y1"] + wall2["y2"]) / 2
        
        dist = np.sqrt((mid1_x - mid2_x)**2 + (mid1_y - mid2_y)**2)
        return dist < threshold
    
    def _merge_wall_group(self, group: List[Dict]) -> Dict:
        """Merge a group of walls into one"""
        all_x = [w["x1"] for w in group] + [w["x2"] for w in group]
        all_y = [w["y1"] for w in group] + [w["y2"] for w in group]
        
        # Find endpoints that are furthest apart
        max_dist = 0
        best_pair = None
        
        for i, (x1, y1) in enumerate(zip(all_x, all_y)):
            for j, (x2, y2) in enumerate(zip(all_x[i+1:], all_y[i+1:]), i+1):
                dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                if dist > max_dist:
                    max_dist = dist
                    best_pair = ((x1, y1), (x2, y2))
        
        if best_pair:
            (x1, y1), (x2, y2) = best_pair
            return {
                "x1": float(x1),
                "y1": float(y1),
                "x2": float(x2),
                "y2": float(y2),
                "length": float(max_dist),
                "type": group[0].get("type", "internal"),
                "thickness": float(self.wall_thickness)
            }
        
        return group[0]
    
    def _is_near_wall(self, x: float, y: float, walls: List[Dict], threshold: float = 15) -> bool:
        """Check if a point is near any wall"""
        for wall in walls:
            # Calculate distance from point to line segment
            dist = self._point_to_line_distance(x, y, wall)
            if dist < threshold:
                return True
        return False
    
    def _point_to_line_distance(self, x: float, y: float, wall: Dict) -> float:
        """Calculate distance from point to line segment"""
        x1, y1 = wall["x1"], wall["y1"]
        x2, y2 = wall["x2"], wall["y2"]
        
        # Vector from point to line endpoints
        A = x - x1
        B = y - y1
        C = x2 - x1
        D = y2 - y1
        
        dot = A * C + B * D
        len_sq = C * C + D * D
        
        if len_sq == 0:
            return np.sqrt(A * A + B * B)
        
        param = dot / len_sq
        
        if param < 0:
            xx, yy = x1, y1
        elif param > 1:
            xx, yy = x2, y2
        else:
            xx, yy = x1 + param * C, y1 + param * D
        
        dx = x - xx
        dy = y - yy
        return np.sqrt(dx * dx + dy * dy)

    def _project_point_to_segment(
        self,
        x: float,
        y: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> Tuple[float, float, float]:
        """Project point onto segment and return (px, py, distance)."""
        A = x - x1
        B = y - y1
        C = x2 - x1
        D = y2 - y1
        len_sq = C * C + D * D
        if len_sq == 0:
            return x1, y1, np.sqrt(A * A + B * B)
        t = (A * C + B * D) / len_sq
        if t < 0:
            px, py = x1, y1
        elif t > 1:
            px, py = x2, y2
        else:
            px, py = x1 + t * C, y1 + t * D
        dx = x - px
        dy = y - py
        return px, py, np.sqrt(dx * dx + dy * dy)

    def _distance_to_boundaries(
        self,
        x: float,
        y: float,
        boundaries: List[Dict],
    ) -> Tuple[Optional[float], Optional[Tuple[float, float]]]:
        """Return distance to nearest boundary segment and projection point."""
        if not boundaries:
            return None, None
        best_dist = None
        best_point = None
        for b in boundaries:
            px, py, dist = self._project_point_to_segment(
                x, y, b["x1"], b["y1"], b["x2"], b["y2"]
            )
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_point = (px, py)
        return best_dist, best_point

    def _snap_exit(self, exit_data: Dict, walls: List[Dict], boundaries: List[Dict]) -> Dict:
        """Snap exit to nearest wall or boundary if close."""
        x = float(exit_data.get("x", 0.0))
        y = float(exit_data.get("y", 0.0))

        # Prefer boundary snap for main entrances
        if exit_data.get("type") == "main_entrance" and boundaries:
            dist, point = self._distance_to_boundaries(x, y, boundaries)
            if dist is not None and dist < 12 and point:
                exit_data["x"], exit_data["y"] = float(point[0]), float(point[1])
                exit_data["z"] = float(point[1])
                return exit_data

        # Snap to closest wall if nearby
        best_dist = None
        best_point = None
        for wall in walls:
            px, py, dist = self._project_point_to_segment(
                x, y, wall["x1"], wall["y1"], wall["x2"], wall["y2"]
            )
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_point = (px, py)
        if best_dist is not None and best_dist < 12 and best_point:
            exit_data["x"], exit_data["y"] = float(best_point[0]), float(best_point[1])
            exit_data["z"] = float(best_point[1])

        return exit_data

    def _dedupe_exits(self, exits: List[Dict], min_dist: float = 12.0) -> List[Dict]:
        """Merge exits that are too close to each other."""
        if not exits:
            return []

        def _dist(a: Dict, b: Dict) -> float:
            dx = float(a.get("x", 0.0)) - float(b.get("x", 0.0))
            dy = float(a.get("y", 0.0)) - float(b.get("y", 0.0))
            return np.sqrt(dx * dx + dy * dy)

        ordered = sorted(
            exits,
            key=lambda e: (
                1 if e.get("type") == "main_entrance" else 0,
                float(e.get("width", 0.0)),
            ),
            reverse=True,
        )
        merged: List[Dict] = []
        for cand in ordered:
            merged_into = False
            for existing in merged:
                if _dist(cand, existing) <= min_dist:
                    # Merge: keep dominant type, max width/height
                    if cand.get("type") == "main_entrance":
                        existing["type"] = "main_entrance"
                    existing["width"] = max(float(existing.get("width", 0.0)), float(cand.get("width", 0.0)))
                    existing["height"] = max(float(existing.get("height", 0.0)), float(cand.get("height", 0.0)))
                    existing["x"] = (float(existing.get("x", 0.0)) + float(cand.get("x", 0.0))) / 2
                    existing["y"] = (float(existing.get("y", 0.0)) + float(cand.get("y", 0.0))) / 2
                    existing["z"] = float(existing.get("y", 0.0))
                    # Track sources
                    sources = set(existing.get("sources", []))
                    if "source" in existing:
                        sources.add(existing["source"])
                    if "source" in cand:
                        sources.add(cand["source"])
                    if sources:
                        existing["sources"] = sorted(sources)
                    merged_into = True
                    break
            if not merged_into:
                merged.append(cand)

        return merged
    
    def _is_wall_contour(self, contour, walls: List[Dict]) -> bool:
        """Check if a contour is part of a wall"""
        # Get contour center
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return False
        
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        
        return self._is_near_wall(cx, cy, walls, threshold=5)
    
    def _detect_boundary_exits(self, boundaries: List[Dict], open_mask: np.ndarray) -> List[Dict]:
        """Detect exits at building boundaries (main entrances)"""
        exits = []

        if not boundaries:
            return exits

        height, width = open_mask.shape
        min_exit_width_px = max(float(self.min_exit_width), min(width, height) * 0.008)
        max_exit_width_px = max(24.0, min(width, height) * self.max_exit_width_ratio)
        step = 4  # sampling step along boundary segments

        for boundary in boundaries:
            x1, y1 = float(boundary["x1"]), float(boundary["y1"])
            x2, y2 = float(boundary["x2"]), float(boundary["y2"])
            length = max(1.0, boundary.get("length", np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)))
            num_samples = max(2, int(length / step))

            runs = []
            current = []
            for i in range(num_samples):
                t = i / (num_samples - 1) if num_samples > 1 else 0
                x = int(round(x1 + t * (x2 - x1)))
                y = int(round(y1 + t * (y2 - y1)))
                if 0 <= x < width and 0 <= y < height and open_mask[y, x] > 0:
                    current.append((x, y, i))
                else:
                    if current:
                        runs.append(current)
                        current = []
            if current:
                runs.append(current)

            for run in runs:
                if len(run) < 2:
                    continue
                gap_width = len(run) * step
                # Skip runs that span most of the boundary (likely missing wall)
                if gap_width > length * 0.25:
                    continue
                if gap_width < min_exit_width_px or gap_width > max_exit_width_px:
                    continue
                center_sample = sum(p[2] for p in run) / len(run)
                center_t = center_sample / max(1, num_samples - 1)
                # Avoid corner artifacts that commonly appear in scanned plans.
                if center_t < 0.08 or center_t > 0.92:
                    continue

                gap_x = sum(p[0] for p in run) / len(run)
                gap_y = sum(p[1] for p in run) / len(run)
                exits.append({
                    "x": float(gap_x),
                    "y": float(gap_y),
                    "z": float(gap_y),
                    "width": float(gap_width),
                    "height": float(self.wall_thickness * 2),
                    "name": f"Main Exit {len(exits) + 1}",
                    "type": "main_entrance",
                    "capacity": int(gap_width * 1.33),
                    "is_emergency": True,
                    "is_accessible": True,
                    "source": "boundary_gap",
                })

        return exits
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "walls": [],
            "exits": [],
            "obstacles": [],
            "boundaries": [],
            "boundary_polygon": [],
            "boundary_area": 0.0,
            "rooms": [],
            "corridors": [],
            "open_spaces": [],
            "doors": [],
            "building_bounds": {},
            "wall_count": 0,
            "exit_count": 0,
            "obstacle_count": 0,
            "room_count": 0,
            "corridor_count": 0,
            "open_space_count": 0,
            "door_count": 0,
            "processed": False,
            "image_dimensions": {},
            "pipeline": "none",
            "quality": {"score": 0.0, "warnings": ["processing_failed"]},
            "processing_time_ms": None,
            "pipeline_steps": [],
            "processing_error": None,
        }


    def _convert_semantic_results(self, semantic_result: Dict) -> Dict:
        """Convert semantic processing results to floor plan processor format"""
        # Extract elements from semantic result
        walls = semantic_result.get("walls", [])
        exits = semantic_result.get("exits", [])
        rooms = semantic_result.get("rooms", [])
        furniture = semantic_result.get("furniture", [])
        obstacles = normalize_detected_obstacles(furniture)
        
        # Calculate building bounds
        if walls:
            all_x = [w.get("x1", 0) for w in walls] + [w.get("x2", 0) for w in walls]
            all_y = [w.get("y1", 0) for w in walls] + [w.get("y2", 0) for w in walls]
            building_bounds = {
                "min_x": float(min(all_x)),
                "min_y": float(min(all_y)),
                "max_x": float(max(all_x)),
                "max_y": float(max(all_y)),
                "width": float(max(all_x) - min(all_x)),
                "height": float(max(all_y) - min(all_y))
            }
        else:
            img_dims = semantic_result.get("image_dimensions", {})
            building_bounds = {
                "min_x": 0,
                "min_y": 0,
                "max_x": float(img_dims.get("width", 0)),
                "max_y": float(img_dims.get("height", 0)),
                "width": float(img_dims.get("width", 0)),
                "height": float(img_dims.get("height", 0))
            }
        
        # Convert rooms format
        converted_rooms = []
        for room in rooms:
            if isinstance(room, dict):
                bbox = room.get("bbox")
                if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                    try:
                        x1 = float(bbox[0])
                        y1 = float(bbox[1])
                        x2 = float(bbox[2])
                        y2 = float(bbox[3])
                        room_x = x1
                        room_y = y1
                        room_width = max(0.0, x2 - x1)
                        room_height = max(0.0, y2 - y1)
                    except (TypeError, ValueError):
                        room_x = room.get("x", 0)
                        room_y = room.get("y", 0)
                        room_width = room.get("width", 0)
                        room_height = room.get("height", 0)
                else:
                    room_x = room.get("x", 0)
                    room_y = room.get("y", 0)
                    room_width = room.get("width", 0)
                    room_height = room.get("height", 0)
                converted_rooms.append({
                    "x": room_x,
                    "y": room_y,
                    "width": room_width,
                    "height": room_height,
                    "area": room.get("area", max(0.0, float(room_width) * float(room_height))),
                    "name": room.get("name", f"Room {len(converted_rooms) + 1}"),
                    "room_type": room.get("room_type", "unknown")
                })

        boundaries = [
            wall
            for wall in walls
            if str(wall.get("type", "")).lower()
            in {"external", "boundary", "external_boundary", "perimeter", "outer"}
        ]
        if not boundaries and walls:
            # Semantic outputs may omit external labels; derive conservative rectangle boundaries.
            all_x = [float(w.get("x1", 0.0)) for w in walls] + [float(w.get("x2", 0.0)) for w in walls]
            all_y = [float(w.get("y1", 0.0)) for w in walls] + [float(w.get("y2", 0.0)) for w in walls]
            min_x = float(min(all_x))
            max_x = float(max(all_x))
            min_y = float(min(all_y))
            max_y = float(max(all_y))
            boundaries = [
                {"x1": min_x, "y1": min_y, "x2": max_x, "y2": min_y, "type": "external_boundary"},
                {"x1": max_x, "y1": min_y, "x2": max_x, "y2": max_y, "type": "external_boundary"},
                {"x1": max_x, "y1": max_y, "x2": min_x, "y2": max_y, "type": "external_boundary"},
                {"x1": min_x, "y1": max_y, "x2": min_x, "y2": min_y, "type": "external_boundary"},
            ]
        
        result = {
            "walls": walls,
            "exits": exits,
            "obstacles": obstacles,
            "boundaries": boundaries,
            "rooms": converted_rooms if converted_rooms else rooms,
            "building_bounds": building_bounds,
            "wall_count": len(walls),
            "exit_count": len(exits),
            "obstacle_count": len(obstacles),
            "room_count": len(converted_rooms) if converted_rooms else len(rooms),
            "processed": True,
            "ml_enhanced": semantic_result.get("ml_enhanced", False),
            "overall_confidence": semantic_result.get("overall_confidence", 0.0),
            "image_dimensions": semantic_result.get("image_dimensions", {})
        }

        boundary_polygon, boundary_area = self._compute_boundary_polygon(result.get("boundaries", []))
        result["boundary_polygon"] = boundary_polygon
        result["boundary_area"] = boundary_area
        
        return result


# Singleton instance
floor_plan_processor = FloorPlanProcessor()
