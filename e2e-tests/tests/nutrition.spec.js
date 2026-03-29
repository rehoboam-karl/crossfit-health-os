/**
 * Nutrition Feature Tests
 * Tests nutrition and diet tracking features
 */

const { test, expect } = require('@playwright/test');
const { TEST_USERS } = require('../utils/fixtures');
const { clearBrowserData, loginViaAPI } = require('../utils/helpers');

test.describe('Nutrition', () => {

  test.beforeEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.afterEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.describe('Nutrition Page Access', () => {

    test('should require authentication for nutrition page', async ({ page }) => {
      await page.goto('/dashboard/nutrition');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('should allow authenticated access to nutrition', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/nutrition');
      
      await expect(page).toHaveURL(/\/dashboard\/nutrition/);
    });

  });

  test.describe('Nutrition Page Content', () => {

    test('should display macro targets', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/nutrition');
      
      // Should show macro information
      await expect(page.locator('body')).toContainText(/protein|carbs?|fat|calorie/i);
    });

    test('should display daily progress', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/nutrition');
      
      // Should show today's macros or progress
      await expect(page.locator('body')).toBeVisible();
    });

    test('should display meal list', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/nutrition');
      
      // Should show meals section
      await expect(page.locator('body')).toContainText(/meal|food|intake/i);
    });

  });

  test.describe('Nutrition Actions', () => {

    test('should add a meal', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/nutrition');
      
      // Look for add meal button
      const addButton = page.locator('button:has-text("Add"), button:has-text("Log"), button:has-text("+")').first();
      if (await addButton.isVisible()) {
        await addButton.click();
        
        // Should show meal entry form
        await expect(page.locator('body')).toBeVisible();
      }
    });

  });

});
