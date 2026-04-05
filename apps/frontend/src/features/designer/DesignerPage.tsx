import { CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { ErrorPanel } from "@/components/common/ErrorPanel";
import { ExitConfigPanel } from "@/features/designer/ExitConfigPanel";
import { FloorPlanPreviewCanvas } from "@/features/designer/FloorPlanPreviewCanvas";
import { FloorPlanUploadPanel } from "@/features/designer/FloorPlanUploadPanel";
import {
  mergeDesignerExits,
  normalizeDesignerExits,
  toDesignerExitPayload,
} from "@/features/designer/designerExitModel";
import { AdminKeyDialog } from "@/features/settings/AdminKeyDialog";
import { buildDesignerWorkspaceModel } from "@/lib/api/adapters";
import { ApiClientError } from "@/lib/api/client";
import {
  addFloorPlanExits,
  getFloorPlanMetadata,
  getFloorPlanPipeline,
  getFloorPlanQualityReport,
  reprocessFloorPlan,
} from "@/lib/api/designer";
import { DesignerExitModel, FloorPlanMetadata } from "@/lib/api/types";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";

const LOCAL_FLOOR_PLAN_STORAGE_KEY = "peopleflow.localFloorPlans";

interface PipelineStageViewModel {
  key: string;
  label: string;
  helper: string;
  state: "done" | "current" | "pending";
}

function hasItems(value: unknown): value is unknown[] {
  return Array.isArray(value) && value.length > 0;
}

function toFiniteNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatDescriptor(value: string): string {
  const compact = value.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  if (!compact) return "Unknown";
  return compact.replace(/\b\w/g, (character) => character.toUpperCase());
}

function shortenIdentifier(value: string, leading = 8, trailing = 4): string {
  const trimmed = value.trim();
  if (!trimmed) return "none";
  if (trimmed.length <= leading + trailing + 1) return trimmed;
  return `${trimmed.slice(0, leading)}...${trimmed.slice(-trailing)}`;
}

function readLocalFloorPlanCache(): Record<string, FloorPlanMetadata> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.sessionStorage.getItem(LOCAL_FLOOR_PLAN_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, FloorPlanMetadata>;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeLocalFloorPlanCache(cache: Record<string, FloorPlanMetadata>): void {
  if (typeof window === "undefined") return;
  try {
    const serializable: Record<string, FloorPlanMetadata> = {};
    for (const [id, floorPlan] of Object.entries(cache)) {
      serializable[id] = { ...floorPlan, preview_image_url: undefined };
    }
    window.sessionStorage.setItem(LOCAL_FLOOR_PLAN_STORAGE_KEY, JSON.stringify(serializable));
  } catch {
    // no-op
  }
}

function mergeFloorPlanMetadata(remote?: FloorPlanMetadata, local?: FloorPlanMetadata): FloorPlanMetadata | undefined {
  if (!remote && !local) return undefined;

  const merged: FloorPlanMetadata = { ...(local ?? {}), ...(remote ?? {}) } as FloorPlanMetadata;
  const remotePipeline = typeof remote?.pipeline === "string" ? remote.pipeline : undefined;
  const localPipeline = typeof local?.pipeline === "string" ? local.pipeline : undefined;
  const preferLocalGeometry = remotePipeline === "mock-fallback" && Boolean(localPipeline) && localPipeline !== "mock-fallback";

  const arrayKeys: Array<keyof FloorPlanMetadata> = [
    "detected_walls",
    "detected_exits",
    "detected_obstacles",
    "boundaries",
    "boundary_polygon",
    "rooms",
    "corridors",
    "open_spaces",
    "floors",
    "pipeline_steps",
    "exits",
  ];

  for (const key of arrayKeys) {
    const remoteValue = remote?.[key];
    const localValue = local?.[key];
    if (preferLocalGeometry && hasItems(localValue)) merged[key] = localValue;
    else if (hasItems(remoteValue)) merged[key] = remoteValue;
    else if (hasItems(localValue)) merged[key] = localValue;
  }

  if (remotePipeline === "mock-fallback" && localPipeline && localPipeline !== "mock-fallback") {
    merged.pipeline = localPipeline;
    if (merged.processing_time_ms == null && local?.processing_time_ms != null) merged.processing_time_ms = local.processing_time_ms;
    if (!hasItems(merged.pipeline_steps) && hasItems(local?.pipeline_steps)) merged.pipeline_steps = local.pipeline_steps;
    if ((!merged.processing_metadata || Object.keys(merged.processing_metadata as Record<string, unknown>).length === 0) && local?.processing_metadata) {
      merged.processing_metadata = local.processing_metadata;
    }
  }

  if (typeof local?.preview_image_url === "string" && local.preview_image_url.trim()) {
    merged.preview_image_url = local.preview_image_url;
  }
  if (!merged.id) merged.id = String(remote?.id ?? local?.id ?? "");
  return merged;
}

function resolvePipelineData(
  pipelineData: Record<string, unknown> | undefined,
  metadata: FloorPlanMetadata | undefined,
): Record<string, unknown> | undefined {
  if (!pipelineData && !metadata) return undefined;

  const remotePipeline = typeof pipelineData?.pipeline === "string" ? pipelineData.pipeline : undefined;
  const metadataPipeline = typeof metadata?.pipeline === "string" ? metadata.pipeline : undefined;

  if (!pipelineData) {
    return {
      pipeline: metadataPipeline ?? "unknown",
      processing_time_ms: metadata?.processing_time_ms ?? "n/a",
      pipeline_steps: metadata?.pipeline_steps ?? [],
    };
  }

  if (remotePipeline === "mock-fallback" && metadataPipeline && metadataPipeline !== "mock-fallback") {
    return {
      ...pipelineData,
      pipeline: metadataPipeline,
      processing_time_ms: metadata?.processing_time_ms ?? pipelineData.processing_time_ms,
      pipeline_steps: hasItems(metadata?.pipeline_steps) ? metadata.pipeline_steps : pipelineData.pipeline_steps,
    };
  }

  return pipelineData;
}

function normalizeApiError(error: unknown): ApiClientError | null {
  return error instanceof ApiClientError ? error : null;
}

function isNotFoundApiError(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

function describePlanDimensions(metadata: FloorPlanMetadata | undefined): string {
  const bounds = metadata?.building_bounds as Record<string, unknown> | undefined;
  const minX = toFiniteNumber(bounds?.min_x);
  const maxX = toFiniteNumber(bounds?.max_x);
  const minY = toFiniteNumber(bounds?.min_y);
  const maxY = toFiniteNumber(bounds?.max_y);
  if (minX != null && maxX != null && minY != null && maxY != null && maxX > minX && maxY > minY) {
    return `${Math.round(maxX - minX)} x ${Math.round(maxY - minY)}`;
  }

  const imageDimensions = metadata?.image_dimensions as Record<string, unknown> | undefined;
  const width = toFiniteNumber(imageDimensions?.width ?? imageDimensions?.w);
  const height = toFiniteNumber(imageDimensions?.height ?? imageDimensions?.h);
  if (width != null && height != null && width > 0 && height > 0) {
    return `${Math.round(width)} x ${Math.round(height)} px`;
  }
  return "Awaiting geometry";
}

function buildPipelineStages(args: {
  hasPlan: boolean;
  pipeline?: Record<string, unknown>;
  wallCount: number;
  exitCount: number;
  simulationReady: boolean;
}): PipelineStageViewModel[] {
  const rawSteps = Array.isArray(args.pipeline?.pipeline_steps)
    ? (args.pipeline?.pipeline_steps as Array<Record<string, unknown>>)
    : [];

  if (rawSteps.length > 0) {
    const mapped = rawSteps.map((step, index) => {
      const label = formatDescriptor(String(step.name ?? step.step ?? `stage_${index + 1}`));
      const duration = toFiniteNumber(step.duration_ms ?? step.duration);
      const helper = duration != null ? `${Math.round(duration)} ms` : "Completed";
      return {
        key: `${label}-${index}`,
        label,
        helper,
        state: (index === rawSteps.length - 1 && !args.simulationReady ? "current" : "done") as PipelineStageViewModel["state"],
      };
    });
    mapped.push({
      key: "ready",
      label: "Ready For Simulation",
      helper: args.simulationReady ? "Validated for launch" : "Confirm quality and usable exits",
      state: args.simulationReady ? "done" : "pending",
    });
    return mapped;
  }

  if (!args.hasPlan) {
    return [
      { key: "upload", label: "Upload Plan", helper: "Select a floor plan to begin", state: "current" },
      { key: "parse", label: "Parse Layout", helper: "Geometry will appear here", state: "pending" },
      { key: "detect", label: "Detect Geometry", helper: "Walls and rooms appear after processing", state: "pending" },
      { key: "exits", label: "Configure Exits", helper: "Place exits on the canvas or by form", state: "pending" },
      { key: "ready", label: "Ready For Simulation", helper: "Validation required", state: "pending" },
    ];
  }

  return [
    { key: "upload", label: "Upload Plan", helper: "Plan loaded", state: "done" },
    { key: "parse", label: "Parse Layout", helper: args.pipeline ? formatDescriptor(String(args.pipeline.pipeline ?? "complete")) : "Waiting for pipeline data", state: args.pipeline ? "done" : "current" },
    { key: "detect", label: "Detect Geometry", helper: args.wallCount > 0 ? `${args.wallCount} wall segments available` : "Geometry needs cleanup", state: args.wallCount > 0 ? "done" : args.pipeline ? "current" : "pending" },
    { key: "exits", label: "Configure Exits", helper: args.exitCount > 0 ? `${args.exitCount} exits configured` : "Add at least one usable exit", state: args.exitCount > 0 ? "done" : args.wallCount > 0 ? "current" : "pending" },
    { key: "ready", label: "Ready For Simulation", helper: args.simulationReady ? "Validated for launch" : "Needs stronger coverage", state: args.simulationReady ? "done" : args.exitCount > 0 ? "current" : "pending" },
  ];
}

export function DesignerPage() {
  const queryClient = useQueryClient();
  const activeFloorPlanId = useWorkspaceStore((state) => state.activeFloorPlanId);
  const setActiveFloorPlanId = useWorkspaceStore((state) => state.setActiveFloorPlanId);
  const setActiveFloorPlanSnapshot = useWorkspaceStore((state) => state.setActiveFloorPlanSnapshot);
  const selectedExitId = useWorkspaceStore((state) => state.selectedExitId);
  const setSelectedExitId = useWorkspaceStore((state) => state.setSelectedExitId);
  const clearSelectedExitId = useWorkspaceStore((state) => state.clearSelectedExitId);
  const selectedExitPoints = useWorkspaceStore((state) => state.selectedExitPoints);
  const setSelectedExitPoints = useWorkspaceStore((state) => state.setSelectedExitPoints);
  const clearSelectedExitPoints = useWorkspaceStore((state) => state.clearSelectedExitPoints);
  const canvasZoom = useWorkspaceStore((state) => state.canvasZoom);
  const canvasPan = useWorkspaceStore((state) => state.canvasPan);
  const setCanvasZoom = useWorkspaceStore((state) => state.setCanvasZoom);
  const setCanvasPan = useWorkspaceStore((state) => state.setCanvasPan);
  const designerPaneRatio = useWorkspaceStore((state) => state.designerPaneRatio);
  const setDesignerPaneRatio = useWorkspaceStore((state) => state.setDesignerPaneRatio);

  const [floorPlanId, setFloorPlanId] = useState(activeFloorPlanId);
  const [adminDialogOpen, setAdminDialogOpen] = useState(false);
  const [localFloorPlans, setLocalFloorPlans] = useState<Record<string, FloorPlanMetadata>>(readLocalFloorPlanCache);
  const [remoteUnavailableFloorPlanIds, setRemoteUnavailableFloorPlanIds] = useState<Record<string, true>>({});
  const [previewGridEnabled, setPreviewGridEnabled] = useState(true);
  const [previewPlacementBusy, setPreviewPlacementBusy] = useState(false);
  const [previewPlacementError, setPreviewPlacementError] = useState<unknown>(null);
  const [reprocessMode, setReprocessMode] = useState<"auto" | "traditional" | "semantic">("auto");

  const previewUrlsRef = useRef<Record<string, string>>({});
  const hasLocalSnapshot = Boolean(floorPlanId && localFloorPlans[floorPlanId]);
  const localOnlyFloorPlan = Boolean(hasLocalSnapshot && floorPlanId && remoteUnavailableFloorPlanIds[floorPlanId]);
  const shouldQueryRemoteFloorPlan = Boolean(floorPlanId) && !floorPlanId.startsWith("mock-") && !localOnlyFloorPlan;

  const metadataQuery = useQuery({
    queryKey: ["designer", "metadata", floorPlanId],
    queryFn: ({ signal }) => getFloorPlanMetadata(floorPlanId, undefined, signal),
    enabled: shouldQueryRemoteFloorPlan,
  });
  const pipelineQuery = useQuery({
    queryKey: ["designer", "pipeline", floorPlanId],
    queryFn: ({ signal }) => getFloorPlanPipeline(floorPlanId, signal),
    enabled: shouldQueryRemoteFloorPlan,
  });
  const qualityQuery = useQuery({
    queryKey: ["designer", "quality", floorPlanId],
    queryFn: ({ signal }) => getFloorPlanQualityReport(floorPlanId, undefined, signal),
    enabled: shouldQueryRemoteFloorPlan,
  });

  const remoteMetadata = shouldQueryRemoteFloorPlan ? metadataQuery.data : undefined;
  const remotePipeline = shouldQueryRemoteFloorPlan ? pipelineQuery.data : undefined;
  const remoteQuality = shouldQueryRemoteFloorPlan ? qualityQuery.data : undefined;

  const selectedMetadata = useMemo(() => mergeFloorPlanMetadata(remoteMetadata, localFloorPlans[floorPlanId]), [floorPlanId, localFloorPlans, remoteMetadata]);
  const selectedPipeline = useMemo(() => resolvePipelineData(remotePipeline, selectedMetadata), [remotePipeline, selectedMetadata]);
  const selectedQualityReport = useMemo(
    () => (remoteQuality?.quality_report as Record<string, unknown> | undefined) ?? (selectedMetadata?.quality_report as Record<string, unknown> | undefined),
    [remoteQuality?.quality_report, selectedMetadata?.quality_report],
  );
  const workspaceModel = useMemo(
    () => buildDesignerWorkspaceModel({ floorPlanId, metadata: selectedMetadata, pipeline: selectedPipeline, qualityReport: selectedQualityReport, localOnly: localOnlyFloorPlan }),
    [floorPlanId, localOnlyFloorPlan, selectedMetadata, selectedPipeline, selectedQualityReport],
  );

  const designerContentStyle = useMemo(() => ({ "--designer-canvas": `${Math.round(designerPaneRatio * 100)}%` }) as CSSProperties, [designerPaneRatio]);
  const canvasViewState = useMemo(() => ({ zoom: canvasZoom, panX: canvasPan.x, panY: canvasPan.y }), [canvasPan.x, canvasPan.y, canvasZoom]);

  const qualityScore = toFiniteNumber(selectedQualityReport?.quality_score);
  const usableExitCount = Math.max(workspaceModel.exitCount, toFiniteNumber(selectedQualityReport?.usable_exit_count) ?? 0);
  const geometryCount = toFiniteNumber(selectedQualityReport?.geometry_count) ?? toFiniteNumber(selectedQualityReport?.wall_count) ?? workspaceModel.wallCount;
  const roomCount = toFiniteNumber(selectedQualityReport?.room_count) ?? (Array.isArray(selectedMetadata?.rooms) ? selectedMetadata.rooms.length : 0);
  const readinessReasons = useMemo(() => Array.isArray(selectedQualityReport?.readiness_reasons) ? selectedQualityReport.readiness_reasons.map((reason) => formatDescriptor(String(reason))) : [], [selectedQualityReport]);
  const qualityWarnings = useMemo(() => Array.isArray(selectedQualityReport?.warnings) ? selectedQualityReport.warnings.map((warning) => formatDescriptor(String(warning))) : [], [selectedQualityReport]);
  const planDisplayName = String(selectedMetadata?.building_name ?? selectedMetadata?.filename ?? (floorPlanId ? `Plan ${shortenIdentifier(floorPlanId, 6, 4)}` : "No floor plan selected"));
  const planDimensions = describePlanDimensions(selectedMetadata);
  const processingTimeLabel = selectedMetadata?.processing_time_ms != null && Number.isFinite(Number(selectedMetadata.processing_time_ms)) ? `${Math.round(Number(selectedMetadata.processing_time_ms))} ms` : "n/a";
  const pipelineLabel = formatDescriptor(String(selectedPipeline?.pipeline ?? "idle"));
  const activePlanStatus = !floorPlanId ? "No active plan" : workspaceModel.localOnly ? "Local-only snapshot" : shouldQueryRemoteFloorPlan ? "Connected to backend" : "Session workspace";
  const activePlanHealth = workspaceModel.simulationReady ? "Simulation ready" : usableExitCount > 0 ? "Needs quality pass" : "Needs exits";
  const selectedManualExits = useMemo(
    () =>
      normalizeDesignerExits(
        Array.isArray(selectedMetadata?.manual_exits)
          ? (selectedMetadata?.manual_exits as Array<Record<string, unknown>>)
          : [],
        "manual",
      ),
    [selectedMetadata?.manual_exits],
  );
  const selectedDetectedExits = useMemo(
    () =>
      normalizeDesignerExits(
        Array.isArray(selectedMetadata?.detected_exits)
          ? (selectedMetadata?.detected_exits as Array<Record<string, unknown>>)
          : [],
        "detected",
      ),
    [selectedMetadata?.detected_exits],
  );
  const selectedMetadataExits = useMemo(
    () =>
      normalizeDesignerExits(
        Array.isArray(selectedMetadata?.exits)
          ? (selectedMetadata?.exits as Array<Record<string, unknown>>)
          : [],
        "detected",
      ),
    [selectedMetadata?.exits],
  );
  const selectedVisibleExits = useMemo(() => {
    if (selectedManualExits.length > 0 || selectedDetectedExits.length > 0) {
      return mergeDesignerExits(selectedManualExits, selectedDetectedExits);
    }
    return selectedMetadataExits;
  }, [selectedDetectedExits, selectedManualExits, selectedMetadataExits]);
  const selectedDesignerExit = useMemo(
    () => selectedVisibleExits.find((exitItem) => exitItem.id === selectedExitId) ?? null,
    [selectedExitId, selectedVisibleExits],
  );
  const pipelineStages = useMemo(() => buildPipelineStages({ hasPlan: Boolean(floorPlanId), pipeline: selectedPipeline, wallCount: workspaceModel.wallCount, exitCount: usableExitCount, simulationReady: workspaceModel.simulationReady }), [floorPlanId, selectedPipeline, usableExitCount, workspaceModel.simulationReady, workspaceModel.wallCount]);
  const knownFloorPlans = useMemo(() => {
    const items = new Map<string, FloorPlanMetadata>();
    for (const [id, floorPlan] of Object.entries(localFloorPlans)) items.set(id, floorPlan);
    if (floorPlanId && selectedMetadata) items.set(floorPlanId, selectedMetadata);
    return [...items.entries()]
      .map(([id, floorPlan]) => ({ id, name: String(floorPlan.building_name ?? floorPlan.filename ?? `Plan ${shortenIdentifier(id, 6, 4)}`), helper: describePlanDimensions(floorPlan), floors: Array.isArray(floorPlan.floors) ? floorPlan.floors.length : 0 }))
      .sort((left, right) => (left.id === floorPlanId ? -1 : right.id === floorPlanId ? 1 : left.name.localeCompare(right.name)));
  }, [floorPlanId, localFloorPlans, selectedMetadata]);

  const reprocessMutation = useMutation({
    mutationFn: async () => {
      if (!floorPlanId) throw new Error("No floor plan selected");
      return reprocessFloorPlan(floorPlanId, { mode: reprocessMode, debug: false });
    },
    onSuccess: async () => {
      if (!floorPlanId) return;
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["designer", "metadata", floorPlanId] }),
        queryClient.invalidateQueries({ queryKey: ["designer", "pipeline", floorPlanId] }),
        queryClient.invalidateQueries({ queryKey: ["designer", "quality", floorPlanId] }),
        queryClient.invalidateQueries({ queryKey: ["designer", "exits", floorPlanId] }),
      ]);
    },
    onError: (error) => {
      const apiError = normalizeApiError(error);
      if (apiError && (apiError.code === "admin_key_missing" || apiError.code === "admin_key_invalid")) {
        setAdminDialogOpen(true);
      }
    },
  });

  useEffect(
    () => () => {
      for (const url of Object.values(previewUrlsRef.current)) {
        if (typeof url === "string" && url.startsWith("blob:")) window.URL.revokeObjectURL(url);
      }
      previewUrlsRef.current = {};
    },
    [],
  );

  useEffect(() => {
    writeLocalFloorPlanCache(localFloorPlans);
  }, [localFloorPlans]);

  useEffect(() => {
    if (floorPlanId && floorPlanId !== activeFloorPlanId) setActiveFloorPlanId(floorPlanId);
  }, [activeFloorPlanId, floorPlanId, setActiveFloorPlanId]);

  useEffect(() => {
    if (!floorPlanId || !selectedMetadata) return;
    setActiveFloorPlanSnapshot(selectedMetadata);
  }, [floorPlanId, selectedMetadata, setActiveFloorPlanSnapshot]);

  useEffect(() => {
    clearSelectedExitId();
    clearSelectedExitPoints();
  }, [clearSelectedExitId, clearSelectedExitPoints, floorPlanId]);

  useEffect(() => {
    if (!selectedExitId) {
      if (selectedExitPoints.length > 0) {
        clearSelectedExitPoints();
      }
      return;
    }

    if (!selectedDesignerExit) {
      clearSelectedExitId();
      clearSelectedExitPoints();
      return;
    }

    const nextPoint = { x: Number(selectedDesignerExit.x.toFixed(2)), y: Number(selectedDesignerExit.y.toFixed(2)) };
    const currentPoint = selectedExitPoints[0];
    if (!currentPoint || Math.abs(currentPoint.x - nextPoint.x) > 0.001 || Math.abs(currentPoint.y - nextPoint.y) > 0.001 || selectedExitPoints.length !== 1) {
      setSelectedExitPoints([nextPoint]);
    }
  }, [
    clearSelectedExitId,
    clearSelectedExitPoints,
    selectedDesignerExit,
    selectedExitId,
    selectedExitPoints,
    setSelectedExitPoints,
  ]);

  useEffect(() => {
    if (!floorPlanId || !hasLocalSnapshot) return;
    const hasRemote404 = [metadataQuery.error, pipelineQuery.error, qualityQuery.error].some(isNotFoundApiError);
    if (!hasRemote404) return;
    setRemoteUnavailableFloorPlanIds((previous) => (previous[floorPlanId] ? previous : { ...previous, [floorPlanId]: true }));
  }, [floorPlanId, hasLocalSnapshot, metadataQuery.error, pipelineQuery.error, qualityQuery.error]);

  useEffect(() => {
    if (!floorPlanId || hasLocalSnapshot) return;
    const hasRemote404 = [metadataQuery.error, pipelineQuery.error, qualityQuery.error].some(isNotFoundApiError);
    if (!hasRemote404) return;
    setFloorPlanId("");
    setActiveFloorPlanId("");
    setActiveFloorPlanSnapshot(null);
  }, [floorPlanId, hasLocalSnapshot, metadataQuery.error, pipelineQuery.error, qualityQuery.error, setActiveFloorPlanId, setActiveFloorPlanSnapshot]);

  const upsertLocalPreviewExit = useCallback((exitItem: DesignerExitModel): string => {
    if (!floorPlanId) return exitItem.id;

    let resolvedExitId = exitItem.id;
    setLocalFloorPlans((previous) => {
      const base = previous[floorPlanId] ?? selectedMetadata;
      if (!base) return previous;
      const existingExits = normalizeDesignerExits(
        Array.isArray(base.exits) ? (base.exits as Array<Record<string, unknown>>) : [],
        "manual_local",
      );
      const duplicate = existingExits.find(
        (entry) =>
          Math.abs(entry.x - exitItem.x) < 0.001 &&
          Math.abs(entry.y - exitItem.y) < 0.001,
      );
      if (duplicate) {
        resolvedExitId = duplicate.id;
        return previous;
      }
      const next = {
        ...base,
        exits: [...existingExits, exitItem].map((entry) => toDesignerExitPayload(entry)) as FloorPlanMetadata["exits"],
      };
      setActiveFloorPlanSnapshot(next);
      return { ...previous, [floorPlanId]: next };
    });
    return resolvedExitId;
  }, [floorPlanId, selectedMetadata, setActiveFloorPlanSnapshot]);

  const handlePreviewExitPlacement = useCallback(async (point: { x: number; y: number }) => {
    if (!floorPlanId || previewPlacementBusy) return;
    const exitPayload: DesignerExitModel = {
      id: `manual-exit-${Date.now().toString(36)}`,
      name: `Manual Exit ${selectedVisibleExits.length + 1}`,
      x: Number(point.x.toFixed(2)),
      y: Number(point.y.toFixed(2)),
      z: Number(point.y.toFixed(2)),
      width: 2.0,
      capacity: 100,
      source: "preview_grid",
    };

    setPreviewPlacementError(null);
    setSelectedExitId(exitPayload.id);
    setSelectedExitPoints([point]);
    if (floorPlanId.startsWith("mock-") || localOnlyFloorPlan) {
      const resolvedExitId = upsertLocalPreviewExit(exitPayload);
      setSelectedExitId(resolvedExitId);
      return;
    }

    setPreviewPlacementBusy(true);
    try {
      await addFloorPlanExits(floorPlanId, [toDesignerExitPayload(exitPayload)]);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["designer", "exits", floorPlanId] }),
        queryClient.invalidateQueries({ queryKey: ["designer", "metadata", floorPlanId] }),
        queryClient.invalidateQueries({ queryKey: ["designer", "pipeline", floorPlanId] }),
      ]);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError && (apiError.code === "admin_key_missing" || apiError.code === "admin_key_invalid")) setAdminDialogOpen(true);
      setPreviewPlacementError(error);
    } finally {
      setPreviewPlacementBusy(false);
    }
  }, [floorPlanId, localOnlyFloorPlan, previewPlacementBusy, queryClient, selectedVisibleExits.length, setSelectedExitId, setSelectedExitPoints, upsertLocalPreviewExit]);

  const handleStoredPlanSelection = useCallback((nextPlanId: string) => {
    if (!nextPlanId || nextPlanId === floorPlanId) return;
    setFloorPlanId(nextPlanId);
    setActiveFloorPlanId(nextPlanId);
    if (localFloorPlans[nextPlanId]) setActiveFloorPlanSnapshot(localFloorPlans[nextPlanId]);
    setCanvasZoom(1);
    setCanvasPan({ x: 0, y: 0 });
    clearSelectedExitId();
    clearSelectedExitPoints();
  }, [clearSelectedExitId, clearSelectedExitPoints, floorPlanId, localFloorPlans, setActiveFloorPlanId, setActiveFloorPlanSnapshot, setCanvasPan, setCanvasZoom]);

  const handleFloorPlanUploaded = useCallback((payload: FloorPlanMetadata) => {
    const id = String(payload.id ?? "");
    if (!id) return;

    const nextPreviewUrl = typeof payload.preview_image_url === "string" ? payload.preview_image_url : "";
    const previousPreviewUrl = previewUrlsRef.current[id];
    if (previousPreviewUrl && previousPreviewUrl !== nextPreviewUrl && previousPreviewUrl.startsWith("blob:")) {
      window.URL.revokeObjectURL(previousPreviewUrl);
    }
    if (nextPreviewUrl) previewUrlsRef.current[id] = nextPreviewUrl;

    setLocalFloorPlans((previous) => ({ ...previous, [id]: mergeFloorPlanMetadata(payload, previous[id]) ?? payload }));
    setRemoteUnavailableFloorPlanIds((previous) => {
      if (!previous[id]) return previous;
      const next = { ...previous };
      delete next[id];
      return next;
    });
    setActiveFloorPlanId(id);
    setActiveFloorPlanSnapshot(payload);
    setCanvasZoom(1);
    setCanvasPan({ x: 0, y: 0 });
    clearSelectedExitId();
    clearSelectedExitPoints();
    setFloorPlanId(id);
  }, [clearSelectedExitId, clearSelectedExitPoints, setActiveFloorPlanId, setActiveFloorPlanSnapshot, setCanvasPan, setCanvasZoom]);

  const handleLocalExitsUpdated = useCallback((nextExits: DesignerExitModel[]) => {
    if (!floorPlanId) return;

    setLocalFloorPlans((previous) => {
      const existing = previous[floorPlanId] ?? selectedMetadata;
      if (!existing) return previous;

      const normalizedExits = nextExits.map((exitItem) => toDesignerExitPayload(exitItem)) as FloorPlanMetadata["exits"];
      const next = { ...existing, exits: normalizedExits };
      setActiveFloorPlanSnapshot(next);
      return { ...previous, [floorPlanId]: next };
    });

    if (selectedExitId && !nextExits.some((exitItem) => exitItem.id === selectedExitId)) {
      clearSelectedExitId();
      clearSelectedExitPoints();
    }
  }, [clearSelectedExitId, clearSelectedExitPoints, floorPlanId, selectedExitId, selectedMetadata, setActiveFloorPlanSnapshot]);

  const metricCards = [
    { label: "Pipeline", value: pipelineLabel, helper: activePlanStatus },
    { label: "Quality", value: qualityScore != null ? `${Math.round(qualityScore * 100)}%` : "--", helper: activePlanHealth },
    { label: "Exits", value: String(usableExitCount), helper: "Detected and authored" },
    { label: "Geometry", value: `${geometryCount}/${workspaceModel.obstacleCount}`, helper: "Geometry / obstacles" },
  ];

  const resetCanvasView = () => {
    setCanvasZoom(1);
    setCanvasPan({ x: 0, y: 0 });
    clearSelectedExitId();
    clearSelectedExitPoints();
  };

  return (
    <motion.div className="designer-page animate-fade-rise workspace-shell" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}>
      <motion.section className="workspace-hero designer-intro" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28 }}>
        <div className="designer-intro-grid">
          <div className="space-y-3">
            <p className="label">Design Workflow</p>
            <div className="space-y-2">
              <h2 className="designer-intro-title">Prepare a floor plan for simulation-ready evacuation research.</h2>
              <p className="max-w-3xl text-sm leading-relaxed text-fog">The designer now works like a studio: intake on the left, the spatial canvas in the center, and diagnostics plus exit authoring on the right so you can move from upload to readiness without losing context.</p>
            </div>
            <div className="workspace-chip-row">
              <span className="workspace-chip">Active Plan <strong>{floorPlanId ? shortenIdentifier(floorPlanId, 8, 4) : "none"}</strong></span>
              <span className="workspace-chip">Status <strong>{workspaceModel.simulationReady ? "Ready" : "Draft"}</strong></span>
              <span className="workspace-chip">Source <strong>{workspaceModel.localOnly ? "Local" : floorPlanId ? "Backend" : "Idle"}</strong></span>
            </div>
          </div>
          <div className="designer-intro-actions">
            <button type="button" className={previewGridEnabled ? "btn-primary" : "btn-secondary"} onClick={() => setPreviewGridEnabled(!previewGridEnabled)}>Grid Snap {previewGridEnabled ? "On" : "Off"}</button>
            <button type="button" className="btn-secondary" onClick={() => floorPlanId && reprocessMutation.mutate()} disabled={!floorPlanId || reprocessMutation.isPending || floorPlanId.startsWith("mock-") || localOnlyFloorPlan}>{reprocessMutation.isPending ? "Reprocessing" : "Reprocess"}</button>
            <button type="button" className="btn-secondary" onClick={resetCanvasView}>Reset Canvas</button>
          </div>
        </div>
      </motion.section>

      <motion.div className="designer-metric-grid" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.06, staggerChildren: 0.05 }}>
        {metricCards.map((card) => (
          <motion.div key={card.label} className="glass-card p-4" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.24 }}>
            <p className="label">{card.label}</p>
            <p className="mt-2 text-2xl font-bold text-snow" style={{ fontFamily: "var(--font-heading)" }}>{card.value}</p>
            <p className="mt-1 text-xs text-fog">{card.helper}</p>
          </motion.div>
        ))}
      </motion.div>

      <div className="designer-studio-grid">
        <aside className="designer-setup-stack">
          <FloorPlanUploadPanel onUploaded={handleFloorPlanUploaded} onRequireAdminKey={() => setAdminDialogOpen(true)} />
          <section className="workspace-pane space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="section-title">Plan Library</h2>
              <span className="theme-fixed-pill">{knownFloorPlans.length} cached</span>
            </div>
            {knownFloorPlans.length === 0 ? <p className="text-sm text-fog">Uploaded plans stay here for the current session so you can switch contexts quickly.</p> : <div className="designer-plan-list">{knownFloorPlans.map((plan) => (
              <button key={plan.id} type="button" className={`designer-plan-button ${plan.id === floorPlanId ? "is-active" : ""}`} onClick={() => handleStoredPlanSelection(plan.id)} title={plan.id}>
                <span className="designer-plan-name">{plan.name}</span>
                <span className="designer-plan-helper">{plan.helper}</span>
                <span className="designer-plan-helper">{plan.floors > 0 ? `${plan.floors} floor${plan.floors > 1 ? "s" : ""}` : "Single workspace"} - {shortenIdentifier(plan.id, 6, 4)}</span>
              </button>
            ))}</div>}
          </section>
          <section className="workspace-pane space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="section-title">Active Plan</h2>
              <span className="theme-fixed-pill">{activePlanHealth}</span>
            </div>
            {floorPlanId ? <div className="designer-summary-grid">
              <div className="designer-summary-card"><p className="label">Plan</p><p className="designer-summary-value">{planDisplayName}</p><p className="designer-summary-helper">{shortenIdentifier(floorPlanId, 8, 4)}</p></div>
              <div className="designer-summary-card"><p className="label">Dimensions</p><p className="designer-summary-value">{planDimensions}</p><p className="designer-summary-helper">{activePlanStatus}</p></div>
              <div className="designer-summary-card"><p className="label">Pipeline</p><p className="designer-summary-value">{pipelineLabel}</p><p className="designer-summary-helper">Processing {processingTimeLabel}</p></div>
              <div className="designer-summary-card"><p className="label">Floors</p><p className="designer-summary-value">{Array.isArray(selectedMetadata?.floors) ? selectedMetadata.floors.length : 1}</p><p className="designer-summary-helper">{usableExitCount} usable exits</p></div>
            </div> : <p className="text-sm text-fog">Upload a plan to see building metadata, revision details, and readiness posture.</p>}
          </section>
          <section className="workspace-pane space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="section-title">Canvas Controls</h2>
              <span className="theme-fixed-pill">{Math.round(designerPaneRatio * 100)} / {100 - Math.round(designerPaneRatio * 100)}</span>
            </div>
            <label className="block"><span className="label">Canvas emphasis</span><input className="input mt-2" type="range" min={52} max={72} value={Math.round(designerPaneRatio * 100)} onChange={(event) => setDesignerPaneRatio(Number(event.target.value) / 100)} /></label>
            <div className="designer-summary-grid">
              <div className="designer-summary-card"><p className="label">Zoom</p><p className="designer-summary-value">{canvasZoom.toFixed(2)}x</p><p className="designer-summary-helper">Current viewport scale</p></div>
              <div className="designer-summary-card"><p className="label">Selected Exit</p><p className="designer-summary-value">{selectedDesignerExit ? "1" : "0"}</p><p className="designer-summary-helper">{selectedDesignerExit ? selectedDesignerExit.source : "No active selection"}</p></div>
            </div>
            {selectedDesignerExit && <div className="space-y-2"><div className="rounded-xl border border-emerald-300/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100">{selectedDesignerExit.name}: ({selectedDesignerExit.x.toFixed(2)}, {selectedDesignerExit.y.toFixed(2)}) • width {selectedDesignerExit.width.toFixed(2)} • cap {selectedDesignerExit.capacity}</div></div>}
          </section>
        </aside>

        <div className="designer-main-grid" style={designerContentStyle}>
          <section className="designer-canvas-stage">
            <section className="workspace-pane space-y-4">
              <div className="designer-stage-toolbar">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="label">Spatial Canvas</p>
                    {previewPlacementBusy && <span className="theme-fixed-pill">Saving exit placement</span>}
                  </div>
                  <h3 className="section-title text-xl">Preview-first editing workspace</h3>
                  <p className="text-sm leading-relaxed text-fog">The canvas is the primary surface. Use grid placement for fast exit authoring, then confirm quality and pipeline readiness without leaving the page.</p>
                </div>
                <div className="designer-stage-badges">
                  <span className="workspace-chip">Grid <strong>{previewGridEnabled ? "Snap On" : "Free"}</strong></span>
                  <span className="workspace-chip">Plan <strong>{floorPlanId ? shortenIdentifier(floorPlanId, 6, 4) : "none"}</strong></span>
                  <span className="workspace-chip">Mode <strong>{reprocessMode}</strong></span>
                </div>
              </div>
              <label className="block max-w-xs"><span className="label">Reprocess mode</span><select className="input mt-2" value={reprocessMode} onChange={(event) => setReprocessMode(event.target.value as "auto" | "traditional" | "semantic")}><option value="auto">Auto</option><option value="traditional">Traditional</option><option value="semantic">Semantic</option></select></label>
              {previewPlacementError != null && <ErrorPanel error={previewPlacementError} />}
            </section>
            {!floorPlanId ? <section className="workspace-pane min-h-[560px] grid place-items-center"><EmptyState title="No floor plan loaded" message="Upload a plan to start editing geometry." /></section> : selectedMetadata ? <ErrorBoundary><FloorPlanPreviewCanvas floorPlan={selectedMetadata} displayExits={selectedVisibleExits} enableGrid={previewGridEnabled} enableExitPlacement={previewGridEnabled} onPlaceExit={previewGridEnabled ? handlePreviewExitPlacement : undefined} viewState={canvasViewState} onViewStateChange={(nextViewState) => { setCanvasZoom(nextViewState.zoom); setCanvasPan({ x: nextViewState.panX, y: nextViewState.panY }); }} selectedExitId={selectedExitId} onSelectedExitIdChange={setSelectedExitId} selectedExitPoints={selectedExitPoints} onSelectedExitPointsChange={setSelectedExitPoints} /></ErrorBoundary> : <section className="workspace-pane min-h-[560px] grid place-items-center text-sm text-fog">Loading floor plan...</section>}
          </section>

          <aside className="designer-insight-stack">
            <section className="workspace-pane space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="section-title">Pipeline Progress</h2>
                <span className="theme-fixed-pill">{workspaceModel.simulationReady ? "Ready" : "In Review"}</span>
              </div>
              {floorPlanId && shouldQueryRemoteFloorPlan && pipelineQuery.isLoading && <p className="text-sm text-fog">Loading pipeline...</p>}
              {!floorPlanId ? <p className="text-sm text-fog">Upload a plan to unlock the processing pipeline and step-level readiness guidance.</p> : <ol className="designer-pipeline-list">{pipelineStages.map((stage) => <li key={stage.key} className={`designer-pipeline-item is-${stage.state}`}><span className="designer-pipeline-dot" aria-hidden="true" /><div className="space-y-1"><p className="designer-pipeline-label">{stage.label}</p><p className="designer-pipeline-helper">{stage.helper}</p></div></li>)}</ol>}
              {shouldQueryRemoteFloorPlan && pipelineQuery.error && <ErrorPanel error={pipelineQuery.error} />}
              {reprocessMutation.error && <ErrorPanel error={reprocessMutation.error} />}
            </section>
            <section className="workspace-pane space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="section-title">Readiness & Quality</h2>
                <span className="theme-fixed-pill">{qualityScore != null ? `${Math.round(qualityScore * 100)} score` : "No score"}</span>
              </div>
              {floorPlanId && shouldQueryRemoteFloorPlan && qualityQuery.isLoading && <p className="text-sm text-fog">Loading quality report...</p>}
              {floorPlanId && !shouldQueryRemoteFloorPlan && hasLocalSnapshot && <p className="text-xs text-amber-200">Using the local cached floor plan because the backend record is unavailable.</p>}
              {shouldQueryRemoteFloorPlan && qualityQuery.error && <ErrorPanel error={qualityQuery.error} />}
              <div className="designer-quality-grid">
                <div className="designer-summary-card"><p className="label">Quality</p><p className="designer-summary-value">{qualityScore != null ? `${Math.round(qualityScore * 100)}%` : "--"}</p><p className="designer-summary-helper">Signal confidence</p></div>
                <div className="designer-summary-card"><p className="label">Usable Exits</p><p className="designer-summary-value">{usableExitCount}</p><p className="designer-summary-helper">Ready for simulation</p></div>
                <div className="designer-summary-card"><p className="label">Rooms</p><p className="designer-summary-value">{roomCount}</p><p className="designer-summary-helper">Semantic spaces</p></div>
                <div className="designer-summary-card"><p className="label">Geometry</p><p className="designer-summary-value">{geometryCount}</p><p className="designer-summary-helper">Walls and boundaries</p></div>
              </div>
              {readinessReasons.length > 0 && <div className="space-y-2"><p className="label">Readiness blockers</p><div className="designer-note-list">{readinessReasons.map((reason) => <div key={reason} className="designer-note-chip">{reason}</div>)}</div></div>}
              {qualityWarnings.length > 0 && <div className="space-y-2"><p className="label">Warnings</p><div className="designer-note-list">{qualityWarnings.map((warning) => <div key={warning} className="designer-note-chip is-warning">{warning}</div>)}</div></div>}
            </section>
            {floorPlanId ? <ExitConfigPanel floorPlanId={floorPlanId} useLocalOnly={localOnlyFloorPlan} onRequireAdminKey={() => setAdminDialogOpen(true)} seedExits={selectedVisibleExits} selectedExitId={selectedExitId} onSelectedExitIdChange={setSelectedExitId} onLocalExitsUpdated={handleLocalExitsUpdated} /> : <section className="workspace-pane"><EmptyState title="Exit authoring unavailable" message="Upload a floor plan first." /></section>}
            <section className="workspace-pane space-y-3">
              <h3 className="section-title">Structured Diagnostics</h3>
              <p className="text-sm text-fog">Raw payloads are still available for debugging, but the main page now prioritizes human-readable readiness signals first.</p>
              {selectedPipeline && <details className="designer-raw-details"><summary>Pipeline payload</summary><pre className="code-panel max-h-[220px]">{JSON.stringify(selectedPipeline, null, 2)}</pre></details>}
              {selectedQualityReport && <details className="designer-raw-details"><summary>Quality payload</summary><pre className="code-panel max-h-[220px]">{JSON.stringify(selectedQualityReport, null, 2)}</pre></details>}
            </section>
          </aside>
        </div>
      </div>

      <AdminKeyDialog open={adminDialogOpen} onClose={() => setAdminDialogOpen(false)} />
    </motion.div>
  );
}
