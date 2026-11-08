import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for the Phenotype fleet E2E suite.
 *
 * Targets the deployed landing pages at kooshapari.com subdomains.
 * Set BASE_URL env var to test against a local stack instead.
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [["html", { open: "never" }], ["list"]]
    : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "https://byteport.kooshapari.com",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command: "bun run dev",
        url: "http://localhost:4321",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
