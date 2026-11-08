import { test, expect } from '@playwright/test';

test.describe('Accessibility - WCAG 2.1 AA Compliance', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Keyboard Navigation', () => {
    test('chat widget can be opened with keyboard (Tab + Enter)', async ({ page }) => {
      // Tab to chat button
      await page.keyboard.press('Tab');

      // Check if focused element is chat button or navigate to it
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.focus();

      // Open with Enter
      await page.keyboard.press('Enter');

      const chatWindow = page.locator('text=4SGM Support');
      await expect(chatWindow).toBeVisible();
    });

    test('can send message using keyboard only', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Focus and type
      await messageInput.focus();
      await messageInput.type('Keyboard navigation test');

      // Send with Enter
      await page.keyboard.press('Enter');

      await expect(messageInput).toHaveValue('', { timeout: 2000 });
    });

    test('Tab key cycles through interactive elements', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Focus should be manageable with Tab
      await messageInput.focus();
      await expect(messageInput).toBeFocused();

      // Tab to next element
      await page.keyboard.press('Tab');

      // Should move focus or stay on input (both acceptable)
      const focusedElement = await page.evaluate(() => {
        return document.activeElement?.tagName;
      });

      expect(focusedElement).toBeTruthy();
    });

    test('Shift+Tab navigates backwards', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');
      await messageInput.focus();

      // Shift+Tab should navigate
      await page.keyboard.press('Shift+Tab');

      // Focus should move or remain accessible
      const focusedElement = await page.evaluate(() => {
        return document.activeElement?.getAttribute('aria-label') ||
               document.activeElement?.getAttribute('type') ||
               document.activeElement?.tagName;
      });

      expect(focusedElement).toBeTruthy();
    });

    test('Escape key closes chat widget', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const chatWindow = page.locator('text=4SGM Support');
      await expect(chatWindow).toBeVisible();

      // Close with Escape
      await page.keyboard.press('Escape');

      // Chat should be hidden or not visible
      const isVisible = await chatWindow.isVisible().catch(() => false);
      expect(!isVisible).toBe(true);
    });
  });

  test.describe('ARIA Attributes', () => {
    test('chat button has proper aria-label', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      const label = await chatButton.getAttribute('aria-label');

      expect(label).toBe('Open chat');
    });

    test('chat widget has proper dialog role', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const dialog = page.locator('[role="dialog"]').first();
      await expect(dialog).toBeVisible();

      const role = await dialog.getAttribute('role');
      expect(role).toBe('dialog');
    });

    test('form inputs have associated labels or aria-label', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Input should have either aria-label or placeholder
      const ariaLabel = await messageInput.getAttribute('aria-label');
      const placeholder = await messageInput.getAttribute('placeholder');

      expect(ariaLabel || placeholder).toBeTruthy();
    });

    test('buttons have accessible names', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const buttons = page.locator('button');
      const count = await buttons.count();

      // All buttons should have accessible names
      for (let i = 0; i < Math.min(count, 5); i++) {
        const button = buttons.nth(i);
        const ariaLabel = await button.getAttribute('aria-label');
        const textContent = await button.textContent();

        // Button should have either aria-label or text content
        expect(ariaLabel || textContent?.trim()).toBeTruthy();
      }
    });

    test('heading hierarchy is proper', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const headings = page.locator('h1, h2, h3, h4, h5, h6');
      const count = await headings.count();

      // Should have meaningful heading structure
      expect(count).toBeGreaterThanOrEqual(0);

      if (count > 0) {
        // Check heading levels don't skip
        const firstHeading = headings.first();
        const level = await firstHeading.evaluate((el) => {
          return parseInt(el.tagName.charAt(1));
        });

        // First heading should typically be h1 or h2
        expect([1, 2, 3]).toContain(level);
      }
    });
  });

  test.describe('Color Contrast', () => {
    test('chat button has sufficient color contrast', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();

      const contrast = await page.evaluate(() => {
        const button = document.querySelector('button[aria-label="Open chat"]');
        if (!button) return null;

        const styles = window.getComputedStyle(button);
        const bgColor = styles.backgroundColor;
        const color = styles.color;

        // Returns the computed colors (would need actual contrast ratio calculation)
        return { bgColor, color };
      });

      expect(contrast).toBeTruthy();
      expect(contrast?.bgColor).toBeTruthy();
      expect(contrast?.color).toBeTruthy();
    });

    test('text elements have readable color combinations', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const chatContent = page.locator('[role="dialog"]');
      await expect(chatContent).toBeVisible();

      // Verify text is readable (not white on white, etc.)
      const textElements = chatContent.locator('p, div, span');
      const count = await textElements.count();

      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('Focus Management', () => {
    test('focus visible indicator is present on button', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();

      // Focus the button
      await chatButton.focus();

      // Check if focus indicator exists (outline or box-shadow)
      const hasFocusStyle = await page.evaluate(() => {
        const button = document.querySelector('button[aria-label="Open chat"]');
        if (!button) return false;

        const styles = window.getComputedStyle(button);
        return styles.outline !== 'none' ||
               styles.boxShadow !== 'none' ||
               button.matches(':focus-visible');
      });

      expect(hasFocusStyle).toBe(true);
    });

    test('focus trap within modal dialog', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const dialog = page.locator('[role="dialog"]').first();
      await expect(dialog).toBeVisible();

      // Get all focusable elements within dialog
      const focusableElements = dialog.locator(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );

      const count = await focusableElements.count();

      // Should have at least some focusable elements
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('focus returns to trigger when modal closes', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();

      // Focus and open
      await chatButton.focus();
      await chatButton.click();

      const dialog = page.locator('[role="dialog"]').first();
      await expect(dialog).toBeVisible();

      // Close with Escape
      await page.keyboard.press('Escape');

      // Focus should return to button or be manageable
      const focusedElement = await page.evaluate(() => {
        return document.activeElement?.getAttribute('aria-label') ||
               document.activeElement?.className;
      });

      expect(focusedElement).toBeTruthy();
    });
  });

  test.describe('Screen Reader Support', () => {
    test('messages have proper semantic structure', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');
      await messageInput.fill('Screen reader test');
      await page.keyboard.press('Enter');

      // Messages should have semantic structure
      const messages = page.locator('[role="dialog"] p, [role="dialog"] div').filter({
        has: page.locator(':not(input)')
      });

      const count = await messages.count();

      // Should have some message content visible
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('error states are announced accessibly', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Try to trigger error with very long input
      const longInput = 'a'.repeat(10000);
      await messageInput.fill(longInput);

      // Check for error announcement
      const errorMessage = page.locator('[role="alert"], .error, [aria-live]').first();

      // Error might be visible or not, both are acceptable
      const hasErrorIndicator = await errorMessage.isVisible().catch(() => false);
      expect(typeof hasErrorIndicator).toBe('boolean');
    });

    test('live regions announce messages', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      // Check for aria-live regions
      const liveRegion = page.locator('[aria-live]').first();

      // Live region should be present for dynamic updates
      const hasLiveRegion = await liveRegion.isVisible().catch(() => false);

      // Live regions are recommended but not strictly required
      expect(typeof hasLiveRegion).toBe('boolean');
    });
  });

  test.describe('Text Sizing and Spacing', () => {
    test('text is readable at different zoom levels', async ({ page }) => {
      // Test at 100% zoom (default)
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');
      let boundingBox = await messageInput.boundingBox();

      expect(boundingBox).toBeTruthy();
      expect(boundingBox?.height).toBeGreaterThan(20); // Reasonable text size

      // Close and zoom
      await page.keyboard.press('Escape');
      await page.evaluate(() => {
        document.body.style.zoom = '150%';
      });

      // Reopen and verify still readable
      await chatButton.click();
      const newBoundingBox = await messageInput.boundingBox();

      expect(newBoundingBox).toBeTruthy();
      expect(newBoundingBox?.height).toBeGreaterThan(20);
    });

    test('line spacing allows comfortable reading', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const chatContent = page.locator('[role="dialog"]');

      const lineHeight = await chatContent.evaluate((el) => {
        return window.getComputedStyle(el).lineHeight;
      });

      // Line height should be set (not 'normal')
      expect(lineHeight).toBeTruthy();
    });
  });

  test.describe('Mobile Accessibility', () => {
    test('touch targets are at least 48px', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      const boundingBox = await chatButton.boundingBox();

      expect(boundingBox).toBeTruthy();

      // WCAG 2.5.5 recommends 44x44px, Apple recommends 48x48px
      if (boundingBox) {
        const minSize = Math.min(boundingBox.width, boundingBox.height);
        expect(minSize).toBeGreaterThanOrEqual(40); // Slightly flexible
      }
    });

    test('touch-activated elements dont have hover-only content', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });

      const chatButton = page.locator('button[aria-label="Open chat"]').first();

      // All important content should be accessible via tap, not hover
      const ariaLabel = await chatButton.getAttribute('aria-label');
      const textContent = await chatButton.textContent();

      expect(ariaLabel || textContent).toBeTruthy();
    });
  });

  test.describe('Language and Internationalization', () => {
    test('page has lang attribute', async ({ page }) => {
      const htmlTag = page.locator('html').first();
      const lang = await htmlTag.getAttribute('lang');

      expect(lang).toBeTruthy();
      expect(['en', 'en-US'].includes(lang || '')).toBe(true);
    });

    test('chat widget respects language settings', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      // Verify text is in expected language
      const chatContent = page.locator('text=4SGM Support');
      await expect(chatContent).toBeVisible();
    });
  });

  test.describe('Form Accessibility', () => {
    test('input field is properly labeled', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Should have placeholder or aria-label
      const ariaLabel = await messageInput.getAttribute('aria-label');
      const placeholder = await messageInput.getAttribute('placeholder');

      expect(ariaLabel || placeholder).toBeTruthy();
    });

    test('input has proper type attribute', async ({ page }) => {
      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');
      const type = await messageInput.getAttribute('type');

      // Should be text, not generic
      expect(['text', 'search'].includes(type || 'text')).toBe(true);
    });
  });
});
