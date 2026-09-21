import { test, expect } from "@playwright/test";
test("repository to PR to persisted scan and issue filters", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("GitHub repository URL")
    .fill("https://github.com/devprobe-fixtures/review-lab");
  await page.getByRole("button", { name: "Analyze repository" }).click();
  await expect(page).toHaveURL(/repositories\/\d+/);
  await page
    .getByRole("link", { name: /Tighten authentication validation/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Changed files" }),
  ).toBeVisible();
  await expect(page.getByText("src/auth.py")).toBeVisible();
  await page.getByRole("button", { name: "Analyze PR", exact: true }).click();
  await expect(page).toHaveURL(/scans\/\d+/);
  await expect(page.getByText("completed", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Possible hardcoded sensitive value", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Severity", { exact: true }).selectOption("high");
  await expect(
    page.getByText("Code changed without", { exact: false }),
  ).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByText("Code changed without", { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole("heading", {name:"Suggested tests"})).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/scan-result.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Back to repository" }).click();
  await expect(
    page.getByRole("heading", { name: "Recent scans" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Scan #/ }).first(),
  ).toBeVisible();
});
test("repository errors are useful", async ({ page }) => {
  await page.goto("/");
  await page
    .getByLabel("GitHub repository URL")
    .fill("https://gitlab.com/team/project");
  await page.getByRole("button", { name: "Analyze repository" }).click();
  await expect(page.locator("#repo-error")).toContainText("Enter a GitHub");
  await page
    .getByLabel("GitHub repository URL")
    .fill("https://github.com/missing/project");
  await page.getByRole("button", { name: "Analyze repository" }).click();
  await expect(page.locator("#repo-error")).toContainText("not found");
});
test("mobile form and navigation remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByLabel("GitHub repository URL")).toBeVisible();
  await page.getByRole("link", { name: "How it works" }).click();
  await expect(
    page.getByRole("heading", { name: "Built for a thoughtful review." }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});
