import { expect, test } from "@playwright/test";

const liveModeEnabled = process.env.PEOPLEFLOW_E2E_LIVE === "1";

test.describe("live backend smoke", () => {
  test.skip(!liveModeEnabled, "Live backend smoke is disabled.");

  test("submits a real background benchmark through the web UI", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Research-Grade Evacuation Intelligence Workspace/i })).toBeVisible();

    await page.goto("/experiments");
    await expect(page.getByRole("heading", { name: /Research Execution Console/i })).toBeVisible();

    await page.getByRole("button", { name: "Benchmark" }).click();

    const responsePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v2/experiments/benchmarks/corridor/run") &&
        response.request().method() === "POST",
    );

    await page.getByRole("button", { name: /Run corridor/i }).click();

    const response = await responsePromise;
    expect(response.status()).toBe(202);

    const payload = (await response.json()) as { data?: { job_id?: string }; job_id?: string };
    const jobId = String(payload.data?.job_id ?? payload.job_id ?? "");
    expect(jobId).toMatch(/^expjob-/);

    await expect(page.getByText(new RegExp(jobId, "i")).first()).toBeVisible({ timeout: 15_000 });
  });
});
