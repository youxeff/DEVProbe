import { test, expect } from "@playwright/test";
test("account registration, tenant-owned scan, settings and organization isolation", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Welcome to DevProbe" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "New here? Create an account" })
    .click();
  await page.getByLabel("Your name").fill("Browser Tester");
  await page
    .getByLabel("Organization name", { exact: true })
    .fill("Review Team");
  await page
    .getByLabel("Email", { exact: true })
    .fill(`browser-${Date.now()}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("browser-fixture-password");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page.getByLabel("GitHub repository URL")).toBeVisible();
  await page
    .getByLabel("GitHub repository URL")
    .fill("https://github.com/devprobe-fixtures/review-lab");
  await page.getByRole("button", { name: "Analyze repository" }).click();
  await page
    .getByRole("link", { name: /Tighten authentication validation/ })
    .click();
  await page.getByRole("button", { name: "Analyze PR", exact: true }).click();
  await expect(page.getByText("completed", { exact: true })).toBeVisible();
  const scanUrl = page.url();
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Make DevProbe yours." }),
  ).toBeVisible();
  await expect(page.getByText("1 / 50", { exact: true })).toBeVisible();
  await expect(page.getByText("scan · requested")).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/settings.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.getByLabel("New organization name").fill("Isolated Workspace");
  await page
    .getByRole("button", { name: "Create organization", exact: true })
    .click();
  await expect(page.getByLabel("Active organization")).toHaveValue(/\d+/);
  await expect(
    page.getByLabel("Active organization").locator("option:checked"),
  ).toHaveText("Isolated Workspace");
  await page.goto(scanUrl);
  await expect(
    page.getByText("Scan not found.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome to DevProbe" }),
  ).toBeVisible();
});
