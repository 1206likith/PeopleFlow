import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import { HomePage } from "@/features/home/HomePage";
import { renderWithProviders } from "@/test/renderWithProviders";
import { mswServer } from "@/test/mswServer";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";
import { API_BASE_URL } from "@/lib/api/client";

const API = API_BASE_URL;

describe("HomePage integration", () => {
  it("renders the command center with recent runs and health cards", async () => {
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-home" });
    useSimulationStore.setState({ selectedSimulationId: "sim-home" });

    mswServer.use(
      http.get(`${API}/api/v2/simulations/`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/", correlation_id: "h1", timestamp: new Date().toISOString() },
          data: {
            simulations: [{ id: "sim-home", name: "Demo Run", status: "running", emergency_type: "fire", num_agents: 120 }],
            total: 1,
          },
        }),
      ),
      http.get(`${API}/api/v2/system/status`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/system/status", correlation_id: "h2", timestamp: new Date().toISOString() },
          data: { database: "demo", unity_enabled: true },
        }),
      ),
      http.get(`${API}/api/v2/system/info`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/system/info", correlation_id: "h3", timestamp: new Date().toISOString() },
          data: { service_version: "v2.1.0" },
        }),
      ),
    );

    renderWithProviders(<HomePage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Research-Grade Evacuation Intelligence Workspace/i })).toBeInTheDocument();
      expect(screen.getByText(/fp-home/i)).toBeInTheDocument();
      expect(screen.getByText(/sim-home/i)).toBeInTheDocument();
      expect(screen.getByText(/Health Strip/i)).toBeInTheDocument();
    });
  });
});
