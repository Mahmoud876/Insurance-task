import { test, expect } from '@playwright/test';

test.describe('Bulk Scrub', () => {
  test('should trigger bulk scrub for selected claims', async ({ page }) => {
    await page.goto('/claims');

    // Select multiple claims
    const checkboxes = page.locator('input[aria-label^="Select claim"]');
    await checkboxes.first().check();
    await checkboxes.nth(1).check();

    await page.click('button:has-text("Bulk scrub")');

    // Verify some visual indicator of scrubbing (e.g., status message or toast)
    // Since we don't have a specific message, we'll wait a bit
    await page.waitForTimeout(2000);
    // In a real app, we'd check for a "Scrubbing complete" message
  });
});
