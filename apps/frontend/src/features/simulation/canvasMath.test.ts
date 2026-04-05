import { describe, expect, it } from "vitest";
import { deriveBounds, projectPoint } from "@/features/simulation/canvasMath";

describe("canvasMath", () => {
  it("derives bounds from points", () => {
    const bounds = deriveBounds([
      { x: -10, y: 2 },
      { x: 20, y: 15 },
    ]);

    expect(bounds.minX).toBe(-10);
    expect(bounds.maxX).toBe(20);
    expect(bounds.minY).toBe(2);
    expect(bounds.maxY).toBe(15);
  });

  it("projects points into canvas coordinates", () => {
    const point = projectPoint({ x: 5, y: 5 }, { minX: 0, maxX: 10, minY: 0, maxY: 10 }, 200, 200, 20);
    expect(point.x).toBeGreaterThan(20);
    expect(point.y).toBeGreaterThan(20);
    expect(point.y).toBeLessThan(180);
  });
});
