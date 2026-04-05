import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import { AnalyticsHubPage } from "@/features/analytics/AnalyticsHubPage";
import { renderWithProviders } from "@/test/renderWithProviders";
import { mswServer } from "@/test/mswServer";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { API_BASE_URL } from "@/lib/api/client";

const API = API_BASE_URL;

describe("AnalyticsHubPage integration", () => {
  it("renders session-linked overview with partial endpoint failures", async () => {
    useSimulationStore.setState({ activeSessionId: "session-a", selectedSimulationId: "session-a" });

    mswServer.use(
      http.get(`${API}/api/v3/simulation/sessions`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions", correlation_id: "a1", timestamp: new Date().toISOString() },
          data: {
            sessions: [
              {
                id: "session-a",
                config: {
                  floor_plan_ref: "fp-a",
                  mode: "studio",
                  num_agents: 10,
                  emergency_type: "fire",
                  routing_policy: "guided_evacuation",
                  panic_level: 0.55,
                  hazards: [],
                  agent_profiles: [],
                  blocked_exits: [],
                  storage_policy: { record_frames: true, max_frames: 1200, frame_stride: 1, persist_frames: true },
                },
                state: { status: "completed", connection_state: "idle", frame_count: 3, event_count: 2 },
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                analysis_available: true,
                replay_available: true,
                status_timeline: [],
                provenance: {},
              },
            ],
            total: 1,
          },
        }),
      ),
      http.get(`${API}/api/v3/simulation/sessions/session-a/analysis`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions/session-a/analysis", correlation_id: "a2", timestamp: new Date().toISOString() },
          data: {
            session_id: "session-a",
            status: "completed",
            simulation_time: 34,
            frame_count: 3,
            total_agents: 10,
            evacuated: 2,
            remaining: 8,
            completion_percentage: 20,
            flow_rate: 1.7,
            peak_density: 0.42,
            exit_usage: { e1: 2 },
            profile_counts: { staff: 2 },
            timeline: [{ timestamp: 1, evacuated: 1, remaining: 9, flow_rate: 1.2, peak_density: 0.3 }],
            event_markers: [],
            density_heatmap: [[0.1, 0.2]],
            final_summary: { routing_policy: "guided_evacuation", emergency_type: "fire", metrics: { average_evacuation_time: 34 } },
          },
        }),
      ),
      http.get(`${API}/api/v3/simulation/sessions/session-a/replay`, async () => HttpResponse.json({ error: "boom" }, { status: 500 })),
    );

    renderWithProviders(<AnalyticsHubPage />);

    await waitFor(() => {
      expect(screen.getByText(/Total Agents/i)).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "10" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "34s" })).toBeInTheDocument();
    });
  });
});
