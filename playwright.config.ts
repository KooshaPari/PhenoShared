import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:4173/handbook/",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "bunx vitepress preview docs --port 4173 --host 127.0.0.1",
    url: "http://127.0.0.1:4173/handbook/",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
