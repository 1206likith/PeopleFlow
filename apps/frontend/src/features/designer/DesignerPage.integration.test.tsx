import { describe, expect, it } from "vitest";
import { beforeEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import userEvent from "@testing-library/user-event";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { DesignerPage } from "@/features/designer/DesignerPage";
import { renderWithProviders } from "@/test/renderWithProviders";
import { mswServer } from "@/test/mswServer";
import { API_BASE_URL } from "@/lib/api/client";
import { useWorkspaceStore } from "@/lib/state/workspaceStore";

const API = API_BASE_URL;
const LOCAL_FLOOR_PLAN_STORAGE_KEY = "peopleflow.localFloorPlans";

function installCanvasViewport(width = 640, height = 480) {
  Object.defineProperty(HTMLCanvasElement.prototype, "clientWidth", {
    configurable: true,
    get: () => width,
  });
  Object.defineProperty(HTMLCanvasElement.prototype, "clientHeight", {
    configurable: true,
    get: () => height,
  });
  Object.defineProperty(HTMLCanvasElement.prototype, "getBoundingClientRect", {
    configurable: true,
    value: () =>
      ({
        width,
        height,
        top: 0,
        left: 0,
        right: width,
        bottom: height,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      }) satisfies DOMRect,
  });
  Object.defineProperty(HTMLCanvasElement.prototype, "setPointerCapture", {
    configurable: true,
    value: vi.fn(),
  });
  Object.defineProperty(HTMLCanvasElement.prototype, "releasePointerCapture", {
    configurable: true,
    value: vi.fn(),
  });
}

describe("DesignerPage integration", () => {
  beforeEach(() => {
    installCanvasViewport();
  });

  it("uploads and loads exits", async () => {
    mswServer.use(
      http.post(`${API}/api/v2/simulations/upload`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/upload", correlation_id: "t1", timestamp: new Date().toISOString() },
          data: { id: "fp-1", building_name: "Main Building", exits: [] },
        }),
      ),
      http.get(`${API}/api/v2/simulations/floor-plans/fp-1/exits`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-1/exits", correlation_id: "t2", timestamp: new Date().toISOString() },
          data: { exits: [{ id: "exit-a", name: "Exit A", x: 5, y: 9, width: 2 }] },
        }),
      ),
      http.get(`${API}/api/v2/simulations/floor-plans/fp-1`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-1", correlation_id: "t3", timestamp: new Date().toISOString() },
          data: { id: "fp-1", exits: [], detected_walls: [], detected_obstacles: [], boundary_polygon: [] },
        }),
      ),
      http.get(`${API}/api/v2/simulations/floor-plans/fp-1/pipeline`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-1/pipeline", correlation_id: "t4", timestamp: new Date().toISOString() },
          data: { pipeline: "mock", pipeline_steps: [] },
        }),
      ),
      http.get(`${API}/api/v2/simulations/floor-plans/fp-1/quality-report`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-1/quality-report", correlation_id: "t5", timestamp: new Date().toISOString() },
          data: { floor_plan_id: "fp-1", quality_report: { simulation_ready: true, wall_count: 12, usable_exit_count: 2 } },
        }),
      ),
    );

    renderWithProviders(<DesignerPage />);

    await userEvent.click(screen.getByRole("button", { name: /upload floor plan/i }));

    await waitFor(() => {
      expect(screen.getByText(/floor plan uploaded successfully/i)).toBeInTheDocument();
      expect(screen.getByText("Exit A")).toBeInTheDocument();
    });
  });

  it("selects an exit from the grid and edits it in place", async () => {
    const localPlan = {
      id: "mock-designer-plan",
      building_name: "Local Mock Plan",
      exits: [
        { id: "exit-a", name: "Exit A", x: 50, y: 50, z: 50, width: 2, capacity: 100, source: "manual_local" },
        { id: "exit-b", name: "Exit B", x: 75, y: 25, z: 25, width: 2.5, capacity: 120, source: "manual_local" },
      ],
      detected_walls: [],
      detected_obstacles: [],
      boundary_polygon: [],
      building_bounds: {
        min_x: 0,
        max_x: 100,
        min_y: 0,
        max_y: 100,
      },
    };

    window.sessionStorage.setItem(
      LOCAL_FLOOR_PLAN_STORAGE_KEY,
      JSON.stringify({ [localPlan.id]: localPlan }),
    );
    useWorkspaceStore.setState({
      activeFloorPlanId: localPlan.id,
      activeFloorPlanSnapshot: localPlan,
      selectedExitId: "",
      selectedExitPoints: [],
      canvasZoom: 1,
      canvasPan: { x: 0, y: 0 },
      designerPaneRatio: 0.6,
    });

    const { container } = renderWithProviders(<DesignerPage />);
    const canvas = container.querySelector("canvas");
    expect(canvas).not.toBeNull();

    await waitFor(() => {
      expect(screen.getByText("Exit A")).toBeInTheDocument();
    });

    fireEvent.click(canvas!, { clientX: 320, clientY: 240 });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Exit A")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /update selected exit/i })).toBeInTheDocument();
    });

    const widthInput = screen.getByLabelText(/width/i);
    await userEvent.clear(widthInput);
    await userEvent.type(widthInput, "3.5");
    await userEvent.click(screen.getByRole("button", { name: /update selected exit/i }));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Exit A")).toBeInTheDocument();
      expect(screen.getByText(/width: 3.50/i)).toBeInTheDocument();
      expect(screen.getByText(/Exit B/i)).toBeInTheDocument();
    });

    await userEvent.click(screen.getAllByRole("button", { name: /delete/i })[0]);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /add new exit/i })).toBeInTheDocument();
      expect(screen.queryByText(/^Exit A$/)).not.toBeInTheDocument();
      expect(screen.getByText(/^Exit B$/)).toBeInTheDocument();
    });
  });

  it("deletes a detected exit from a backend-backed floor plan", async () => {
    useWorkspaceStore.setState({
      activeFloorPlanId: "fp-detected-delete",
      activeFloorPlanSnapshot: {
        id: "fp-detected-delete",
        building_name: "Detected Delete",
        exits: [],
        detected_walls: [],
        detected_obstacles: [],
        boundary_polygon: [],
      },
      selectedExitId: "",
      selectedExitPoints: [],
      canvasZoom: 1,
      canvasPan: { x: 0, y: 0 },
      designerPaneRatio: 0.6,
    });

    let exitsPayload = {
      exits: [{ id: "detected-a", name: "Detected A", x: 18, y: 12, z: 12, width: 2, capacity: 90, source: "detected" }],
      detected_exits: [{ id: "detected-a", name: "Detected A", x: 18, y: 12, z: 12, width: 2, capacity: 90, source: "detected" }],
      manual_exits: [],
    };

    mswServer.use(
      http.get(`${API}/api/v2/simulations/floor-plans/fp-detected-delete/exits`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-detected-delete/exits", correlation_id: "d1", timestamp: new Date().toISOString() },
          data: exitsPayload,
        }),
      ),
      http.delete(`${API}/api/v2/simulations/floor-plans/fp-detected-delete/exits/detected-a`, async () => {
        exitsPayload = { exits: [], detected_exits: [], manual_exits: [] };
        return HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-detected-delete/exits/detected-a", correlation_id: "d2", timestamp: new Date().toISOString() },
          data: { removed_exit_id: "detected-a", removed_detected_exit_ids: ["detected-a"] },
        });
      }),
      http.get(`${API}/api/v2/simulations/floor-plans/fp-detected-delete`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-detected-delete", correlation_id: "d3", timestamp: new Date().toISOString() },
          data: { id: "fp-detected-delete", exits: [], detected_walls: [], detected_obstacles: [], boundary_polygon: [] },
        }),
      ),
      http.get(`${API}/api/v2/simulations/floor-plans/fp-detected-delete/pipeline`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-detected-delete/pipeline", correlation_id: "d4", timestamp: new Date().toISOString() },
          data: { pipeline: "semantic", pipeline_steps: [] },
        }),
      ),
      http.get(`${API}/api/v2/simulations/floor-plans/fp-detected-delete/quality-report`, async () =>
        HttpResponse.json({
          meta: { version: "v2", mode: "demo", path: "/api/v2/simulations/floor-plans/fp-detected-delete/quality-report", correlation_id: "d5", timestamp: new Date().toISOString() },
          data: { floor_plan_id: "fp-detected-delete", quality_report: { simulation_ready: true, wall_count: 10, usable_exit_count: 1 } },
        }),
      ),
    );

    renderWithProviders(<DesignerPage />);

    await waitFor(() => {
      expect(screen.getByText("Detected A")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /delete/i }));

    await waitFor(() => {
      expect(screen.queryByText("Detected A")).not.toBeInTheDocument();
    });
  });
});
