import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:4197', channel: 'chrome', trace: 'retain-on-failure' },
  outputDir: 'output/playwright/acceptance',
  webServer: { command: 'node scripts/preview-server.js', url: 'http://127.0.0.1:4197', reuseExistingServer: false },
});
