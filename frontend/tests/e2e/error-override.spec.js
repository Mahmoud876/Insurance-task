import { test, expect } from '@playwright/test';

test.describe('Error Override', () => {
  test('should allow overriding an ERROR finding with a reason', async ({ page }) => {
    // Navigate to a claim that has an ERROR finding
    // For a real test, we would use a seeded claim ID
    await page.goto('/claims/1');

    const errorFinding = page.locator('.border-red-200.bg-red-50\\/40').first();
    await expect(errorFinding).toBeVisible();

    await errorFinding.locator('button:has-text("Override")').click();
    await page.fill('textarea[placeholder="Document the clinical or operational reason"]', 'Clinical reason for override');
    await page.click('button:has-text("Confirm override")');

    // Verify the finding is no longer in the active list
    await expect(errorFinding).not.toBeVisible();
  });
});
