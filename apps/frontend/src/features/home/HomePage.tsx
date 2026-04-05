import { useEffect, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { buildDashboardSnapshot } from "@/lib/api/adapters";
import { listSimulations } from "@/lib/api/simulation";
import { getSystemInfo, getSystemStatus } from "@/lib/api/system";
import { useSessionStore } from "@/lib/state/sessionStore";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";
import { useSpringCounter } from "@/lib/hooks/useSpringCounter";

interface Dot {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

const moduleCards = [
  {
    title: "Building Designer",
    route: "/designer",
    description: "Upload floor plans, inspect geometry quality, and author exits with simulation-ready diagnostics.",
    accent: "from-cyan-400/25 to-cyan-500/5",
  },
  {
    title: "Simulation Hub",
    route: "/simulation",
    description: "Launch, pause, resume, and inspect live runs with split 2D and 3D visualization.",
    accent: "from-emerald-400/20 to-emerald-500/5",
  },
  {
    title: "Analytics Lab",
    route: "/analytics",
    description: "Review evacuation curves, density, policy comparisons, and publication-oriented statistics.",
    accent: "from-sky-400/20 to-sky-500/5",
  },
  {
    title: "Experiments",
    route: "/experiments",
    description: "Run multi-seed research batches, inspect progress, and compare best-performing policies.",
    accent: "from-violet-400/20 to-violet-500/5",
  },
] as const;

function useAgentField(agentCount: number, paused: boolean) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx || paused) {
      return;
    }

    const dots: Dot[] = Array.from({ length: Math.max(24, Math.min(240, agentCount || 120)) }, () => ({
      x: Math.random(),
      y: Math.random(),
      vx: (Math.random() - 0.5) * 0.0022,
      vy: (Math.random() - 0.5) * 0.0022,
    }));

    let rafId = 0;

    const render = () => {
      const { width, height } = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);

      for (const dot of dots) {
        dot.x += dot.vx;
        dot.y += dot.vy;

        if (dot.x < 0 || dot.x > 1) dot.vx *= -1;
        if (dot.y < 0 || dot.y > 1) dot.vy *= -1;

        const px = dot.x * width;
        const py = dot.y * height;

        ctx.beginPath();
        ctx.arc(px, py, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(0,229,200,0.9)";
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(px - dot.vx * 9000, py - dot.vy * 9000);
        ctx.strokeStyle = "rgba(56,184,245,0.16)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      rafId = window.requestAnimationFrame(render);
    };

    rafId = window.requestAnimationFrame(render);
    return () => window.cancelAnimationFrame(rafId);
  }, [agentCount, paused]);

  return canvasRef;
}

