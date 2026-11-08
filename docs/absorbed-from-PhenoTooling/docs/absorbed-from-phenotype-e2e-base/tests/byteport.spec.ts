import { test, expect } from "@playwright/test";

/**
 * BytePort landing page E2E test.
 * Verifies the hero CTA, GitHub stats, and footer render correctly.
 */
test.describe("BytePort landing page", () => {
  test("hero CTA is visible and links to GitHub", async ({ page }) => {
    await page.goto("/");

    const cta = page.getByRole("link", { name: /view on github/i });
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute("href", /github\.com/);
  });

  test("GitHub stats card renders", async ({ page }) => {
    await page.goto("/");

    // The GitHubStats component should render with stars/forks
    const stats = page.getByTestId("github-stats");
    await expect(stats).toBeVisible();
  });

  test("footer has the current year", async ({ page }) => {
    await page.goto("/");
    const footer = page.locator("footer");
    const year = new Date().getFullYear().toString();
    await expect(footer).toContainText(year);
  });
});
