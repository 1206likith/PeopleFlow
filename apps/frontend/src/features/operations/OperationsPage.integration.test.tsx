import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import { OperationsPage } from "@/features/operations/OperationsPage";
import { renderWithProviders } from "@/test/renderWithProviders";
import { mswServer } from "@/test/mswServer";
import { API_BASE_URL } from "@/lib/api/client";

const API = API_BASE_URL;

describe("OperationsPage integration", () => {
  it("renders overview telemetry for the operations console", async () => {
    mswServer.use(
      http.get(`${API}/api/v3/simulation/sessions`, async () =>
        HttpResponse.json({
          meta: { version: "v3", mode: "demo", path: "/api/v3/simulation/sessions", correlation_id: "o0", timestamp: new Date().toISOString() },
          data: { sessions: [], total: 0 },
        }),
      ),
      http.get(`${API}/api/v2/simulations/batches`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/batches", correlation_id: "o1", timestamp: new Date().toISOString() },
          data: {
            batches: [{ batch_id: "ops-batch", status: "running", runs: 4, completed_runs: 3 }],
            total: 1,
          },
        }),
      ),
      http.get(`${API}/api/v2/system/status`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/system/status", correlation_id: "o2", timestamp: new Date().toISOString() },
          data: { system_status: "healthy", unity_enabled: true },
        }),
      ),
      http.get(`${API}/api/v2/system/capabilities`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/system/capabilities", correlation_id: "o3", timestamp: new Date().toISOString() },
          data: { capabilities: [{ id: "ml", enabled: true }, { id: "reports", enabled: false }] },
        }),
      ),
    );

    renderWithProviders(<OperationsPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Backend Parity Control Surface/i })).toBeInTheDocument();
      expect(screen.getByText(/Admin Key Required/i)).toBeInTheDocument();
      expect(screen.getByText(/Operator Brief/i)).toBeInTheDocument();
      expect(screen.getByText(/9 modules/i)).toBeInTheDocument();
    });
  });
});
