# ML Models for Floor Plan Recognition

## Overview

This system integrates three ML models for comprehensive floor plan recognition:

1. **U-Net** - Wall segmentation (pixel-level)
2. **YOLOv8** - Furniture and object detection
3. **Mask-RCNN** - Instance segmentation

## Model Setup

### Prerequisites

```bash
# Core backend first
setup_backend.bat

# Optional ML extras
setup_backend_ml.bat
```

### Platform Note

- `torch` and `ultralytics` are the primary optional ML dependencies for the default backend workflow.
- `detectron2` is best-effort only and is not included in `requirements-ml.txt`.
- On Windows with newer Python runtimes, `detectron2` often needs a specialized wheel or Linux/WSL environment.

### Model Files

Place trained models in `apps/backend/app/models/`:

- `unet_walls.pth` - U-Net model for wall segmentation
- `yolov8_floorplan.pt` - YOLOv8 model for furniture detection
- `mask_rcnn_floorplan.pth` - Mask-RCNN model for instance segmentation

### Training Models (Optional)

If models are not available, the system falls back to OpenCV-based methods. To train:

1. **U-Net Training**: Use floor plan images with wall masks
2. **YOLOv8 Training**: Use annotated furniture/object datasets
3. **Mask-RCNN Training**: Use instance segmentation datasets

## Usage

```python
from app.services.ml_floorplan_recognition import ml_floorplan_recognizer

# Process floor plan with ML models
results = ml_floorplan_recognizer.process_floor_plan(
    "path/to/floorplan.jpg",
    confidence_threshold=0.5
)

# Results include:
# - Wall segmentation with confidence
# - Furniture detection with bounding boxes
# - Room type classification
# - Architectural symbols
# - Enhanced gap detection
# - Overall confidence score
```

## Features

### Enhanced Recognition

- **Room Types**: Bedroom, kitchen, bathroom, living room, dining room, corridor
- **Furniture Detection**: Beds, sofas, tables, appliances, fixtures
- **Architectural Symbols**: Doors, windows, stairs, elevators
- **Confidence Scores**: Per-element and overall confidence

### Validation

- Automatic validation metrics
- Confidence reporting
- Parameter tuning for different building types
- Ground truth comparison (if available)

## Building Type Tuning

The system can be tuned for different building types:

```python
from app.services.floorplan_validation import floorplan_validator

# Tune parameters for residential buildings
params = floorplan_validator.tune_parameters(
    test_images=["img1.jpg", "img2.jpg"],
    ground_truths=[gt1, gt2],
    building_type="residential"
)
```

## Fallback Behavior

If ML models are not available, the system automatically falls back to:
- OpenCV-based wall detection
- Contour-based furniture detection
- Basic gap detection

This ensures the system works even without trained models.

At runtime, PeopleFlow now logs one summarized optional-dependency warning instead of repeating the same fallback warning for every model wrapper.


