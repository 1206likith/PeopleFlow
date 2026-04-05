import { PointerEvent, WheelEvent, useEffect, useMemo, useRef, useState } from "react";
import { projectPoint } from "@/features/simulation/canvasMath";
import {
  filterWallsForRender,
  isBoundaryWall,
  parseFrameGeometry,
  pickGridStep,
} from "@/features/simulation/frameGeometry";
import { SimulationFrame } from "@/lib/api/types";

export interface SimulationCanvasLayers {
  walls: boolean;
  boundaries: boolean;
  exits: boolean;
  obstacles: boolean;
  trails: boolean;
  heatmap: boolean;
}

interface SimulationCanvas2DProps {
  frame: SimulationFrame | null;
  layers?: SimulationCanvasLayers;
}

interface ViewState {
  zoom: number;
  panX: number;
  panY: number;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function SimulationCanvas2D({ frame, layers }: SimulationCanvas2DProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const dragRef = useRef<{ pointerId: number; x: number; y: number } | null>(null);
  const trailRef = useRef<Map<string, Array<{ x: number; y: number }>>>(new Map());
  const [isDragging, setIsDragging] = useState(false);
  const [view, setView] = useState<ViewState>({ zoom: 1, panX: 0, panY: 0 });

  const layerState: SimulationCanvasLayers = {
    walls: layers?.walls ?? true,
    boundaries: layers?.boundaries ?? true,
    exits: layers?.exits ?? true,
    obstacles: layers?.obstacles ?? true,
    trails: layers?.trails ?? true,
    heatmap: layers?.heatmap ?? false,
  };

  const geometry = useMemo(() => parseFrameGeometry(frame), [frame]);
  const renderWalls = useMemo(() => filterWallsForRender(geometry.walls, geometry.bounds, 480), [geometry.bounds, geometry.walls]);

  useEffect(() => {
    if (!frame) {
      trailRef.current.clear();
      return;
    }
    const trails = trailRef.current;
    const activeIds = new Set<string>();
    for (const agent of geometry.agents) {
      activeIds.add(agent.id);
      const path = trails.get(agent.id) ?? [];
      path.push({ x: agent.x, y: agent.y });
      if (path.length > 56) path.splice(0, path.length - 56);
      trails.set(agent.id, path);
    }
    for (const id of [...trails.keys()]) {
      if (!activeIds.has(id)) trails.delete(id);
    }
  }, [frame, geometry.agents]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#0e1824";
    ctx.fillRect(0, 0, width, height);

    if (!frame) {
      ctx.fillStyle = "#9cb2c7";
      ctx.font = "14px IBM Plex Sans";
      ctx.fillText("Waiting for simulation frames...", 24, 32);
      return;
    }

    const bounds = geometry.bounds;
    const centerX = width / 2;
    const centerY = height / 2;
    const project = (x: number, y: number) => {
      const base = projectPoint({ x, y }, bounds, width, height);
      return {
        x: (base.x - centerX) * view.zoom + centerX + view.panX,
        y: (base.y - centerY) * view.zoom + centerY + view.panY,
      };
    };

    const span = Math.max(1, Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY));
    const gridStep = pickGridStep(span);

    ctx.strokeStyle = "rgba(116, 177, 212, 0.12)";
    ctx.lineWidth = 1;
    for (let x = Math.ceil(bounds.minX / gridStep) * gridStep; x <= bounds.maxX + 0.5 * gridStep; x += gridStep) {
      const a = project(x, bounds.minY);
      const b = project(x, bounds.maxY);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }
    for (let y = Math.ceil(bounds.minY / gridStep) * gridStep; y <= bounds.maxY + 0.5 * gridStep; y += gridStep) {
      const a = project(bounds.minX, y);
      const b = project(bounds.maxX, y);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    if (layerState.heatmap && geometry.agents.length > 0) {
      const cell = clamp(16 * view.zoom, 10, 24);
      const heat = new Map<string, number>();
      for (const agent of geometry.agents) {
        const point = project(agent.x, agent.y);
        const cx = Math.floor(point.x / cell);
        const cy = Math.floor(point.y / cell);
        const key = `${cx}:${cy}`;
        heat.set(key, (heat.get(key) ?? 0) + 1);
      }
      for (const [key, count] of heat.entries()) {
        const [cxStr, cyStr] = key.split(":");
        const cx = Number(cxStr);
        const cy = Number(cyStr);
        const intensity = clamp(count / 10, 0.06, 0.52);
        ctx.fillStyle = `rgba(255, 120, 80, ${intensity.toFixed(3)})`;
        ctx.fillRect(cx * cell, cy * cell, cell, cell);
      }
    }

    if (layerState.walls || layerState.boundaries) {
      for (const wall of renderWalls) {
        const isBoundary = isBoundaryWall(wall.type);
        if (isBoundary && !layerState.boundaries) continue;
        if (!isBoundary && !layerState.walls) continue;
        const start = project(wall.x1, wall.y1);
        const end = project(wall.x2, wall.y2);
        ctx.strokeStyle = isBoundary ? "rgba(70, 218, 252, 0.95)" : "rgba(126, 149, 170, 0.88)";
        ctx.lineWidth = isBoundary ? clamp(1.8 * view.zoom, 1.2, 3.2) : clamp(1.2 * view.zoom, 1, 2.4);
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
      }
    }

    if (layerState.obstacles) {
      ctx.fillStyle = "rgba(255, 179, 71, 0.26)";
      for (const obstacle of geometry.obstacles) {
        const widthWorld = obstacle.width;
        const heightWorld = obstacle.height;
        if (widthWorld <= 0 || heightWorld <= 0) continue;
        const topLeft = project(obstacle.x, obstacle.y);
        const bottomRight = project(obstacle.x + widthWorld, obstacle.y + heightWorld);
        const rx = Math.min(topLeft.x, bottomRight.x);
        const ry = Math.min(topLeft.y, bottomRight.y);
        const rw = Math.max(2, Math.abs(bottomRight.x - topLeft.x));
        const rh = Math.max(2, Math.abs(bottomRight.y - topLeft.y));
        ctx.fillRect(rx, ry, rw, rh);
      }
    }

    if (layerState.trails) {
      ctx.strokeStyle = "rgba(255, 190, 108, 0.36)";
      ctx.lineWidth = clamp(1 * view.zoom, 0.8, 2);
      for (const trail of trailRef.current.values()) {
        if (trail.length < 2) continue;
        ctx.beginPath();
        const start = project(trail[0].x, trail[0].y);
        ctx.moveTo(start.x, start.y);
        for (let i = 1; i < trail.length; i += 1) {
          const p = project(trail[i].x, trail[i].y);
          ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
      }
    }

    if (layerState.exits) {
      for (const exit of geometry.exits) {
        const p = project(exit.x, exit.y);
        const radius = clamp((exit.width * 0.8 + 2.2) * view.zoom, 3, 10);
        ctx.beginPath();
        ctx.fillStyle = exit.blocked ? "#ff6f91" : "#1ec8ff";
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    for (const agent of geometry.agents) {
      const point = project(agent.x, agent.y);
      const status = agent.status;
      const panicTint = clamp(agent.panicLevel, 0, 1);
      const radius = clamp(3.1 * view.zoom, 2.2, 5.8);
      ctx.beginPath();
      if (status === "evacuated") {
        ctx.fillStyle = "#39d353";
      } else if (status === "collapsed") {
        ctx.fillStyle = "#8b5cf6";
      } else {
        const red = Math.round(255);
        const green = Math.round(179 - panicTint * 50);
        const blue = Math.round(71 - panicTint * 30);
        ctx.fillStyle = `rgb(${red} ${green} ${blue})`;
      }
      ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    const navDebug = (frame.nav_debug ?? {}) as Record<string, unknown>;
    const penetrations = Number(frame.wall_penetration_count ?? 0);
    const collisions = Number(frame.collision_events ?? 0);
    const runtimeWallCount = Number(navDebug.runtime_wall_count ?? renderWalls.length);
    const rawWallCount = Number(navDebug.raw_wall_count ?? geometry.walls.length);

    ctx.fillStyle = "#d8e4ef";
    ctx.font = "12px IBM Plex Sans";
    ctx.fillText(`Agents: ${geometry.agents.length}`, 14, height - 52);
    ctx.fillText(`Collisions: ${collisions}`, 14, height - 38);
    ctx.fillText(`Penetrations: ${penetrations}`, 14, height - 24);
    ctx.fillText(`Walls: ${runtimeWallCount}/${rawWallCount}`, 14, height - 10);
    ctx.fillText(`Zoom ${view.zoom.toFixed(2)}x`, width - 86, height - 12);
  }, [frame, geometry, layerState.boundaries, layerState.exits, layerState.heatmap, layerState.obstacles, layerState.trails, layerState.walls, renderWalls, view.panX, view.panY, view.zoom]);

  const resetView = () => {
    setView({ zoom: 1, panX: 0, panY: 0 });
  };

  const handleWheel = (event: WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const cursorX = event.clientX - rect.left;
    const cursorY = event.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const zoomFactor = event.deltaY < 0 ? 1.1 : 0.9;

    setView((current) => {
      const nextZoom = clamp(current.zoom * zoomFactor, 0.55, 6);
      const scale = nextZoom / current.zoom;
      return {
        zoom: nextZoom,
        panX: cursorX - (cursorX - cx - current.panX) * scale - cx,
        panY: cursorY - (cursorY - cy - current.panY) * scale - cy,
      };
    });
  };

  const handlePointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
    if (event.button !== 0) return;
    dragRef.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsDragging(true);
  };

  const handlePointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    dragRef.current = { ...drag, x: event.clientX, y: event.clientY };
    setView((current) => ({
      ...current,
      panX: current.panX + dx,
      panY: current.panY + dy,
    }));
  };

  const handlePointerUp = (event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    setIsDragging(false);
  };

  return (
    <div className="panel">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="section-title">2D Simulation View</h3>
        <button type="button" className="btn-secondary ml-auto" onClick={resetView}>
          Reset View
        </button>
      </div>
      <p className="mt-2 text-sm text-mist/70">Mouse wheel zooms. Drag to pan. Walls/exits/obstacles are fidelity-filtered to remove scan noise.</p>
      <div className="mt-3 overflow-hidden rounded-lg border border-white/10">
        <canvas
          ref={canvasRef}
          className={isDragging ? "h-[430px] w-full cursor-grabbing" : "h-[430px] w-full cursor-grab"}
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        />
      </div>
    </div>
  );
}
