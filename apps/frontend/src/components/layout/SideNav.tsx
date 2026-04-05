import clsx from "clsx";
import { NavLink } from "react-router-dom";
import { useSessionStore } from "@/lib/state/sessionStore";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";

const icons = {
  home: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M3 12 12 4l9 8" />
      <path d="M6 10.5V20h12v-9.5" />
      <path d="M10 20v-5h4v5" />
    </svg>
  ),
  designer: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <path d="M8 3v18M3 9h5M3 15h5" />
    </svg>
  ),
  simulation: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 2v3M12 19v3M3 12h3M18 12h3M5.64 5.64l2.12 2.12M16.24 16.24l2.12 2.12M5.64 18.36l2.12-2.12M16.24 7.76l2.12-2.12" />
    </svg>
  ),
  analytics: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M3 3v18h18" />
      <path d="m7 15 4-4 3 2 4-6" />
    </svg>
  ),
  scenarios: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M4 6h16M4 10h16M4 14h10M4 18h7" />
    </svg>
  ),
  operations: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.65 1.65 0 0 0 15 19.4a1.65 1.65 0 0 0-1 .6 1.65 1.65 0 0 0-.33 1V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-.33-1 1.65 1.65 0 0 0-1-.6 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-.6-1 1.65 1.65 0 0 0-1-.33H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1-.33 1.65 1.65 0 0 0 .6-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-.6 1.65 1.65 0 0 0 .33-1V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 .33 1 1.65 1.65 0 0 0 1 .6 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c0 .39.14.76.4 1 .26.26.61.4 1 .4H21a2 2 0 1 1 0 4h-.09c-.39 0-.74.14-1 .4-.26.26-.4.61-.4 1Z" />
    </svg>
  ),
  experiments: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <path d="M9 3h6" />
      <path d="M10 9h4" />
      <path d="M8 3v5l-4.5 8.5A3 3 0 0 0 6.2 21h11.6a3 3 0 0 0 2.7-4.5L16 8V3" />
    </svg>
  ),
};

const navItems = [
  { to: "/", label: "Home", icon: icons.home, end: true },
  { to: "/designer", label: "Designer", icon: icons.designer },
  { to: "/simulation", label: "Simulation", icon: icons.simulation },
  { to: "/analytics", label: "Analytics", icon: icons.analytics },
  { to: "/scenarios", label: "Scenarios", icon: icons.scenarios },
  { to: "/operations", label: "Operations", icon: icons.operations },
  { to: "/experiments", label: "Experiments", icon: icons.experiments },
] as const;

export function SideNav() {
  const sidebarCollapsed = useSessionStore((state) => state.sidebarCollapsed);
  const toggleSidebarCollapsed = useSessionStore((state) => state.toggleSidebarCollapsed);
  const socketStatus = useSimulationStore((state) => state.socketStatus);
  const frames = useSimulationStore((state) => state.frames);
  const activeFloorPlanId = useWorkspaceStore((state) => state.activeFloorPlanId);

  const liveLabel = socketStatus === "open" ? "Live" : socketStatus === "reconnecting" ? "Recovering" : "Standby";

  return (
    <aside
      className={clsx(
        "sidenav-shell flex shrink-0 flex-col overflow-hidden",
        sidebarCollapsed ? "w-[92px]" : "w-[260px]",
      )}
    >
      <div className="flex items-center gap-3 px-3 py-4">
        <div className="grid h-11 w-11 place-items-center rounded-2xl border border-white/10 bg-white/5 text-cyan-200 shadow-[0_10px_30px_rgba(0,0,0,0.2)]">
          <svg viewBox="0 0 32 32" fill="none" className="h-7 w-7">
            <rect width="32" height="32" rx="11" fill="url(#peopleflow-shell-logo)" />
            <path d="M9.5 12.4a2.4 2.4 0 1 0 0-4.8 2.4 2.4 0 0 0 0 4.8Zm6.5 0a2.4 2.4 0 1 0 0-4.8 2.4 2.4 0 0 0 0 4.8Zm6.5 0a2.4 2.4 0 1 0 0-4.8 2.4 2.4 0 0 0 0 4.8Z" fill="white" fillOpacity=".94" />
            <path d="M6.8 22c0-1.8 1.4-3.2 3.2-3.2s3.2 1.4 3.2 3.2M13.4 22c0-1.8 1.4-3.2 3.2-3.2s3.2 1.4 3.2 3.2M20 22c0-1.8 1.4-3.2 3.2-3.2s3.2 1.4 3.2 3.2" stroke="white" strokeOpacity=".94" strokeWidth="1.4" strokeLinecap="round" />
            <defs>
              <linearGradient id="peopleflow-shell-logo" x1="3" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse">
                <stop stopColor="#00e5c8" />
                <stop offset=".48" stopColor="#38b8f5" />
                <stop offset="1" stopColor="#7c6dff" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        {!sidebarCollapsed && (
          <div className="min-w-0">
            <p className="text-sm font-semibold tracking-[0.08em] text-cyan-200">PEOPLEFLOW</p>
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Research Dashboard</p>
          </div>
        )}
      </div>

      <div className="sidenav-divider mb-4 mt-1" />

      <nav className="flex-1 space-y-1 overflow-y-auto px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={"end" in item ? item.end : undefined}
            className={({ isActive }) =>
              clsx(
                "group flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm font-medium transition-all duration-200",
                isActive
                  ? "sidenav-link-active"
                  : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/5 hover:text-white",
              )
            }
            title={sidebarCollapsed ? item.label : undefined}
          >
            <span className="shrink-0">{item.icon}</span>
            {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="mt-4 space-y-3 px-2">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
          <div className="flex items-center gap-2">
            <span className={clsx("h-2.5 w-2.5 rounded-full", socketStatus === "open" ? "bg-emerald-400" : socketStatus === "reconnecting" ? "bg-amber-400" : "bg-slate-500")} />
            {!sidebarCollapsed && (
              <>
                <span className="text-xs font-semibold text-white">Runtime</span>
                <span className="ml-auto text-[10px] font-medium uppercase tracking-[0.14em] text-slate-400">{liveLabel}</span>
              </>
            )}
          </div>
          {!sidebarCollapsed && (
            <div className="mt-3 grid gap-2 text-[11px] text-slate-400">
              <div className="flex items-center justify-between">
                <span>Buffered frames</span>
                <span className="font-mono text-cyan-200">{frames.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Active plan</span>
                <span className="max-w-[7rem] truncate font-mono text-slate-200">{activeFloorPlanId || "none"}</span>
              </div>
            </div>
          )}
        </div>

        <button
          type="button"
          className="btn-secondary flex w-full items-center justify-center gap-2"
          onClick={() => toggleSidebarCollapsed()}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
            <path d={sidebarCollapsed ? "m9 18 6-6-6-6" : "m15 18-6-6 6-6"} />
          </svg>
          {!sidebarCollapsed && <span>{sidebarCollapsed ? "Expand Rail" : "Collapse Rail"}</span>}
        </button>
      </div>
    </aside>
  );
}
