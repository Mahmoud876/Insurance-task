import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Scans', () => {
  const screens = [
    { name: 'Dashboard', path: '/dashboard' },
    { name: 'Claims List', path: '/claims' },
    { name: 'Claim Editor', path: '/claims/new' },
    { name: 'Patients', path: '/patients' },
  ];

  for (const screen of screens) {
    test(`should have no critical accessibility violations on ${screen.name}`, async ({ page }) => {
      await page.goto(screen.path);

      // Wait for any loading states to finish
      await page.waitForLoadState('networkidle');

      const accessibilityScanResults = await new AxeBuilder({ page }).analyze();

      expect(accessibilityScanResults.violations).toEqual([]);
    });
  }
});
