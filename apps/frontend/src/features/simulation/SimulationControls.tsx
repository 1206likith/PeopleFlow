import { FormEvent, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { pauseSimulation, resumeSimulation, startSimulation, stopSimulation } from "@/lib/api/simulation";
import { ApiClientError } from "@/lib/api/client";
import { FloorPlanMetadata } from "@/lib/api/types";

interface SimulationControlsProps {
  selectedSimulationId: string;
  onSimulationStarted: (id: string) => void;
  onRequireAdminKey: () => void;
  defaultFloorPlanId?: string;
  floorPlanSnapshot?: FloorPlanMetadata | null;
}

function isAdminError(error: unknown): boolean {
  return (
    error instanceof ApiClientError &&
    (error.code === "admin_key_missing" || error.code === "admin_key_invalid" || error.status === 401 || error.status === 403)
  );
}

function asFiniteNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function toSegmentList(
  value: unknown,
  limit: number,
): Array<Record<string, number | string>> {
  if (!Array.isArray(value)) {
    return [];
  }
  const segments: Array<Record<string, number | string>> = [];
  for (const item of value) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const source = item as Record<string, unknown>;
    const x1 = asFiniteNumber(source.x1, Number.NaN);
    const y1 = asFiniteNumber(source.y1, Number.NaN);
    const x2 = asFiniteNumber(source.x2, Number.NaN);
    const y2 = asFiniteNumber(source.y2, Number.NaN);
    if (![x1, y1, x2, y2].every(Number.isFinite)) {
      continue;
    }
    segments.push({
      x1,
      y1,
      x2,
      y2,
      type: String(source.type ?? "internal"),
      length: asFiniteNumber(source.length, Math.hypot(x2 - x1, y2 - y1)),
      thickness: clamp(asFiniteNumber(source.thickness, 2), 1, 20),
    });
    if (segments.length >= limit) {
      break;
    }
  }
  return segments;
}

function toRectList(
  value: unknown,
  limit: number,
  yKey: "y" | "z" = "y",
): Array<Record<string, number>> {
  if (!Array.isArray(value)) {
    return [];
  }
  const items: Array<Record<string, number>> = [];
  for (const item of value) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const source = item as Record<string, unknown>;
    const x = asFiniteNumber(source.x, Number.NaN);
    const y = asFiniteNumber(source[yKey] ?? source.y, Number.NaN);
    const width = asFiniteNumber(source.width, Number.NaN);
    const height = asFiniteNumber(source.height, Number.NaN);
    if (![x, y, width, height].every(Number.isFinite) || width <= 0 || height <= 0) {
      continue;
    }
    items.push({ x, y, width, height });
    if (items.length >= limit) {
      break;
    }
  }
  return items;
}

function toExitList(value: unknown, limit: number): Array<Record<string, unknown>> {
  if (!Array.isArray(value)) {
    return [];
  }
  const exits: Array<Record<string, unknown>> = [];
  for (const [index, item] of value.entries()) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const source = item as Record<string, unknown>;
    const x = asFiniteNumber(source.x, Number.NaN);
    const y = asFiniteNumber(source.y ?? source.z, Number.NaN);
    if (![x, y].every(Number.isFinite)) {
      continue;
    }
    const width = clamp(asFiniteNumber(source.width, 2), 0.5, 80);
    exits.push({
      id: String(source.id ?? `snapshot-exit-${index + 1}`),
      name: String(source.name ?? `Snapshot Exit ${index + 1}`),
      x,
      y,
      z: asFiniteNumber(source.z ?? source.y, y),
      width,
      height: clamp(asFiniteNumber(source.height, width), 0.5, 80),
      capacity: Math.max(1, Math.round(asFiniteNumber(source.capacity, width * 12))),
      source: String(source.source ?? "client_snapshot"),
      is_emergency: source.is_emergency !== false,
      is_accessible: source.is_accessible !== false,
    });
    if (exits.length >= limit) {
      break;
    }
  }
  return exits;
}

