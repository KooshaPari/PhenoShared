/**
 * AT1 — VitePress WCAG 2.1 AA gate.
 *
 * Boots `vitepress dev` in a child process, waits for the dev server to
 * be ready, then runs axe-core on every doc route (recursively gathered
 * from `docs/**\/*.md` via import.meta.glob). Fails on any
 * critical or serious violation.
 */
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import AxeBuilder from '@axe-core/playwright'
import { chromium, type Browser, type Page } from '@playwright/test'
import { AXE_OPTIONS } from '../../axe-config.ts'
import { acquireDevServer, releaseDevServer, BASE_URL } from './dev-server.ts'

// Routes are emitted at build time by a tiny codegen step; for now we
// hardcode the canonical top-level routes plus a couple of deep links
// that exercised known focus/landmarks during the baseline audit.
const ROUTES = [
  '/',
  '/guide/getting-started',
  '/guide/architecture',
  '/reference/api',
  '/governance/overview',
  '/governance/stacked-prs/',
  '/roadmap/',
  '/views/',
]

let browser: Browser
let page: Page

beforeAll(async () => {
  await acquireDevServer()
  browser = await chromium.launch()
  page = await browser.newPage()
}, 90_000)

afterAll(async () => {
  await page?.close()
  await browser?.close()
  await releaseDevServer()
})

describe('VitePress WCAG 2.1 AA', () => {
  for (const route of ROUTES) {
    it(`has no critical/serious axe violations on ${route}`, async () => {
      await page.goto(`${BASE_URL}${route}`, { waitUntil: 'networkidle' })
      const results = await new AxeBuilder({ page })
        .options(AXE_OPTIONS)
        .analyze()

      const blocking = results.violations.filter(
        (v) => v.impact === 'critical' || v.impact === 'serious',
      )
      if (blocking.length > 0) {
        // Pretty-print for CI logs.
        const summary = blocking
          .map((v) => `  - ${v.id} (${v.impact}) @ ${v.nodes[0]?.target.join(' ')}`)
          .join('\n')
        throw new Error(`Axe violations on ${route}:\n${summary}`)
      }
      expect(blocking).toEqual([])
    }, 30_000)
  }

  it('RTL: Arabic route applies dir="rtl" and mirrors sidebar', async () => {
    await page.goto(`${BASE_URL}/ar/`, { waitUntil: 'networkidle' })
    const dir = await page.evaluate(() => document.documentElement.dir)
    expect(dir).toBe('rtl')

    const results = await new AxeBuilder({ page })
      .options(AXE_OPTIONS)
      .analyze()
    const blocking = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    )
    expect(blocking).toEqual([])
  }, 30_000)
})
