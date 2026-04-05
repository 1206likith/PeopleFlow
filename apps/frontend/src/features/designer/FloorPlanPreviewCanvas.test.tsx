import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, waitFor } from "@testing-library/react";
import { FloorPlanPreviewCanvas } from "@/features/designer/FloorPlanPreviewCanvas";
import { DesignerExitModel, FloorPlanMetadata } from "@/lib/api/types";

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

const FLOOR_PLAN: FloorPlanMetadata = {
  id: "fp-canvas",
  exits: [],
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

const EXITS: DesignerExitModel[] = [
  {
    id: "exit-a",
    name: "Exit A",
    x: 50,
    y: 50,
    z: 50,
    width: 2,
    capacity: 100,
    source: "manual",
  },
];

describe("FloorPlanPreviewCanvas", () => {
  beforeEach(() => {
    installCanvasViewport();
  });

  it("selects the nearest existing exit before creating a new one", async () => {
    const onPlaceExit = vi.fn();
    const onSelectedExitIdChange = vi.fn();
    const onSelectedExitPointsChange = vi.fn();

    const { container } = render(
      <FloorPlanPreviewCanvas
        floorPlan={FLOOR_PLAN}
        displayExits={EXITS}
        enableGrid
        enableExitPlacement
        onPlaceExit={onPlaceExit}
        onSelectedExitIdChange={onSelectedExitIdChange}
        onSelectedExitPointsChange={onSelectedExitPointsChange}
      />,
    );

    const canvas = container.querySelector("canvas");
    expect(canvas).not.toBeNull();

    await waitFor(() => {
      expect(canvas?.width).toBeGreaterThan(0);
    });

    fireEvent.click(canvas!, { clientX: 320, clientY: 240 });

    expect(onSelectedExitIdChange).toHaveBeenCalledWith("exit-a");
    expect(onPlaceExit).not.toHaveBeenCalled();
    expect(onSelectedExitPointsChange).toHaveBeenCalledWith([{ x: 50, y: 50 }]);
  });

  it("creates a new exit on empty grid clicks", async () => {
    const onPlaceExit = vi.fn();
    const onSelectedExitIdChange = vi.fn();
    const onSelectedExitPointsChange = vi.fn();

    const { container } = render(
      <FloorPlanPreviewCanvas
        floorPlan={FLOOR_PLAN}
        displayExits={EXITS}
        enableGrid
        enableExitPlacement
        onPlaceExit={onPlaceExit}
        onSelectedExitIdChange={onSelectedExitIdChange}
        onSelectedExitPointsChange={onSelectedExitPointsChange}
      />,
    );

    const canvas = container.querySelector("canvas");
    expect(canvas).not.toBeNull();

    await waitFor(() => {
      expect(canvas?.width).toBeGreaterThan(0);
    });

    fireEvent.click(canvas!, { clientX: 500, clientY: 100 });

    expect(onPlaceExit).toHaveBeenCalledWith({ x: 80, y: 80 });
    expect(onSelectedExitIdChange).not.toHaveBeenCalled();
    expect(onSelectedExitPointsChange).toHaveBeenCalledWith([{ x: 80, y: 80 }]);
  });

  it("does not select or create exits after a drag pan", async () => {
    const onPlaceExit = vi.fn();
    const onSelectedExitIdChange = vi.fn();
    const onSelectedExitPointsChange = vi.fn();

    const { container } = render(
      <FloorPlanPreviewCanvas
        floorPlan={FLOOR_PLAN}
        displayExits={EXITS}
        enableGrid
        enableExitPlacement
        onPlaceExit={onPlaceExit}
        onSelectedExitIdChange={onSelectedExitIdChange}
        onSelectedExitPointsChange={onSelectedExitPointsChange}
      />,
    );

    const canvas = container.querySelector("canvas");
    expect(canvas).not.toBeNull();

    await waitFor(() => {
      expect(canvas?.width).toBeGreaterThan(0);
    });

    fireEvent.pointerDown(canvas!, { pointerId: 1, button: 0, clientX: 200, clientY: 200 });
    fireEvent.pointerMove(canvas!, { pointerId: 1, clientX: 220, clientY: 220 });
    fireEvent.pointerUp(canvas!, { pointerId: 1, clientX: 220, clientY: 220 });
    fireEvent.click(canvas!, { clientX: 220, clientY: 220 });

    expect(onPlaceExit).not.toHaveBeenCalled();
    expect(onSelectedExitIdChange).not.toHaveBeenCalled();
    expect(onSelectedExitPointsChange).not.toHaveBeenCalled();
  });
});
