import { test, expect } from '@playwright/test';

test.describe('Claim Lifecycle', () => {
  test('should create, scrub, fix, and submit a claim', async ({ page }) => {
    // 1. Create Claim
    await page.goto('/claims/new');
    await page.fill('input#patient_id', 'Test Patient');
    await page.fill('input#service_date_from', '2026-09-12');
    await page.click('button:has-text("Save changes")');
    await expect(page).toHaveURL(/\/claims\/\d+/);

    const claimId = page.url().split('/').pop();

    // 2. Scrub
    await page.goto('/claims');
    await page.check(`input[aria-label="Select claim ${claimId}"]`);
    await page.click('button:has-text("Bulk scrub")');
    // Wait for scrub completion
    await page.waitForTimeout(2000);

    // 3. Fix Findings
    await page.goto(`/claims/${claimId}`);
    // Look for an ERROR finding (red background)
    const errorFinding = page.locator('.border-red-200.bg-red-50\\/40').first();
    await expect(errorFinding).toBeVisible();

    // Apply a fix if available, otherwise override
    const fixButton = errorFinding.locator('button:has-text("Apply fix")');
    if (await fixButton.isVisible()) {
      await fixButton.click();
    } else {
      await errorFinding.locator('button:has-text("Override")').click();
      await page.fill('textarea[placeholder="Document the clinical or operational reason"]', 'Valid clinical override');
      await page.click('button:has-text("Confirm override")');
    }

    // 4. Submit
    await page.click('button:has-text("Submit")');
    await page.click('button:has-text("Confirm submit")');
    await expect(page.locator('text=Claim submitted and moved to Submitted.')).toBeVisible();
  });
});