function buildFloorPlanSnapshot(
  metadata: FloorPlanMetadata | null | undefined,
): Record<string, unknown> | undefined {
  if (!metadata || typeof metadata !== "object") {
    return undefined;
  }

  const walls = toSegmentList(metadata.detected_walls, 2500);
  const boundaries = toSegmentList(metadata.boundaries, 400);
  const obstacles = toRectList(metadata.detected_obstacles, 800, "z");
  const rooms = toRectList(metadata.rooms, 800, "y");
  const exits = toExitList(metadata.exits ?? metadata.detected_exits, 200);

  if (walls.length === 0 && boundaries.length === 0 && exits.length === 0) {
    return undefined;
  }

  const rawBounds = (metadata.building_bounds ?? {}) as Record<string, unknown>;
  const minX = asFiniteNumber(rawBounds.min_x, 0);
  const minY = asFiniteNumber(rawBounds.min_y, 0);
  const maxX = asFiniteNumber(rawBounds.max_x, 0);
  const maxY = asFiniteNumber(rawBounds.max_y, 0);
  const bounds =
    maxX > minX && maxY > minY
      ? {
          min_x: minX,
          min_y: minY,
          max_x: maxX,
          max_y: maxY,
          width: asFiniteNumber(rawBounds.width, maxX - minX),
          height: asFiniteNumber(rawBounds.height, maxY - minY),
        }
      : undefined;

  return {
    id: metadata.id,
    pipeline: metadata.pipeline,
    processing_time_ms: metadata.processing_time_ms,
    building_bounds: bounds,
    image_dimensions: metadata.image_dimensions ?? {},
    detected_walls: walls,
    boundaries,
    detected_obstacles: obstacles,
    rooms,
    exits,
  };
}

interface SnapshotValidation {
  geometryCount: number;
  wallCount: number;
  boundaryCount: number;
  usableExitCount: number;
  pipeline: string;
  simulationReady: boolean | null;
}

function validateSnapshotRuntimeReadiness(
  metadata: FloorPlanMetadata | null | undefined,
): SnapshotValidation | null {
  if (!metadata || typeof metadata !== "object") {
    return null;
  }
  const walls = toSegmentList(metadata.detected_walls, 2500);
  const boundaries = toSegmentList(metadata.boundaries, 1200);
  const exits = toExitList(metadata.exits ?? metadata.detected_exits, 300);
  const quality = (metadata.quality_report ?? {}) as Record<string, unknown>;
  const qualityReady = quality.simulation_ready;
  return {
    geometryCount: walls.length + boundaries.length,
    wallCount: walls.length,
    boundaryCount: boundaries.length,
    usableExitCount: exits.length,
    pipeline: String(metadata.pipeline ?? ""),
    simulationReady:
      typeof metadata.simulation_ready === "boolean"
        ? metadata.simulation_ready
        : typeof qualityReady === "boolean"
          ? qualityReady
          : null,
  };
}

