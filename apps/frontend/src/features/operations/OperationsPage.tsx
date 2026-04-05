import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiClientError } from "@/lib/api/client";
import {
  exportSimulationBatch,
  exportSimulationFramesCsv,
  getBatchesAliasSubpath,
  getSimulationAgents,
  getSimulationBatch,
  getSimulationHazards,
  getSimulationSurvivalScore,
  getUnityStatus,
  listBatchesAlias,
  listSimulationBatches,
  startBatchSimulation,
  updateSimulationBoundary,
  updateSimulationExits,
  updateSimulationHazards,
  updateSimulationMetadata,
} from "@/lib/api/simulation";
import {
  controlSimulationSession,
  getSimulationSessionAnalysis,
  listSimulationSessions,
} from "@/lib/api/simulationSessions";
import {
  getAuditLog,
  getCapability,
  getSystemConfig,
  getSystemInfo,
  getSystemStatus,
  listActiveCapabilities,
  listCapabilities,
  listCapabilityCategories,
  updateCapability,
} from "@/lib/api/system";
import { addMetricsFrame, calculateMetrics, resetMetrics } from "@/lib/api/metrics";
import { mlPredictCongestion, mlRecommendations, mlRecommendExits } from "@/lib/api/ml";
import { comparePolicies, optimizeExits } from "@/lib/api/optimization";
import {
  downloadPdfReport,
  getHeatmapData,
  getReplayAgentTimeline,
  getReplayDeathZones,
  getReplayDensityEvolution,
  getReplayReport,
  getReplayTimeline,
  getValidationBenchmarks,
  predictBottlenecks,
  predictDeathZones,
  predictExitCollapse,
  predictOptimize,
  predictSurvivalScore,
  validateSimulation,
} from "@/lib/api/analytics";
import { getResultFrames, getResultSummary, saveResultFrame } from "@/lib/api/results";
import { getUnityScene, unityControl, unityStart } from "@/lib/api/unity";
import { getFloorPlansAliasRoot, getFloorPlansAliasSubpath } from "@/lib/api/designer";
import { getScenarioRecommendedExits } from "@/lib/api/scenarios";
import { getFloorPlanTrainingStatus, trainFloorPlanModel } from "@/lib/api/models";
import { AdminKeyDialog } from "@/features/settings/AdminKeyDialog";
import { computeBatchCompletion, normalizeBatchRow, rankBatchesByEvacTime } from "@/lib/contracts/batchAggregation";
import { useSessionStore } from "@/lib/state/sessionStore";

const tabs = [
  "System",
  "ML",
  "Optimization",
  "Metrics",
  "Results",
  "Simulation Ops",
  "Batches",
  "Unity",
  "Aliases",
] as const;
type OpsTab = (typeof tabs)[number];

function defaultJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function safeParseJson(raw: string): unknown {
  return JSON.parse(raw);
}

function isAdminError(error: unknown): boolean {
  return (
    error instanceof ApiClientError &&
    (error.status === 401 || error.status === 403 || error.code === "admin_key_missing" || error.code === "admin_key_invalid")
  );
}

