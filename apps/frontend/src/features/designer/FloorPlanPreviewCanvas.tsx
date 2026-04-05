import { MouseEvent, PointerEvent, WheelEvent, useEffect, useMemo, useRef, useState } from "react";
import { DesignerExitModel, FloorPlanMetadata } from "@/lib/api/types";
import {
  buildDesignerExitSelectionRadius,
  normalizeDesignerExits,
} from "@/features/designer/designerExitModel";

interface FloorPlanPreviewCanvasProps {
  floorPlan: FloorPlanMetadata | undefined;
  displayExits?: DesignerExitModel[];
  enableGrid?: boolean;
  enableExitPlacement?: boolean;
  onPlaceExit?: (point: { x: number; y: number }) => void;
  viewState?: CanvasViewState;
  onViewStateChange?: (viewState: CanvasViewState) => void;
  selectedExitId?: string;
  onSelectedExitIdChange?: (exitId: string) => void;
  selectedExitPoints?: Point[];
  onSelectedExitPointsChange?: (points: Point[]) => void;
}

interface Point {
  x: number;
  y: number;
}

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

interface WallSegment {
  a: Point;
  b: Point;
  length: number;
}

interface RectShape {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface RenderProjection {
  usesImage: boolean;
  drawX: number;
  drawY: number;
  drawWidth: number;
  drawHeight: number;
  padding: number;
  canvasWidth: number;
  canvasHeight: number;
  bounds: Bounds;
  rangeX: number;
  rangeY: number;
  gridStep: number;
  selectionRadiusPx: number;
}

interface CanvasViewState {
  zoom: number;
  panX: number;
  panY: number;
}

function toFiniteNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function hasFiniteBounds(bounds: Record<string, unknown> | undefined): bounds is Record<string, number> {
  if (!bounds) {
    return false;
  }
  const minX = Number(bounds.min_x);
  const maxX = Number(bounds.max_x);
  const minY = Number(bounds.min_y);
  const maxY = Number(bounds.max_y);
  return [minX, maxX, minY, maxY].every(Number.isFinite) && maxX > minX && maxY > minY;
}

function getBounds(points: Point[], fallback: Bounds): Bounds {
  if (points.length === 0) {
    return fallback;
  }

  return points.reduce(
    (acc, point) => ({
      minX: Math.min(acc.minX, point.x),
      maxX: Math.max(acc.maxX, point.x),
      minY: Math.min(acc.minY, point.y),
      maxY: Math.max(acc.maxY, point.y),
    }),
    {
      minX: Number.POSITIVE_INFINITY,
      maxX: Number.NEGATIVE_INFINITY,
      minY: Number.POSITIVE_INFINITY,
      maxY: Number.NEGATIVE_INFINITY,
    },
  );
}

function asPoint(value: unknown): Point | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const source = value as Record<string, unknown>;
  const x = toFiniteNumber(source.x, Number.NaN);
  const y = toFiniteNumber(source.y, Number.NaN);
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return null;
  }
  return { x, y };
}

function asWallSegment(value: unknown): WallSegment | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const source = value as Record<string, unknown>;
  const x1 = toFiniteNumber(source.x1, Number.NaN);
  const y1 = toFiniteNumber(source.y1 ?? source.z1, Number.NaN);
  const x2 = toFiniteNumber(source.x2, Number.NaN);
  const y2 = toFiniteNumber(source.y2 ?? source.z2, Number.NaN);
  if (![x1, y1, x2, y2].every(Number.isFinite)) {
    return null;
  }

  const length = Math.hypot(x2 - x1, y2 - y1);
  return { a: { x: x1, y: y1 }, b: { x: x2, y: y2 }, length };
}

function asRect(value: unknown, yKey: "y" | "z" = "y"): RectShape | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const source = value as Record<string, unknown>;
  const x = toFiniteNumber(source.x, Number.NaN);
  const y = toFiniteNumber(source[yKey] ?? source.y, Number.NaN);
  const width = toFiniteNumber(source.width, Number.NaN);
  const height = toFiniteNumber(source.height, Number.NaN);
  if (![x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0) {
    return null;
  }
  return { x, y, width, height };
}

function wallAngleDegrees(segment: WallSegment): number {
  const angle = Math.abs((Math.atan2(segment.b.y - segment.a.y, segment.b.x - segment.a.x) * 180) / Math.PI) % 180;
  return angle > 90 ? 180 - angle : angle;
}