export function HomePage() {
  const simulationsQuery = useQuery({
    queryKey: ["dashboard", "simulations"],
    queryFn: ({ signal }) => listSimulations(signal),
    refetchInterval: 10_000,
  });
  const systemStatusQuery = useQuery({
    queryKey: ["dashboard", "system-status"],
    queryFn: ({ signal }) => getSystemStatus(signal),
    refetchInterval: 15_000,
  });
  const systemInfoQuery = useQuery({
    queryKey: ["dashboard", "system-info"],
    queryFn: ({ signal }) => getSystemInfo(signal),
    staleTime: 60_000,
  });

  const activeFloorPlanId = useWorkspaceStore((state) => state.activeFloorPlanId);
  const selectedSimulationId = useSimulationStore((state) => state.selectedSimulationId);
  const frames = useSimulationStore((state) => state.frames);
  const socketStatus = useSimulationStore((state) => state.socketStatus);
  const reducedMotion = useSessionStore((state) => state.reducedMotion);

  const snapshot = useMemo(
    () =>
      buildDashboardSnapshot({
        selectedSimulationId,
        socketStatus,
        activeFloorPlanId,
        simulations: simulationsQuery.data?.simulations ?? [],
        liveFrame: frames[frames.length - 1] ?? null,
        systemStatus: systemStatusQuery.data ?? null,
        systemInfo: systemInfoQuery.data ?? null,
      }),
    [
      activeFloorPlanId,
      frames,
      selectedSimulationId,
      simulationsQuery.data?.simulations,
      socketStatus,
      systemInfoQuery.data,
      systemStatusQuery.data,
    ],
  );

  const liveFrame = snapshot.liveFrame;
  const flowRate = useSpringCounter(liveFrame?.flowRate ?? 0, 550);
  const evacuated = useSpringCounter(liveFrame?.evacuated ?? 0, 550);
  const activeAgents = useSpringCounter(liveFrame?.agentCount ?? 0, 550);
  const canvasRef = useAgentField(Math.max(80, liveFrame?.agentCount ?? 120), reducedMotion);

  const serviceVersion = String(snapshot.systemInfo?.service_version ?? "v2");
  const systemMode = String(snapshot.systemStatus?.database ?? "demo");
  const unityEnabled = String(snapshot.systemStatus?.unity_enabled ?? "unknown");

  return (
    <div className="command-center-page">
      <motion.header
        className="cc-header p-6"
        initial={{ opacity: 0, y: reducedMotion ? 0 : 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: reducedMotion ? 0.12 : 0.34 }}
      >
        <div className="max-w-3xl">
          <p className="cc-kicker">PeopleFlow Command Center</p>
          <h1>Research-Grade Evacuation Intelligence Workspace</h1>
          <p className="mt-3 max-w-2xl">
            Coordinate floor-plan preparation, real-time simulation control, analytics, and experiments from one production dashboard designed around research reproducibility.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link to="/designer" className="btn-primary">Upload Floor Plan</Link>
            <Link to="/simulation" className="btn-secondary">Open Simulation Hub</Link>
            <Link to="/analytics" className="btn-secondary">Review Analytics</Link>
          </div>
        </div>

        <div className="grid min-w-[280px] gap-3 sm:grid-cols-2">
          <div className="rounded-[18px] border border-white/10 bg-white/5 p-4">
            <p className="label">Backend</p>
            <p className="mt-3 text-2xl font-bold text-white">{serviceVersion}</p>
            <p className="mt-1 text-xs text-slate-400">Service version</p>
          </div>
          <div className="rounded-[18px] border border-white/10 bg-white/5 p-4">
            <p className="label">Database</p>
            <p className="mt-3 text-2xl font-bold text-white">{systemMode}</p>
            <p className="mt-1 text-xs text-slate-400">Environment health</p>
          </div>
          <div className="rounded-[18px] border border-white/10 bg-white/5 p-4">
            <p className="label">Unity</p>
            <p className="mt-3 text-2xl font-bold text-white">{unityEnabled}</p>
            <p className="mt-1 text-xs text-slate-400">Visualization bridge</p>
          </div>
          <div className="rounded-[18px] border border-white/10 bg-white/5 p-4">
            <p className="label">Live Runs</p>
            <p className="mt-3 text-2xl font-bold text-white">{snapshot.activeSimulationCount}</p>
            <p className="mt-1 text-xs text-slate-400">Active simulations</p>
          </div>
        </div>
      </motion.header>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_1.6fr_1fr]">
        <aside className="cc-rail">
          <div className="flex items-center justify-between">
            <h3 className="section-title">Health Strip</h3>
            <span className="theme-fixed-pill">{snapshot.socketStatus}</span>
          </div>
          <div className="mt-4 grid gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="label">Selected plan</p>
              <p className="mt-3 break-all font-mono text-sm text-slate-100">{snapshot.activeFloorPlanId || "No active plan"}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="label">Selected simulation</p>
              <p className="mt-3 break-all font-mono text-sm text-slate-100">{snapshot.selectedSimulationId || "No live selection"}</p>
            </div>
          </div>

          <div className="mt-5">
            <h3 className="section-title">Recent Runs</h3>
            <ul className="mt-3 space-y-2">
              {snapshot.recentSimulations.length === 0 && (
                <li className="rounded-2xl border border-dashed border-white/10 bg-white/5 p-4 text-sm text-slate-400">
                  No simulation history yet.
                </li>
              )}
              {snapshot.recentSimulations.map((simulation) => (
                <li key={simulation.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-white">{simulation.name || simulation.id}</p>
                      <p className="text-xs text-slate-400">{simulation.emergency_type || "fire"} · {simulation.status || "unknown"}</p>
                    </div>
                    <span className="font-mono text-xs text-cyan-200">{simulation.num_agents ?? "--"}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <main className="cc-stage p-4">
          <div className="cc-stage-top">
            <div>
              <p className="label">Live telemetry</p>
              <h3 className="mt-3 text-2xl font-bold text-white">Primary simulation field</h3>
            </div>
            <span className="cc-live-pill">{snapshot.socketStatus.toUpperCase()}</span>
          </div>

          <div className="cc-floorplan-wrap mt-4">
            <canvas ref={canvasRef} className="cc-agent-overlay" aria-label="Live simulation background" />
            <div className="absolute inset-0 grid place-items-center">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <div className="rounded-2xl border border-white/10 bg-[rgba(6,10,20,0.82)] px-4 py-3 text-center">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Agents</p>
                  <p className="mt-2 font-mono text-2xl text-cyan-200">{Math.round(activeAgents)}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-[rgba(6,10,20,0.82)] px-4 py-3 text-center">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Evacuated</p>
                  <p className="mt-2 font-mono text-2xl text-emerald-300">{Math.round(evacuated)}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-[rgba(6,10,20,0.82)] px-4 py-3 text-center">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Flow</p>
                  <p className="mt-2 font-mono text-2xl text-amber-300">{Math.round(flowRate)}</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-[rgba(6,10,20,0.82)] px-4 py-3 text-center">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Peak density</p>
                  <p className="mt-2 font-mono text-2xl text-violet-300">{(liveFrame?.peakDensity ?? 0).toFixed(2)}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {moduleCards.map((card) => (
              <Link
                key={card.route}
                to={card.route}
                className={`rounded-[20px] border border-white/10 bg-gradient-to-br ${card.accent} p-5 transition-all duration-200 hover:-translate-y-1 hover:border-white/20`}
              >
                <p className="label">{card.route}</p>
                <h3 className="mt-3 text-xl font-semibold text-white">{card.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{card.description}</p>
              </Link>
            ))}
          </div>
        </main>

        <aside className="cc-kpis">
          <article className="cc-kpi-card">
            <p>Total runs</p>
            <h4>{snapshot.totalSimulationCount}</h4>
          </article>
          <article className="cc-kpi-card">
            <p>Selected plan</p>
            <h4>{snapshot.activeFloorPlanId ? "Ready" : "Needed"}</h4>
          </article>
          <article className="cc-kpi-card">
            <p>Live timestamp</p>
            <h4>{liveFrame ? `${Math.round(liveFrame.timestamp)}s` : "--"}</h4>
          </article>
          <article className="cc-kpi-card">
            <p>Reduced motion</p>
            <h4>{reducedMotion ? "On" : "Off"}</h4>
          </article>
        </aside>
      </section>
    </div>
  );
}
