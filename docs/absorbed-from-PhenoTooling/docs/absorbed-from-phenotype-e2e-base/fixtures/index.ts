/**
 * Shared test fixtures for the Phenotype E2E suite.
 */

import { test as base, type Page } from "@playwright/test";

/**
 * Extended test fixture providing:
 * - `page`: Playwright page with a known-good landing URL
 * - `gotoLanding`: helper that navigates to one of the canonical landing pages
 */
export const test = base.extend<{
  gotoLanding: (site?: "byteport" | "phenokits" | "agileplus" | "projects") => Promise<void>;
}>({
  gotoLanding: async ({ page }, use) => {
    await use(async (site = "byteport") => {
      const urls: Record<string, string> = {
        byteport: "https://byteport.kooshapari.com",
        phenokits: "https://phenokits.kooshapari.com",
        agileplus: "https://agileplus.kooshapari.com",
        projects: "https://projects.kooshapari.com",
      };
      await page.goto(urls[site] ?? urls.byteport!);
    });
  },
});

export { expect, type Page } from "@playwright/test";
