import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { mswServer } from "@/test/mswServer";
import { vi } from "vitest";
import { useSessionStore } from "@/lib/state/sessionStore";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";

beforeAll(() => mswServer.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  mswServer.resetHandlers();

  if (typeof window !== "undefined") {
    window.sessionStorage.clear();
  }

  useSessionStore.setState({
    adminKey: "",
    actorId: "web-dashboard",
    hasPromptedAdminKey: false,
    theme: "dark",
    sidebarCollapsed: false,
    reducedMotion: false,
  });
  useSimulationStore.setState({
    activeSession: null,
    activeSessionId: "",
    selectedSimulationId: "",
    draftConfig: {
      floor_number: 1,
      mode: "studio",
      num_agents: 260,
      emergency_type: "fire",
      routing_policy: "shortest_path",
      panic_level: 0.45,
      hazards: [],
      agent_profiles: [],
      blocked_exits: [],
      exits: [],
      parameter_overrides: { speed_multiplier: 1.2 },
      storage_policy: {
        record_frames: true,
        max_frames: 1200,
        frame_stride: 1,
        persist_frames: true,
      },
      max_runtime_seconds: 180,
    },
    liveFrame: null,
    frames: [],
    currentFrameIndex: 0,
    eventBuffer: [],
    analysisSnapshot: null,
    connectionState: "idle",
    socketStatus: "idle",
    viewMode: "split",
    isReplaying: false,
    runParams: {
      agentCount: 260,
      panicLevel: 0.45,
      speedMultiplier: 1.2,
      emergencyType: "fire",
      policy: "Shortest Path",
    },
    simulationPaneRatio: 0.6,
  });
  useWorkspaceStore.setState({
    activeFloorPlanId: "",
    activeFloorPlanSnapshot: null,
    selectedExitId: "",
    selectedExitPoints: [],
    canvasZoom: 1,
    canvasPan: { x: 0, y: 0 },
    designerPaneRatio: 0.6,
  });
});
afterAll(() => mswServer.close());

if (typeof HTMLCanvasElement !== "undefined") {
  Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
    value: vi.fn(() => {
      const noop = () => undefined;
      const gradient = { addColorStop: noop };
      return {
        setTransform: noop,
        save: noop,
        restore: noop,
        clip: noop,
        rect: noop,
        setLineDash: noop,
        translate: noop,
        rotate: noop,
        scale: noop,
        clearRect: noop,
        fillRect: noop,
        drawImage: noop,
        beginPath: noop,
        moveTo: noop,
        lineTo: noop,
        stroke: noop,
        strokeRect: noop,
        arc: noop,
        fill: noop,
        closePath: noop,
        fillText: noop,
        strokeText: noop,
        createLinearGradient: () => gradient,
        createRadialGradient: () => gradient,
        measureText: () => ({ width: 0 }),
        font: "",
        strokeStyle: "",
        fillStyle: "",
        lineWidth: 1,
      };
    }) as unknown as HTMLCanvasElement["getContext"],
  });
}
