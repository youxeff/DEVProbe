import { test, expect } from "@playwright/test";
test("scan page polls pending and running states until completion", async ({
  page,
}) => {
  const response = await page.request.post("/api/backend/scans", {
    data: {
      repo_url: "https://github.com/devprobe-fixtures/review-lab",
      pr_number: 12,
    },
  });
  const { scan_id } = await response.json();
  let reads = 0;
  await page.route(`**/api/backend/scans/${scan_id}`, async (route) => {
    const result = await route.fetch();
    const data = await result.json();
    reads++;
    await route.fulfill({
      response: result,
      json: {
        ...data,
        status: reads === 1 ? "pending" : reads === 2 ? "running" : data.status,
      },
    });
  });
  await page.goto(`/scans/${scan_id}`);
  await expect(
    page.getByRole("heading", { name: "Your scan is queued" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Review findings" }),
  ).toBeVisible({ timeout: 10000 });
  expect(reads).toBeGreaterThanOrEqual(3);
});
