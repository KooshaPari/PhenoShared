import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: ["a11y.spec.js", "responsive.spec.js", "visual.spec.js"],
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  webServer: process.env.VISUAL_BASE_URL
    ? undefined
    : {
        command: "node ./serve-viewer.mjs",
        url: "http://127.0.0.1:4173",
        reuseExistingServer: !process.env.CI,
        timeout: 30_000,
      },
  use: {
    baseURL: process.env.VISUAL_BASE_URL ?? "http://127.0.0.1:4173",
    viewport: { width: 1280, height: 720 },
    colorScheme: "dark",
    reducedMotion: "reduce",
  },
  snapshotPathTemplate: "../golden/{arg}{ext}",
});
