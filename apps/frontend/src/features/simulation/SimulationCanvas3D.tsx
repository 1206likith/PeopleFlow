import { PointerEvent, WheelEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  filterWallsForRender,
  isBoundaryWall,
  parseFrameGeometry,
  pickGridStep,
} from "@/features/simulation/frameGeometry";
import { SimulationFrame } from "@/lib/api/types";

interface SimulationCanvasLayers {
  walls: boolean;
  boundaries: boolean;
  exits: boolean;
  obstacles: boolean;
  trails: boolean;
  heatmap: boolean;
}

interface SimulationCanvas3DProps {
  frame: SimulationFrame | null;
  layers?: SimulationCanvasLayers;
}

interface CameraState {
  yaw: number;
  pitch: number;
  distance: number;
  panX: number;
  panZ: number;
}

interface ProjectedPoint {
  x: number;
  y: number;
  depth: number;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function averageDepth(points: ProjectedPoint[]): number {
  return points.reduce((sum, point) => sum + point.depth, 0) / Math.max(1, points.length);
}

export function SimulationCanvas3D({ frame, layers }: SimulationCanvas3DProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const dragRef = useRef<{ pointerId: number; x: number; y: number; mode: "rotate" | "pan" } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [camera, setCamera] = useState<CameraState>({
    yaw: -0.82,
    pitch: 0.62,
    distance: 220,
    panX: 0,
    panZ: 0,
  });

  const layerState: SimulationCanvasLayers = {
    walls: layers?.walls ?? true,
    boundaries: layers?.boundaries ?? true,
    exits: layers?.exits ?? true,
    obstacles: layers?.obstacles ?? true,
    trails: layers?.trails ?? true,
    heatmap: layers?.heatmap ?? false,
  };

  const geometry = useMemo(() => parseFrameGeometry(frame), [frame]);
  const renderWalls = useMemo(() => filterWallsForRender(geometry.walls, geometry.bounds, 560), [geometry.bounds, geometry.walls]);
  const spanX = Math.max(1, geometry.bounds.maxX - geometry.bounds.minX);
  const spanY = Math.max(1, geometry.bounds.maxY - geometry.bounds.minY);
  const maxSpan = Math.max(spanX, spanY);
  const defaultDistance = clamp(maxSpan * 2.2, 80, 1200);

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

    if (typeof ctx.createLinearGradient === "function") {
      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, "#112334");
      gradient.addColorStop(1, "#0a1320");
      ctx.fillStyle = gradient;
    } else {
      ctx.fillStyle = "#0a1320";
    }
    ctx.fillRect(0, 0, width, height);

    if (!frame) {
      ctx.fillStyle = "#9cb2c7";
      ctx.font = "14px IBM Plex Sans";
      ctx.fillText("Waiting for simulation frames...", 24, 32);
      return;
    }

    const centerX = (geometry.bounds.minX + geometry.bounds.maxX) / 2 + camera.panX;
    const centerZ = (geometry.bounds.minY + geometry.bounds.maxY) / 2 + camera.panZ;
    const focal = Math.min(width, height) * 0.96;

    const project = (x: number, y: number, z: number): ProjectedPoint | null => {
      const tx = x - centerX;
      const ty = y;
      const tz = z - centerZ;

      const cosYaw = Math.cos(camera.yaw);
      const sinYaw = Math.sin(camera.yaw);
      const xYaw = tx * cosYaw - tz * sinYaw;
      const zYaw = tx * sinYaw + tz * cosYaw;

      const cosPitch = Math.cos(camera.pitch);
      const sinPitch = Math.sin(camera.pitch);
      const yPitch = ty * cosPitch - zYaw * sinPitch;
      const zPitch = ty * sinPitch + zYaw * cosPitch;

      const depth = zPitch + camera.distance;
      if (depth <= 1.5) return null;

      return {
        x: width / 2 + (xYaw * focal) / depth,
        y: height / 2 - (yPitch * focal) / depth,
        depth,
      };
    };

    const drawCommands: Array<{ depth: number; draw: () => void }> = [];
    const wallHeight = clamp(maxSpan * 0.08, 3, 26);

