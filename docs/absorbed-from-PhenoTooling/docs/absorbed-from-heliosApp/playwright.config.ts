import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "apps/desktop/tests/e2e",
  timeout: 30000,
  use: {
    headless: true,
  },
});
