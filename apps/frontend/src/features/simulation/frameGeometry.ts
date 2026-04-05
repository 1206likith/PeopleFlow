import { SimulationFrame } from "@/lib/api/types";

export interface ParsedBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface ParsedWall {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  type: string;
  length: number;
}

export interface ParsedObstacle {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ParsedExit {
  id: string;
  x: number;
  y: number;
  width: number;
  blocked: boolean;
}

export interface ParsedAgent {
  id: string;
  x: number;
  y: number;
  status: string;
  panicLevel: number;
}

export interface ParsedFrameGeometry {
  bounds: ParsedBounds;
  walls: ParsedWall[];
  obstacles: ParsedObstacle[];
  exits: ParsedExit[];
  agents: ParsedAgent[];
  points: Array<{ x: number; y: number }>;
}

function asFinite(value: unknown, fallback = Number.NaN): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function deriveBounds(points: Array<{ x: number; y: number }>): ParsedBounds {
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

function wallAngleDegrees(wall: ParsedWall): number {
  const dx = wall.x2 - wall.x1;
  const dy = wall.y2 - wall.y1;
  let angle = Math.abs((Math.atan2(dy, dx) * 180) / Math.PI) % 180;
  if (angle > 90) {
    angle = 180 - angle;
  }
  return angle;
}

function isNearOrthogonal(wall: ParsedWall, tolerance = 11): boolean {
  const angle = wallAngleDegrees(wall);
  return Math.min(Math.abs(angle), Math.abs(90 - angle)) <= tolerance;
}

export function isBoundaryWall(type: string): boolean {
  const normalized = type.toLowerCase();
  return (
    normalized.includes("boundary") ||
    normalized.includes("external") ||
    normalized === "top" ||
    normalized === "bottom" ||
    normalized === "left" ||
    normalized === "right"
  );
}

export function pickGridStep(span: number): number {
  const safeSpan = Math.max(1, span);
  const rough = safeSpan / 12;
  const power = 10 ** Math.floor(Math.log10(rough));
  for (const base of [1, 2, 5, 10]) {
    const step = base * power;
    if (step >= rough) return step;
  }
  return power * 10;
}

export function parseFrameGeometry(frame: SimulationFrame | null): ParsedFrameGeometry {
  const walls: ParsedWall[] = [];
  const exits: ParsedExit[] = [];
  const obstacles: ParsedObstacle[] = [];
  const agents: ParsedAgent[] = [];
  const points: Array<{ x: number; y: number }> = [];

  const rawBounds = (frame?.building_bounds ?? {}) as Record<string, unknown>;
  const minX = asFinite(rawBounds.min_x);
  const maxX = asFinite(rawBounds.max_x);
  const minY = asFinite(rawBounds.min_y);
  const maxY = asFinite(rawBounds.max_y);
  if ([minX, maxX, minY, maxY].every(Number.isFinite) && maxX > minX && maxY > minY) {
    points.push({ x: minX, y: minY }, { x: maxX, y: maxY });
  }

  for (const item of frame?.agents ?? []) {
    const x = asFinite(item.x);
    const y = asFinite(item.z ?? item.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    const agent: ParsedAgent = {
      id: String(item.agent_id),
      x,
      y,
      status: String(item.status ?? "moving"),
      panicLevel: clamp(asFinite(item.panic_level, 0), 0, 1),
    };
    agents.push(agent);
    points.push({ x: agent.x, y: agent.y });
  }

  for (const item of frame?.exits ?? []) {
    const x = asFinite(item.x);
    const y = asFinite(item.z ?? item.y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    const width = Math.max(0.4, asFinite(item.width, 2));
    const exitItem: ParsedExit = {
      id: String(item.id ?? `exit-${exits.length + 1}`),
      x,
      y,
      width,
      blocked: Boolean((item as { blocked?: boolean }).blocked),
    };
    exits.push(exitItem);
    points.push({ x: exitItem.x, y: exitItem.y });
  }

  if (Array.isArray(frame?.obstacles)) {
    for (const obstacle of frame.obstacles) {
      const x = asFinite((obstacle as { x?: number }).x);
      const y = asFinite((obstacle as { z?: number; y?: number }).z ?? (obstacle as { y?: number }).y);
      const widthValue = Math.max(0, asFinite((obstacle as { width?: number }).width, 0));
      const heightValue = Math.max(
        0,
        asFinite((obstacle as { depth?: number; height?: number }).depth ?? (obstacle as { height?: number }).height, 0),
      );
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      obstacles.push({ x, y, width: widthValue, height: heightValue });
      points.push({ x, y });
      if (widthValue > 0 && heightValue > 0) {
        points.push({ x: x + widthValue, y: y + heightValue });
      }
    }
  }

  if (Array.isArray(frame?.walls)) {
    for (const wall of frame.walls) {
      const x1 = asFinite((wall as { x1?: number }).x1);
      const y1 = asFinite((wall as { y1?: number }).y1);
      const x2 = asFinite((wall as { x2?: number }).x2);
      const y2 = asFinite((wall as { y2?: number }).y2);
      if (![x1, y1, x2, y2].every(Number.isFinite)) continue;
      const length = Math.hypot(x2 - x1, y2 - y1);
      walls.push({
        x1,
        y1,
        x2,
        y2,
        type: String((wall as { type?: string }).type ?? ""),
        length,
      });
      points.push({ x: x1, y: y1 }, { x: x2, y: y2 });
    }
  }

  const bounds = deriveBounds(points);
  return { bounds, walls, obstacles, exits, agents, points };
}

export function filterWallsForRender(
  walls: ParsedWall[],
  bounds: ParsedBounds,
  maxWalls = 420,
): ParsedWall[] {
  if (walls.length === 0) return [];

  const spanX = Math.max(1, bounds.maxX - bounds.minX);
  const spanY = Math.max(1, bounds.maxY - bounds.minY);
  const minSpan = Math.max(1, Math.min(spanX, spanY));
  const maxDiag = Math.hypot(spanX, spanY) * 1.2;
  const minLength = Math.max(2, minSpan * 0.008);
  const tol = Math.max(1, minSpan * 0.003);
  const dedupe = new Set<string>();
  const normalized: ParsedWall[] = [];

  for (const wall of walls) {
    if (wall.length < minLength || wall.length > maxDiag) continue;
    const key = [
      Math.round(Math.min(wall.x1, wall.x2) / tol),
      Math.round(Math.min(wall.y1, wall.y2) / tol),
      Math.round(Math.max(wall.x1, wall.x2) / tol),
      Math.round(Math.max(wall.y1, wall.y2) / tol),
    ].join(":");
    if (dedupe.has(key)) continue;
    dedupe.add(key);
    normalized.push(wall);
  }

  if (normalized.length <= 140) return normalized;

  const orthCount = normalized.reduce((count, wall) => (isNearOrthogonal(wall) ? count + 1 : count), 0);
  const orthRatio = orthCount / Math.max(1, normalized.length);
  let filtered = normalized;

  if (orthRatio < 0.68) {
    const shortDiagLimit = Math.max(8, minSpan * 0.05);
    filtered = normalized.filter((wall) => {
      if (isBoundaryWall(wall.type)) return true;
      if (isNearOrthogonal(wall)) return wall.length >= Math.max(4, minSpan * 0.01);
      return wall.length <= shortDiagLimit;
    });
  }

  if (filtered.length > maxWalls) {
    filtered = filtered
      .slice()
      .sort((a, b) => {
        const pa = (isBoundaryWall(a.type) ? 10000 : 0) + (isNearOrthogonal(a) ? 5000 : 0) + a.length;
        const pb = (isBoundaryWall(b.type) ? 10000 : 0) + (isNearOrthogonal(b) ? 5000 : 0) + b.length;
        return pb - pa;
      })
      .slice(0, maxWalls);
  }

  return filtered;
}

