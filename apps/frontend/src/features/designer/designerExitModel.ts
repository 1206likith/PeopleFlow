import { DesignerExitModel } from "@/lib/api/types";

export interface ExitDraftModel {
  name: string;
  x: number;
  y: number;
  z: number;
  width: number;
  capacity: number;
}

function toFiniteNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function buildExitKey(exitItem: Pick<DesignerExitModel, "id" | "x" | "z">): string {
  const id = String(exitItem.id ?? "").trim();
  if (id) {
    return `id:${id}`;
  }
  return `coord:${Math.round(exitItem.x * 100)}:${Math.round(exitItem.z * 100)}`;
}

export function toDesignerExitDraft(exitItem?: DesignerExitModel | null): ExitDraftModel {
  if (!exitItem) {
    return {
      name: "Main Exit",
      x: 0,
      y: 0,
      z: 0,
      width: 2,
      capacity: 100,
    };
  }

  return {
    name: exitItem.name,
    x: exitItem.x,
    y: exitItem.y,
    z: exitItem.z,
    width: exitItem.width,
    capacity: exitItem.capacity,
  };
}

export function normalizeDesignerExit(
  entry: Record<string, unknown>,
  index: number,
  sourceFallback = "detected",
): DesignerExitModel | null {
  const x = toFiniteNumber(entry.x, Number.NaN);
  const y = toFiniteNumber(entry.y ?? entry.z, Number.NaN);
  const z = toFiniteNumber(entry.z ?? entry.y, Number.NaN);

  if (![x, y, z].every(Number.isFinite)) {
    return null;
  }

  return {
    id: String(entry.id ?? `${sourceFallback}-exit-${index + 1}`),
    name: String(entry.name ?? `Exit ${index + 1}`),
    x,
    y,
    z,
    width: Math.max(0.5, toFiniteNumber(entry.width, 2)),
    capacity: Math.max(1, Math.round(toFiniteNumber(entry.capacity, 100))),
    source: String(entry.source ?? sourceFallback),
  };
}

export function normalizeDesignerExits(
  entries: Array<Record<string, unknown>>,
  sourceFallback = "detected",
): DesignerExitModel[] {
  return entries
    .map((entry, index) => normalizeDesignerExit(entry, index, sourceFallback))
    .filter((entry): entry is DesignerExitModel => Boolean(entry));
}

export function mergeDesignerExits(
  primary: DesignerExitModel[],
  secondary: DesignerExitModel[],
): DesignerExitModel[] {
  const merged: DesignerExitModel[] = [];
  const seen = new Set<string>();

  const pushUnique = (exitItem: DesignerExitModel) => {
    const key = buildExitKey(exitItem);
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    merged.push(exitItem);
  };

  for (const exitItem of primary) {
    pushUnique(exitItem);
  }
  for (const exitItem of secondary) {
    pushUnique(exitItem);
  }

  return merged;
}

export function buildDesignerExitSelectionRadius(gridCellPixels: number): number {
  const safeGrid = Number.isFinite(gridCellPixels) ? gridCellPixels : 0;
  return Math.min(30, Math.max(18, Math.max(18, safeGrid / 2)));
}

export function toDesignerExitPayload(exitItem: ExitDraftModel & Partial<DesignerExitModel>): Record<string, unknown> {
  return {
    id: exitItem.id,
    name: exitItem.name,
    x: Number(exitItem.x.toFixed(2)),
    y: Number(exitItem.y.toFixed(2)),
    z: Number(exitItem.z.toFixed(2)),
    width: Number(exitItem.width.toFixed(2)),
    capacity: Math.round(exitItem.capacity),
    source: exitItem.source,
    is_emergency: true,
    is_accessible: true,
  };
}
