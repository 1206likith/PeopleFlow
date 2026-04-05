import { beforeEach, describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { SimulationHubPage } from "@/features/simulation/SimulationHubPage";
import { renderWithProviders } from "@/test/renderWithProviders";
import { mswServer } from "@/test/mswServer";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";
import { API_BASE_URL } from "@/lib/api/client";

const API = API_BASE_URL;

class MockWebSocket {
  static OPEN = 1;
  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(url: string) {
    void url;
    setTimeout(() => this.onopen?.(), 0);
  }

  send(payload: string) {
    void payload;
  }

  close() {
    this.onclose?.();
  }
}

describe("SimulationHubPage integration", () => {
  beforeEach(() => {
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);
  });

  it("launches a session and shows the active session id", async () => {
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-active" });
    let createPayload: Record<string, unknown> | null = null;

    mswServer.use(
      http.get(`${API}/api/v3/simulation/sessions`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions", correlation_id: "sv31", timestamp: new Date().toISOString() },
          data: { sessions: [], total: 0 },
        }),
      ),
      http.post(`${API}/api/v3/simulation/sessions`, async ({ request }) => {
        createPayload = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions", correlation_id: "sv32", timestamp: new Date().toISOString() },
          data: {
            id: "session-123",
            config: createPayload,
            state: { status: "draft", connection_state: "idle", frame_count: 0, event_count: 0 },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            analysis_available: false,
            replay_available: false,
            status_timeline: [],
            provenance: {},
          },
        });
      }),
      http.post(`${API}/api/v3/simulation/sessions/session-123/control`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-123/control", correlation_id: "sv33", timestamp: new Date().toISOString() },
          data: {
            id: "session-123",
            config: createPayload,
            state: { status: "running", connection_state: "streaming", frame_count: 1, event_count: 1, latest_frame_id: 1, latest_timestamp: 1.2 },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            analysis_available: true,
            replay_available: true,
            status_timeline: [],
            provenance: {},
            recent_events: [{ event_id: "evt-1", session_id: "session-123", type: "state_change", timestamp: 0, severity: "info", title: "Session started", message: "Session state is now running.", data: {} }],
          },
        }),
      ),
      http.get(`${API}/api/v3/simulation/sessions/session-123`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-123", correlation_id: "sv34", timestamp: new Date().toISOString() },
          data: {
            id: "session-123",
            config: createPayload,
            state: { status: "running", connection_state: "streaming", frame_count: 1, event_count: 1, latest_frame_id: 1, latest_timestamp: 1.2 },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            analysis_available: true,
            replay_available: true,
            status_timeline: [],
            provenance: {},
            recent_events: [{ event_id: "evt-1", session_id: "session-123", type: "state_change", timestamp: 0, severity: "info", title: "Session started", message: "Session state is now running.", data: {} }],
          },
        }),
      ),
      http.get(`${API}/api/v3/simulation/sessions/session-123/analysis`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-123/analysis", correlation_id: "sv35", timestamp: new Date().toISOString() },
          data: {
            session_id: "session-123",
            status: "running",
            simulation_time: 1.2,
            frame_count: 1,
            total_agents: 260,
            evacuated: 0,
            remaining: 260,
            completion_percentage: 0,
            flow_rate: 0,
            peak_density: 0.12,
            exit_usage: { e1: 0 },
            profile_counts: {},
            timeline: [],
            event_markers: [],
            density_heatmap: [],
            final_summary: { routing_policy: "shortest_path" },
          },
        }),
      ),
      http.get(`${API}/api/v3/simulation/sessions/session-123/replay`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-123/replay", correlation_id: "sv36", timestamp: new Date().toISOString() },
          data: {
            session_id: "session-123",
            offset: 0,
            limit: 180,
            count: 1,
            frames: [{ simulation_id: "session-123", timestamp: 1.2, frame_id: 1, agents: [], exits: [], stats: { evacuated: 0, remaining: 260 } }],
            events: [],
          },
        }),
      ),
    );

    renderWithProviders(<SimulationHubPage />);

    await userEvent.click(screen.getByRole("button", { name: /launch session/i }));

    await waitFor(() => {
      expect(screen.getByText((_, node) => node?.textContent === "Session session-123")).toBeInTheDocument();
    });

    expect(createPayload?.["floor_plan_ref"]).toBe("fp-active");
  });

  it("prevents duplicate launch requests while a session launch is pending", async () => {
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-guard" });
    let createCalls = 0;

    mswServer.use(
      http.get(`${API}/api/v3/simulation/sessions`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions", correlation_id: "sg1", timestamp: new Date().toISOString() },
          data: { sessions: [], total: 0 },
        }),
      ),
      http.post(`${API}/api/v3/simulation/sessions`, async () => {
        createCalls += 1;
        await new Promise((resolve) => setTimeout(resolve, 80));
        return HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions", correlation_id: "sg2", timestamp: new Date().toISOString() },
          data: {
            id: "session-guard",
            config: { floor_plan_ref: "fp-guard", num_agents: 260, emergency_type: "fire", routing_policy: "shortest_path", panic_level: 0.45, mode: "studio", floor_number: 1, hazards: [], agent_profiles: [], blocked_exits: [], exits: [], parameter_overrides: { speed_multiplier: 1.2 }, storage_policy: { record_frames: true, max_frames: 1200, frame_stride: 1, persist_frames: true } },
            state: { status: "draft", connection_state: "idle", frame_count: 0, event_count: 0 },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            analysis_available: false,
            replay_available: false,
            status_timeline: [],
            provenance: {},
          },
        });
      }),
      http.post(`${API}/api/v3/simulation/sessions/session-guard/control`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-guard/control", correlation_id: "sg3", timestamp: new Date().toISOString() },
          data: {
            id: "session-guard",
            config: { floor_plan_ref: "fp-guard", num_agents: 260, emergency_type: "fire", routing_policy: "shortest_path", panic_level: 0.45, mode: "studio", floor_number: 1, hazards: [], agent_profiles: [], blocked_exits: [], exits: [], parameter_overrides: { speed_multiplier: 1.2 }, storage_policy: { record_frames: true, max_frames: 1200, frame_stride: 1, persist_frames: true } },
            state: { status: "running", connection_state: "streaming", frame_count: 0, event_count: 0 },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            analysis_available: false,
            replay_available: false,
            status_timeline: [],
            provenance: {},
          },
        }),
      ),
      http.get(`${API}/api/v3/simulation/sessions/session-guard`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-guard", correlation_id: "sg4", timestamp: new Date().toISOString() },
          data: {
            id: "session-guard",
            config: { floor_plan_ref: "fp-guard", num_agents: 260, emergency_type: "fire", routing_policy: "shortest_path", panic_level: 0.45, mode: "studio", floor_number: 1, hazards: [], agent_profiles: [], blocked_exits: [], exits: [], parameter_overrides: { speed_multiplier: 1.2 }, storage_policy: { record_frames: true, max_frames: 1200, frame_stride: 1, persist_frames: true } },
            state: { status: "running", connection_state: "streaming", frame_count: 0, event_count: 0 },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            analysis_available: false,
            replay_available: false,
            status_timeline: [],
            provenance: {},
          },
        }),
      ),
      http.get(`${API}/api/v3/simulation/sessions/session-guard/analysis`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-guard/analysis", correlation_id: "sg5", timestamp: new Date().toISOString() },
          data: {
            session_id: "session-guard",
            status: "running",
            simulation_time: 0,
            frame_count: 0,
            total_agents: 260,
            evacuated: 0,
            remaining: 260,
            completion_percentage: 0,
            flow_rate: 0,
            peak_density: 0,
            exit_usage: {},
            profile_counts: {},
            timeline: [],
            event_markers: [],
            density_heatmap: [],
            final_summary: {},
          },
        }),
      ),
      http.get(`${API}/api/v3/simulation/sessions/session-guard/replay`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-guard/replay", correlation_id: "sg6", timestamp: new Date().toISOString() },
          data: { session_id: "session-guard", offset: 0, limit: 180, count: 0, frames: [], events: [] },
        }),
      ),
    );

    renderWithProviders(<SimulationHubPage />);

    const launchButton = screen.getByRole("button", { name: /launch session/i });
    await userEvent.dblClick(launchButton);

    await waitFor(() => {
      expect(screen.getByText((_, node) => node?.textContent === "Session session-guard")).toBeInTheDocument();
    });

    expect(createCalls).toBe(1);
  });

  it("applies disaster presets to the session draft and derived run params", async () => {
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-disaster" });

    mswServer.use(
      http.get(`${API}/api/v3/simulation/sessions`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions", correlation_id: "dp1", timestamp: new Date().toISOString() },
          data: { sessions: [], total: 0 },
        }),
      ),
    );

    renderWithProviders(<SimulationHubPage />);

    await userEvent.click(screen.getByRole("button", { name: /earthquake/i }));

    await waitFor(() => {
      const state = useSimulationStore.getState();
      expect(state.draftConfig.emergency_type).toBe("earthquake");
      expect(state.draftConfig.routing_policy).toBe("least_crowded");
      expect(state.draftConfig.panic_level).toBeCloseTo(0.68, 2);
      expect(state.runParams.emergencyType).toBe("earthquake");
      expect(state.runParams.policy).toBe("Least Crowded");
      expect(state.runParams.agentCount).toBe(220);
    });
  });
});
