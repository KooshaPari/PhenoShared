import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const tabs = [
  "Bundles",
  "History",
  "Unfinished",
  "Memory",
  "Live Feed",
  "Search",
  "Timeline",
  "Replay",
];

const viewports = [
  { width: 375, height: 812 },
  { width: 768, height: 900 },
  { width: 1280, height: 720 },
];

async function waitForViewerHotkeys(page) {
  await expect(page.locator("html")).toHaveAttribute(
    "data-sl-hotkeys-ready",
    "true",
  );
}

for (const viewport of viewports) {
  test.describe(`${viewport.width}px viewport`, () => {
    test.use({ viewport });

    for (const tabName of tabs) {
      test(`${tabName} has no WCAG AA violations`, async ({ page }) => {
        await page.goto("/");
        const tab = page.getByRole("tab", { name: tabName, exact: true });
        await tab.click();
        await expect(tab).toHaveAttribute("aria-selected", "true");

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze();

        expect(results.violations).toEqual([]);
        await expect(page.getByRole("main")).toBeVisible();
        await expect(
          page.getByRole("navigation", { name: "Primary viewer navigation" }),
        ).toBeVisible();
      });
    }
  });
}

test("ARIA tabs expose state and support the standard keyboard pattern", async ({
  page,
}) => {
  await page.goto("/");
  const tablist = page.getByRole("tablist", { name: "SessionLedger views" });
  const bundles = tablist.getByRole("tab", { name: "Bundles" });
  const history = tablist.getByRole("tab", { name: "History" });
  const replay = tablist.getByRole("tab", { name: "Replay" });

  await bundles.focus();
  await page.keyboard.press("ArrowRight");
  await expect(history).toBeFocused();
  await expect(history).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("tabpanel", { name: "History" })).toBeVisible();

  await page.keyboard.press("End");
  await expect(replay).toBeFocused();
  await page.keyboard.press("Home");
  await expect(bundles).toBeFocused();
});

test("Tab order reaches active tab then active-panel controls", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Search" }).click();

  await expect(page.getByRole("tab", { name: "Search" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" }),
  ).toBeFocused();
});

test("Escape clears the search without moving focus", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Search" }).click();
  const since = page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" });
  await since.fill("2026-01-01");
  await since.press("Escape");
  await expect(since).toHaveValue("");
  await expect(since).toBeFocused();
});

test("Help control opens keyboard help and Escape closes it", async ({
  page,
}) => {
  await page.goto("/");
  const helpDialog = page.locator('[data-testid="keyboard-help-dialog"]');
  const helpButton = page.getByRole("button", { name: "Help (?)" });
  await expect(helpDialog).toHaveCount(0);
  await expect(helpButton).toBeVisible();
  await expect(helpButton).toHaveAttribute("aria-haspopup", "dialog");
  await expect(helpButton).toHaveAttribute("aria-expanded", "false");

  await helpButton.click();
  await expect(helpDialog).toHaveCount(1);
  await expect(helpButton).toHaveAttribute("aria-expanded", "true");
  await expect(
    page.getByRole("heading", { name: "Keyboard shortcuts" }),
  ).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(helpDialog).toHaveCount(0);
  await expect(helpButton).toBeFocused();
  await expect(helpButton).toHaveAttribute("aria-expanded", "false");
});

test("Escape closes help overlay even when focus is in a search field", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Search", exact: true }).click();
  const since = page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" });
  await since.fill("2026-01-01");
  await since.focus();

  const helpDialog = page.locator('[data-testid="keyboard-help-dialog"]');
  await page.getByRole("button", { name: "Help (?)" }).click();
  await expect(helpDialog).toHaveCount(1);

  await page.keyboard.press("Escape");
  await expect(helpDialog).toHaveCount(0);
  await expect(since).toHaveValue("2026-01-01");
  await expect(page.getByRole("button", { name: "Help (?)" })).toBeFocused();
});

