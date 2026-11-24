import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  webServer: {
    command: 'npm run docs:build && npm run docs:dev',
    port: 4175,
    reuseExistingServer: !process.env.CI,
  },
});
