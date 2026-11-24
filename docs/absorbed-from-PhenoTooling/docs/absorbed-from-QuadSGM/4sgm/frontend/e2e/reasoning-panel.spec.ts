import { test, expect } from '@playwright/test';


// Helper to open the global chat widget
async function openChatWidget(page: any) {
  const chatWindow = page.locator('text=4SGM Support').first();
  if (await chatWindow.isVisible()) {
    return;
  }

  const chatButton = page.locator('button[aria-label="Open chat"]').first();
  await chatButton.waitFor({ state: 'visible', timeout: 5000 });
  await chatButton.click();

  await chatWindow.waitFor({ state: 'visible', timeout: 5000 });
}

// Helper to open the reasoning panel from the chat header
async function openReasoningPanel(page: any) {
  await openChatWidget(page);

  const reasoningButton = page
    .locator('button[aria-label="Open reasoning trail"]').first();
  await reasoningButton.waitFor({ state: 'visible', timeout: 5000 });
  await reasoningButton.click();

  const panelHeader = page.locator('text=Reasoning Trail').first();
  await panelHeader.waitFor({ state: 'visible', timeout: 5000 });
}

test.describe('Reasoning Panel E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('opens reasoning panel from chat widget header', async ({ page }) => {
    await openReasoningPanel(page);

    const header = page.locator('text=Reasoning Trail').first();
    await expect(header).toBeVisible();
  });

  test('shows empty state before reasoning events stream in', async ({ page }) => {
    await openReasoningPanel(page);

    const expandButton = page
      .locator('button[aria-label="Expand reasoning panel"]').first();
    if (await expandButton.isVisible()) {
      await expandButton.click();
    }

    const emptyState = page.getByText('No reasoning steps streamed yet.');
    await expect(emptyState).toBeVisible();
  });

  test('allows collapsing and expanding reasoning content', async ({ page }) => {
    await openReasoningPanel(page);

    const expandButton = page
      .locator('button[aria-label="Expand reasoning panel"]').first();
    if (await expandButton.isVisible()) {
      await expandButton.click();
    }

    const content = page.getByText('No reasoning steps streamed yet.');
    await expect(content).toBeVisible();

    const collapseButton = page
      .locator('button[aria-label="Collapse reasoning panel"]').first();
    await collapseButton.click();
    await expect(content).toBeHidden();
  });

  test('can be closed and reopened without breaking chat', async ({ page }) => {
    await openReasoningPanel(page);

    const closeButton = page
      .locator('button[aria-label="Close reasoning panel"]').first();
    await closeButton.click();

    await expect(
      page.locator('text=Reasoning Trail').first(),
    ).not.toBeVisible();

    // Reopen panel
    await openReasoningPanel(page);
    await expect(
      page.locator('text=Reasoning Trail').first(),
    ).toBeVisible();
  });

  test('reasoning panel is responsive on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await openReasoningPanel(page);

    const header = page.locator('text=Reasoning Trail').first();
    await expect(header).toBeVisible();
  });
});
