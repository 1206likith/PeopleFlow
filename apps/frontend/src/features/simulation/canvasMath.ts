export interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface CanvasPoint {
  x: number;
  y: number;
}

export function projectPoint(point: CanvasPoint, bounds: Bounds, width: number, height: number, padding = 24): CanvasPoint {
  const rangeX = Math.max(1, bounds.maxX - bounds.minX);
  const rangeY = Math.max(1, bounds.maxY - bounds.minY);
  const scale = Math.min((width - padding * 2) / rangeX, (height - padding * 2) / rangeY);

  return {
    x: (point.x - bounds.minX) * scale + padding,
    y: height - ((point.y - bounds.minY) * scale + padding),
  };
}

export function deriveBounds(points: CanvasPoint[]): Bounds {
  if (points.length === 0) {
    return { minX: -50, maxX: 50, minY: -50, maxY: 50 };
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
