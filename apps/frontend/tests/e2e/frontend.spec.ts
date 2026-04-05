import { expect, test } from "@playwright/test";
import { installPeopleFlowApiMocks } from "./mockApi";

test("core app flow smoke: home to designer to simulation to analytics", async ({ page }) => {
  await installPeopleFlowApiMocks(page);

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Research-Grade Evacuation Intelligence Workspace/i })).toBeVisible();

  await page.goto("/designer");
  await expect(page).toHaveURL(/\/designer$/);
  await expect(page.getByText(/Prepare a floor plan for simulation-ready evacuation research/i)).toBeVisible();

  await page.getByRole("button", { name: /^Upload Floor Plan$/ }).click();
  await expect(page.getByText(/Floor plan uploaded successfully/i)).toBeVisible();
  await expect(page.getByText(/E2E Research Building/i).first()).toBeVisible();

  const previewCanvas = page.locator("canvas").first();
  await expect(previewCanvas).toBeVisible();
  await previewCanvas.click({ position: { x: 220, y: 220 } });
  await expect(page.getByText(/Exit 1:/i)).toBeVisible();

  await page.goto("/simulation");
  await expect(page.getByRole("heading", { name: /Live Control Workspace/i })).toBeVisible();
  await page.getByRole("button", { name: /Start Simulation/i }).click();
  await expect(page.getByText(/Active simulation: sim-e2e/i)).toBeVisible();

  await page.goto("/analytics");
  await expect(page.getByRole("heading", { name: /Publication-Ready Results Workspace/i })).toBeVisible();
  await expect(page.getByText(/Total Agents/i)).toBeVisible();
  await expect(page.getByText(/^240$/)).toBeVisible();
});

test("route aliases stay wired to the current app shell", async ({ page }) => {
  await installPeopleFlowApiMocks(page);

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: /Research-Grade Evacuation Intelligence Workspace/i })).toBeVisible();

  await page.goto("/design");
  await expect(page).toHaveURL(/\/designer$/);
  await expect(page.getByText(/Prepare a floor plan for simulation-ready evacuation research/i)).toBeVisible();
});
