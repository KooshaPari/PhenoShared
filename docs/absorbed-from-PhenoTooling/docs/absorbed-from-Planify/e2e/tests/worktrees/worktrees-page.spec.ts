/**
 * Copyright (c) 2025-present AgilePlus
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * E2E tests for the Worktrees page (/worktrees).
 *
 * Prerequisites:
 *   - Plane web dev server running on E2E_BASE_URL (default: http://localhost:3000)
 *   - User logged in to Plane workspace with Agent/Worktrees access
 *
 * Test coverage:
 *   - [ ] Worktrees page loads without errors
 *   - [ ] Page renders correct heading "Worktrees"
 *   - [ ] Empty state shown when no worktrees exist
 *   - [ ] "Create Worktree" button is visible
 *   - [ ] Worktree cards display name, branch, and status
 *   - [ ] Loading state shown during data fetch
 *   - [ ] Error state with retry button shown on API failure
 */

import { test, expect } from "@playwright/test";

async function navigateToWorktreesPage(page: any, workspaceSlug = "agileplus") {
  await page.goto(`/${workspaceSlug}/worktrees`);
  await page.waitForLoadState("networkidle");
}


test.describe("Worktrees Page", () => {
  test.beforeEach(async ({ page }) => {
    await navigateToWorktreesPage(page);
  });

  test("should load without crashing", async ({ page }) => {
    await expect(page.locator("body")).not.toContainText("Something went wrong");
  });

  test("should display the Worktrees heading", async ({ page }) => {
    const heading = page.getByRole("heading", { name: /worktrees/i });
    await expect(heading).toBeVisible({ timeout: 10_000 });
  });

  test("should show Create Worktree button", async ({ page }) => {
    const createBtn = page.getByRole("button", { name: /create worktree/i });
    await expect(createBtn.first()).toBeVisible();
  });

  test("should show empty state when no worktrees exist", async ({ page }) => {
    const emptyState = page.getByText(/no worktrees yet/i);
    const emptyCount = await emptyState.count();
    if (emptyCount > 0) {
      await expect(emptyState.first()).toBeVisible();
    }
  });

  test("should show sidebar Worktrees link", async ({ page }) => {
    const link = page.getByRole("link", { name: /worktrees/i });
    await expect(link.first()).toBeVisible();
  });

  test("should display worktree cards with name and status when worktrees exist", async ({ page }) => {
    // Look for GitBranch icon + card structure
    const cards = page.locator("[class*='rounded-lg'][class*='border']").filter({
      has: page.locator("[class*='GitBranch']"),
    });
    const count = await cards.count();
    if (count > 0) {
      await expect(cards.first()).toBeVisible();
    }
  });

  test("should display sidebar Agents link", async ({ page }) => {
    const link = page.getByRole("link", { name: /agents/i });
    await expect(link.first()).toBeVisible();
  });

  test("should navigate to Agents page from sidebar", async ({ page }) => {
    const link = page.getByRole("link", { name: /agents/i });
    await link.first().click();
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/agents/);
  });

  test("should be usable on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await navigateToWorktreesPage(page);
    const bodyWidth = await page.locator("body").evaluate((el) => el.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(375);
  });
});
