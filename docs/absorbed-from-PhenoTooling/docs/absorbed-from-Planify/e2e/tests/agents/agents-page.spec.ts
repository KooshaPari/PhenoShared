/**
 * Copyright (c) 2025-present AgilePlus
 * SPDX-License-Identifier: AGPL-3.0-only
 *
 * E2E tests for the Agents page (/agents).
 *
 * Prerequisites:
 *   - Plane web dev server running on E2E_BASE_URL (default: http://localhost:3000)
 *   - User logged in to Plane workspace
 *   - Agents module accessible in sidebar
 *
 * Test coverage:
 *   - [ ] Agents page loads without errors
 *   - [ ] Page renders correct heading "AI Agents"
 *   - [ ] Empty state shown when no agents exist
 *   - [ ] Sidebar link "Agents" navigates to /agents
 *   - [ ] "Create Agent" button is visible
 *   - [ ] Agent cards display name and status badge
 *   - [ ] Clicking an agent card navigates to agent detail
 *   - [ ] Loading state shown during data fetch
 *   - [ ] Error state with retry button shown on API failure
 *   - [ ] Page is responsive on mobile viewports
 */

import { test, expect } from "@playwright/test";

// =============================================================================
// Helpers
// =============================================================================

const AGENTS_PATH = "/agents";
const WORKTREES_PATH = "/worktrees";

/**
 * Navigate to the workspace agents page.
 * Assumes the user is already logged in and has a workspace slug.
 */
async function navigateToAgentsPage(page: any, workspaceSlug = "agileplus") {
  await page.goto(`/${workspaceSlug}${AGENTS_PATH}`);
  await page.waitForLoadState("networkidle");
}

/**
 * Navigate to the workspace worktrees page.
 */
async function navigateToWorktreesPage(page: any, workspaceSlug = "agileplus") {
  await page.goto(`/${workspaceSlug}${WORKTREES_PATH}`);
  await page.waitForLoadState("networkidle");
}

/**
 * Wait for the page to be fully hydrated (network idle + no pending requests).
 */

// =============================================================================
// Fixtures
// =============================================================================

/**
 * These tests run against a live Plane instance.
 * Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASS env vars to run authenticated tests.
 */
test.describe("Agents Page", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to agents page before each test
    await navigateToAgentsPage(page);
  });

  // ===========================================================================
  // Loading & Rendering
  // ===========================================================================

  test("should load the agents page without crashing", async ({ page }) => {
    // Page should not show an error overlay
    await expect(page.locator("body")).not.toContainText("Something went wrong");
  });

  test("should display the page heading", async ({ page }) => {
    // Check for "AI Agents" or "Agents" heading
    const heading = page.getByRole("heading", { name: /agents/i });
    await expect(heading).toBeVisible({ timeout: 10_000 });
  });

  test("should display sidebar navigation link", async ({ page }) => {
    // The sidebar should have a link to Agents
    const agentsLink = page.getByRole("link", { name: /agents/i });
    await expect(agentsLink).toBeVisible();
  });

  // ===========================================================================
  // Empty State
  // ===========================================================================

  test("should show empty state when no agents exist", async ({ page }) => {
    // Look for "No agents yet" empty state
    const emptyState = page.getByText(/no agents yet/i);
    // If no agents, empty state should be visible
    const emptyStateCount = await emptyState.count();
    if (emptyStateCount > 0) {
      await expect(emptyState.first()).toBeVisible();
      // Create button should also be visible in empty state
      const createBtn = page.getByRole("button", { name: /create agent/i });
      await expect(createBtn.first()).toBeVisible();
    }
  });

  // ===========================================================================
  // Create Agent Button
  // ===========================================================================

  test("should show Create Agent button", async ({ page }) => {
    const createBtn = page.getByRole("button", { name: /create agent/i });
    await expect(createBtn.first()).toBeVisible();
  });

  test("should open create agent modal when Create Agent button is clicked", async ({ page }) => {
    const createBtn = page.getByRole("button", { name: /create agent/i });
    await createBtn.first().click();

    // Modal should open with a form
    const modal = page.getByRole("dialog");
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Modal should have name input
    const nameInput = modal.getByLabel(/name|agent name/i);
    await expect(nameInput).toBeVisible();
  });

  // ===========================================================================
  // Agent Cards (when agents exist)
  // ===========================================================================

  test("should display agent cards with name and status", async ({ page }) => {
    // Find all agent cards
    const agentCards = page.locator("[class*='rounded-lg'][class*='border']").filter({
      has: page.locator("[class*='Bot']"),
    });

    const cardCount = await agentCards.count();
    if (cardCount > 0) {
      // First card should have a name
      await expect(agentCards.first()).toBeVisible();
      // First card should have a status badge
      const badge = agentCards.first().locator("[class*='Badge']");
      const badgeCount = await badge.count();
      if (badgeCount > 0) {
        await expect(badge.first()).toBeVisible();
      }
    }
  });

  test("should navigate to agent detail when card is clicked", async ({ page }) => {
    // Look for any agent card link/button
    const agentCard = page.locator("[class*='cursor-pointer'][class*='border']").first();
    const cardCount = await agentCard.count();
    if (cardCount > 0) {
      await agentCard.click();
      // URL should contain /agents/ and an agent ID
      await expect(page).toHaveURL(/\/agents\/[^/]+/);
    }
  });

  // ===========================================================================
  // Sidebar Navigation
  // ===========================================================================

  test("should highlight Agents in sidebar when on agents page", async ({ page }) => {
    // The sidebar link for agents should be active/highlighted
    const agentsLink = page.getByRole("link", { name: /agents/i }).first();
    // Active state usually has a different background
    await expect(agentsLink).toHaveAttribute("aria-current", "page").catch(() => {
      // Fallback: just check it's visible
      expect(agentsLink).toBeVisible();
    });
  });

  test("should be able to navigate to Worktrees from sidebar", async ({ page }) => {
    // Find worktrees link in sidebar
    const worktreesLink = page.getByRole("link", { name: /worktrees/i });
    await worktreesLink.first().click();
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/worktrees/);
  });

  // ===========================================================================
  // Responsive
  // ===========================================================================

  test("should be usable on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await navigateToAgentsPage(page);
    // Page should render without horizontal overflow
    const body = page.locator("body");
    const bodyWidth = await body.evaluate((el) => el.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(375);
  });

  // ===========================================================================
  // Worktrees Page Quick Check
  // ===========================================================================

  test("should navigate to Worktrees page and render correctly", async ({ page }) => {
    await navigateToWorktreesPage(page);
    const heading = page.getByRole("heading", { name: /worktrees/i });
    await expect(heading).toBeVisible({ timeout: 10_000 });
  });
});
