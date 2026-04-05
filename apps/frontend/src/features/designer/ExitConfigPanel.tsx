import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addFloorPlanExits,
  deleteFloorPlanExit,
  getFloorPlanExits,
  replaceFloorPlanExits,
} from "@/lib/api/designer";
import { ErrorPanel } from "@/components/common/ErrorPanel";
import { EmptyState } from "@/components/common/EmptyState";
import { ApiClientError } from "@/lib/api/client";
import { DesignerExitModel } from "@/lib/api/types";
import {
  ExitDraftModel,
  mergeDesignerExits,
  normalizeDesignerExits,
  toDesignerExitDraft,
  toDesignerExitPayload,
} from "@/features/designer/designerExitModel";

interface ExitConfigPanelProps {
  floorPlanId: string;
  onRequireAdminKey: () => void;
  useLocalOnly?: boolean;
  seedExits?: DesignerExitModel[];
  selectedExitId?: string;
  onSelectedExitIdChange?: (exitId: string) => void;
  onLocalExitsUpdated?: (exits: DesignerExitModel[]) => void;
}

const DEFAULT_DRAFT = toDesignerExitDraft();

function normalizeApiError(error: unknown): ApiClientError | null {
  return error instanceof ApiClientError ? error : null;
}

function isManualSource(source: string): boolean {
  return source.startsWith("manual") || source === "preview_grid" || source === "manual_override";
}

function buildManualOverrideId(exitItem: DesignerExitModel): string {
  return isManualSource(exitItem.source) ? exitItem.id : `manual-override-${exitItem.id}`;
}

function buildExitLabel(exitItem: DesignerExitModel): string {
  return exitItem.name || exitItem.id;
}

function buildSourceLabel(exitItem: DesignerExitModel): string {
  return exitItem.source.replace(/_/g, " ");
}