function isNearOrthogonal(angle: number, tolerance = 12): boolean {
  return Math.min(Math.abs(angle), Math.abs(90 - angle)) <= tolerance;
}

function cross(o: Point, a: Point, b: Point): number {
  return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

function convexHull(points: Point[]): Point[] {
  if (points.length <= 3) {
    return points;
  }

  const sorted = [...points]
    .filter((point, index, arr) => arr.findIndex((other) => other.x === point.x && other.y === point.y) === index)
    .sort((a, b) => (a.x === b.x ? a.y - b.y : a.x - b.x));
  if (sorted.length <= 3) {
    return sorted;
  }

  const lower: Point[] = [];
  for (const point of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) {
      lower.pop();
    }
    lower.push(point);
  }

  const upper: Point[] = [];
  for (let i = sorted.length - 1; i >= 0; i -= 1) {
    const point = sorted[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], point) <= 0) {
      upper.pop();
    }
    upper.push(point);
  }

  lower.pop();
  upper.pop();
  return [...lower, ...upper];
}

function pickGridStep(span: number): number {
  const safeSpan = Math.max(1, span);
  const rough = safeSpan / 16;
  const power = 10 ** Math.floor(Math.log10(rough));
  for (const base of [1, 2, 5, 10]) {
    const step = base * power;
    if (step >= rough) {
      return step;
    }
  }
  return power * 10;
}

