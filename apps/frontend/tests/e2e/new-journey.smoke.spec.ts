import { expect, test } from "@playwright/test";
import { installPeopleFlowApiMocks } from "./mockApi";

test("experiments launches a background benchmark job and operations enforces admin gating", async ({ page }) => {
  const apiState = await installPeopleFlowApiMocks(page);

  await page.goto("/experiments");
  await expect(page.getByRole("heading", { name: /Research Execution Console/i })).toBeVisible();

  await page.getByRole("button", { name: "Benchmark" }).click();
  await page.getByRole("button", { name: /Run corridor/i }).click();

  await expect(page.getByRole("heading", { name: /Benchmark corridor/i }).first()).toBeVisible();
  await expect(page.getByText(new RegExp(apiState.benchmarkJobId, "i")).first()).toBeVisible();
  await expect(page.getByText(/Paper Suite Alpha/i).first()).toBeVisible();

  await page.goto("/operations");
  await expect(page.getByRole("heading", { name: /Backend Parity Control Surface/i })).toBeVisible();

  await page.getByRole("button", { name: /Batches/i }).first().click();
  await page.getByRole("button", { name: /POST start-batch/i }).click();

  await expect(page.getByRole("heading", { name: /Admin key required/i })).toBeVisible();
  await page.getByLabel(/Admin key/i).fill(apiState.adminKey);
  await page.getByRole("button", { name: /Save for session/i }).click();

  await page.getByRole("button", { name: /POST start-batch/i }).click();
  await expect(page.getByText(/batch-smoke/i)).toBeVisible();
});
