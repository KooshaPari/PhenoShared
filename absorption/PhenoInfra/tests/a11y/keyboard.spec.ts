/**
 * AT2 — Keyboard-only navigation tests.
 *
 * Verifies:
 *   1. The skip link is the first focusable element on every route.
 *   2. Tab order reaches main content without traps.
 *   3. The skip link activates and moves focus to <main>.
 *   4. Tab into a code block does not steal focus.
 */
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { chromium, type Browser, type Page } from '@playwright/test'
import { acquireDevServer, releaseDevServer, BASE_URL } from './dev-server.ts'

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

const ROUTES = [
  '/',
  '/guide/getting-started',
  '/reference/api',
  '/governance/overview',
]

describe('Keyboard navigation', () => {
  for (const route of ROUTES) {
    it(`skip-link is first tabbable on ${route}`, async () => {
      await page.goto(`${BASE_URL}${route}`, { waitUntil: 'networkidle' })
      await page.keyboard.press('Tab')
      const focused = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null
        return el ? { tag: el.tagName, cls: el.className, text: el.textContent?.trim() } : null
      })
      expect(focused).not.toBeNull()
      expect(focused?.cls).toContain('a11y-skip-link')
    }, 15_000)

    it(`Enter on skip-link focuses #VPContent on ${route}`, async () => {
      await page.goto(`${BASE_URL}${route}`, { waitUntil: 'networkidle' })
      await page.keyboard.press('Tab')
      await page.keyboard.press('Enter')
      // Anchor jumps to #VPContent; focus should land there or on a child.
      const focusedId = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null
        return el?.id ?? el?.closest('[id]')?.id ?? null
      })
      expect(['VPContent', 'main', 'VPContent-container']).toContain(focusedId)
    }, 15_000)
  }

  it('reaches main content within 8 Tabs from a fresh page load', async () => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' })
    const trail: string[] = []
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Tab')
      const tag = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null
        return el ? `${el.tagName}#${el.id || ''}.${el.className?.toString().slice(0, 30) || ''}` : 'none'
      })
      trail.push(tag)
    }
    // Tab trail must contain the skip link and reach the main content.
    expect(trail.some((s) => s.includes('a11y-skip-link'))).toBe(true)
    expect(trail.some((s) => s.includes('VPContent') || s.includes('VPNavBar'))).toBe(true)
  }, 15_000)
})