export function ExitConfigPanel({
  floorPlanId,
  onRequireAdminKey,
  useLocalOnly = false,
  seedExits = [],
  selectedExitId = "",
  onSelectedExitIdChange,
  onLocalExitsUpdated,
}: ExitConfigPanelProps) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<ExitDraftModel>(DEFAULT_DRAFT);
  const isLocalMockPlan = floorPlanId.startsWith("mock-") || useLocalOnly;

  const exitsQuery = useQuery({
    queryKey: ["designer", "exits", floorPlanId],
    queryFn: ({ signal }) => getFloorPlanExits(floorPlanId, undefined, signal),
    enabled: Boolean(floorPlanId) && !isLocalMockPlan,
  });

  const remoteManualExits = useMemo(
    () =>
      normalizeDesignerExits(
        Array.isArray(exitsQuery.data?.manual_exits)
          ? (exitsQuery.data?.manual_exits as Array<Record<string, unknown>>)
          : [],
        "manual",
      ),
    [exitsQuery.data?.manual_exits],
  );
  const remoteDetectedExits = useMemo(
    () =>
      normalizeDesignerExits(
        Array.isArray(exitsQuery.data?.detected_exits)
          ? (exitsQuery.data?.detected_exits as Array<Record<string, unknown>>)
          : [],
        "detected",
      ),
    [exitsQuery.data?.detected_exits],
  );
  const remoteVisibleFallback = useMemo(
    () =>
      normalizeDesignerExits(
        Array.isArray(exitsQuery.data?.exits)
          ? (exitsQuery.data?.exits as Array<Record<string, unknown>>)
          : [],
        "detected",
      ),
    [exitsQuery.data?.exits],
  );

  const exits = useMemo(() => {
    if (isLocalMockPlan) {
      return seedExits;
    }
    if (remoteManualExits.length > 0 || remoteDetectedExits.length > 0) {
      return mergeDesignerExits(remoteManualExits, remoteDetectedExits);
    }
    if (remoteVisibleFallback.length > 0) {
      return remoteVisibleFallback;
    }
    return seedExits;
  }, [isLocalMockPlan, remoteDetectedExits, remoteManualExits, remoteVisibleFallback, seedExits]);

  const editableManualExits = useMemo(
    () => (isLocalMockPlan ? seedExits : remoteManualExits),
    [isLocalMockPlan, remoteManualExits, seedExits],
  );

  const selectedExit = useMemo(
    () => exits.find((exitItem) => exitItem.id === selectedExitId) ?? null,
    [exits, selectedExitId],
  );

  useEffect(() => {
    if (!selectedExitId) {
      setDraft(DEFAULT_DRAFT);
      return;
    }
    if (!selectedExit) {
      onSelectedExitIdChange?.("");
      return;
    }
    setDraft(toDesignerExitDraft(selectedExit));
  }, [onSelectedExitIdChange, selectedExit, selectedExitId]);

  const invalidate = async () => {
    if (isLocalMockPlan) {
      return;
    }
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["designer", "exits", floorPlanId] }),
      queryClient.invalidateQueries({ queryKey: ["designer", "metadata", floorPlanId] }),
      queryClient.invalidateQueries({ queryKey: ["designer", "pipeline", floorPlanId] }),
      queryClient.invalidateQueries({ queryKey: ["designer", "quality", floorPlanId] }),
    ]);
  };

  const handleMutationError = (error: unknown) => {
    const apiError = normalizeApiError(error);
    if (apiError && (apiError.code === "admin_key_missing" || apiError.code === "admin_key_invalid")) {
      onRequireAdminKey();
    }
  };

  const addMutation = useMutation({
    mutationFn: async () => {
      const nextExit: DesignerExitModel = {
        id: `manual-exit-${Date.now().toString(36)}`,
        name: draft.name || `Manual Exit ${exits.length + 1}`,
        x: draft.x,
        y: draft.y,
        z: draft.z,
        width: draft.width,
        capacity: draft.capacity,
        source: isLocalMockPlan ? "manual_local" : "manual_override",
      };

      if (isLocalMockPlan) {
        const nextExits = [...editableManualExits, nextExit];
        onLocalExitsUpdated?.(nextExits);
        return { selectedExitId: nextExit.id };
      }

      await addFloorPlanExits(floorPlanId, [toDesignerExitPayload(nextExit)]);
      return { selectedExitId: nextExit.id };
    },
    onSuccess: async ({ selectedExitId: nextSelectedExitId }) => {
      await invalidate();
      onSelectedExitIdChange?.(nextSelectedExitId);
    },
    onError: handleMutationError,
  });

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedExit) {
        return { selectedExitId: "" };
      }

      const nextId = buildManualOverrideId(selectedExit);
      const nextExit: DesignerExitModel = {
        id: nextId,
        name: draft.name || selectedExit.name || "Manual Exit",
        x: draft.x,
        y: draft.y,
        z: draft.z,
        width: draft.width,
        capacity: draft.capacity,
        source: isLocalMockPlan ? "manual_local" : "manual_override",
      };

      if (isLocalMockPlan) {
        const nextExits = exits.map((exitItem) => (exitItem.id === selectedExit.id ? nextExit : exitItem));
        onLocalExitsUpdated?.(nextExits);
        return { selectedExitId: nextExit.id };
      }

      const existingManual = editableManualExits.find((exitItem) => exitItem.id === nextId);
      const nextManualExits = existingManual
        ? editableManualExits.map((exitItem) => (exitItem.id === nextId ? nextExit : exitItem))
        : [...editableManualExits, nextExit];
      await replaceFloorPlanExits(
        floorPlanId,
        nextManualExits.map((exitItem) => toDesignerExitPayload(exitItem)),
      );
      return { selectedExitId: nextExit.id };
    },
    onSuccess: async ({ selectedExitId: nextSelectedExitId }) => {
      await invalidate();
      onSelectedExitIdChange?.(nextSelectedExitId);
    },
    onError: handleMutationError,
  });

  const deleteMutation = useMutation({
    mutationFn: async (exitItem: DesignerExitModel) => {
      if (isLocalMockPlan) {
        const nextExits = exits.filter((candidate) => candidate.id !== exitItem.id);
        onLocalExitsUpdated?.(nextExits);
        return;
      }
      await deleteFloorPlanExit(floorPlanId, exitItem.id);
    },
    onSuccess: async (_, exitItem) => {
      await invalidate();
      if (selectedExitId === exitItem.id) {
        onSelectedExitIdChange?.("");
      }
    },
    onError: handleMutationError,
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedExit) {
      updateMutation.mutate();
      return;
    }
    addMutation.mutate();
  };

  const handleClearSelection = () => {
    onSelectedExitIdChange?.("");
    setDraft(DEFAULT_DRAFT);
  };

  const mutationBusy = addMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  return (
    <section className="panel space-y-4">
      <div className="space-y-2">
        <h3 className="section-title">Exit Configuration</h3>
        <p className="text-sm text-mist/70">
          Select exits directly on the grid to edit them. Detected exits can be overridden or removed for
          this floor-plan revision without changing the original source scan.
        </p>
      </div>

      <form className="grid gap-3 sm:grid-cols-2" onSubmit={handleSubmit}>
        <label>
          <span className="label">Name</span>
          <input
            className="input"
            value={draft.name}
            onChange={(event) => setDraft((previous) => ({ ...previous, name: event.target.value }))}
          />
        </label>
        <label>
          <span className="label">Width</span>
          <input
            className="input"
            type="number"
            min={0.5}
            step={0.1}
            value={draft.width}
            onChange={(event) => setDraft((previous) => ({ ...previous, width: Number(event.target.value) }))}
          />
        </label>
        <label>
          <span className="label">X</span>
          <input
            className="input"
            type="number"
            value={draft.x}
            onChange={(event) => setDraft((previous) => ({ ...previous, x: Number(event.target.value) }))}
          />
        </label>
        <label>
          <span className="label">Y</span>
          <input
            className="input"
            type="number"
            value={draft.y}
            onChange={(event) => setDraft((previous) => ({ ...previous, y: Number(event.target.value), z: Number(event.target.value) }))}
          />
        </label>
        <label>
          <span className="label">Z</span>
          <input
            className="input"
            type="number"
            value={draft.z}
            onChange={(event) => setDraft((previous) => ({ ...previous, z: Number(event.target.value), y: Number(event.target.value) }))}
          />
        </label>
        <label>
          <span className="label">Capacity</span>
          <input
            className="input"
            type="number"
            min={1}
            value={draft.capacity}
            onChange={(event) => setDraft((previous) => ({ ...previous, capacity: Number(event.target.value) }))}
          />
        </label>

        <div className="sm:col-span-2 flex flex-wrap gap-2">
          <button type="submit" className="btn-primary" disabled={mutationBusy}>
            {selectedExit ? "Update Selected Exit" : "Add New Exit"}
          </button>
          {selectedExit && (
            <>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => addMutation.mutate()}
                disabled={mutationBusy}
              >
                Add New Exit
              </button>
              <button type="button" className="btn-secondary" onClick={handleClearSelection} disabled={mutationBusy}>
                Clear Selection
              </button>
            </>
          )}
        </div>
      </form>

      {selectedExit && (
        <div className="rounded-xl border border-emerald-300/20 bg-emerald-500/10 px-3 py-3 text-xs text-emerald-100">
          Editing <strong>{buildExitLabel(selectedExit)}</strong> from <strong>{selectedExit.source}</strong>.
          {!isManualSource(selectedExit.source) && " Saving this change will create a manual override."}
        </div>
      )}

      {!isLocalMockPlan && exitsQuery.isLoading && <p className="text-sm text-mist/70">Loading exits...</p>}
      {!isLocalMockPlan && exitsQuery.error && <ErrorPanel error={exitsQuery.error} />}

      {(isLocalMockPlan || !exitsQuery.isLoading) && exits.length === 0 && (
        <EmptyState title="No exits loaded" message="Click the grid to add an exit or upload a plan with detected exits." />
      )}

      {addMutation.error != null && <ErrorPanel error={addMutation.error} />}
      {updateMutation.error != null && <ErrorPanel error={updateMutation.error} />}
      {deleteMutation.error != null && <ErrorPanel error={deleteMutation.error} />}

      {exits.length > 0 && (
        <div className="space-y-2">
          {exits.map((exitItem) => {
            const isSelected = selectedExitId === exitItem.id;
            return (
              <div
                key={exitItem.id}
                className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-ink/45 p-3 ${
                  isSelected ? "border-emerald-300/40 bg-emerald-500/10" : "border-white/10"
                }`}
              >
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  onClick={() => onSelectedExitIdChange?.(exitItem.id)}
                >
                  <p className="text-sm font-semibold text-white">{buildExitLabel(exitItem)}</p>
                  <p className="text-xs text-mist/70">
                    ({exitItem.x.toFixed(2)}, {exitItem.z.toFixed(2)}) width: {exitItem.width.toFixed(2)} • source:{" "}
                    {buildSourceLabel(exitItem)}
                  </p>
                </button>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => deleteMutation.mutate(exitItem)}
                  disabled={deleteMutation.isPending}
                >
                  Delete
                </button>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
