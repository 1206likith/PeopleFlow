import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { AdminKeyDialog } from "@/features/settings/AdminKeyDialog";
import { useSessionStore } from "@/lib/state/sessionStore";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";

function getPageTitle(pathname: string): string {
  if (pathname === "/" || pathname.startsWith("/dashboard")) return "Command Center";
  if (pathname.startsWith("/designer") || pathname.startsWith("/upload") || pathname.startsWith("/design")) return "Building Designer";
  if (pathname.startsWith("/simulation") || pathname.startsWith("/simulate")) return "Simulation Hub";
  if (pathname.startsWith("/analytics")) return "Analytics Lab";
  if (pathname.startsWith("/scenarios")) return "Scenario Builder";
  if (pathname.startsWith("/operations")) return "Operations Hub";
  if (pathname.startsWith("/experiments")) return "Experiments";
  return "PeopleFlow";
}

function compactReference(value: string, leading = 8, trailing = 4): string {
  const trimmed = value.trim();
  if (!trimmed) return "none";
  if (trimmed.length <= leading + trailing + 1) return trimmed;
  return `${trimmed.slice(0, leading)}...${trimmed.slice(-trailing)}`;
}

export function TopUtilityBar() {
  const location = useLocation();
  const [adminDialogOpen, setAdminDialogOpen] = useState(false);
  const selectedSimulationId = useSimulationStore((state) => state.selectedSimulationId);
  const socketStatus = useSimulationStore((state) => state.socketStatus);
  const activeFloorPlanId = useWorkspaceStore((state) => state.activeFloorPlanId);
  const theme = useSessionStore((state) => state.theme);
  const toggleTheme = useSessionStore((state) => state.toggleTheme);
  const adminKey = useSessionStore((state) => state.adminKey);
  const reducedMotion = useSessionStore((state) => state.reducedMotion);
  const pageTitle = getPageTitle(location.pathname);

  const statusTone = useMemo(() => {
    if (socketStatus === "open") return { label: "Streaming", color: "#8de55f" };
    if (socketStatus === "reconnecting" || socketStatus === "connecting") return { label: "Recovering", color: "#f5c842" };
    if (socketStatus === "error") return { label: "Socket Error", color: "#ff6b6b" };
    return { label: "Idle", color: "#94a3b8" };
  }, [socketStatus]);

  return (
    <>
      <header className="topbar">
        <div className="topbar-content">
          <div className="topbar-lockup">
            <p className="topbar-eyebrow">PeopleFlow / Research UI</p>
            <h1 className="topbar-title">{pageTitle}</h1>
          </div>

          <div className="topbar-utility-stack">
            <div className="topbar-context-row">
              <div className="topbar-pill">
                <span className="topbar-status-dot" style={{ backgroundColor: statusTone.color }} />
                <span>{statusTone.label}</span>
              </div>
              <div className="topbar-pill topbar-pill-token" title={activeFloorPlanId || "No active floor plan"}>
                <span className="topbar-pill-label">Plan</span>
                <span className="topbar-pill-value">{compactReference(activeFloorPlanId)}</span>
              </div>
              <div className="topbar-pill topbar-pill-token" title={selectedSimulationId || "No active simulation"}>
                <span className="topbar-pill-label">Sim</span>
                <span className="topbar-pill-value">{compactReference(selectedSimulationId)}</span>
              </div>
            </div>

            <div className="topbar-action-row">
              <div className="theme-fixed-pill">{reducedMotion ? "Reduced Motion" : "Motion On"}</div>
              <button type="button" className="btn-secondary" onClick={() => toggleTheme()}>
                {theme === "dark" ? "Light UI" : "Dark UI"}
              </button>
              <button type="button" className="btn-secondary" onClick={() => setAdminDialogOpen(true)}>
                {adminKey ? "Update Admin Key" : "Set Admin Key"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <AdminKeyDialog open={adminDialogOpen} onClose={() => setAdminDialogOpen(false)} />
    </>
  );
}
