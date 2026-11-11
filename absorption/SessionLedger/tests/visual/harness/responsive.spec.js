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
  { width: 360, height: 800 },
  { width: 768, height: 900 },
  { width: 1280, height: 720 },
];

const MIN_TOUCH_PX = 44;

async function expectNoHorizontalOverflow(page, label) {
  const metrics = await page.evaluate(() => {
    const documentElement = document.documentElement;
    const body = document.body;

    return {
      documentElement: {
        clientWidth: documentElement.clientWidth,
        scrollWidth: documentElement.scrollWidth,
      },
      body: {
        clientWidth: body.clientWidth,
        scrollWidth: body.scrollWidth,
      },
    };
  });

  const overflowPx = Math.max(
    metrics.documentElement.scrollWidth - metrics.documentElement.clientWidth,
    metrics.body.scrollWidth - metrics.body.clientWidth,
  );

  expect(
    overflowPx,
    `${label} has horizontal overflow: ${JSON.stringify(metrics)}`,
  ).toBeLessThanOrEqual(0);
}

async function expectTouchTarget(locator, label) {
  const box = await locator.boundingBox();
  expect(box, `${label} should be visible`).not.toBeNull();
  expect(box.width, `${label} width`).toBeGreaterThanOrEqual(MIN_TOUCH_PX);
  expect(box.height, `${label} height`).toBeGreaterThanOrEqual(MIN_TOUCH_PX);
}

for (const viewport of viewports) {
  test.describe(`${viewport.width}px viewport`, () => {
    test.use({ viewport });

    test("viewer tabs do not create document-level horizontal overflow", async ({
      page,
    }) => {
      await page.goto("/");
      await expect(
        page.getByRole("tablist", { name: "SessionLedger views" }),
      ).toBeVisible();

      for (const tabName of tabs) {
        const tab = page.getByRole("tab", { name: tabName, exact: true });
        await tab.click();
        await expect(tab).toHaveAttribute("aria-selected", "true");
        await expect(
          page.getByRole("tabpanel", { name: tabName }),
        ).toBeVisible();

        await expectNoHorizontalOverflow(
          page,
          `${tabName} at ${viewport.width}px`,
        );
      }
    });

    if (viewport.width >= 768) {
      test("bundles inbox and transcript use independent desktop panes", async ({
        page,
      }) => {
        await page.goto("/");
        await page.getByRole("tab", { name: "Bundles", exact: true }).click();
        const inbox = page.locator(".bundles-workspace > .session-list");
        const detail = page.locator(".bundles-workspace > .main-content");
        await expect(inbox).toBeVisible();
        await expect(detail).toBeVisible();

        const [inboxBox, detailBox] = await Promise.all([
          inbox.boundingBox(),
          detail.boundingBox(),
        ]);
        expect(inboxBox).not.toBeNull();
        expect(detailBox).not.toBeNull();
        expect(detailBox.x).toBeGreaterThan(inboxBox.x + inboxBox.width - 1);

        await page.locator(".session-item").first().click();
        await expect(
          page.getByRole("heading", { name: "Conversation" }),
        ).toBeVisible();
        await expect(page.getByTestId("message-user").first()).toBeVisible();
        await expect(page.locator(".main-upper")).toHaveCSS(
          "overflow-y",
          "auto",
        );
      });
    }

    if (viewport.width === 360) {
      test("primary controls meet 44px touch targets", async ({ page }) => {
        await page.goto("/");
        const tablist = page.getByRole("tablist", {
          name: "SessionLedger views",
        });
        await expect(tablist).toBeVisible();

        for (const tabName of tabs) {
          await expectTouchTarget(
            tablist.getByRole("tab", { name: tabName, exact: true }),
            tabName,
          );
        }

        await expectTouchTarget(
          page.getByRole("button", { name: "Toggle light and dark theme" }),
          "theme toggle",
        );

        await page.getByRole("tab", { name: "Search", exact: true }).click();
        await expectTouchTarget(
          page.getByRole("button", { name: "Search" }),
          "Search",
        );
        await expectTouchTarget(
          page.getByRole("button", { name: "Clear" }),
          "Clear",
        );
      });
    }
  });
}
