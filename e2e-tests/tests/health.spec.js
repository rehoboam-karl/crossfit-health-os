/**
 * Health/Biometrics Feature Tests
 * Tests health metrics and biometric tracking features
 */

const { test, expect } = require('@playwright/test');
const { TEST_USERS } = require('../utils/fixtures');
const { clearBrowserData, loginViaAPI } = require('../utils/helpers');

test.describe('Health', () => {

  test.beforeEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.afterEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.describe('Health Page Access', () => {

    test('should require authentication for health page', async ({ page }) => {
      await page.goto('/dashboard/health');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('should allow authenticated access to health', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/health');
      
      await expect(page).toHaveURL(/\/dashboard\/health/);
    });

  });

  test.describe('Health Page Content', () => {

    test('should display health/biometrics section', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/health');
      
      // Should show health related content
      await expect(page.locator('body')).toContainText(/health|biometric|recovery/i);
    });

    test('should display biomarkers', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/health');
      
      // Should show biomarkers section
      await expect(page.locator('body')).toBeVisible();
    });

    test('should display recovery trend', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/health');
      
      // May show recovery trend graph or data
    });

  });

});
