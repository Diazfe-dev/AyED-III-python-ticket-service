import { defineConfig, devices } from "@playwright/test";

const port = process.env.E2E_PORT ?? "5051";
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "tests/ui/e2e",
  testMatch: "**/*.spec.js",
  retries: 0,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  use: { baseURL },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "python tests/ui/e2e/server.py",
    env: { PYTHONPATH: ".", E2E_PORT: port },
    url: `${baseURL}/health`,
    reuseExistingServer: !process.env.CI,
  },
});
