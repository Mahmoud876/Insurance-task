import { test, expect } from '@playwright/test';

test.describe('Analytics Dashboard', () => {
  test('should load the analytics dashboard with data', async ({ page }) => {
    await page.goto('/dashboard');

    // Check for key sections in AnalyticsCharts.jsx
    await expect(page.locator('text=Status funnel')).toBeVisible();
    await expect(page.locator('text=First-pass clean rate')).toBeVisible();
    await expect(page.locator('text=Top findings')).toBeVisible();
    await expect(page.locator('text=Findings by category')).toBeVisible();

    // Check that at least some data is rendered in the funnel
    const statusBars = page.locator('.bg-indigo-500');
    await expect(statusBars).not.toHaveCount(0);
  });
});
