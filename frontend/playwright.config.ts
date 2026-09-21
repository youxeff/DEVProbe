import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch:
    process.env.E2E_AUTH === "true"
      ? "account.e2e.ts"
      : ["workflow.e2e.ts", "polling.e2e.ts"],
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    launchOptions: process.env.CHROMIUM_PATH
      ? {
          executablePath: process.env.CHROMIUM_PATH,
          timeout: 10000,
          args: [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--single-process",
            "--no-zygote",
            "--use-gl=angle",
            "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
            "--in-process-gpu",
          ],
        }
      : undefined,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `cd ../backend && ${process.env.DEVPROBE_PYTHON || "python"} -m alembic upgrade head && ${process.env.DEVPROBE_PYTHON || "python"} -m uvicorn tests.e2e_server:app --host 127.0.0.1 --port 8100 --no-access-log`,
      url: "http://127.0.0.1:8100/health",
      env: {
        DATABASE_URL:
          process.env.E2E_AUTH === "true"
            ? "sqlite:///./e2e-auth.db"
            : "sqlite:///./e2e.db",
        PYTHONPATH: ".",
        AUTH_ENABLED: process.env.E2E_AUTH || "false",
        PUBLIC_URL: "http://127.0.0.1:3100",
        SCAN_MODE: "sync",
      },
      reuseExistingServer: false,
    },
    {
      command: "npm run start -- --hostname 127.0.0.1 --port 3100",
      url: "http://127.0.0.1:3100",
      reuseExistingServer: false,
    },
  ],
  timeout: 60000,
});
