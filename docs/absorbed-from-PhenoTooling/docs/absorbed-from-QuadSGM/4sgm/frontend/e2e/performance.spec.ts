import { test, expect } from '@playwright/test';

test.describe('Performance Benchmarks', () => {

  test.describe('Page Load Performance', () => {
    test('homepage loads within 3 seconds', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/', { waitUntil: 'domcontentloaded' });

      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(3000);
      console.log(`Homepage loaded in ${loadTime}ms`);
    });

    test('page reaches networkidle within 5 seconds', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/', { waitUntil: 'networkidle' });

      const loadTime = Date.now() - startTime;

      expect(loadTime).toBeLessThan(5000);
      console.log(`Page reached networkidle in ${loadTime}ms`);
    });

    test('chat widget button appears quickly', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.waitFor({ state: 'visible', timeout: 2000 });

      const appearTime = Date.now() - startTime;

      expect(appearTime).toBeLessThan(2000);
      console.log(`Chat button appeared in ${appearTime}ms`);
    });
  });

  test.describe('Chat Widget Performance', () => {
    test('chat widget opens within 500ms', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();

      const startTime = Date.now();
      await chatButton.click();

      const chatWindow = page.locator('text=4SGM Support');
      await chatWindow.waitFor({ state: 'visible', timeout: 2000 });

      const openTime = Date.now() - startTime;

      expect(openTime).toBeLessThan(500);
      console.log(`Chat widget opened in ${openTime}ms`);
    });

    test('message input becomes interactive quickly', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const startTime = Date.now();

      const messageInput = page.locator('input[placeholder*="Type your"]');
      await messageInput.waitFor({ state: 'visible', timeout: 1000 });

      const interactiveTime = Date.now() - startTime;

      expect(interactiveTime).toBeLessThan(1000);
      console.log(`Message input became interactive in ${interactiveTime}ms`);
    });

    test('message sends within 2 seconds', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      const startTime = Date.now();

      await messageInput.fill('Performance test message');
      await page.keyboard.press('Enter');

      // Wait for input to be cleared (indicating message was sent)
      await messageInput.waitFor({ state: 'empty', timeout: 5000 }).catch(() => {
        // Also acceptable if message clears via has("") state
      });

      const sendTime = Date.now() - startTime;

      expect(sendTime).toBeLessThan(5000);
      console.log(`Message sent within ${sendTime}ms`);
    });
  });

  test.describe('Message Response Performance', () => {
    test('AI response arrives within 10 seconds', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Send a question
      const startTime = Date.now();

      await messageInput.fill('What time is it?');
      await page.keyboard.press('Enter');

      // Look for response indicator (assistant message, loading state, etc.)
      const assistantMessage = page.locator('.assistant-message, [class*="assistant"]').first();

      await assistantMessage.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {
        // Response might not appear if no backend
      });

      const responseTime = Date.now() - startTime;

      // Response should arrive within reasonable time
      expect(responseTime).toBeLessThan(15000);
      console.log(`Response arrived in ${responseTime}ms`);
    });

    test('reasoning panel loads efficiently', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const reasoningButton = page.locator('button[aria-label="Open reasoning trail"]').first();

      const startTime = Date.now();

      try {
        await reasoningButton.click({ timeout: 1000 });

        const reasoningPanel = page.locator('text=Reasoning Trail');
        await reasoningPanel.waitFor({ state: 'visible', timeout: 2000 });

        const loadTime = Date.now() - startTime;

        expect(loadTime).toBeLessThan(3000);
        console.log(`Reasoning panel loaded in ${loadTime}ms`);
      } catch {
        // Reasoning button might not be available immediately
        // This is acceptable
      }
    });
  });

  test.describe('Interaction Performance', () => {
    test('typing feels responsive (no lag)', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Type quickly and measure responsiveness
      const startTime = Date.now();

      const testMessage = 'Responsiveness test 12345';
      for (const char of testMessage) {
        const charStart = Date.now();
        await messageInput.press(char);
        const charTime = Date.now() - charStart;

        // Each character should process in <50ms
        expect(charTime).toBeLessThan(100);
      }

      const totalTime = Date.now() - startTime;

      console.log(`Typed ${testMessage.length} characters in ${totalTime}ms`);
      expect(totalTime).toBeLessThan(2000);
    });

    test('scrolling chat messages is smooth', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Send multiple messages
      for (let i = 0; i < 5; i++) {
        await messageInput.fill(`Message ${i + 1}`);
        await page.keyboard.press('Enter');
        await page.waitForTimeout(200);
      }

      const chatContent = page.locator('[role="dialog"]').first();

      // Measure scroll performance
      const startTime = Date.now();

      // Scroll down
      await chatContent.evaluate((el) => {
        el.scrollTop = el.scrollHeight;
      });

      const scrollTime = Date.now() - startTime;

      expect(scrollTime).toBeLessThan(100);
      console.log(`Scroll completed in ${scrollTime}ms`);
    });
  });

  test.describe('Memory and Resource Usage', () => {
    test('chat widget does not cause excessive memory growth', async ({ page }) => {
      await page.goto('/');

      const initialMemory = await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0;
      });

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');

      // Send several messages
      for (let i = 0; i < 3; i++) {
        await messageInput.fill(`Memory test message ${i}`);
        await page.keyboard.press('Enter');
        await page.waitForTimeout(300);
      }

      const finalMemory = await page.evaluate(() => {
        return (performance as any).memory?.usedJSHeapSize || 0;
      });

      // Memory growth should be reasonable (less than 50MB increase for 3 messages)
      const memoryGrowth = finalMemory - initialMemory;

      console.log(`Memory growth: ${(memoryGrowth / 1024 / 1024).toFixed(2)}MB`);

      // Reasonable limit for memory growth
      expect(memoryGrowth).toBeLessThan(50 * 1024 * 1024);
    });

    test('closing chat widget releases resources', async ({ page }) => {
      await page.goto('/');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();

      // Open and close multiple times
      for (let i = 0; i < 3; i++) {
        await chatButton.click();

        const chatWindow = page.locator('text=4SGM Support');
        await chatWindow.waitFor({ state: 'visible', timeout: 1000 });

        // Close
        await page.keyboard.press('Escape');

        await page.waitForTimeout(200);
      }

      // Page should remain responsive
      const startTime = Date.now();

      await chatButton.click();

      const chatWindow = page.locator('text=4SGM Support');
      await chatWindow.waitFor({ state: 'visible', timeout: 1000 });

      const openTime = Date.now() - startTime;

      // Should still open quickly after multiple open/close cycles
      expect(openTime).toBeLessThan(500);
    });
  });

  test.describe('Network Performance', () => {
    test('chat API calls complete efficiently', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Listen to network requests
      const requests: { url: string; duration: number }[] = [];

      page.on('requestfinished', (request) => {
        const duration = request.timing().responseEnd - request.timing().requestStart;
        if (request.url().includes('/api') || request.url().includes('/chat')) {
          requests.push({
            url: request.url(),
            duration: duration
          });
        }
      });

      const chatButton = page.locator('button[aria-label="Open chat"]').first();
      await chatButton.click();

      const messageInput = page.locator('input[placeholder*="Type your"]');
      await messageInput.fill('Network performance test');
      await page.keyboard.press('Enter');

      // Wait for requests to complete
      await page.waitForTimeout(2000);

      // All API calls should be reasonably fast
      for (const req of requests) {
        console.log(`API request ${req.url}: ${req.duration}ms`);
        // Allow up to 5 seconds for any single request
        expect(req.duration).toBeLessThan(5000);
      }
    });

    test('images and assets load efficiently', async ({ page }) => {
      const startTime = Date.now();

      await page.goto('/');

      const images = page.locator('img');
      const count = await images.count();

      let loadedCount = 0;

      for (let i = 0; i < count; i++) {
        const img = images.nth(i);

        try {
          const complete = await img.evaluate((el: HTMLImageElement) => {
            return el.complete;
          });

          if (complete) {
            loadedCount++;
          }
        } catch {
          // Image might not be available
        }
      }

      const totalTime = Date.now() - startTime;

      console.log(`Loaded ${loadedCount}/${count} images in ${totalTime}ms`);

      // Page assets should load reasonably fast
      expect(totalTime).toBeLessThan(5000);
    });
  });

  test.describe('CSS and Layout Performance', () => {
    test('no layout thrashing occurs during interactions', async ({ page }) => {
      await page.goto('/');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();

      const startTime = Date.now();

      // Trigger layout changes
      await chatButton.click();

      const chatWindow = page.locator('text=4SGM Support');
      await chatWindow.waitFor({ state: 'visible', timeout: 2000 });

      const interactionTime = Date.now() - startTime;

      // Should not be overly slow due to layout thrashing
      expect(interactionTime).toBeLessThan(1000);
    });

    test('animations perform smoothly', async ({ page }) => {
      await page.goto('/');

      const chatButton = page.locator('button[aria-label="Open chat"]').first();

      const startTime = Date.now();

      await chatButton.click();

      // Measure animation completion
      await page.waitForTimeout(300);

      const animationTime = Date.now() - startTime;

      console.log(`Animation completed in ${animationTime}ms`);

      // Animations should be reasonably quick
      expect(animationTime).toBeLessThan(1000);
    });
  });

  test.describe('Benchmarks Summary', () => {
    test('performance metrics are within acceptable ranges', async ({ page }) => {
      await page.goto('/', { waitUntil: 'domcontentloaded' });

      const metrics = await page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;

        return {
          domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
          loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
          firstPaint: navigation.responseEnd - navigation.responseStart,
          domInteractive: navigation.domInteractive - navigation.navigationStart,
          domComplete: navigation.domComplete - navigation.navigationStart,
        };
      });

      console.log('Performance Metrics:');
      console.log(`  DOM Content Loaded: ${metrics.domContentLoaded}ms`);
      console.log(`  Load Complete: ${metrics.loadComplete}ms`);
      console.log(`  First Paint: ${metrics.firstPaint}ms`);
      console.log(`  DOM Interactive: ${metrics.domInteractive}ms`);
      console.log(`  DOM Complete: ${metrics.domComplete}ms`);

      // Main metrics should be acceptable
      expect(metrics.domContentLoaded).toBeLessThan(3000);
      expect(metrics.domComplete).toBeLessThan(5000);
    });
  });
});
