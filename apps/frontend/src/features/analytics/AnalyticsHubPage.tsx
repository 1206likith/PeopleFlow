import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  buildAnalyticsPanelModel,
  normalizeSimulationAnalysisSnapshot,
  normalizeSimulationReplaySlice,
  normalizeSimulationSession,
} from "@/lib/api/adapters";
import {
  getSimulationSessionAnalysis,
  getSimulationSessionReplay,
  listSimulationSessions,
} from "@/lib/api/simulationSessions";
import { ErrorPanel } from "@/components/common/ErrorPanel";
import { EmptyState } from "@/components/common/EmptyState";
import { useSessionStore } from "@/lib/state/sessionStore";
import { useSimulationStore } from "@/lib/state/simulationStore";

const tabs = ["Evacuation Curve", "Flow Rate", "Heatmap", "Policy Compare", "Statistics"] as const;
type AnalyticsTab = (typeof tabs)[number];

function toRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function formatMaybe(value: unknown, digits = 0): string {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "--";
}

export function AnalyticsHubPage() {
  const [tab, setTab] = useState<AnalyticsTab>("Evacuation Curve");
  const activeSessionId = useSimulationStore((state) => state.activeSessionId);
  const setSelectedSimulationId = useSimulationStore((state) => state.setSelectedSimulationId);
  const reducedMotion = useSessionStore((state) => state.reducedMotion);

  const sessionsQuery = useQuery({
    queryKey: ["analytics-v3", "sessions"],
    queryFn: ({ signal }) => listSimulationSessions({ limit: 40 }, signal),
    refetchInterval: 10_000,
  });

  const analysisQuery = useQuery({
    queryKey: ["analytics-v3", "analysis", activeSessionId],
    queryFn: ({ signal }) => getSimulationSessionAnalysis(activeSessionId, signal),
    enabled: Boolean(activeSessionId),
  });

  const replayQuery = useQuery({
    queryKey: ["analytics-v3", "replay", activeSessionId],
    queryFn: ({ signal }) => getSimulationSessionReplay(activeSessionId, { limit: 220 }, signal),
    enabled: Boolean(activeSessionId),
  });

  useEffect(() => {
    if (!activeSessionId && sessionsQuery.data?.sessions?.length) {
      const latest = normalizeSimulationSession(sessionsQuery.data.sessions[0]);
      setSelectedSimulationId(latest.id);
    }
  }, [activeSessionId, setSelectedSimulationId, sessionsQuery.data?.sessions]);

  const analysis = analysisQuery.data ? normalizeSimulationAnalysisSnapshot(analysisQuery.data) : null;
  const replay = replayQuery.data ? normalizeSimulationReplaySlice(replayQuery.data) : null;
  const partialFailures = [
    analysisQuery.error ? "analysis" : null,
    replayQuery.error ? "replay" : null,
  ].filter((value): value is string => Boolean(value));

  const panelModel = useMemo(
    () =>
      buildAnalyticsPanelModel({
        summary: analysis
          ? {
              simulation_id: analysis.session_id,
              total_agents: analysis.total_agents,
              evacuated: analysis.evacuated,
              total_time: analysis.simulation_time,
              frames_count: analysis.frame_count,
              final_stats: analysis.final_summary,
            }
          : undefined,
        frames: replay?.frames,
        timeline: analysis?.timeline,
        metrics: analysis?.final_summary?.metrics as Record<string, unknown> | undefined,
        exitUsage: analysis?.exit_usage,
        partialFailures,
      }),
    [analysis, partialFailures, replay?.frames],
  );

  const finalStats = toRecord(analysis?.final_summary?.metrics);
  const hasChartData = panelModel.chartData.length > 0;
  const sessionRows = sessionsQuery.data?.sessions?.map((row) => normalizeSimulationSession(row)) ?? [];

  return (
    <div className="analytics-lab-page">
      <header className="analytics-lab-header p-6">
        <div className="max-w-3xl">
          <p className="analytics-kicker">Analytics Lab</p>
          <h1>Session-Linked Results Workspace</h1>
          <p className="mt-3">
            Analytics now read directly from the canonical simulation session contract, so replay, live metrics, event markers, and summary outputs stay aligned with the session you launched in the studio.
          </p>
          {partialFailures.length > 0 && (
            <p className="mt-4 rounded-full border border-amber-400/20 bg-amber-400/10 px-4 py-2 text-xs font-medium text-amber-100">
              Partial session degradation: {partialFailures.join(", ")}. Available analytics are still shown.
            </p>
          )}
        </div>

        <div className="analytics-controls">
          <select className="input" value={activeSessionId} onChange={(event) => setSelectedSimulationId(event.target.value)}>
            <option value="">Select session...</option>
            {sessionRows.map((session) => (
              <option key={session.id} value={session.id}>{session.id} - {session.state.status}</option>
            ))}
          </select>
        </div>
      </header>

      <section className="analytics-kpi-grid">
        <article><p>Total Agents</p><h3>{panelModel.totalAgents || "--"}</h3></article>
        <article><p>Evacuated</p><h3>{panelModel.evacuated || "--"}</h3></article>
        <article><p>Final Evac Time</p><h3>{panelModel.evacTime}</h3></article>
        <article><p>Peak Density</p><h3>{panelModel.peakDensity}</h3></article>
        <article><p>Throughput</p><h3>{panelModel.throughput}</h3></article>
        <article><p>Policy</p><h3>{String(analysis?.final_summary?.routing_policy ?? panelModel.policyWinner ?? "--")}</h3></article>
      </section>

      <section className="analytics-tabbar">
        {tabs.map((entry) => (
          <button key={entry} type="button" onClick={() => setTab(entry)} className={tab === entry ? "active" : ""}>
            {entry}
          </button>
        ))}
      </section>

      {!activeSessionId && (
        <section className="analytics-panel-shell">
          <EmptyState title="Select session" message="Choose a simulation session to inspect replay and analysis." icon="chart" />
        </section>
      )}

      {activeSessionId && (
        <section className="analytics-panel-shell">
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, x: reducedMotion ? 0 : 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: reducedMotion ? 0 : -14 }}
              transition={{ duration: reducedMotion ? 0.12 : 0.28, ease: [0.16, 1, 0.3, 1] }}
              className="analytics-panel"
            >
              {(analysisQuery.error || replayQuery.error) && !hasChartData && (
                <ErrorPanel error={analysisQuery.error ?? replayQuery.error ?? "Unable to load analytics data."} />
              )}

              {!analysisQuery.error && !replayQuery.error && !hasChartData && tab !== "Policy Compare" && (
                <p>No session analytics available for this run yet.</p>
              )}

              {tab === "Evacuation Curve" && hasChartData && (
                <ResponsiveContainer width="100%" height={360}>
                  <LineChart data={panelModel.chartData}>
                    <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="t" stroke="rgba(255,255,255,0.45)" />
                    <YAxis stroke="rgba(255,255,255,0.45)" />
                    <Tooltip />
                    <Line type="monotone" dataKey="evacuated" stroke="#00e5c8" strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              )}

              {tab === "Flow Rate" && hasChartData && (
                <ResponsiveContainer width="100%" height={360}>
                  <AreaChart data={panelModel.chartData}>
                    <defs>
                      <linearGradient id="flowGradientAnalyticsV3" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#38b8f5" stopOpacity={0.58} />
                        <stop offset="100%" stopColor="#38b8f5" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="t" stroke="rgba(255,255,255,0.45)" />
                    <YAxis stroke="rgba(255,255,255,0.45)" />
                    <Tooltip />
                    <Area type="monotone" dataKey="flow" stroke="#38b8f5" fill="url(#flowGradientAnalyticsV3)" strokeWidth={2.5} />
                  </AreaChart>
                </ResponsiveContainer>
              )}

              {tab === "Heatmap" && (
                panelModel.densityGrid.length > 0 ? (
                  <div className="analytics-heatmap-grid" style={{ gridTemplateColumns: `repeat(${panelModel.densityGrid[0].length}, minmax(0, 1fr))` }}>
                    {panelModel.densityGrid.flatMap((row, rowIndex) => row.map((value, colIndex) => {
                      const density = Math.max(0, Math.min(1, Number(value) || 0));
                      const hue = 210 - density * 155;
                      const sat = 82;
                      const light = 60 - density * 18;
                      return <span key={`${rowIndex}-${colIndex}`} style={{ background: `hsl(${hue} ${sat}% ${light}%)` }} />;
                    }))}
                  </div>
                ) : <p>Heatmap frames are not available for this session.</p>
              )}

              {tab === "Policy Compare" && (
                panelModel.policyData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={360}>
                    <BarChart data={panelModel.policyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                      <XAxis dataKey="policy" stroke="rgba(255,255,255,0.45)" />
                      <YAxis stroke="rgba(255,255,255,0.45)" />
                      <Tooltip />
                      <Bar dataKey="score" radius={[8, 8, 0, 0]}>
                        {panelModel.policyData.map((entry, index) => (
                          <Cell key={entry.policy} fill={["#00e5c8", "#38b8f5", "#7c6dff", "#f5c842", "#ff7d3b", "#ff6b6b"][index % 6]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : <p>Exit utilization data is not available for this session yet.</p>
              )}

              {tab === "Statistics" && (
                <table className="analytics-stats-table">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Mean</th>
                      <th>Std Dev</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Evac Time</td>
                      <td>{panelModel.evacTime}</td>
                      <td>{formatMaybe(finalStats.average_evacuation_time, 2)}</td>
                      <td>{String(analysis?.status ?? "--")}</td>
                    </tr>
                    <tr>
                      <td>Flow Rate</td>
                      <td>{panelModel.throughput}</td>
                      <td>{formatMaybe(finalStats.total_flow_rate, 2)}</td>
                      <td>{String(analysis?.final_summary?.emergency_type ?? "--")}</td>
                    </tr>
                    <tr>
                      <td>Peak Density</td>
                      <td>{panelModel.peakDensity}</td>
                      <td>{formatMaybe(finalStats.peak_congestion_density, 3)}</td>
                      <td>{String(analysis?.final_summary?.routing_policy ?? "--")}</td>
                    </tr>
                    <tr>
                      <td>Events</td>
                      <td>{analysis?.event_markers.length ?? 0}</td>
                      <td>--</td>
                      <td>{replay?.events.length ?? 0} replay markers</td>
                    </tr>
                  </tbody>
                </table>
              )}
            </motion.div>
          </AnimatePresence>
        </section>
      )}
    </div>
  );
}
