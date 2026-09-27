/// <reference types="vitest" />
/**
 * Vitest config for the AT a11y baseline.
 *
 * Uses Playwright as the browser provider so test files can call
 * `chromium.launch()` and `page.goto()` directly, then run axe-core.
 * Run with: `bun run test:a11y` → `vitest run tests/a11y`.
 */
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    include: ['tests/a11y/**/*.spec.ts'],
    testTimeout: 90_000,
    hookTimeout: 90_000,
    teardownTimeout: 30_000,
    // Serialize: we boot one VitePress dev server per test file.
    fileParallelism: false,
    pool: 'forks',
    poolOptions: { forks: { singleFork: true } },
  },
})
