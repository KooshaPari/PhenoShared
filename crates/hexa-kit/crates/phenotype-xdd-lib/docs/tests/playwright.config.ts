import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: {
    baseURL: 'http://127.0.0.1:4174'
  },
  webServer: {
    command: 'npm run docs:dev -- --host 127.0.0.1 --port 4174',
    cwd: '..',
    port: 4174,
    reuseExistingServer: true,
    timeout: 120_000
  }
})
