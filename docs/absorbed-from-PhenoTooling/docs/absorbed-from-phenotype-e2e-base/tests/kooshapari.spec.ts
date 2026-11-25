import { expect, test } from "@playwright/test";

/**
 * Kooshapari (root) landing page E2E test.
 * Verifies the hero CTA, footer, and nav links.
 */
test.describe("Kooshapari landing page", () => {
	test("hero CTA is visible and links to GitHub", async ({ page }) => {
		await page.goto("/");

		const cta = page.getByRole("link", { name: /view on github/i });
		await expect(cta).toBeVisible();
		await expect(cta).toHaveAttribute("href", /github\.com/);
	});

	test("footer has the current year", async ({ page }) => {
		await page.goto("/");
		const footer = page.locator("footer");
		const year = new Date().getFullYear().toString();
		await expect(footer).toContainText(year);
	});

	test("nav links render and point to valid anchors", async ({ page }) => {
		await page.goto("/");

		const nav = page.locator("header nav");
		await expect(nav).toBeVisible();
		const links = nav.getByRole("link");
		await expect(links.first()).toBeVisible();
	});
});
