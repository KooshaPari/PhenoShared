import { expect, test } from '@playwright/test';

const routes = ['/', '/adr/ADR-001-hexagonal-architecture', '/zh-CN/', '/zh-TW/', '/fa/', '/fa-Latn/'];

for (const route of routes) {
  test(`loads ${route}`, async ({ page }) => {
    await page.goto(route);
    await expect(page).toHaveTitle(/go-hex|Docs/);
    await expect(page.locator('body')).toContainText('Docs');
  });
}