export function OperationsPage() {
  const adminKey = useSessionStore((state) => state.adminKey);
  const [expandedTab, setExpandedTab] = useState<OpsTab | null>("System");
  const [busyKey, setBusyKey] = useState("");
  const [results, setResults] = useState<Record<string, unknown>>({});
  const [adminDialogOpen, setAdminDialogOpen] = useState(false);

  const [simulationId, setSimulationId] = useState("");
  const [disasterType, setDisasterType] = useState("fire");
  const [batchId, setBatchId] = useState("");
  const [aliasSubpath, setAliasSubpath] = useState("");
  const [floorAliasSubpath, setFloorAliasSubpath] = useState("");
  const [capabilityId, setCapabilityId] = useState("");
  const [capabilityEnabled, setCapabilityEnabled] = useState(true);
  const [capabilitySource, setCapabilitySource] = useState("frontend-ops");
  const [agentId, setAgentId] = useState(1);
  const [buildingType, setBuildingType] = useState("office");

  const [mlPayload, setMlPayload] = useState(
    defaultJson({
      agents: [{ agent_id: 1, x: 2, y: 2, z: 0, speed: 1.2, status: "moving" }],
      exits: [{ id: "e1", x: 10, y: 0, z: 0, width: 2, capacity: 100 }],
      time_horizon: 30,
    }),
  );

  const [optimizePayload, setOptimizePayload] = useState(
    defaultJson({
      building_bounds: { min_x: 0, max_x: 100, min_y: 0, max_y: 100 },
      current_exits: [{ id: "e1", x: 10, y: 0, z: 0, width: 2 }],
      num_agents: 120,
      generations: 10,
      population_size: 10,
    }),
  );

  const [predictOptimizePayload, setPredictOptimizePayload] = useState(
    defaultJson({
      exits: [{ id: "e1", x: 10, y: 0, z: 0, width: 2 }],
      building_bounds: { min_x: 0, max_x: 100, min_y: 0, max_y: 100 },
      agent_positions: [{ x: 1, y: 1, z: 0 }],
      current_score: 72,
      budget: 100000,
    }),
  );

  const [metricsFramePayload, setMetricsFramePayload] = useState(
    defaultJson({ timestamp: 1, agents: [{ agent_id: 1, x: 1, y: 1, z: 0, speed: 1, status: "moving" }], bottlenecks: [] }),
  );

  const [resultFramePayload, setResultFramePayload] = useState(
    defaultJson({ timestamp: 1, agents: [{ agent_id: 1, x: 1, y: 1, z: 0, speed: 1, status: "moving" }], bottlenecks: [] }),
  );

  const [hazardUpdatePayload, setHazardUpdatePayload] = useState(
    defaultJson([{ type: "fire", x: 10, y: 10, z: 0, intensity: 0.7, radius: 6 }]),
  );

  const [exitUpdatePayload, setExitUpdatePayload] = useState(
    defaultJson([{ id: "e1", name: "Exit A", x: 10, y: 0, z: 0, width: 2, capacity: 100 }]),
  );

  const [boundaryUpdatePayload, setBoundaryUpdatePayload] = useState(
    defaultJson({ points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }] }),
  );

  const [metadataUpdatePayload, setMetadataUpdatePayload] = useState(defaultJson({ tags: ["review"], notes: "ops update", priority: 5 }));

  const [batchPayload, setBatchPayload] = useState(
    defaultJson({
      config: { num_agents: 120, emergency_type: "fire", panic_level: 0.45, floor_plan_id: "", exits: [] },
      runs: 3,
      seed_start: 100,
      seed_step: 1,
      realtime: false,
    }),
  );

  const [unityStartPayload, setUnityStartPayload] = useState(
    defaultJson({ simulation_id: "demo-unity", num_agents: 100, emergency_type: "fire", panic_level: 0.5, floor_number: 1, exits: [] }),
  );

  const [unityCommand, setUnityCommand] = useState<"pause" | "resume" | "stop">("pause");
  const [modelJobId, setModelJobId] = useState("");

  const [modelTrainPayload, setModelTrainPayload] = useState(
    defaultJson({
      data_path: "./apps/backend/data/training/floorplan_dataset",
      epochs: 20,
      batch_size: 8,
      learning_rate: 0.001,
    }),
  );

  const prettyResults = useMemo(
    () => Object.fromEntries(Object.entries(results).map(([key, value]) => [key, typeof value === "string" ? value : JSON.stringify(value, null, 2)])),
    [results],
  );

  const batchMirrorQuery = useQuery({
    queryKey: ["operations", "batches", "mirror"],
    queryFn: ({ signal }) => listSimulationBatches({ limit: 24 }, signal),
    refetchInterval: 8_000,
  });
  const systemOverviewQuery = useQuery({
    queryKey: ["operations", "system", "overview"],
    queryFn: ({ signal }) => getSystemStatus(signal),
    refetchInterval: 15_000,
  });
  const capabilitiesOverviewQuery = useQuery({
    queryKey: ["operations", "capabilities", "overview"],
    queryFn: ({ signal }) => listCapabilities(undefined, signal),
    refetchInterval: 20_000,
  });

  const batchMirrorRows = useMemo(() => {
    const rows = batchMirrorQuery.data?.batches ?? [];
    return rows.map((row) => normalizeBatchRow(row));
  }, [batchMirrorQuery.data?.batches]);

  const batchMirrorCompletion = useMemo(() => computeBatchCompletion(batchMirrorRows), [batchMirrorRows]);
  const batchMirrorTop = useMemo(() => rankBatchesByEvacTime(batchMirrorRows, 2), [batchMirrorRows]);
  const capabilityRows = useMemo(() => {
    const value = capabilitiesOverviewQuery.data as { capabilities?: Array<Record<string, unknown>> } | undefined;
    return Array.isArray(value?.capabilities) ? value.capabilities : [];
  }, [capabilitiesOverviewQuery.data]);
  const enabledCapabilityCount = useMemo(
    () => capabilityRows.filter((capability) => capability.enabled !== false).length,
    [capabilityRows],
  );
  const sessionOverviewQuery = useQuery({
    queryKey: ["operations", "sessions", "overview"],
    queryFn: ({ signal }) => listSimulationSessions({ limit: 12 }, signal),
    refetchInterval: 8_000,
  });
  const sessionRows = useMemo(() => sessionOverviewQuery.data?.sessions ?? [], [sessionOverviewQuery.data?.sessions]);

  const run = async (key: string, action: () => Promise<unknown>) => {
    setBusyKey(key);
    try {
      const output = await action();
      setResults((prev) => ({ ...prev, [key]: output }));
    } catch (error) {
      if (isAdminError(error)) {
        setAdminDialogOpen(true);
      }
      setResults((prev) => ({ ...prev, [key]: { error: String((error as Error).message ?? error) } }));
    } finally {
      setBusyKey("");
    }
  };

  const panelOutput = (key: string) => {
    const isBusy = busyKey === key;
    const output = prettyResults[key];
    
    if (isBusy) {
      return (
        <div className="mt-4 rounded-xl bg-[#0a0a0d] border border-white/10 p-4 shadow-inner overflow-hidden relative min-h-[100px]">
          <div className="absolute inset-0 w-[200%] animate-[spin_4s_linear_infinite] opacity-20" style={{ background: 'linear-gradient(90deg, transparent, rgba(6,182,212,0.35), transparent)' }} />
          <div className="absolute inset-0 bg-[#0a0a0d]/80 backdrop-blur-sm" />
          <div className="relative z-10 flex items-center gap-3 font-mono text-xs text-cyan-300">
             <span className="animate-pulse">▶</span>
             <span className="animate-pulse">Awaiting uplink sequence...</span>
          </div>
        </div>
      );
    }
    
    if (!output) return null;
    
    return (
      <div className="mt-4 rounded-xl bg-[#0a0a0d] border border-white/10 p-4 font-mono text-[11px] text-emerald-400 shadow-inner overflow-auto max-h-[400px]">
        <div className="flex items-center gap-2 mb-3 pb-3 border-b border-white/5 opacity-70">
           <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
           <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
           <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
           <span className="ml-2 text-[10px] text-fog font-sans tracking-wider">TERMINAL ~ {key}</span>
        </div>
        <pre className="whitespace-pre-wrap break-all">{String(output)}</pre>
      </div>
    );
  };

  return (
    <div className="legacy-page legacy-operations animate-fade-rise space-y-6">
      <header className="page-header workspace-hero space-y-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{ background: "linear-gradient(135deg, #10b981 0%, #34d399 100%)", boxShadow: "0 0 20px rgba(52,211,153,0.3)" }}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
              </svg>
            </div>
            <div>
              <p className="label">Operations Console</p>
              <h1 className="text-2xl font-bold text-snow" style={{ fontFamily: "var(--font-heading)" }}>Backend Parity Control Surface</h1>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="theme-fixed-pill">{tabs.length} modules</span>
            <span className="theme-fixed-pill">{adminKey ? "Admin Key Loaded" : "Admin Key Required"}</span>
          </div>
        </div>
        <p className="text-sm leading-relaxed text-fog">
          Run system diagnostics, policy tooling, metrics pipelines, batch operations, alias routes, and Unity bridge commands from one research-operations workspace.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article className="glass-card p-4">
          <p className="label">System state</p>
          <p className="mt-3 text-2xl font-bold text-white">{String(systemOverviewQuery.data?.status ?? systemOverviewQuery.data?.system_status ?? "unknown")}</p>
          <p className="mt-1 text-xs text-fog">backend health snapshot</p>
        </article>
        <article className="glass-card p-4">
          <p className="label">Unity bridge</p>
          <p className="mt-3 text-2xl font-bold text-white">{String(systemOverviewQuery.data?.unity_enabled ?? "unknown")}</p>
          <p className="mt-1 text-xs text-fog">visualization runtime</p>
        </article>
        <article className="glass-card p-4">
          <p className="label">Capabilities</p>
          <p className="mt-3 text-2xl font-bold text-white">{enabledCapabilityCount}</p>
          <p className="mt-1 text-xs text-fog">enabled of {capabilityRows.length || 0}</p>
        </article>
        <article className="glass-card p-4">
          <p className="label">Batch mirror</p>
          <p className="mt-3 text-2xl font-bold text-white">{batchMirrorCompletion}%</p>
          <p className="mt-1 text-xs text-fog">{batchMirrorRows.length} tracked batches</p>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
        <article className="workspace-pane space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="section-title">Operator Brief</h2>
            <span className="theme-fixed-pill">{expandedTab ?? "None"}</span>
          </div>
          <p className="text-sm leading-relaxed text-fog">
            The overview cards stay passive; each accordion below is the write-capable surface. That keeps diagnostics readable while admin-gated mutations remain deliberate.
          </p>
        </article>
        <article className="workspace-pane space-y-3">
          <h2 className="section-title">Next Actions</h2>
          <div className="grid gap-2 text-sm text-slate-200">
            <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">Check `System` before running privileged mutations.</div>
            <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">Use `Batches` and `Experiments` together for parity validation.</div>
            <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">Open `Unity` only after a simulation ID is active.</div>
          </div>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <article className="workspace-pane space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="section-title">Session Runtime</h2>
            <span className="theme-fixed-pill">{sessionRows.length} v3 sessions</span>
          </div>
          <label>
            <span className="label">Active session ID</span>
            <input className="input mt-2" value={simulationId} onChange={(e) => setSimulationId(e.target.value)} placeholder="session-..." />
          </label>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary" disabled={!simulationId || busyKey === "session_analysis"} onClick={() => run("session_analysis", () => getSimulationSessionAnalysis(simulationId))}>Get Analysis</button>
            <button className="btn-secondary" disabled={!simulationId || busyKey === "session_start"} onClick={() => run("session_start", () => controlSimulationSession(simulationId, { action: "start" }))}>Start</button>
            <button className="btn-secondary" disabled={!simulationId || busyKey === "session_pause"} onClick={() => run("session_pause", () => controlSimulationSession(simulationId, { action: "pause" }))}>Pause</button>
            <button className="btn-secondary" disabled={!simulationId || busyKey === "session_resume"} onClick={() => run("session_resume", () => controlSimulationSession(simulationId, { action: "resume" }))}>Resume</button>
            <button className="btn-secondary" disabled={!simulationId || busyKey === "session_stop"} onClick={() => run("session_stop", () => controlSimulationSession(simulationId, { action: "stop" }))}>Stop</button>
            <button className="btn-primary" disabled={!simulationId || busyKey === "session_reset"} onClick={() => run("session_reset", () => controlSimulationSession(simulationId, { action: "reset" }))}>Reset</button>
          </div>
          {panelOutput("session_analysis")}
          {panelOutput("session_start")}
          {panelOutput("session_pause")}
          {panelOutput("session_resume")}
          {panelOutput("session_stop")}
          {panelOutput("session_reset")}
        </article>

        <article className="workspace-pane space-y-4">
          <h2 className="section-title">Session Snapshot</h2>
          <div className="grid gap-2 text-sm text-slate-200">
            {sessionRows.length > 0 ? sessionRows.map((session) => (
              <button
                key={String((session as { id?: string }).id ?? "")}
                type="button"
                className="rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-left transition hover:border-cyan-400/40"
                onClick={() => setSimulationId(String((session as { id?: string }).id ?? ""))}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-cyan-200">{String((session as { id?: string }).id ?? "")}</span>
                  <span>{String((session as { state?: { status?: string } }).state?.status ?? "unknown")}</span>
                </div>
              </button>
            )) : <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-3 text-slate-400">No v3 sessions indexed yet.</div>}
          </div>
        </article>
      </section>

      <div className="space-y-4">

            {/* System Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "System" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "System" ? null : "System")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               System
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "System" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "System" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">System Endpoints</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" onClick={() => run("system_info", () => getSystemInfo())} disabled={busyKey === "system_info"}>Info</button>
              <button className="btn-secondary" onClick={() => run("system_config", () => getSystemConfig())} disabled={busyKey === "system_config"}>Config</button>
              <button className="btn-secondary" onClick={() => run("system_status", () => getSystemStatus())} disabled={busyKey === "system_status"}>Status</button>
              <button className="btn-secondary" onClick={() => run("system_capabilities", () => listCapabilities())} disabled={busyKey === "system_capabilities"}>Capabilities</button>
              <button className="btn-secondary" onClick={() => run("system_capabilities_active", () => listActiveCapabilities())} disabled={busyKey === "system_capabilities_active"}>Active</button>
              <button className="btn-secondary" onClick={() => run("system_capabilities_categories", () => listCapabilityCategories())} disabled={busyKey === "system_capabilities_categories"}>Categories</button>
              <button className="btn-secondary" onClick={() => run("system_audit", () => getAuditLog(100))} disabled={busyKey === "system_audit"}>Audit</button>
            </div>
            {panelOutput("system_info")}
            {panelOutput("system_config")}
            {panelOutput("system_status")}
            {panelOutput("system_capabilities")}
            {panelOutput("system_capabilities_active")}
            {panelOutput("system_capabilities_categories")}
            {panelOutput("system_audit")}
          </section>

          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Capability Update</h3>
            <label>
              <span className="label">Capability ID</span>
              <input className="input" value={capabilityId} onChange={(e) => setCapabilityId(e.target.value)} placeholder="capability id" />
            </label>
            <label className="mt-3 flex items-center gap-2 text-sm text-mist/80">
              <input type="checkbox" checked={capabilityEnabled} onChange={(e) => setCapabilityEnabled(e.target.checked)} /> Enabled
            </label>
            <label className="mt-3">
              <span className="label">Source</span>
              <input className="input" value={capabilitySource} onChange={(e) => setCapabilitySource(e.target.value)} />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={!capabilityId || busyKey === "get_capability"} onClick={() => run("get_capability", () => getCapability(capabilityId))}>Get Capability</button>
              <button className="btn-primary" disabled={!capabilityId || busyKey === "update_capability"} onClick={() => run("update_capability", () => updateCapability(capabilityId, { enabled: capabilityEnabled, source: capabilitySource }))}>Update Capability</button>
            </div>
            {panelOutput("get_capability")}
            {panelOutput("update_capability")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

            {/* ML Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "ML" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "ML" ? null : "ML")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               ML
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "ML" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "ML" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">ML Inference Endpoints</h3>
            <textarea className="input min-h-[180px] font-mono text-xs" value={mlPayload} onChange={(e) => setMlPayload(e.target.value)} />
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={busyKey === "ml_predict_congestion"} onClick={() => run("ml_predict_congestion", () => mlPredictCongestion(safeParseJson(mlPayload) as Record<string, unknown>))}>Predict Congestion</button>
              <button className="btn-secondary" disabled={busyKey === "ml_recommend_exits"} onClick={() => run("ml_recommend_exits", () => mlRecommendExits(safeParseJson(mlPayload) as Record<string, unknown>))}>Recommend Exits</button>
              <button className="btn-primary" disabled={busyKey === "ml_recommendations"} onClick={() => run("ml_recommendations", () => mlRecommendations(safeParseJson(mlPayload) as Record<string, unknown>))}>Recommendations</button>
            </div>
            {panelOutput("ml_predict_congestion")}
            {panelOutput("ml_recommend_exits")}
            {panelOutput("ml_recommendations")}
          </section>

          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Predictions + Validation</h3>
            <label>
              <span className="label">Simulation ID (validation/report actions)</span>
              <input className="input" value={simulationId} onChange={(e) => setSimulationId(e.target.value)} placeholder="simulation id" />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={busyKey === "pred_bottlenecks"} onClick={() => run("pred_bottlenecks", () => predictBottlenecks(safeParseJson(mlPayload) as Record<string, unknown>))}>POST bottlenecks</button>
              <button className="btn-secondary" disabled={busyKey === "pred_death_zones"} onClick={() => run("pred_death_zones", () => predictDeathZones(safeParseJson(mlPayload) as Record<string, unknown>))}>POST death-zones</button>
              <button className="btn-secondary" disabled={busyKey === "pred_exit_collapse"} onClick={() => run("pred_exit_collapse", () => predictExitCollapse(safeParseJson(mlPayload) as Record<string, unknown>))}>POST exit-collapse</button>
              <button className="btn-secondary" disabled={busyKey === "pred_survival_score"} onClick={() => run("pred_survival_score", () => predictSurvivalScore(safeParseJson(mlPayload) as Record<string, unknown>))}>POST survival-score</button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={busyKey === "validation_benchmarks"} onClick={() => run("validation_benchmarks", () => getValidationBenchmarks())}>GET validation/benchmarks</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "validation_simulation"} onClick={() => run("validation_simulation", () => validateSimulation(simulationId))}>POST validation/validate</button>
            </div>
            {panelOutput("pred_bottlenecks")}
            {panelOutput("pred_death_zones")}
            {panelOutput("pred_exit_collapse")}
            {panelOutput("pred_survival_score")}
            {panelOutput("validation_benchmarks")}
            {panelOutput("validation_simulation")}
          </section>

          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Model Training Endpoints</h3>
            <textarea className="input min-h-[160px] font-mono text-xs" value={modelTrainPayload} onChange={(e) => setModelTrainPayload(e.target.value)} />
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-primary" disabled={busyKey === "models_train_floorplan"} onClick={() => run("models_train_floorplan", () => trainFloorPlanModel(safeParseJson(modelTrainPayload) as Record<string, unknown>))}>POST models/floorplan/train</button>
            </div>
            <label className="mt-3 block">
              <span className="label">Training Job ID</span>
              <input className="input" value={modelJobId} onChange={(e) => setModelJobId(e.target.value)} placeholder="job id" />
            </label>
            <button className="btn-secondary mt-2" disabled={!modelJobId || busyKey === "models_train_status"} onClick={() => run("models_train_status", () => getFloorPlanTrainingStatus(modelJobId))}>GET models/floorplan/train/{'{job_id}'}</button>
            {panelOutput("models_train_floorplan")}
            {panelOutput("models_train_status")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

            {/* Optimization Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "Optimization" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "Optimization" ? null : "Optimization")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               Optimization
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "Optimization" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "Optimization" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Optimization Engine</h3>
            <textarea className="input min-h-[180px] font-mono text-xs" value={optimizePayload} onChange={(e) => setOptimizePayload(e.target.value)} />
            <label className="mt-3 block">
              <span className="label">Simulation ID (for compare-policies)</span>
              <input className="input" value={simulationId} onChange={(e) => setSimulationId(e.target.value)} placeholder="simulation id" />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={busyKey === "optimization_exits"} onClick={() => run("optimization_exits", () => optimizeExits(safeParseJson(optimizePayload) as Record<string, unknown>))}>Optimize Exits</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "optimization_compare"} onClick={() => run("optimization_compare", () => comparePolicies(simulationId))}>Compare Policies</button>
            </div>
            {panelOutput("optimization_exits")}
            {panelOutput("optimization_compare")}
          </section>

          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Predictions Optimize</h3>
            <textarea className="input min-h-[180px] font-mono text-xs" value={predictOptimizePayload} onChange={(e) => setPredictOptimizePayload(e.target.value)} />
            <button className="btn-primary mt-3" disabled={busyKey === "predict_optimize"} onClick={() => run("predict_optimize", () => predictOptimize(safeParseJson(predictOptimizePayload) as Record<string, unknown>))}>Run /predictions/optimize</button>
            {panelOutput("predict_optimize")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

            {/* Metrics Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "Metrics" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "Metrics" ? null : "Metrics")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               Metrics
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "Metrics" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "Metrics" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Metrics Engine</h3>
            <textarea className="input min-h-[160px] font-mono text-xs" value={metricsFramePayload} onChange={(e) => setMetricsFramePayload(e.target.value)} />
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={busyKey === "metrics_add"} onClick={() => run("metrics_add", () => addMetricsFrame(safeParseJson(metricsFramePayload) as Record<string, unknown>))}>Add Frame</button>
              <button className="btn-secondary" disabled={busyKey === "metrics_calculate"} onClick={() => run("metrics_calculate", () => calculateMetrics())}>Calculate</button>
              <button className="btn-danger" disabled={busyKey === "metrics_reset"} onClick={() => run("metrics_reset", () => resetMetrics())}>Reset</button>
            </div>
            {panelOutput("metrics_add")}
            {panelOutput("metrics_calculate")}
            {panelOutput("metrics_reset")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

            {/* Results Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "Results" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "Results" ? null : "Results")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               Results
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "Results" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "Results" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Results API</h3>
            <label>
              <span className="label">Simulation ID</span>
              <input className="input" value={simulationId} onChange={(e) => setSimulationId(e.target.value)} placeholder="simulation id" />
            </label>
            <textarea className="input mt-3 min-h-[160px] font-mono text-xs" value={resultFramePayload} onChange={(e) => setResultFramePayload(e.target.value)} />
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={!simulationId || busyKey === "results_frame_post"} onClick={() => run("results_frame_post", () => saveResultFrame(simulationId, safeParseJson(resultFramePayload) as Record<string, unknown>))}>POST frame</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "results_frames_get"} onClick={() => run("results_frames_get", () => getResultFrames(simulationId))}>GET frames</button>
              <button className="btn-primary" disabled={!simulationId || busyKey === "results_summary_get"} onClick={() => run("results_summary_get", () => getResultSummary(simulationId))}>GET summary</button>
            </div>
            {panelOutput("results_frame_post")}
            {panelOutput("results_frames_get")}
            {panelOutput("results_summary_get")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

            {/* Simulation Ops Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "Simulation Ops" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "Simulation Ops" ? null : "Simulation Ops")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               Simulation Ops
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "Simulation Ops" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "Simulation Ops" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Simulation Advanced Endpoints</h3>
            <label>
              <span className="label">Simulation ID</span>
              <input className="input" value={simulationId} onChange={(e) => setSimulationId(e.target.value)} placeholder="simulation id" />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={!simulationId || busyKey === "sim_agents"} onClick={() => run("sim_agents", () => getSimulationAgents(simulationId))}>GET agents</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "sim_hazards"} onClick={() => run("sim_hazards", () => getSimulationHazards(simulationId))}>GET hazards</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "sim_survival"} onClick={() => run("sim_survival", () => getSimulationSurvivalScore(simulationId, { disasterType }))}>GET survival-score</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "sim_export_frames"} onClick={() => run("sim_export_frames", () => exportSimulationFramesCsv(simulationId, { limit: 500, stride: 2 }))}>Export frames CSV</button>
            </div>
            <label className="mt-3 block">
              <span className="label">Disaster Type</span>
              <input className="input" value={disasterType} onChange={(e) => setDisasterType(e.target.value)} />
            </label>
            {panelOutput("sim_agents")}
            {panelOutput("sim_hazards")}
            {panelOutput("sim_survival")}
            {panelOutput("sim_export_frames")}
          </section>

          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Simulation Update Endpoints</h3>
            <p className="text-xs text-mist/70">Payloads are JSON arrays/objects matching backend schemas.</p>

            <label className="mt-3 block">
              <span className="label">Hazards Payload</span>
              <textarea className="input min-h-[100px] font-mono text-xs" value={hazardUpdatePayload} onChange={(e) => setHazardUpdatePayload(e.target.value)} />
            </label>
            <button className="btn-secondary mt-2" disabled={!simulationId || busyKey === "sim_hazard_update"} onClick={() => run("sim_hazard_update", () => updateSimulationHazards(simulationId, safeParseJson(hazardUpdatePayload) as Array<Record<string, unknown>>))}>POST hazards/update</button>

            <label className="mt-3 block">
              <span className="label">Exits Payload</span>
              <textarea className="input min-h-[100px] font-mono text-xs" value={exitUpdatePayload} onChange={(e) => setExitUpdatePayload(e.target.value)} />
            </label>
            <button className="btn-secondary mt-2" disabled={!simulationId || busyKey === "sim_exit_update"} onClick={() => run("sim_exit_update", () => updateSimulationExits(simulationId, safeParseJson(exitUpdatePayload) as Array<Record<string, unknown>>))}>POST exits/update</button>

            <label className="mt-3 block">
              <span className="label">Boundary Payload</span>
              <textarea className="input min-h-[100px] font-mono text-xs" value={boundaryUpdatePayload} onChange={(e) => setBoundaryUpdatePayload(e.target.value)} />
            </label>
            <button className="btn-secondary mt-2" disabled={!simulationId || busyKey === "sim_boundary_update"} onClick={() => run("sim_boundary_update", () => updateSimulationBoundary(simulationId, safeParseJson(boundaryUpdatePayload) as Record<string, unknown>))}>POST boundary/update</button>

            <label className="mt-3 block">
              <span className="label">Metadata Payload</span>
              <textarea className="input min-h-[90px] font-mono text-xs" value={metadataUpdatePayload} onChange={(e) => setMetadataUpdatePayload(e.target.value)} />
            </label>
            <button className="btn-primary mt-2" disabled={!simulationId || busyKey === "sim_metadata_update"} onClick={() => run("sim_metadata_update", () => updateSimulationMetadata(simulationId, safeParseJson(metadataUpdatePayload) as { tags?: string[]; notes?: string; label?: string; priority?: number }))}>PUT metadata</button>

            {panelOutput("sim_hazard_update")}
            {panelOutput("sim_exit_update")}
            {panelOutput("sim_boundary_update")}
            {panelOutput("sim_metadata_update")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

            {/* Batches Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "Batches" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "Batches" ? null : "Batches")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               Batches
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "Batches" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "Batches" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Batch Simulation APIs</h3>
            <textarea className="input min-h-[180px] font-mono text-xs" value={batchPayload} onChange={(e) => setBatchPayload(e.target.value)} />
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-primary" disabled={busyKey === "start_batch"} onClick={() => run("start_batch", () => startBatchSimulation(safeParseJson(batchPayload) as Record<string, unknown>))}>POST start-batch</button>
              <button className="btn-secondary" disabled={busyKey === "list_batches"} onClick={() => run("list_batches", () => listSimulationBatches({ limit: 20 }))}>GET simulations/batches</button>
            </div>

            <label className="mt-3 block">
              <span className="label">Batch ID</span>
              <input className="input" value={batchId} onChange={(e) => setBatchId(e.target.value)} placeholder="batch id" />
            </label>
            <div className="mt-2 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={!batchId || busyKey === "get_batch"} onClick={() => run("get_batch", () => getSimulationBatch(batchId))}>GET batch</button>
              <button className="btn-secondary" disabled={!batchId || busyKey === "export_batch"} onClick={() => run("export_batch", () => exportSimulationBatch(batchId))}>Export batch CSV</button>
            </div>

            <label className="mt-3 block">
              <span className="label">Alias subpath (for /api/v2/batches/{'{subpath}'})</span>
              <input className="input" value={aliasSubpath} onChange={(e) => setAliasSubpath(e.target.value)} placeholder="batch-id or batch-id/export" />
            </label>
            <div className="mt-2 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={busyKey === "alias_batches_root"} onClick={() => run("alias_batches_root", () => listBatchesAlias())}>GET /batches alias root</button>
              <button className="btn-secondary" disabled={!aliasSubpath || busyKey === "alias_batches_sub"} onClick={() => run("alias_batches_sub", () => getBatchesAliasSubpath(aliasSubpath))}>GET /batches alias subpath</button>
            </div>

            <div className="workspace-surface rounded-2xl p-4">
              <div className="flex items-center justify-between">
                <h4 className="section-title">Live Batch Aggregation Mirror</h4>
                <span className="theme-fixed-pill">{batchMirrorCompletion}% complete</span>
              </div>
              <p className="workspace-muted mt-2">Uses the same normalization/ranking utility as `/experiments` to keep parity across both pages.</p>
              {batchMirrorQuery.error && <p className="mt-2 text-xs text-rose-300">Batch mirror failed to refresh.</p>}
              <div className="mt-3 grid gap-2">
                {(batchMirrorRows.length ? batchMirrorRows.slice(0, 4) : [{ id: "no-batches", status: "standby", runs: 0, completedRuns: 0 }]).map((row) => (
                  <article key={row.id} className="rounded-xl border border-white/10 bg-black/20 p-3">
                    <p className="text-sm font-semibold text-snow">{row.id}</p>
                    <p className="text-xs text-fog">{row.status} · {row.completedRuns}/{row.runs}</p>
                  </article>
                ))}
              </div>
              {batchMirrorTop.length > 0 && (
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  {batchMirrorTop.map((row, index) => (
                    <div key={`${row.id}-${index}`} className="rounded-xl border border-emerald-300/20 bg-emerald-500/10 p-3">
                      <p className="text-[11px] uppercase tracking-wider text-emerald-200">{index === 0 ? "Top Batch" : "Runner-Up"}</p>
                      <p className="text-sm font-semibold text-snow">{row.winningPolicy ?? "Policy pending"}</p>
                      <p className="text-xs text-fog">{typeof row.bestEvacTime === "number" ? `Best ${Math.round(row.bestEvacTime)}s` : "No timing data"}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {panelOutput("start_batch")}
            {panelOutput("list_batches")}
            {panelOutput("get_batch")}
            {panelOutput("export_batch")}
            {panelOutput("alias_batches_root")}
            {panelOutput("alias_batches_sub")}
          </section>

          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Scenario Exit Recommendations</h3>
            <label>
              <span className="label">Building Type</span>
              <input className="input" value={buildingType} onChange={(e) => setBuildingType(e.target.value)} placeholder="office|school|mall" />
            </label>
            <button className="btn-secondary mt-3" disabled={!buildingType || busyKey === "scenario_recommended_exits"} onClick={() => run("scenario_recommended_exits", () => getScenarioRecommendedExits(buildingType, { buildingWidth: 100, buildingHeight: 100 }))}>GET scenarios/exits/{'{building_type}'}</button>
            {panelOutput("scenario_recommended_exits")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

            {/* Unity Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "Unity" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "Unity" ? null : "Unity")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               Unity
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "Unity" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "Unity" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Unity Start / Control</h3>
            <textarea className="input min-h-[160px] font-mono text-xs" value={unityStartPayload} onChange={(e) => setUnityStartPayload(e.target.value)} />
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-primary" disabled={busyKey === "unity_start"} onClick={() => run("unity_start", () => unityStart(safeParseJson(unityStartPayload) as Record<string, unknown>))}>POST unity/start</button>
            </div>

            <label className="mt-3 block">
              <span className="label">Simulation ID</span>
              <input className="input" value={simulationId} onChange={(e) => setSimulationId(e.target.value)} placeholder="simulation id" />
            </label>
            <label className="mt-3 block">
              <span className="label">Command</span>
              <select className="input" value={unityCommand} onChange={(e) => setUnityCommand(e.target.value as "pause" | "resume" | "stop") }>
                <option value="pause">pause</option>
                <option value="resume">resume</option>
                <option value="stop">stop</option>
              </select>
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={!simulationId || busyKey === "unity_control"} onClick={() => run("unity_control", () => unityControl({ simulation_id: simulationId, command: unityCommand }))}>POST unity/control</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "unity_status"} onClick={() => run("unity_status", () => getUnityStatus(simulationId))}>GET unity/status</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "unity_scene"} onClick={() => run("unity_scene", () => getUnityScene(simulationId))}>GET unity/scene</button>
            </div>
            {panelOutput("unity_start")}
            {panelOutput("unity_control")}
            {panelOutput("unity_status")}
            {panelOutput("unity_scene")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

            {/* Aliases Accordion */}
      <div className="glass-card overflow-hidden transition-all duration-300 shadow-lg" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
         <button 
           type="button"
           className="w-full flex items-center justify-between p-5 text-left transition-colors"
           style={{ background: expandedTab === "Aliases" ? "rgba(255,255,255,0.03)" : "transparent" }}
           onClick={() => setExpandedTab(expandedTab === "Aliases" ? null : "Aliases")}
         >
            <h2 className="text-lg font-bold text-snow flex items-center gap-4" style={{ fontFamily: "var(--font-heading)" }}>
               <span className="text-cyan-300 text-sm font-mono tracking-widest">OPS</span>
               Aliases
            </h2>
            <svg className={`w-5 h-5 text-fog transition-transform duration-300 ${expandedTab === "Aliases" ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
         </button>
         
         <div className={`transition-all duration-500 overflow-hidden ${expandedTab === "Aliases" ? "opacity-100" : "max-h-0 opacity-0"}`}>
            <div className="p-5 border-t border-white/5 space-y-6">
               <div className="surface-grid">
                  
          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Floor Plan Alias Endpoints</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={busyKey === "floor_alias_root"} onClick={() => run("floor_alias_root", () => getFloorPlansAliasRoot())}>GET /api/v2/floor-plans</button>
            </div>
            <label className="mt-3 block">
              <span className="label">Subpath</span>
              <input className="input" value={floorAliasSubpath} onChange={(e) => setFloorAliasSubpath(e.target.value)} placeholder="{floor_plan_id} or {floor_plan_id}/pipeline" />
            </label>
            <button className="btn-secondary mt-2" disabled={!floorAliasSubpath || busyKey === "floor_alias_sub"} onClick={() => run("floor_alias_sub", () => getFloorPlansAliasSubpath(floorAliasSubpath))}>GET /api/v2/floor-plans/{'{subpath}'}</button>
            {panelOutput("floor_alias_root")}
            {panelOutput("floor_alias_sub")}
          </section>

          <section className="glass-card p-5 space-y-4">
            <h3 className="section-title">Replay Extended Endpoints</h3>
            <label>
              <span className="label">Simulation ID</span>
              <input className="input" value={simulationId} onChange={(e) => setSimulationId(e.target.value)} placeholder="simulation id" />
            </label>
            <label className="mt-3 block">
              <span className="label">Agent ID</span>
              <input className="input" type="number" value={agentId} onChange={(e) => setAgentId(Number(e.target.value || 1))} />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={!simulationId || busyKey === "replay_timeline"} onClick={() => run("replay_timeline", () => getReplayTimeline(simulationId))}>GET replay/timeline</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "replay_density"} onClick={() => run("replay_density", () => getReplayDensityEvolution(simulationId))}>GET replay/density-evolution</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "replay_death_zones"} onClick={() => run("replay_death_zones", () => getReplayDeathZones(simulationId))}>GET replay/death-zones</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "replay_agent"} onClick={() => run("replay_agent", () => getReplayAgentTimeline(simulationId, agentId))}>GET replay/agent</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "replay_report"} onClick={() => run("replay_report", () => getReplayReport(simulationId))}>GET replay/report</button>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <button className="btn-secondary" disabled={!simulationId || busyKey === "reports_heatmap"} onClick={() => run("reports_heatmap", () => getHeatmapData(simulationId))}>GET reports/heatmap</button>
              <button className="btn-secondary" disabled={!simulationId || busyKey === "reports_pdf"} onClick={() => run("reports_pdf", async () => {
                const blob = await downloadPdfReport(simulationId);
                return { type: blob.type, size: blob.size };
              })}>GET reports/pdf</button>
            </div>
            {panelOutput("replay_timeline")}
            {panelOutput("replay_density")}
            {panelOutput("replay_death_zones")}
            {panelOutput("replay_agent")}
            {panelOutput("replay_report")}
            {panelOutput("reports_heatmap")}
            {panelOutput("reports_pdf")}
          </section>
        
               </div>
            </div>
         </div>
      </div>

      </div>

      <AdminKeyDialog open={adminDialogOpen} onClose={() => setAdminDialogOpen(false)} />
    </div>
  );
}
