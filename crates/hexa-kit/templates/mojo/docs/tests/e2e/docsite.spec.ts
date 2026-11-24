import { expect, test } from '@playwright/test';

const routes = ['/', '/BRANCH_PROTECTION', '/UPGRADE', '/zh-CN/', '/zh-TW/', '/fa/', '/fa-Latn/'];

for (const route of routes) {
  test(`loads ${route}`, async ({ page }) => {
    await page.goto(route);
    await expect(page).toHaveTitle(/template-lang-mojo|Docs/);
    await expect(page.locator('body')).toContainText('Docs');
  });
}
