const { test, expect } = require('@playwright/test');

test('Playwright is working', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example/);
});

test('Can navigate to login page (structure test)', async ({ page }) => {
  // This tests the test framework, not the actual app
  await page.goto('https://example.com');
  await expect(page.locator('h1')).toContainText('Example Domain');
});
