import { test, expect } from '@playwright/test'

test('homepage exposes the primary docs routes', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Cross-Cutting xDD Utilities')).toBeVisible()
  await expect(page.locator('#VPContent').getByRole('link', { name: 'Guide' })).toBeVisible()
  await expect(page.locator('#VPContent').getByRole('link', { name: 'Reference' }).first()).toBeVisible()
})

for (const [route, heading] of [
  ['/guide/', 'Guide'],
  ['/reference/', 'Reference'],
  ['/reference/architecture/', 'Architecture'],
  ['/reference/property-testing/', 'Property Testing'],
  ['/reference/contract-testing/', 'Contract Testing'],
  ['/reference/mutation-testing/', 'Mutation Testing'],
  ['/reference/specdd/', 'SpecDD']
]) {
  test(`core public routes resolve: ${route}`, async ({ page }) => {
    await page.goto(route)
    await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible()
  })
}

for (const route of ['/zh-CN/', '/zh-TW/', '/fa/', '/fa-Latn/']) {
  test(`locale landing pages resolve: ${route}`, async ({ page }) => {
    await page.goto(route)
    await expect(page.locator('h1').first()).toBeVisible()
  })
}
