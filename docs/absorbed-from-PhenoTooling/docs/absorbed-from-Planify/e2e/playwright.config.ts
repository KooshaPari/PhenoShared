/**
 * Copyright (c) 2025-present AgilePlus
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * E2E Test Configuration for AgilePlus Agent and Worktrees modules.
 *
 * Prerequisites:
 *   1. Start Plane: bun --filter=web dev --port 3000
 *   2. Start API:   cd apps/api && source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000
 *
 * Run tests:
 *   bun playwright test
 *   bun playwright test e2e/tests/agents
 *   bun playwright test e2e/tests/worktrees
 *   bun playwright test --headed
 *   bun playwright test --debug
 *
 * Environment variables (set in .env or shell):
 *   E2E_BASE_URL   - Plane frontend URL (default: http://localhost:3000)
 *   E2E_API_URL    - Plane API URL (default: http://localhost:8000)
 *   E2E_WORKSPACE  - Workspace slug (default: agileplus)
 *   E2E_ADMIN_EMAIL
 *   E2E_ADMIN_PASS
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e/tests",
  ignoreWebProcesses: ["**/node_modules/**", "**/.git/**", "**/dist/**"],

  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "e2e/test-results/html" }],
    ["json", { outputFile: "e2e/test-results/results.json" }],
  ],

  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    ignoreHTTPSErrors: true,
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
    { name: "chromium-mobile", use: { ...devices["Pixel 5"] } },
  ],

  outputDir: "e2e/test-results",
});