test("Ctrl+K opens command palette and Escape closes it", async ({ page }) => {
  await page.goto("/");
  await waitForViewerHotkeys(page);
  const palette = page.locator('[data-testid="command-palette-dialog"]');
  await expect(palette).toHaveCount(0);

  await page.keyboard.press("Control+k");
  await expect(palette).toHaveCount(1);
  await expect(palette).toHaveAttribute("role", "dialog");
  await expect(palette).toHaveAttribute("aria-modal", "true");
  await expect(
    page.getByRole("heading", { name: "Command palette" }),
  ).toBeVisible();
  await expect(
    page.getByRole("listbox", { name: "Viewer commands" }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: /Focus search/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: /Open keyboard help/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: /Next view tab/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: /Previous view tab/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: /Clear search/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: /Toggle theme/ }),
  ).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(palette).toHaveCount(0);
});

test("command palette Focus search switches to Search and focuses the filter", async ({
  page,
}) => {
  await page.goto("/");
  await waitForViewerHotkeys(page);
  const palette = page.locator('[data-testid="command-palette-dialog"]');
  await page.keyboard.press("Control+k");
  await expect(palette).toHaveCount(1);
  const focusSearch = page.getByRole("option", { name: /Focus search/ });
  await expect(focusSearch).toBeVisible();
  await focusSearch.click();
  await expect(page.getByRole("tab", { name: "Search" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(
    page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" }),
  ).toBeFocused();
});

test("command palette Open keyboard help opens the help overlay", async ({
  page,
}) => {
  await page.goto("/");
  await waitForViewerHotkeys(page);
  const helpDialog = page.locator('[data-testid="keyboard-help-dialog"]');
  const palette = page.locator('[data-testid="command-palette-dialog"]');
  await page.keyboard.press("Control+k");
  await expect(palette).toHaveCount(1);
  const openHelp = page.getByRole("option", { name: /Open keyboard help/ });
  await expect(openHelp).toBeVisible();
  await openHelp.click();
  await expect(helpDialog).toHaveCount(1);
  await expect(
    page.getByRole("heading", { name: "Keyboard shortcuts" }),
  ).toBeVisible();
});

test("command palette Next view tab advances the active tab", async ({
  page,
}) => {
  await page.goto("/");
  await waitForViewerHotkeys(page);
  await expect(page.getByRole("tab", { name: "Bundles" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  const palette = page.locator('[data-testid="command-palette-dialog"]');
  await page.keyboard.press("Control+k");
  await expect(palette).toHaveCount(1);
  const nextTab = page.getByRole("option", { name: /Next view tab/ });
  await expect(nextTab).toBeVisible();
  await nextTab.click();
  await expect(page.getByRole("tab", { name: "History" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("tab", { name: "History" })).toBeFocused();
});

test("command palette Clear search resets filters on the Search tab", async ({
  page,
}) => {
  await page.goto("/");
  await waitForViewerHotkeys(page);
  await page.getByRole("tab", { name: "Search", exact: true }).click();
  const since = page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" });
  await since.fill("2026-01-01");
  const palette = page.locator('[data-testid="command-palette-dialog"]');
  await page.keyboard.press("Control+k");
  await expect(palette).toHaveCount(1);
  const clearSearch = page.getByRole("option", { name: /Clear search/ });
  await expect(clearSearch).toBeVisible();
  await clearSearch.click();
  await expect(page.getByRole("tab", { name: "Search" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(since).toHaveValue("");
  await expect(since).toBeFocused();
});

test("primary controls expose stable accessible names", async ({ page }) => {
  await page.goto("/");

  const theme = page.getByRole("button", {
    name: "Toggle light and dark theme",
  });
  await expect(theme).toBeVisible();
  await expect(theme).toBeEnabled();

  const help = page.getByRole("button", { name: "Help (?)" });
  await expect(help).toBeVisible();
  await expect(help).toHaveAttribute("aria-controls", "keyboard-help-dialog");

  // Bundles uses synchronous sample data after the loading gate; wait on role+name.
  const filter = page.getByRole("textbox", { name: "Filter sessions" });
  await expect(filter).toBeVisible();
  await expect(filter).toHaveAttribute("placeholder", "Filter sessions...");

  await page.getByRole("tab", { name: "Search", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Model (substring)" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Show advanced filters" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Search", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Clear", exact: true }),
  ).toBeVisible();
});

test("Search advanced filters disclose on demand with recognition badge", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("tab", { name: "Search", exact: true }).click();

  const toggle = page.getByTestId("search-advanced-toggle");
  const panel = page.getByTestId("search-advanced-panel");
  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(toggle).toHaveAttribute(
    "aria-controls",
    "search-advanced-filters",
  );
  await expect(panel).toBeHidden();
  await expect(
    page.getByRole("spinbutton", { name: "Min Tokens" }),
  ).toBeHidden();

  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(
    page.getByRole("button", { name: "Hide advanced filters" }),
  ).toBeVisible();
  await expect(panel).toBeVisible();
  await expect(
    page.getByRole("group", { name: "Advanced search filters" }),
  ).toBeVisible();

  const minTokens = page.getByRole("spinbutton", { name: "Min Tokens" });
  await expect(minTokens).toBeVisible();
  await minTokens.fill("1000");
  await expect(page.getByTestId("search-advanced-badge")).toContainText(
    "1 active",
  );

  await page.getByRole("button", { name: "Hide advanced filters" }).click();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(panel).toBeHidden();
  await expect(page.getByTestId("search-advanced-badge")).toContainText(
    "1 active",
  );

  await page.getByRole("button", { name: "Clear", exact: true }).click();
  await page.getByRole("button", { name: "Confirm clear" }).click();
  await expect(page.getByTestId("search-advanced-badge")).toHaveCount(0);
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
});

test.describe("status regions and cognitive fixtures", () => {
  test("content skeleton exposes busy status region", async ({ page }) => {
    await page.goto("/?fixture=skeleton");
    const skeleton = page.getByTestId("content-skeleton");
    await expect(skeleton).toBeVisible();
    await expect(skeleton).toHaveAttribute("role", "status");
    await expect(skeleton).toHaveAttribute("aria-live", "polite");
    await expect(skeleton).toHaveAttribute("aria-busy", "true");
    await expect(skeleton).toHaveAttribute("aria-label", /loading/i);
  });

  test("long loading fixture exposes patience hint on status region", async ({
    page,
  }) => {
    await page.goto("/?fixture=loading-long");
    const loading = page.getByTestId("loading-state");
    await expect(loading).toBeVisible();
    await expect(loading).toHaveAttribute("role", "status");
    await expect(loading).toHaveAttribute("aria-live", "polite");
    await expect(loading).toHaveAttribute("aria-busy", "true");
    await expect(page.getByTestId("loading-patience-hint")).toContainText(
      /minute/i,
    );
  });

  test("search error fixture exposes assertive alert with retry", async ({
    page,
  }) => {
    await page.goto("/?fixture=search-error");
    const error = page.getByRole("alert");
    await expect(error).toBeVisible();
    await expect(error).toHaveAttribute("aria-live", "assertive");
    await expect(error).toHaveAttribute("id", "search-error-message");
    await expect(error).toContainText(/something went wrong/i);
    const retry = page.getByRole("button", { name: "Retry" });
    await expect(retry).toBeVisible();
    await expect(retry).toBeEnabled();
    await expect(retry).toHaveAttribute(
      "aria-describedby",
      "search-error-message-detail",
    );
    await expect(page.getByTestId("error-state-retry")).toBeVisible();
    await expect(
      page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" }),
    ).toBeVisible();
  });

  test("search error fixture associates fields via aria-invalid and aria-errormessage", async ({
    page,
  }) => {
    await page.goto("/?fixture=search-error");
    const error = page.getByRole("alert");
    await expect(error).toHaveAttribute("id", "search-error-message");

    for (const name of ["Since (YYYY-MM-DD)", "Model (substring)"]) {
      const field = page.getByRole("textbox", { name });
      await expect(field).toHaveAttribute("aria-invalid", "true");
      await expect(field).toHaveAttribute(
        "aria-errormessage",
        "search-error-message",
      );
    }

    const retry = page.getByRole("button", { name: "Retry" });
    await expect(retry).toBeVisible();
    await expect(retry).toHaveAttribute(
      "aria-describedby",
      "search-error-message-detail",
    );
  });

  test("Clear asks for confirmation before wiping search filters", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "Search", exact: true }).click();
    const since = page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" });
    await since.fill("2026-01-01");

    await page.getByRole("button", { name: "Clear", exact: true }).click();
    const confirm = page.getByRole("alertdialog");
    await expect(confirm).toBeVisible();
    await expect(confirm).toContainText(/clear search/i);
    await expect(since).toHaveValue("2026-01-01");

    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByRole("alertdialog")).toHaveCount(0);
    await expect(since).toHaveValue("2026-01-01");

    await page.getByRole("button", { name: "Clear", exact: true }).click();
    await expect(page.getByRole("alertdialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("alertdialog")).toHaveCount(0);
    await expect(since).toHaveValue("2026-01-01");

    await page.getByRole("button", { name: "Clear", exact: true }).click();
    await page.getByRole("button", { name: "Confirm clear" }).click();
    await expect(page.getByRole("alertdialog")).toHaveCount(0);
    await expect(since).toHaveValue("");
  });

  test("search error fixture dismisses on Escape without moving focus", async ({
    page,
  }) => {
    await page.goto("/?fixture=search-error");
    const since = page.getByRole("textbox", { name: "Since (YYYY-MM-DD)" });
    const error = page.getByRole("alert");
    await expect(error).toBeVisible();
    await expect(since).toHaveAttribute("aria-invalid", "true");

    await since.focus();
    await page.keyboard.press("Escape");
    await expect(error).toHaveCount(0);
    await expect(since).toHaveAttribute("aria-invalid", "false");
    await expect(since).toBeFocused();
  });

  test("stream skeleton fixture exposes labelled feed status and stream skeleton", async ({
    page,
  }) => {
    await page.goto("/?fixture=stream-skeleton");
    const status = page.getByTestId("live-feed-status");
    await expect(status).toBeVisible();
    await expect(status).toHaveAttribute("role", "status");
    await expect(status).toHaveAttribute("aria-live", "polite");
    await expect(status).toHaveAttribute("aria-label", /connecting/i);
    await expect(page.getByTestId("content-skeleton")).toBeVisible();
  });
});

test.describe("landmarks and reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("landmarks stay visible under reduced motion on default tab", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(
      page.getByRole("navigation", { name: "Primary viewer navigation" }),
    ).toBeVisible();
    await expect(page.getByRole("main")).toBeVisible();
    await expect(
      page.getByRole("tablist", { name: "SessionLedger views" }),
    ).toBeVisible();
  });

  test("loading spinner animation is flattened under reduced motion", async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/?fixture=loading-long");
    await expect(page.getByTestId("loading-state")).toBeVisible();
    const reduced = await page.evaluate(
      () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    );
    expect(reduced).toBe(true);
    const info = await page.evaluate(() => {
      const spinner = document.querySelector(".sl-loading-spinner");
      if (!spinner) return null;
      const style = getComputedStyle(spinner);
      return {
        duration: style.animationDuration,
        name: style.animationName,
        playState: style.animationPlayState,
      };
    });
    expect(info).not.toBeNull();
    const flattened =
      info.name === "none" ||
      info.duration === "0s" ||
      info.duration === "0.01ms" ||
      /^0(\.0\d*)?ms$/.test(info.duration) ||
      /^1e-0[45]s$/.test(info.duration);
    expect(flattened).toBeTruthy();
  });
});

test("help overlay lists every shortcut row for keyboard efficiency", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Help (?)" }).click();
  const rows = page.locator(".help-overlay-table tbody tr");
  await expect(rows).toHaveCount(12);
  await expect(page.getByRole("dialog")).toHaveAttribute(
    "aria-labelledby",
    "help-overlay-title",
  );
  await expect(
    page.getByRole("columnheader", { name: "Shortcut" }),
  ).toBeVisible();
  await expect(
    page.getByRole("columnheader", { name: "Action" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Close keyboard help" }),
  ).toBeVisible();
});
