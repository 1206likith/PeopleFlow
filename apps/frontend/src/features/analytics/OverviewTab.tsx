import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import {
  getSimulationExitUsage,
  getSimulationMetrics,
  getSimulationProfileCounts,
  getSimulationSummary,
  getSimulationTimeline,
} from "@/lib/api/simulation";
import { ErrorPanel } from "@/components/common/ErrorPanel";
import { EmptyState } from "@/components/common/EmptyState";

interface OverviewTabProps {
  simulationId: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="analytics-tooltip glass-card p-4 shadow-2xl">
        <p className="text-xs font-semibold uppercase tracking-wider text-fog mb-3">{`Time: ${label}s`}</p>
        <div className="space-y-2">
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-6">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ backgroundColor: entry.color, boxShadow: `0 0 10px ${entry.color}` }} />
                <span className="text-sm text-mist capitalize">{entry.name}</span>
              </div>
              <span className="text-sm font-mono font-medium text-white">{entry.value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export function OverviewTab({ simulationId }: OverviewTabProps) {
  const summaryQuery = useQuery({
    queryKey: ["analytics", "summary", simulationId],
    queryFn: ({ signal }) => getSimulationSummary(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  const metricsQuery = useQuery({
    queryKey: ["analytics", "metrics", simulationId],
    queryFn: ({ signal }) => getSimulationMetrics(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  const timelineQuery = useQuery({
    queryKey: ["analytics", "timeline", simulationId],
    queryFn: ({ signal }) => getSimulationTimeline(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  const exitUsageQuery = useQuery({
    queryKey: ["analytics", "exit-usage", simulationId],
    queryFn: ({ signal }) => getSimulationExitUsage(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  const profileQuery = useQuery({
    queryKey: ["analytics", "profile-counts", simulationId],
    queryFn: ({ signal }) => getSimulationProfileCounts(simulationId, signal),
    enabled: Boolean(simulationId),
  });

  if (!simulationId) {
    return <EmptyState title="Select simulation" message="Choose a simulation from the Analytics Hub selector." />;
  }

  return (
    <div className="space-y-6">
      {/* ── 3-Block KPI Summaries ──────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="analytics-kpi-card glass-card p-6 relative overflow-hidden flex flex-col justify-between shadow-lg">
          <div className="analytics-kpi-glow bg-cyan-500/10" />
           <span className="text-xs font-semibold uppercase tracking-wider text-fog relative z-10 flex items-center gap-2">
             <div className="w-1.5 h-1.5 rounded-full bg-cyan-300" />
             Total Agents
           </span>
           <div className="mt-5 flex items-baseline gap-2 relative z-10">
             <span className="text-5xl font-bold text-snow" style={{ fontFamily: "var(--font-heading)" }}>{summaryQuery.data?.total_agents ?? "—"}</span>
             <span className="text-sm text-mist">profiles</span>
           </div>
        </div>
        
          <div className="analytics-kpi-card glass-card p-6 relative overflow-hidden flex flex-col justify-between shadow-lg">
            <div className="analytics-kpi-glow bg-emerald-500/10" />
           <span className="text-xs font-semibold uppercase tracking-wider text-fog relative z-10 flex items-center gap-2">
             <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
             Evacuated
           </span>
           <div className="mt-5 flex items-baseline gap-2 relative z-10">
             <span className="text-5xl font-bold text-emerald-400" style={{ fontFamily: "var(--font-heading)" }}>{summaryQuery.data?.evacuated ?? "—"}</span>
             <span className="text-sm text-mist mt-1 leading-tight">successfully<br/>exited</span>
           </div>
        </div>

          <div className="analytics-kpi-card glass-card p-6 relative overflow-hidden flex flex-col justify-between shadow-lg">
            <div className="analytics-kpi-glow bg-sky-500/10" />
           <span className="text-xs font-semibold uppercase tracking-wider text-fog relative z-10 flex items-center gap-2">
             <div className="w-1.5 h-1.5 rounded-full bg-sky-400" />
             Total Time
           </span>
           <div className="mt-5 flex items-baseline gap-2 relative z-10">
             <span className="text-5xl font-bold text-sky-400" style={{ fontFamily: "var(--font-heading)" }}>{summaryQuery.data?.total_time ?? "—"}</span>
             <span className="text-sm text-mist">seconds</span>
           </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
        {/* ── Evacuation Timeline Chart ──────── */}
        <div className="analytics-chart-shell glass-card p-6 flex flex-col min-h-[400px]">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-semibold text-snow uppercase tracking-wider">Evacuation Timeline</h3>
            <span className="analytics-chart-chip text-xs text-fog py-1 px-3 rounded-full">Volume over time</span>
          </div>
          
          <div className="flex-1 relative">
            {timelineQuery.isLoading && <p className="absolute inset-0 flex items-center justify-center text-sm text-fog">Loading timeline...</p>}
            {timelineQuery.error && <div className="absolute inset-0"><ErrorPanel error={timelineQuery.error} /></div>}
            {timelineQuery.data && (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timelineQuery.data.points} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorEvacuated" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#34d399" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#34d399" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorRemaining" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#fbbf24" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="timestamp" stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} tickMargin={10} axisLine={false} />
                  <YAxis stroke="rgba(255,255,255,0.2)" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} tickMargin={10} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                  <Area type="monotone" dataKey="evacuated" stroke="#34d399" strokeWidth={2} fillOpacity={1} fill="url(#colorEvacuated)" />
                  <Area type="monotone" dataKey="remaining" stroke="#fbbf24" strokeWidth={2} fillOpacity={1} fill="url(#colorRemaining)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* ── Computed Metrics Sidebar ──────── */}
        <div className="analytics-diagnostics-shell glass-card p-6 flex flex-col">
          <h3 className="text-sm font-semibold text-snow uppercase tracking-wider mb-4">Diagnostic Details</h3>
          
          <div className="flex-1 space-y-4 overflow-y-auto hidden-scrollbar pr-2 pb-2">
            <div className="space-y-2">
              <span className="text-[10px] uppercase tracking-wider text-fog">Engine Metrics</span>
              {metricsQuery.isLoading && <p className="text-xs text-fog">Loading...</p>}
              {metricsQuery.error && <ErrorPanel error={metricsQuery.error} />}
              {metricsQuery.data && (
                <div className="analytics-json-box">
                  <pre className="text-[10px] text-mist/80 font-mono whitespace-pre-wrap word-break">
                    {JSON.stringify(metricsQuery.data.metrics ?? metricsQuery.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <span className="text-[10px] uppercase tracking-wider text-fog">Exit Utilization</span>
              {exitUsageQuery.isLoading && <p className="text-xs text-fog">Loading...</p>}
              {exitUsageQuery.error && <ErrorPanel error={exitUsageQuery.error} />}
              {exitUsageQuery.data && (
                <div className="analytics-json-box">
                  <pre className="text-[10px] text-mist/80 font-mono whitespace-pre-wrap word-break">
                    {JSON.stringify(exitUsageQuery.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <span className="text-[10px] uppercase tracking-wider text-fog">Profile Distribution</span>
              {profileQuery.isLoading && <p className="text-xs text-fog">Loading...</p>}
              {profileQuery.error && <ErrorPanel error={profileQuery.error} />}
              {profileQuery.data && (
                <div className="analytics-json-box">
                  <pre className="text-[10px] text-mist/80 font-mono whitespace-pre-wrap word-break">
                    {JSON.stringify(profileQuery.data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
    </div>
  );
}

