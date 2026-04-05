import { CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  normalizeSimulationAnalysisSnapshot,
  normalizeSimulationFrame,
  normalizeSimulationSession,
  normalizeSimulationSessionConfig,
} from "@/lib/api/adapters";
import {
  controlSimulationSession,
  createSimulationSession,
  getSimulationSession,
  getSimulationSessionAnalysis,
  getSimulationSessionReplay,
  listSimulationSessions,
} from "@/lib/api/simulationSessions";
import { DisasterPreset, SimulationControlCommand, SimulationEvent } from "@/lib/api/types";
import { extractSimulationFrameFromSocketPayload } from "@/lib/contracts/simulationContracts";
import { useSpringCounter } from "@/lib/hooks/useSpringCounter";
import { useSessionStore } from "@/lib/state/sessionStore";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";
import { PeopleFlowSocketClient } from "@/lib/ws/socketClient";
import { WebSocketMessage } from "@/lib/api/types";
import { AdminKeyDialog } from "@/features/settings/AdminKeyDialog";
import { SimulationCanvas2D } from "@/features/simulation/SimulationCanvas2D";
import { SimulationCanvas3D } from "@/features/simulation/SimulationCanvas3D";
import { TimelineStrip } from "@/features/simulation/TimelineStrip";

const policies = [
  { label: "Shortest Path", value: "shortest_path" },
  { label: "Least Crowded", value: "least_crowded" },
  { label: "Guided Evacuation", value: "guided_evacuation" },
] as const;

const emergencyTypes = [
  { value: "fire", label: "Fire" },
  { value: "earthquake", label: "Earthquake" },
  { value: "flood", label: "Flood" },
  { value: "gas_leak", label: "Gas Leak" },
  { value: "bomb_blast", label: "Bomb Blast" },
] as const;

const modes = [
  { value: "studio", label: "Studio" },
  { value: "validation", label: "Validation" },
  { value: "batch", label: "Batch" },
] as const;

const disasterPresets: DisasterPreset[] = [
  {
    id: "fire",
    label: "Fire Drill",
    emergencyType: "fire",
    policy: "guided_evacuation",
    panicLevel: 0.58,
    speedMultiplier: 1.08,
    agentCount: 260,
    summary: "Smoke pressure and visibility loss reward guided egress.",
  },
  {
    id: "earthquake",
    label: "Earthquake",
    emergencyType: "earthquake",
    policy: "least_crowded",
    panicLevel: 0.68,
    speedMultiplier: 0.88,
    agentCount: 220,
    summary: "Debris and exit disruption favor congestion-aware routing.",
  },
  {
    id: "flood",
    label: "Flood",
    emergencyType: "flood",
    policy: "least_crowded",
    panicLevel: 0.48,
    speedMultiplier: 0.72,
    agentCount: 180,
    summary: "Water drag slows movement and compresses safe corridors.",
  },
  {
    id: "gas_leak",
    label: "Gas Leak",
    emergencyType: "gas_leak",
    policy: "guided_evacuation",
    panicLevel: 0.56,
    speedMultiplier: 0.94,
    agentCount: 200,
    summary: "Exposure risk and low visibility benefit orderly guidance.",
  },
  {
    id: "bomb_blast",
    label: "Bomb Blast",
    emergencyType: "bomb_blast",
    policy: "shortest_path",
    panicLevel: 0.82,
    speedMultiplier: 1.22,
    agentCount: 140,
    summary: "Acute shock favors immediate nearest-exit escape.",
  },
];

function formatPolicyLabel(value: string): string {
  const hit = policies.find((entry) => entry.value === value);
  if (hit) return hit.label;
  return value.replace(/_/g, " ");
}