export function SimulationControls({
  selectedSimulationId,
  onSimulationStarted,
  onRequireAdminKey,
  defaultFloorPlanId = "",
  floorPlanSnapshot = null,
}: SimulationControlsProps) {
  const [floorPlanId, setFloorPlanId] = useState(defaultFloorPlanId);
  const [numAgents, setNumAgents] = useState(150);
  const [panicLevel, setPanicLevel] = useState(0.45);
  const [emergencyType, setEmergencyType] = useState("fire");
  const [seed, setSeed] = useState<number | "">("");
  const resolvedFloorPlanId = useMemo(() => {
    const explicit = floorPlanId.trim();
    if (explicit) {
      return explicit;
    }
    const fallback = defaultFloorPlanId.trim();
    return fallback || undefined;
  }, [defaultFloorPlanId, floorPlanId]);
  const resolvedFloorPlanSnapshot = useMemo(
    () => buildFloorPlanSnapshot(floorPlanSnapshot),
    [floorPlanSnapshot],
  );
  const snapshotValidation = useMemo(
    () => validateSnapshotRuntimeReadiness(floorPlanSnapshot),
    [floorPlanSnapshot],
  );
  const snapshotMatchesSelectedFloorPlan = useMemo(() => {
    const snapshotId = typeof floorPlanSnapshot?.id === "string" ? floorPlanSnapshot.id : "";
    if (!snapshotId || !resolvedFloorPlanId) {
      return true;
    }
    return snapshotId === resolvedFloorPlanId;
  }, [floorPlanSnapshot?.id, resolvedFloorPlanId]);
  const startBlockReason = useMemo(() => {
    if (!resolvedFloorPlanId && !resolvedFloorPlanSnapshot) {
      return "Select an uploaded floor plan before starting simulation.";
    }
    if (!snapshotValidation || !snapshotMatchesSelectedFloorPlan) {
      return undefined;
    }
    const pipeline = snapshotValidation.pipeline.trim().toLowerCase();
    if (pipeline === "mock-fallback" || pipeline === "none") {
      return "Active floor plan is fallback geometry. Re-upload and reprocess before starting.";
    }
    if (snapshotValidation.geometryCount <= 0) {
      return "No detected walls/boundaries found for the active floor plan.";
    }
    if (snapshotValidation.usableExitCount <= 0) {
      return "No usable exits found. Add exits in Building Designer.";
    }
    if (snapshotValidation.simulationReady === false) {
      return "Floor plan is marked not simulation-ready. Reprocess in Designer.";
    }
    return undefined;
  }, [resolvedFloorPlanId, resolvedFloorPlanSnapshot, snapshotMatchesSelectedFloorPlan, snapshotValidation]);

  const startMutation = useMutation({
    mutationFn: () =>
      startSimulation({
        floor_plan_id: resolvedFloorPlanId,
        floor_plan_snapshot: resolvedFloorPlanSnapshot,
        num_agents: numAgents,
        emergency_type: emergencyType,
        panic_level: panicLevel,
        seed: seed === "" ? undefined : Number(seed),
      }),
    onSuccess: (result) => onSimulationStarted(result.id),
    onError: (error) => {
      if (isAdminError(error)) {
        onRequireAdminKey();
      }
    },
  });
  const startDisabled = startMutation.isPending || Boolean(startBlockReason);

  const pauseMutation = useMutation({
    mutationFn: () => pauseSimulation(selectedSimulationId),
    onError: (error) => isAdminError(error) && onRequireAdminKey(),
  });
  const resumeMutation = useMutation({
    mutationFn: () => resumeSimulation(selectedSimulationId),
    onError: (error) => isAdminError(error) && onRequireAdminKey(),
  });
  const stopMutation = useMutation({
    mutationFn: () => stopSimulation(selectedSimulationId),
    onError: (error) => isAdminError(error) && onRequireAdminKey(),
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (startBlockReason) {
      return;
    }
    startMutation.mutate();
  };

  return (
    <section className="panel space-y-4">
      <h3 className="section-title">Simulation Control</h3>
      {defaultFloorPlanId && (
        <p className="text-xs text-mist/70">
          Defaulting to active floor plan: <span className="text-mist/90">{defaultFloorPlanId}</span>
        </p>
      )}

      <form className="grid gap-3 sm:grid-cols-2" onSubmit={submit}>
        <label>
          <span className="label">Floor Plan ID</span>
          <input className="input" value={floorPlanId} onChange={(e) => setFloorPlanId(e.target.value)} placeholder="auto-filled from upload" />
        </label>
        <label>
          <span className="label">Emergency Type</span>
          <select className="input" value={emergencyType} onChange={(e) => setEmergencyType(e.target.value)}>
            <option value="fire">Fire</option>
            <option value="earthquake">Earthquake</option>
            <option value="flood">Flood</option>
            <option value="gas_leak">Gas Leak</option>
          </select>
        </label>
        <label>
          <span className="label">Agents</span>
          <input className="input" type="number" min={1} max={10000} value={numAgents} onChange={(e) => setNumAgents(Number(e.target.value))} />
        </label>
        <label>
          <span className="label">Panic Level</span>
          <input
            className="input"
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={panicLevel}
            onChange={(e) => setPanicLevel(Number(e.target.value))}
          />
        </label>
        <label className="sm:col-span-2">
          <span className="label">Seed</span>
          <input
            className="input"
            type="number"
            value={seed}
            onChange={(e) => setSeed(e.target.value === "" ? "" : Number(e.target.value))}
            placeholder="optional"
          />
        </label>

        <div className="sm:col-span-2 flex flex-wrap gap-2">
          <button type="submit" className="btn-primary" disabled={startDisabled}>
            {startMutation.isPending ? "Starting..." : "Start Simulation"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => pauseMutation.mutate()}
            disabled={!selectedSimulationId || pauseMutation.isPending}
          >
            Pause
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => resumeMutation.mutate()}
            disabled={!selectedSimulationId || resumeMutation.isPending}
          >
            Resume
          </button>
          <button
            type="button"
            className="btn-danger"
            onClick={() => stopMutation.mutate()}
            disabled={!selectedSimulationId || stopMutation.isPending}
          >
            Stop
          </button>
        </div>
      </form>

      {snapshotValidation && (
        <p className="text-xs text-mist/70">
          Geometry: {snapshotValidation.geometryCount} ({snapshotValidation.wallCount} walls, {snapshotValidation.boundaryCount} boundaries) | Exits: {snapshotValidation.usableExitCount}
        </p>
      )}
      {startBlockReason && <p className="text-sm text-amber-200">{startBlockReason}</p>}
      {startMutation.error && <p className="text-sm text-rose-300">{String((startMutation.error as Error).message)}</p>}
      {selectedSimulationId && <p className="text-xs text-mist/70">Active simulation: {selectedSimulationId}</p>}
    </section>
  );
}