    const gridStep = pickGridStep(maxSpan);
    ctx.strokeStyle = "rgba(95, 160, 200, 0.24)";
    ctx.lineWidth = 1;
    for (let x = Math.ceil(geometry.bounds.minX / gridStep) * gridStep; x <= geometry.bounds.maxX + gridStep * 0.5; x += gridStep) {
      const a = project(x, 0, geometry.bounds.minY);
      const b = project(x, 0, geometry.bounds.maxY);
      if (!a || !b) continue;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }
    for (let z = Math.ceil(geometry.bounds.minY / gridStep) * gridStep; z <= geometry.bounds.maxY + gridStep * 0.5; z += gridStep) {
      const a = project(geometry.bounds.minX, 0, z);
      const b = project(geometry.bounds.maxX, 0, z);
      if (!a || !b) continue;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    if (layerState.walls || layerState.boundaries) {
      for (const wall of renderWalls) {
        const boundary = isBoundaryWall(wall.type);
        if (boundary && !layerState.boundaries) continue;
        if (!boundary && !layerState.walls) continue;
        const a0 = project(wall.x1, 0, wall.y1);
        const b0 = project(wall.x2, 0, wall.y2);
        const a1 = project(wall.x1, wallHeight, wall.y1);
        const b1 = project(wall.x2, wallHeight, wall.y2);
        if (!a0 || !b0 || !a1 || !b1) continue;
        const depth = averageDepth([a0, b0, a1, b1]);
        drawCommands.push({
          depth,
          draw: () => {
            ctx.beginPath();
            ctx.moveTo(a0.x, a0.y);
            ctx.lineTo(b0.x, b0.y);
            ctx.lineTo(b1.x, b1.y);
            ctx.lineTo(a1.x, a1.y);
            ctx.closePath();
            ctx.fillStyle = boundary ? "rgba(44, 208, 245, 0.36)" : "rgba(130, 150, 172, 0.25)";
            ctx.fill();
            ctx.strokeStyle = boundary ? "rgba(88, 224, 255, 0.95)" : "rgba(178, 198, 220, 0.58)";
            ctx.lineWidth = boundary ? 1.4 : 1;
            ctx.stroke();
          },
        });
      }
    }

    if (layerState.obstacles) {
      for (const obstacle of geometry.obstacles) {
        if (obstacle.width <= 0 || obstacle.height <= 0) continue;
        const h = clamp((obstacle.width + obstacle.height) * 0.18, 2, wallHeight * 0.8);
        const x1 = obstacle.x;
        const z1 = obstacle.y;
        const x2 = obstacle.x + obstacle.width;
        const z2 = obstacle.y + obstacle.height;

        const p1 = project(x1, 0, z1);
        const p2 = project(x2, 0, z1);
        const p3 = project(x2, 0, z2);
        const p4 = project(x1, 0, z2);
        const t1 = project(x1, h, z1);
        const t2 = project(x2, h, z1);
        const t3 = project(x2, h, z2);
        const t4 = project(x1, h, z2);
        if (!p1 || !p2 || !p3 || !p4 || !t1 || !t2 || !t3 || !t4) continue;

        drawCommands.push({
          depth: averageDepth([p1, p2, p3, p4, t1, t2, t3, t4]),
          draw: () => {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.lineTo(t2.x, t2.y);
            ctx.lineTo(t1.x, t1.y);
            ctx.closePath();
            ctx.fillStyle = "rgba(255, 182, 90, 0.26)";
            ctx.fill();

            ctx.beginPath();
            ctx.moveTo(p2.x, p2.y);
            ctx.lineTo(p3.x, p3.y);
            ctx.lineTo(t3.x, t3.y);
            ctx.lineTo(t2.x, t2.y);
            ctx.closePath();
            ctx.fillStyle = "rgba(255, 182, 90, 0.2)";
            ctx.fill();

            ctx.beginPath();
            ctx.moveTo(t1.x, t1.y);
            ctx.lineTo(t2.x, t2.y);
            ctx.lineTo(t3.x, t3.y);
            ctx.lineTo(t4.x, t4.y);
            ctx.closePath();
            ctx.fillStyle = "rgba(255, 199, 124, 0.3)";
            ctx.fill();
            ctx.strokeStyle = "rgba(255, 218, 164, 0.58)";
            ctx.lineWidth = 1;
            ctx.stroke();
          },
        });
      }
    }

    if (layerState.exits) {
      for (const exit of geometry.exits) {
        const p0 = project(exit.x, 0, exit.y);
        const p1 = project(exit.x, wallHeight * 1.18, exit.y);
        if (!p0 || !p1) continue;
        const depth = averageDepth([p0, p1]);
        drawCommands.push({
          depth,
          draw: () => {
            ctx.strokeStyle = exit.blocked ? "rgba(255, 111, 145, 0.96)" : "rgba(38, 208, 255, 0.96)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(p0.x, p0.y);
            ctx.lineTo(p1.x, p1.y);
            ctx.stroke();
            const radius = clamp((focal / p1.depth) * (exit.width * 0.15 + 1.5), 2.4, 7.4);
            ctx.beginPath();
            ctx.fillStyle = exit.blocked ? "rgba(255, 130, 158, 0.96)" : "rgba(40, 212, 255, 0.98)";
            ctx.arc(p1.x, p1.y, radius, 0, Math.PI * 2);
            ctx.fill();
          },
        });
      }
    }

    for (const agent of geometry.agents) {
      const projected = project(agent.x, 1.6, agent.y);
      if (!projected) continue;
      const radius = clamp((focal / projected.depth) * 1.2, 1.5, 6.5);
      drawCommands.push({
        depth: projected.depth,
        draw: () => {
          ctx.beginPath();
          if (agent.status === "evacuated") {
            ctx.fillStyle = "#40d66f";
          } else if (agent.status === "collapsed") {
            ctx.fillStyle = "#8b5cf6";
          } else {
            const panic = clamp(agent.panicLevel, 0, 1);
            const green = Math.round(176 - panic * 50);
            ctx.fillStyle = `rgb(255 ${green} 79)`;
          }
          ctx.arc(projected.x, projected.y, radius, 0, Math.PI * 2);
          ctx.fill();
        },
      });
    }

    drawCommands.sort((a, b) => b.depth - a.depth);
    for (const command of drawCommands) command.draw();

    const navDebug = (frame.nav_debug ?? {}) as Record<string, unknown>;
    const runtimeWalls = Number(navDebug.runtime_wall_count ?? renderWalls.length);
    const rawWalls = Number(navDebug.raw_wall_count ?? geometry.walls.length);
    const blockedExits = Number(navDebug.blocked_exit_count ?? 0);

    ctx.fillStyle = "#d8e4ef";
    ctx.font = "12px IBM Plex Sans";
    ctx.fillText(`Agents: ${geometry.agents.length}`, 14, height - 40);
    ctx.fillText(`Walls: ${runtimeWalls}/${rawWalls}`, 14, height - 26);
    ctx.fillText(`Blocked exits: ${blockedExits}`, 14, height - 12);
    ctx.fillText("Drag rotate | Shift+Drag pan | Wheel zoom", width - 240, height - 12);
  }, [camera.distance, camera.panX, camera.panZ, camera.pitch, camera.yaw, frame, geometry, layerState.boundaries, layerState.exits, layerState.obstacles, layerState.walls, maxSpan, renderWalls]);

  const resetCamera = () => {
    setCamera({
      yaw: -0.82,
      pitch: 0.62,
      distance: defaultDistance,
      panX: 0,
      panZ: 0,
    });
  };

  const handleWheel = (event: WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault();
    const factor = event.deltaY < 0 ? 0.9 : 1.12;
    setCamera((current) => ({
      ...current,
      distance: clamp(current.distance * factor, 45, 2200),
    }));
  };

  const handlePointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
    const mode: "rotate" | "pan" = event.shiftKey || event.button === 2 ? "pan" : "rotate";
    dragRef.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, mode };
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsDragging(true);
  };

  const handlePointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;

    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    dragRef.current = { ...drag, x: event.clientX, y: event.clientY };

    if (drag.mode === "rotate") {
      setCamera((current) => ({
        ...current,
        yaw: current.yaw + dx * 0.006,
        pitch: clamp(current.pitch + dy * 0.004, 0.16, 1.34),
      }));
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    const scale = (camera.distance / Math.max(220, Math.min(canvas.clientWidth, canvas.clientHeight))) * 1.15;
    setCamera((current) => ({
      ...current,
      panX: current.panX - dx * scale,
      panZ: current.panZ + dy * scale,
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
        <h3 className="section-title">3D Simulation View</h3>
        <button type="button" className="btn-secondary ml-auto" onClick={resetCamera}>
          Reset Camera
        </button>
      </div>
      <p className="mt-2 text-sm text-mist/70">Interactive 3D projection from detected walls, exits, obstacles, and live agent positions.</p>
      <div className="mt-3 overflow-hidden rounded-lg border border-white/10">
        <canvas
          ref={canvasRef}
          className={isDragging ? "h-[430px] w-full cursor-grabbing" : "h-[430px] w-full cursor-grab"}
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onContextMenu={(event) => event.preventDefault()}
        />
      </div>
    </div>
  );
}