function studioStateLabel(status: string): string {
  const normalized = String(status || "draft").replace(/_/g, " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

export function SimulationHubPage() {
  const [adminDialogOpen, setAdminDialogOpen] = useState(false);
  const adminKey = useSessionStore((state) => state.adminKey);
  const reducedMotion = useSessionStore((state) => state.reducedMotion);
  const activeFloorPlanId = useWorkspaceStore((state) => state.activeFloorPlanId);
  const activeFloorPlanSnapshot = useWorkspaceStore((state) => state.activeFloorPlanSnapshot);
  const {
    activeSession,
    activeSessionId,
    frames,
    liveFrame,
    currentFrameIndex,
    eventBuffer,
    analysisSnapshot,
    connectionState,
    viewMode,
    isReplaying,
    draftConfig,
    simulationPaneRatio,
    setActiveSession,
    setSelectedSimulationId,
    setDraftConfig,
    updateDraftConfig,
    setLiveFrame,
    appendFrame,
    setFrames,
    clearSessionRuntime,
    appendEvent,
    setEventBuffer,
    setAnalysisSnapshot,
    setSocketStatus,
    setViewMode,
    setCurrentFrameIndex,
    setIsReplaying,
    setSimulationPaneRatio,
  } = useSimulationStore();

  const socketRef = useRef<PeopleFlowSocketClient | null>(null);
  const launchLockRef = useRef(false);
  const normalizedDraft = normalizeSimulationSessionConfig({
    ...draftConfig,
    floor_plan_ref: draftConfig.floor_plan_ref || activeFloorPlanId || undefined,
    floor_plan_snapshot: draftConfig.floor_plan_snapshot || activeFloorPlanSnapshot || undefined,
  });
  const activeStatus = activeSession?.state.status ?? "draft";
  const analysisEnabled = Boolean(activeSessionId) && !["draft", "starting"].includes(activeStatus);
  const replayEnabled =
    Boolean(activeSessionId) &&
    !["draft", "starting"].includes(activeStatus) &&
    (isReplaying || activeStatus !== "running");

  const sessionsQuery = useQuery({
    queryKey: ["simulation-v3", "sessions"],
    queryFn: ({ signal }) => listSimulationSessions({ limit: 40 }, signal),
    refetchInterval: 10_000,
  });

  const sessionDetailQuery = useQuery({
    queryKey: ["simulation-v3", "session", activeSessionId],
    queryFn: ({ signal }) => getSimulationSession(activeSessionId, signal),
    enabled: Boolean(activeSessionId),
    refetchInterval:
      activeStatus === "starting" ? 2_000 : activeStatus === "running" || activeStatus === "paused" ? 6_000 : 10_000,
  });

  const analysisQuery = useQuery({
    queryKey: ["simulation-v3", "analysis", activeSessionId],
    queryFn: ({ signal }) => getSimulationSessionAnalysis(activeSessionId, signal),
    enabled: analysisEnabled,
    refetchInterval: activeStatus === "running" ? 8_000 : activeStatus === "paused" ? 12_000 : false,
  });

  const replayQuery = useQuery({
    queryKey: ["simulation-v3", "replay", activeSessionId],
    queryFn: ({ signal }) => getSimulationSessionReplay(activeSessionId, { limit: 180 }, signal),
    enabled: replayEnabled,
    refetchInterval: isReplaying ? 8_000 : activeStatus !== "running" ? 12_000 : false,
  });

  const launchMutation = useMutation({
    mutationFn: async () => createSimulationSession(normalizedDraft),
    onMutate: () => {
      launchLockRef.current = true;
    },
    onSuccess: (session) => {
      const normalized = normalizeSimulationSession(session);
      clearSessionRuntime();
      setActiveSession(normalized);
      setSelectedSimulationId(normalized.id);
      controlMutation.mutate({ action: "start", sessionId: normalized.id });
    },
    onError: () => {
      setAdminDialogOpen(true);
    },
    onSettled: () => {
      launchLockRef.current = false;
    },
  });

  const controlMutation = useMutation({
    mutationFn: ({ action, exitId, targetExit, message, sessionId }: { action: string; exitId?: string; targetExit?: string; message?: string; sessionId?: string }) =>
      controlSimulationSession(sessionId || activeSessionId, {
        action,
        exit_id: exitId,
        target_exit: targetExit,
        message,
      } as SimulationControlCommand),
    onSuccess: (session) => {
      setActiveSession(normalizeSimulationSession(session));
    },
    onError: () => {
      setAdminDialogOpen(true);
    },
  });

  useEffect(() => {
    if (sessionDetailQuery.data) {
      setActiveSession(normalizeSimulationSession(sessionDetailQuery.data));
    }
  }, [sessionDetailQuery.data, setActiveSession]);

  useEffect(() => {
    if (analysisQuery.data) {
      setAnalysisSnapshot(normalizeSimulationAnalysisSnapshot(analysisQuery.data));
    }
  }, [analysisQuery.data, setAnalysisSnapshot]);

  useEffect(() => {
    if (replayQuery.data) {
      setFrames(replayQuery.data.frames ?? []);
      setEventBuffer(replayQuery.data.events ?? []);
    }
  }, [replayQuery.data, setEventBuffer, setFrames]);

  useEffect(() => {
    if (!activeSessionId) {
      socketRef.current?.disconnect();
      socketRef.current = null;
      setSocketStatus("idle");
      return;
    }

    socketRef.current?.disconnect();
    const socket = new PeopleFlowSocketClient({
      onStatus: (status) => setSocketStatus(status),
      onMessage: (message: WebSocketMessage) => {
        const frame = extractSimulationFrameFromSocketPayload(message);
        if (frame) {
          setLiveFrame(frame);
          appendFrame(frame);
        } else if (message.type && message.type !== "subscribed" && message.type !== "pong") {
          appendEvent({
            event_id: `socket-${Date.now()}`,
            session_id: activeSessionId,
            type: String(message.type),
            timestamp: Number(message.timestamp ?? Date.now()),
            severity: "info",
            title: String(message.type).replace(/_/g, " "),
            message: JSON.stringify(message),
            data: message,
          });
        }
      },
      onError: () => setSocketStatus("error"),
    });

    socketRef.current = socket;
    socket.connect({ simulationId: activeSessionId, adminKey: adminKey || undefined });

    return () => {
      socket.disconnect();
    };
  }, [activeSessionId, adminKey, appendEvent, appendFrame, setLiveFrame, setSocketStatus]);

  const activeFrame = useMemo(() => {
    if (isReplaying) {
      return frames[currentFrameIndex] ?? frames[frames.length - 1] ?? liveFrame;
    }
    return liveFrame ?? frames[frames.length - 1] ?? null;
  }, [currentFrameIndex, frames, isReplaying, liveFrame]);

  const normalizedFrame = normalizeSimulationFrame(activeFrame);
  const liveAgentCounter = useSpringCounter(normalizedFrame?.agentCount ?? normalizedDraft.num_agents, 520);
  const evacCounter = useSpringCounter(normalizedFrame?.evacuated ?? analysisSnapshot?.evacuated ?? 0, 520);
  const heatmapVisible = (normalizedFrame?.peakDensity ?? analysisSnapshot?.peak_density ?? 0) > 0.18;
  const selectedPreset = disasterPresets.find((preset) => preset.emergencyType === normalizedDraft.emergency_type) ?? null;
  const sessionRows = sessionsQuery.data?.sessions?.map((row) => normalizeSimulationSession(row)) ?? [];
  const eventRows = [...(eventBuffer ?? []), ...(activeSession?.recent_events ?? [])]
    .reduce<SimulationEvent[]>((acc, event) => {
      if (!acc.find((row) => row.event_id === event.event_id)) acc.push(event);
      return acc;
    }, [])
    .slice(-8)
    .reverse();

  const canLaunch = !launchMutation.isPending && !launchLockRef.current && Boolean(normalizedDraft.floor_plan_ref || normalizedDraft.floor_plan_snapshot);

  const handleLaunch = () => {
    if (!canLaunch) return;
    launchMutation.mutate();
  };

  const handleControl = (action: string) => {
    if (!activeSessionId || controlMutation.isPending) return;
    controlMutation.mutate({ action });
  };

  const applyPreset = (preset: DisasterPreset) => {
    updateDraftConfig({
      emergency_type: preset.emergencyType,
      routing_policy: preset.policy,
      panic_level: preset.panicLevel,
      num_agents: preset.agentCount,
      parameter_overrides: {
        ...(normalizedDraft.parameter_overrides ?? {}),
        speed_multiplier: preset.speedMultiplier,
      },
    });
  };

  return (
    <div className="studio-page">
      <header className="studio-header p-6">
        <div>
          <p className="studio-kicker">Simulation Studio</p>
          <h1>Session-First Control Workspace</h1>
          <p className="mt-3 max-w-3xl">
            Build a draft configuration, launch one canonical simulation session, stay attached to its live stream, and inspect replay plus analysis in the same workspace.
          </p>
        </div>
        <div className="studio-metrics-inline">
          <span>Agents {Math.round(liveAgentCounter)}</span>
          <span>Evacuated {Math.round(evacCounter)}</span>
          <span>Socket {connectionState}</span>
          <span>Session {activeSessionId || "none"}</span>
        </div>
      </header>

      <section
        className="studio-layout"
        style={{ "--studio-split-pane": `${Math.round(simulationPaneRatio * 100)}%` } as CSSProperties}
      >
        <div className="studio-viewport">
          <div className="studio-view-toolbar">
            <div className="studio-view-modes">
              {(["2d", "3d", "split"] as const).map((mode) => (
                <button key={mode} type="button" className={viewMode === mode ? "active" : ""} onClick={() => setViewMode(mode)}>
                  {mode.toUpperCase()}
                </button>
              ))}
            </div>
            <div className={`studio-heatmap-indicator ${heatmapVisible ? "visible" : ""}`}>
              {heatmapVisible ? "Density heatmap active" : "Heatmap standby"}
            </div>
          </div>

          <div className={`studio-canvas-shell ${viewMode === "split" ? "studio-canvas-shell-split" : ""}`}>
            {(viewMode === "2d" || viewMode === "split") && (
              <div className={viewMode === "split" ? "studio-half" : "studio-full"}>
                <SimulationCanvas2D
                  frame={activeFrame}
                  layers={{ walls: true, boundaries: true, exits: true, obstacles: true, trails: true, heatmap: heatmapVisible }}
                />
              </div>
            )}
            {(viewMode === "3d" || viewMode === "split") && (
              <div className={viewMode === "split" ? "studio-half" : "studio-full"}>
                <SimulationCanvas3D
                  frame={activeFrame}
                  layers={{ walls: true, boundaries: true, exits: true, obstacles: true, trails: true, heatmap: heatmapVisible }}
                />
              </div>
            )}
          </div>

          <section className="studio-panel mt-4">
            <div className="flex items-center justify-between gap-3">
              <h3>Live event strip</h3>
              <span className="theme-fixed-pill">{eventRows.length} events</span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {eventRows.length > 0 ? eventRows.map((event) => (
                <article key={event.event_id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="label">{event.type.replace(/_/g, " ")}</p>
                  <h4 className="mt-2 text-sm font-semibold text-white">{event.title}</h4>
                  <p className="mt-2 text-xs leading-relaxed text-slate-300">{event.message}</p>
                  <p className="mt-3 font-mono text-[11px] text-cyan-200">t={event.timestamp.toFixed(1)}</p>
                </article>
              )) : (
                <p className="text-sm text-slate-400">Launch a session to start capturing runtime events.</p>
              )}
            </div>
          </section>

          <section className="studio-panel mt-4">
            <div className="flex items-center justify-between gap-3">
              <h3>Replay and analysis timeline</h3>
              <span className="theme-fixed-pill">{frames.length} buffered frames</span>
            </div>
            <div className="mt-4">
              <TimelineStrip frames={frames} />
            </div>
            {frames.length > 1 && (
              <div className="mt-4">
                <label className="label flex items-center justify-between">
                  Replay scrubber
                  <span>{currentFrameIndex + 1}/{Math.max(frames.length, 1)}</span>
                </label>
                <input
                  className="mt-3 w-full"
                  type="range"
                  min={0}
                  max={Math.max(0, frames.length - 1)}
                  value={currentFrameIndex}
                  onChange={(event) => setCurrentFrameIndex(Number(event.target.value))}
                />
              </div>
            )}
          </section>
        </div>

        <aside className="studio-controls">
          <section className="studio-panel">
            <div className="flex items-center justify-between gap-3">
              <h3>Session selector</h3>
              <span className="theme-fixed-pill">{studioStateLabel(activeStatus)}</span>
            </div>
            <select className="input mt-4" value={activeSessionId} onChange={(event) => setSelectedSimulationId(event.target.value)}>
              <option value="">Create and launch a new session...</option>
              {sessionRows.map((session) => (
                <option key={session.id} value={session.id}>
                  {session.id} - {session.state.status}
                </option>
              ))}
            </select>
            <p className="mt-3 text-xs text-slate-400">
              Draft floor plan: <span className="font-mono text-slate-100">{normalizedDraft.floor_plan_ref || "snapshot only"}</span>
            </p>
          </section>

          <section className="studio-panel">
            <div className="studio-disaster-header">
              <h3>Disaster presets</h3>
              <span className="studio-disaster-caption">Presets tune hazard type, routing, population, and movement bias as one coherent session draft.</span>
            </div>
            <div className="studio-disaster-grid">
              {disasterPresets.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className={`studio-disaster-card ${selectedPreset?.id === preset.id ? "selected" : ""}`}
                  onClick={() => applyPreset(preset)}
                >
                  <div className="studio-disaster-topline">
                    <span>{preset.label}</span>
                    <span>{preset.agentCount} agents</span>
                  </div>
                  <p>{preset.summary}</p>
                </button>
              ))}
            </div>
          </section>

          <section className="studio-panel">
            <h3>Draft configuration</h3>
            <div className="grid gap-4">
              <label>
                <span className="label">Emergency type</span>
                <select className="input mt-2" value={normalizedDraft.emergency_type} onChange={(e) => updateDraftConfig({ emergency_type: e.target.value })}>
                  {emergencyTypes.map((entry) => (
                    <option key={entry.value} value={entry.value}>{entry.label}</option>
                  ))}
                </select>
              </label>

              <label>
                <span className="label">Routing policy</span>
                <div className="mt-2 grid gap-2">
                  {policies.map((entry) => (
                    <button
                      key={entry.value}
                      type="button"
                      className={`rounded-2xl border px-4 py-3 text-left ${normalizedDraft.routing_policy === entry.value ? "border-cyan-400 bg-cyan-500/10 text-white" : "border-white/10 bg-white/5 text-slate-300"}`}
                      onClick={() => updateDraftConfig({ routing_policy: entry.value })}
                    >
                      {entry.label}
                    </button>
                  ))}
                </div>
              </label>

              <label>
                <span className="label">Mode</span>
                <select className="input mt-2" value={normalizedDraft.mode} onChange={(e) => updateDraftConfig({ mode: e.target.value as "studio" | "validation" | "batch" })}>
                  {modes.map((entry) => (
                    <option key={entry.value} value={entry.value}>{entry.label}</option>
                  ))}
                </select>
              </label>

              <label>
                <span className="label flex items-center justify-between">
                  Agent count
                  <span>{normalizedDraft.num_agents}</span>
                </span>
                <input className="mt-2 w-full" type="range" min={20} max={600} step={10} value={normalizedDraft.num_agents} onChange={(e) => updateDraftConfig({ num_agents: Number(e.target.value) })} />
              </label>

              <label>
                <span className="label flex items-center justify-between">
                  Panic level
                  <span>{normalizedDraft.panic_level.toFixed(2)}</span>
                </span>
                <input className="mt-2 w-full" type="range" min={0} max={1} step={0.01} value={normalizedDraft.panic_level} onChange={(e) => updateDraftConfig({ panic_level: Number(e.target.value) })} />
              </label>

              <label>
                <span className="label flex items-center justify-between">
                  Speed multiplier
                  <span>{Number(normalizedDraft.parameter_overrides?.speed_multiplier ?? 1).toFixed(2)}</span>
                </span>
                <input
                  className="mt-2 w-full"
                  type="range"
                  min={0.5}
                  max={2}
                  step={0.01}
                  value={Number(normalizedDraft.parameter_overrides?.speed_multiplier ?? 1)}
                  onChange={(e) => updateDraftConfig({ parameter_overrides: { ...normalizedDraft.parameter_overrides, speed_multiplier: Number(e.target.value) } })}
                />
              </label>

              <label>
                <span className="label">Seed</span>
                <input
                  className="input mt-2"
                  type="number"
                  value={normalizedDraft.seed ?? ""}
                  onChange={(e) => updateDraftConfig({ seed: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="deterministic seed"
                />
              </label>
            </div>
          </section>

          <section className="studio-panel">
            <h3>Run control</h3>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" className="btn-primary" onClick={handleLaunch} disabled={!canLaunch}>
                {launchMutation.isPending ? "Launching..." : "Launch Session"}
              </button>
              <button type="button" className="btn-secondary" onClick={() => handleControl("pause")} disabled={!activeSessionId || activeStatus !== "running" || controlMutation.isPending}>
                Pause
              </button>
              <button type="button" className="btn-secondary" onClick={() => handleControl("resume")} disabled={!activeSessionId || activeStatus !== "paused" || controlMutation.isPending}>
                Resume
              </button>
              <button type="button" className="btn-secondary" onClick={() => handleControl("stop")} disabled={!activeSessionId || !["running", "paused", "stopping"].includes(activeStatus) || controlMutation.isPending}>
                Stop
              </button>
              <button type="button" className="btn-secondary" onClick={() => handleControl("reset")} disabled={!activeSessionId || controlMutation.isPending}>
                Reset
              </button>
            </div>
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
              <p>Active session: <span className="font-mono text-slate-100">{activeSessionId || "none"}</span></p>
              <p className="mt-1">State: {studioStateLabel(activeStatus)}</p>
              <p className="mt-1">Policy: {formatPolicyLabel(normalizedDraft.routing_policy)}</p>
              <p className="mt-1">Replay: {isReplaying ? "scrubbing" : "following live"}</p>
              <div className="mt-3 flex gap-2">
                <button type="button" className="btn-secondary" onClick={() => setIsReplaying(!isReplaying)} disabled={frames.length < 2}>
                  {isReplaying ? "Follow Live" : "Replay"}
                </button>
                <button type="button" className="btn-secondary" onClick={() => setSimulationPaneRatio(simulationPaneRatio === 0.6 ? 0.52 : 0.6)}>
                  Toggle Split
                </button>
              </div>
            </div>
          </section>

          <section className="studio-panel">
            <h3>Analysis dock</h3>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="label">Completion</p>
                <h4 className="mt-2 text-2xl font-semibold text-white">{(analysisSnapshot?.completion_percentage ?? 0).toFixed(1)}%</h4>
              </article>
              <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="label">Peak Density</p>
                <h4 className="mt-2 text-2xl font-semibold text-white">{(analysisSnapshot?.peak_density ?? 0).toFixed(2)}</h4>
              </article>
              <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="label">Flow Rate</p>
                <h4 className="mt-2 text-2xl font-semibold text-white">{(analysisSnapshot?.flow_rate ?? 0).toFixed(2)}</h4>
              </article>
              <article className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="label">Sim Time</p>
                <h4 className="mt-2 text-2xl font-semibold text-white">{(analysisSnapshot?.simulation_time ?? 0).toFixed(1)}s</h4>
              </article>
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="label">Exit usage</p>
              <div className="mt-3 grid gap-2">
                {Object.entries(analysisSnapshot?.exit_usage ?? {}).length > 0 ? Object.entries(analysisSnapshot?.exit_usage ?? {}).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between rounded-xl border border-white/5 bg-black/10 px-3 py-2 text-sm">
                    <span className="font-mono text-slate-200">{key}</span>
                    <span className="text-cyan-200">{value}</span>
                  </div>
                )) : <p className="text-sm text-slate-400">Exit usage populates once frames accumulate.</p>}
              </div>
            </div>
          </section>
        </aside>
      </section>

      <AdminKeyDialog open={adminDialogOpen} onClose={() => setAdminDialogOpen(false)} />
    </div>
  );
}
