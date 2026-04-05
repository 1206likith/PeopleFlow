import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import userEvent from "@testing-library/user-event";
import { screen, waitFor } from "@testing-library/react";
import { ScenarioBuilderPage } from "@/features/scenarios/ScenarioBuilderPage";
import { renderWithProviders } from "@/test/renderWithProviders";
import { mswServer } from "@/test/mswServer";
import { useSimulationStore } from "@/lib/state/simulationStore";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";
import { API_BASE_URL } from "@/lib/api/client";

const API = API_BASE_URL;

describe("ScenarioBuilderPage integration", () => {
  it("prefills the simulation store from the scenario builder", async () => {
    useWorkspaceStore.setState({ activeFloorPlanId: "fp-1" });

    mswServer.use(
      http.get(`${API}/api/v2/scenarios/presets`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/scenarios/presets", correlation_id: "s1", timestamp: new Date().toISOString() },
          data: {
            presets: [
              {
                id: "preset-office",
                name: "Office Fire",
                description: "Office preset",
                emergency_type: "fire",
                building_type: "office",
                panic_level: 0.52,
                recommended_exits: [{ id: "e1" }, { id: "e2" }],
              },
            ],
            count: 1,
          },
        }),
      ),
      http.get(`${API}/api/v2/scenarios/presets/preset-office`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/scenarios/presets/preset-office", correlation_id: "s2", timestamp: new Date().toISOString() },
          data: {
            id: "preset-office",
            name: "Office Fire",
            description: "Office preset",
            emergency_type: "fire",
            building_type: "office",
            panic_level: 0.52,
            recommended_exits: [{ id: "e1" }, { id: "e2" }],
          },
        }),
      ),
    );

    renderWithProviders(<ScenarioBuilderPage />);

    await userEvent.click(await screen.findByRole("button", { name: /Office Fire/i }, { timeout: 4000 }));
    await userEvent.click(screen.getByRole("button", { name: /Prefill Simulation Hub/i }));

    await waitFor(() => {
      const runParams = useSimulationStore.getState().runParams;
      expect(runParams.floorPlanId).toBe("fp-1");
      expect(runParams.policy).toBe("Guided Evacuation");
      expect(runParams.emergencyType).toBe("fire");
    });
  });
});