export function FloorPlanPreviewCanvas({
  floorPlan,
  displayExits,
  enableGrid = false,
  enableExitPlacement = false,
  onPlaceExit,
  viewState,
  onViewStateChange,
  selectedExitId = "",
  onSelectedExitIdChange,
  selectedExitPoints = [],
  onSelectedExitPointsChange,
}: FloorPlanPreviewCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const projectionRef = useRef<RenderProjection | null>(null);
  const renderedExitsRef = useRef<Array<{ id: string; screenX: number; screenY: number; worldX: number; worldY: number }>>([]);
  const dragRef = useRef<{ pointerId: number; startX: number; startY: number; x: number; y: number; moved: boolean } | null>(null);
  const suppressClickRef = useRef(false);
  const [imageVersion, setImageVersion] = useState(0);
  const [internalViewState, setInternalViewState] = useState<CanvasViewState>({ zoom: 1, panX: 0, panY: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const resolvedViewState = viewState ?? internalViewState;
  const resolvedViewStateRef = useRef(resolvedViewState);

  useEffect(() => {
    resolvedViewStateRef.current = resolvedViewState;
  }, [resolvedViewState]);

  const commitViewState = (next: CanvasViewState) => {
    if (onViewStateChange) {
      onViewStateChange(next);
      return;
    }
    setInternalViewState(next);
  };

  const previewStats = useMemo(() => {
    const exits = displayExits ?? normalizeDesignerExits(Array.isArray(floorPlan?.exits) ? floorPlan.exits : [], "detected");
    const detectedWalls = Array.isArray(floorPlan?.detected_walls) ? floorPlan.detected_walls : [];
    const boundaries = Array.isArray(floorPlan?.boundaries) ? floorPlan.boundaries : [];
    const obstacles = Array.isArray(floorPlan?.detected_obstacles) ? floorPlan.detected_obstacles : [];
    return {
      exitCount: exits.length,
      wallCount: detectedWalls.length + boundaries.length,
      obstacleCount: obstacles.length,
    };
  }, [displayExits, floorPlan]);

  const previewData = useMemo(() => {
    const exits = displayExits ?? normalizeDesignerExits(Array.isArray(floorPlan?.exits) ? floorPlan.exits : [], "detected");
    const detectedWalls = Array.isArray(floorPlan?.detected_walls) ? floorPlan.detected_walls : [];
    const boundaries = Array.isArray(floorPlan?.boundaries) ? floorPlan.boundaries : [];
    const walls = [...detectedWalls, ...boundaries];
    const obstacles = Array.isArray(floorPlan?.detected_obstacles) ? floorPlan.detected_obstacles : [];
    const explicitBoundary = Array.isArray(floorPlan?.boundary_polygon) ? floorPlan.boundary_polygon : [];
    const rooms = Array.isArray(floorPlan?.rooms) ? floorPlan.rooms : [];
    const buildingBounds = floorPlan?.building_bounds as Record<string, unknown> | undefined;
    const imageUrlRaw =
      (typeof floorPlan?.preview_image_url === "string" && floorPlan.preview_image_url) ||
      (typeof floorPlan?.image_url === "string" && floorPlan.image_url) ||
      "";
    const imageUrl = imageUrlRaw.trim();

    return { exits, walls, obstacles, explicitBoundary, rooms, buildingBounds, imageUrl };
  }, [displayExits, floorPlan]);

  const handleCanvasClick = (event: MouseEvent<HTMLCanvasElement>) => {
    const projection = projectionRef.current;
    const canvas = canvasRef.current;
    if (!projection || !canvas) {
      return;
    }

    if (suppressClickRef.current) {
      suppressClickRef.current = false;
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const canvasX = event.clientX - rect.left;
    const canvasY = event.clientY - rect.top;
    let nearestExit: (typeof renderedExitsRef.current)[number] | null = null;
    let nearestDistance = Number.POSITIVE_INFINITY;

    for (const exitPoint of renderedExitsRef.current) {
      const distance = Math.hypot(exitPoint.screenX - canvasX, exitPoint.screenY - canvasY);
      if (distance <= projection.selectionRadiusPx && distance < nearestDistance) {
        nearestExit = exitPoint;
        nearestDistance = distance;
      }
    }

    if (nearestExit) {
      onSelectedExitIdChange?.(nearestExit.id);
      onSelectedExitPointsChange?.([
        {
          x: Number(nearestExit.worldX.toFixed(2)),
          y: Number(nearestExit.worldY.toFixed(2)),
        },
      ]);
      return;
    }

    if (!enableExitPlacement || !onPlaceExit) {
      onSelectedExitIdChange?.("");
      onSelectedExitPointsChange?.([]);
      return;
    }

    const currentView = resolvedViewStateRef.current;
    const centerX = projection.canvasWidth / 2;
    const centerY = projection.canvasHeight / 2;
    const baseCanvasX = ((canvasX - centerX - currentView.panX) / currentView.zoom) + centerX;
    const baseCanvasY = ((canvasY - centerY - currentView.panY) / currentView.zoom) + centerY;

    if (
      projection.usesImage &&
      (baseCanvasX < projection.drawX ||
        baseCanvasX > projection.drawX + projection.drawWidth ||
        baseCanvasY < projection.drawY ||
        baseCanvasY > projection.drawY + projection.drawHeight)
    ) {
      return;
    }

    let nx = 0;
    let ny = 0;
    if (projection.usesImage) {
      nx = (baseCanvasX - projection.drawX) / Math.max(1, projection.drawWidth);
      ny = (baseCanvasY - projection.drawY) / Math.max(1, projection.drawHeight);
    } else {
      nx = (baseCanvasX - projection.padding) / Math.max(1, projection.canvasWidth - projection.padding * 2);
      ny = (projection.canvasHeight - baseCanvasY - projection.padding) / Math.max(1, projection.canvasHeight - projection.padding * 2);
    }

    nx = clamp(nx, 0, 1);
    ny = clamp(ny, 0, 1);

    const rawX = projection.bounds.minX + nx * projection.rangeX;
    const rawY = projection.bounds.minY + ny * projection.rangeY;
    const snappedX = clamp(
      Math.round(rawX / projection.gridStep) * projection.gridStep,
      projection.bounds.minX,
      projection.bounds.maxX,
    );
    const snappedY = clamp(
      Math.round(rawY / projection.gridStep) * projection.gridStep,
      projection.bounds.minY,
      projection.bounds.maxY,
    );

    onPlaceExit({
      x: Number(snappedX.toFixed(2)),
      y: Number(snappedY.toFixed(2)),
    });
    onSelectedExitPointsChange?.([{ x: Number(snappedX.toFixed(2)), y: Number(snappedY.toFixed(2)) }]);
  };

  const handleWheel = (event: WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const cursorX = event.clientX - rect.left;
    const cursorY = event.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const currentView = resolvedViewStateRef.current;
    const nextZoom = clamp(currentView.zoom * (event.deltaY < 0 ? 1.1 : 0.9), 0.5, 6);
    const scale = nextZoom / currentView.zoom;

    commitViewState({
      zoom: nextZoom,
      panX: cursorX - (cursorX - centerX - currentView.panX) * scale - centerX,
      panY: cursorY - (cursorY - centerY - currentView.panY) * scale - centerY,
    });
  };

  const handlePointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
    if (event.button !== 0) {
      return;
    }
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      x: event.clientX,
      y: event.clientY,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsDragging(false);
  };

  const handlePointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }

    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    const movedDistance = Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY);
    const moved = drag.moved || movedDistance > 6;
    dragRef.current = { ...drag, x: event.clientX, y: event.clientY, moved };
    if (moved) {
      suppressClickRef.current = true;
      setIsDragging(true);
    }
    const currentView = resolvedViewStateRef.current;
    commitViewState({
      ...currentView,
      panX: currentView.panX + dx,
      panY: currentView.panY + dy,
    });
  };

  const handlePointerUp = (event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    if (drag.moved) {
      suppressClickRef.current = true;
    }
    dragRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    setIsDragging(false);
  };

  useEffect(() => {
    const imageUrl = previewData.imageUrl;
    if (!imageUrl) {
      imageRef.current = null;
      return;
    }

    const image = new Image();
    image.onload = () => {
      imageRef.current = image;
      setImageVersion((version) => version + 1);
    };
    image.onerror = () => {
      imageRef.current = null;
      setImageVersion((version) => version + 1);
    };
    image.src = imageUrl;

    return () => {
      image.onload = null;
      image.onerror = null;
    };
  }, [previewData.imageUrl]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      projectionRef.current = null;
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      projectionRef.current = null;
      return;
    }

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.clearRect(0, 0, width, height);
    const bgGradient = ctx.createLinearGradient(0, 0, 0, height);
    bgGradient.addColorStop(0, "#08111d");
    bgGradient.addColorStop(0.55, "#0c1826");
    bgGradient.addColorStop(1, "#0a1320");
    ctx.fillStyle = bgGradient;
    ctx.fillRect(0, 0, width, height);

    const vignette = ctx.createRadialGradient(width * 0.5, height * 0.42, Math.min(width, height) * 0.12, width * 0.5, height * 0.5, Math.max(width, height) * 0.72);
    vignette.addColorStop(0, "rgba(8, 25, 38, 0)");
    vignette.addColorStop(1, "rgba(3, 7, 14, 0.42)");
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, width, height);

    const image = imageRef.current;
    let drawX = 0;
    let drawY = 0;
    let drawWidth = width;
    let drawHeight = height;
    const centerX = width / 2;
    const centerY = height / 2;

    if (image) {
      const scaleX = width / image.width;
      const scaleY = height / image.height;
      const imageScale = Math.min(scaleX, scaleY);
      drawWidth = image.width * imageScale;
      drawHeight = image.height * imageScale;
      drawX = (width - drawWidth) / 2;
      drawY = (height - drawHeight) / 2;
      ctx.drawImage(image, drawX, drawY, drawWidth, drawHeight);
      ctx.fillStyle = "rgba(8, 20, 32, 0.22)";
      ctx.fillRect(drawX, drawY, drawWidth, drawHeight);
    }

    const boundaryPoints = previewData.explicitBoundary.map(asPoint).filter((value): value is Point => Boolean(value));
    const wallSegments = previewData.walls
      .map(asWallSegment)
      .filter((value): value is WallSegment => Boolean(value));
    const exits = previewData.exits
      .map((entry, index) => {
        const x = toFiniteNumber(entry.x, Number.NaN);
        const y = toFiniteNumber(entry.z ?? entry.y, Number.NaN);
        const widthValue = toFiniteNumber(entry.width, 2);
        if (![x, y].every(Number.isFinite)) {
          return null;
        }
        return {
          id: String(entry.id ?? `preview-exit-${index + 1}`),
          x,
          y,
          width: widthValue,
        };
      })
      .filter((value): value is { id: string; x: number; y: number; width: number } => Boolean(value));
    const obstacles = previewData.obstacles
      .map((entry) => asRect(entry, "z"))
      .filter((value): value is RectShape => Boolean(value));
    const rooms = previewData.rooms
      .map((entry) => asRect(entry, "y"))
      .filter((value): value is RectShape => Boolean(value));

    const fallbackBounds: Bounds =
      image && image.width > 0 && image.height > 0
        ? { minX: 0, maxX: image.width, minY: 0, maxY: image.height }
        : { minX: 0, maxX: 100, minY: 0, maxY: 100 };

    const pointCloud = [
      ...boundaryPoints,
      ...exits.map((entry) => ({ x: entry.x, y: entry.y })),
      ...wallSegments.flatMap((segment) => [segment.a, segment.b]),
      ...rooms.flatMap((rect) => [
        { x: rect.x, y: rect.y },
        { x: rect.x + rect.width, y: rect.y + rect.height },
      ]),
      ...obstacles.flatMap((rect) => [
        { x: rect.x, y: rect.y },
        { x: rect.x + rect.width, y: rect.y + rect.height },
      ]),
    ];

    const geometryBounds = hasFiniteBounds(previewData.buildingBounds)
      ? {
          minX: toFiniteNumber(previewData.buildingBounds.min_x),
          maxX: toFiniteNumber(previewData.buildingBounds.max_x),
          minY: toFiniteNumber(previewData.buildingBounds.min_y),
          maxY: toFiniteNumber(previewData.buildingBounds.max_y),
        }
      : getBounds(pointCloud, fallbackBounds);

    const rangeX = Math.max(1, geometryBounds.maxX - geometryBounds.minX);
    const rangeY = Math.max(1, geometryBounds.maxY - geometryBounds.minY);
    const maxRange = Math.max(rangeX, rangeY);
    const diagonal = Math.hypot(rangeX, rangeY);
    const padding = 20;
    const gridStep = pickGridStep(maxRange);

    const project = (point: Point): Point => {
      const nxRaw = (point.x - geometryBounds.minX) / rangeX;
      const nyRaw = (point.y - geometryBounds.minY) / rangeY;
      const nx = clamp(nxRaw, -0.06, 1.06);
      const ny = clamp(nyRaw, -0.06, 1.06);
      const currentView = resolvedViewStateRef.current;
      const basePoint = image
        ? {
            x: drawX + nx * drawWidth,
            y: drawY + ny * drawHeight,
          }
        : {
            x: padding + nx * Math.max(1, width - padding * 2),
            y: height - (padding + ny * Math.max(1, height - padding * 2)),
          };

      return {
        x: (basePoint.x - centerX) * currentView.zoom + centerX + currentView.panX,
        y: (basePoint.y - centerY) * currentView.zoom + centerY + currentView.panY,
      };
    };

    const projectedGridCell = Math.hypot(
      project({ x: geometryBounds.minX + Math.min(gridStep, rangeX), y: geometryBounds.minY }).x -
        project({ x: geometryBounds.minX, y: geometryBounds.minY }).x,
      project({ x: geometryBounds.minX + Math.min(gridStep, rangeX), y: geometryBounds.minY }).y -
        project({ x: geometryBounds.minX, y: geometryBounds.minY }).y,
    );

    projectionRef.current = {
      usesImage: Boolean(image),
      drawX,
      drawY,
      drawWidth,
      drawHeight,
      padding,
      canvasWidth: width,
      canvasHeight: height,
      bounds: geometryBounds,
      rangeX,
      rangeY,
      gridStep,
      selectionRadiusPx: buildDesignerExitSelectionRadius(projectedGridCell),
    };

    let filteredWalls = wallSegments
      .filter((segment) => segment.length >= 6 && segment.length <= diagonal * 1.1)
      .slice(0, 2600);
    const filteredExits = exits
      .filter((entry) => entry.width > 0 && entry.width <= maxRange * 0.18)
      .slice(0, 60);
    const filteredObstacles = obstacles
      .filter((rect) => rect.width <= maxRange * 0.35 && rect.height <= maxRange * 0.35 && rect.width >= 2 && rect.height >= 2)
      .slice(0, 120);
    const filteredRooms = rooms
      .filter((rect) => rect.width >= 5 && rect.height >= 5 && rect.width <= maxRange * 0.9 && rect.height <= maxRange * 0.9)
      .slice(0, 240);

    const boundaryPad = maxRange * 0.08;
    const boundedBoundary = boundaryPoints
      .filter(
        (point) =>
          point.x >= geometryBounds.minX - boundaryPad &&
          point.x <= geometryBounds.maxX + boundaryPad &&
          point.y >= geometryBounds.minY - boundaryPad &&
          point.y <= geometryBounds.maxY + boundaryPad,
      )
      .map((point) => ({
        x: clamp(point.x, geometryBounds.minX, geometryBounds.maxX),
        y: clamp(point.y, geometryBounds.minY, geometryBounds.maxY),
      }));
    const boundaryRenderPoints = convexHull(boundedBoundary);

    if (filteredWalls.length > 120) {
      const diagonalCount = filteredWalls.reduce((count, segment) => (isNearOrthogonal(wallAngleDegrees(segment)) ? count : count + 1), 0);
      const diagonalRatio = diagonalCount / Math.max(1, filteredWalls.length);
      if (diagonalRatio > 0.28 || filteredWalls.length > 700) {
        // Suppress line-storm artifacts from noisy scans/screenshots.
        filteredWalls = filteredWalls
          .filter((segment) => {
            const angle = wallAngleDegrees(segment);
            if (isNearOrthogonal(angle)) {
              return true;
            }
            return segment.length <= maxRange * 0.06;
          })
          .slice(0, 520);
      } else if (filteredWalls.length > 520) {
        filteredWalls = filteredWalls.slice(0, 520);
      }

      if (filteredWalls.length > 240) {
        filteredWalls = filteredWalls
          .slice()
          .sort((a, b) => {
            const aScore = (isNearOrthogonal(wallAngleDegrees(a)) ? 1 : 0) * 10_000 + a.length;
            const bScore = (isNearOrthogonal(wallAngleDegrees(b)) ? 1 : 0) * 10_000 + b.length;
            return bScore - aScore;
          })
          .slice(0, 240);
      }
    }

    ctx.save();
    if (image) {
      // Keep overlays inside rendered floor-plan area.
      ctx.beginPath();
      ctx.rect(drawX, drawY, drawWidth, drawHeight);
      ctx.clip();
    }

    if (enableGrid && gridStep > 0) {
      const gridColor = "rgba(103, 198, 230, 0.14)";
      ctx.strokeStyle = gridColor;
      ctx.lineWidth = 1;

      const startX = Math.ceil(geometryBounds.minX / gridStep) * gridStep;
      for (let x = startX; x <= geometryBounds.maxX + gridStep * 0.5; x += gridStep) {
        const a = project({ x, y: geometryBounds.minY });
        const b = project({ x, y: geometryBounds.maxY });
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }

      const startY = Math.ceil(geometryBounds.minY / gridStep) * gridStep;
      for (let y = startY; y <= geometryBounds.maxY + gridStep * 0.5; y += gridStep) {
        const a = project({ x: geometryBounds.minX, y });
        const b = project({ x: geometryBounds.maxX, y });
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }

    if (boundaryRenderPoints.length > 2) {
      ctx.beginPath();
      boundaryRenderPoints.forEach((point, index) => {
        const mapped = project(point);
        if (index === 0) {
          ctx.moveTo(mapped.x, mapped.y);
        } else {
          ctx.lineTo(mapped.x, mapped.y);
        }
      });
      ctx.closePath();
      ctx.fillStyle = "rgba(10, 20, 32, 0.34)";
      ctx.fill();

      ctx.beginPath();
      boundaryRenderPoints.forEach((point, index) => {
        const mapped = project(point);
        if (index === 0) {
          ctx.moveTo(mapped.x, mapped.y);
        } else {
          ctx.lineTo(mapped.x, mapped.y);
        }
      });
      ctx.closePath();
      ctx.strokeStyle = "rgba(70, 218, 252, 0.96)";
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }

    ctx.strokeStyle = "rgba(166, 226, 173, 0.36)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "rgba(166, 226, 173, 0.08)";
    for (const room of filteredRooms) {
      const topLeft = project({ x: room.x, y: room.y });
      const bottomRight = project({ x: room.x + room.width, y: room.y + room.height });
      const rx = Math.min(topLeft.x, bottomRight.x);
      const ry = Math.min(topLeft.y, bottomRight.y);
      const rw = Math.max(1, Math.abs(bottomRight.x - topLeft.x));
      const rh = Math.max(1, Math.abs(bottomRight.y - topLeft.y));
      ctx.fillRect(rx, ry, rw, rh);
      ctx.strokeRect(rx, ry, rw, rh);
    }

    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "rgba(14, 22, 32, 0.82)";
    ctx.lineWidth = 4.2;
    for (const wall of filteredWalls) {
      const a = project(wall.a);
      const b = project(wall.b);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    ctx.strokeStyle = "rgba(174, 187, 202, 0.92)";
    ctx.lineWidth = 2.1;
    for (const wall of filteredWalls) {
      const a = project(wall.a);
      const b = project(wall.b);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    ctx.fillStyle = "rgba(255, 179, 71, 0.22)";
    for (const obstacle of filteredObstacles) {
      const topLeft = project({ x: obstacle.x, y: obstacle.y });
      const bottomRight = project({ x: obstacle.x + obstacle.width, y: obstacle.y + obstacle.height });
      const rx = Math.min(topLeft.x, bottomRight.x);
      const ry = Math.min(topLeft.y, bottomRight.y);
      const rw = Math.max(2, Math.abs(bottomRight.x - topLeft.x));
      const rh = Math.max(2, Math.abs(bottomRight.y - topLeft.y));
      ctx.fillRect(rx, ry, rw, rh);
    }

    const pixelBase = (image ? Math.min(drawWidth, drawHeight) : Math.min(width, height)) * resolvedViewStateRef.current.zoom;
    ctx.font = "12px var(--font-body), system-ui, sans-serif";
    ctx.textBaseline = "middle";
    renderedExitsRef.current = [];
    for (const [index, exit] of filteredExits.entries()) {
      const point = project({ x: exit.x, y: exit.y });
      const relativeSize = exit.width / Math.max(1, maxRange);
      const radius = clamp(relativeSize * pixelBase * 0.42, 4, 12);
      const isSelected =
        selectedExitId === exit.id ||
        selectedExitPoints.some(
          (selectedPoint) => Math.abs(selectedPoint.x - exit.x) <= 0.01 && Math.abs(selectedPoint.y - exit.y) <= 0.01,
        );

      renderedExitsRef.current.push({
        id: exit.id,
        screenX: point.x,
        screenY: point.y,
        worldX: exit.x,
        worldY: exit.y,
      });

      if (isSelected) {
        ctx.beginPath();
        ctx.strokeStyle = "rgba(141, 229, 95, 0.95)";
        ctx.lineWidth = 3;
        ctx.arc(point.x, point.y, radius + 8, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.beginPath();
      ctx.strokeStyle = "rgba(255, 255, 255, 0.65)";
      ctx.lineWidth = 2;
      ctx.arc(point.x, point.y, radius + 2, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.fillStyle = "#1ec8ff";
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.fill();

      const label = `E${index + 1}`;
      const labelX = point.x + radius + 8;
      const labelY = point.y - radius - 2;
      ctx.strokeStyle = "rgba(8, 20, 32, 0.88)";
      ctx.lineWidth = 4;
      ctx.strokeText(label, labelX, labelY);
      ctx.fillStyle = "#e8fbff";
      ctx.fillText(label, labelX, labelY);
    }

    ctx.restore();

    if (!image && filteredWalls.length === 0 && filteredExits.length === 0 && boundaryRenderPoints.length === 0) {
      ctx.fillStyle = "rgba(199, 216, 230, 0.7)";
      ctx.font = "14px sans-serif";
      ctx.fillText("No preview geometry available yet.", 20, 30);
    }
  }, [enableGrid, imageVersion, previewData, resolvedViewState, selectedExitId, selectedExitPoints]);

  return (
    <section className="panel space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="section-title">2D Plan Preview</h3>
          <p className="mt-2 text-sm text-mist/70">
            Layers: boundary, detected walls, obstacles, and active exits.
            {enableExitPlacement ? " Click near an existing exit to edit it, or click empty grid space to add a new one." : ""}
          </p>
        </div>
        <div className="workspace-chip-row">
          <span className="workspace-chip">Walls <strong>{previewStats.wallCount}</strong></span>
          <span className="workspace-chip">Exits <strong>{previewStats.exitCount}</strong></span>
          <span className="workspace-chip">Obstacles <strong>{previewStats.obstacleCount}</strong></span>
        </div>
      </div>
      <div className="preview-canvas-shell overflow-hidden rounded-2xl border border-white/10 bg-[#08131f]/80 p-3">
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          className={
            enableExitPlacement
              ? `h-[440px] w-full rounded-xl sm:h-[520px] 2xl:h-[640px] ${isDragging ? "cursor-grabbing" : "cursor-crosshair"}`
              : `h-[440px] w-full rounded-xl sm:h-[520px] 2xl:h-[640px] ${isDragging ? "cursor-grabbing" : "cursor-grab"}`
          }
        />
      </div>
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-fog">
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Boundary</span>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Walls</span>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Rooms</span>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Exits</span>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Zoom {resolvedViewState.zoom.toFixed(2)}x</span>
      </div>
    </section>
  );
}
