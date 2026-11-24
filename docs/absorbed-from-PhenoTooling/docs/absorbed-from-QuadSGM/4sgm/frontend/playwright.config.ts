import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for 4SGM Chat Widget E2E Tests
 *
 * Tests:
 * - Chat widget user interactions
 * - Message sending and receiving
 * - SSE streaming
 * - Error handling
 * - Escalation flows
 * - Responsiveness
 */

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.ts',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use */
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/results.xml' }],
    ['list']
  ],

  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: process.env.BASE_URL || 'http://localhost:3100',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    /* Test against mobile viewports */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev -- -p 3100',
    url: process.env.BASE_URL || 'http://localhost:3100',
    reuseExistingServer: false,
    timeout: 120 * 1000,
  },

  /* Timeout settings */
  timeout: 30 * 1000,
  expect: {
    timeout: 5000,
  },
});
