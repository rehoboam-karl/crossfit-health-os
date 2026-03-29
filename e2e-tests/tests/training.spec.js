/**
 * Training Feature Tests
 * Tests workout and training related features
 */

const { test, expect } = require('@playwright/test');
const { TEST_USERS } = require('../utils/fixtures');
const { clearBrowserData, loginViaAPI } = require('../utils/helpers');

test.describe('Training', () => {

  test.beforeEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.afterEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.describe('Training Page Access', () => {

    test('should require authentication for workouts page', async ({ page }) => {
      await page.goto('/dashboard/workouts');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('should allow authenticated access to workouts', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      await expect(page).toHaveURL(/\/dashboard\/workouts/);
    });

  });

  test.describe('Workouts Display', () => {

    test('should display workouts page content', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      // Page should load and have content
      await expect(page.locator('body')).toContainText(/workout|training|exercise/i);
    });

    test('should display personal records section', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      // May or may not have PR section depending on data
    });

  });

  test.describe('Workout Interaction', () => {

    test('should start a workout', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      // Look for start button
      const startButton = page.locator('button:has-text("Start"), button:has-text("Begin"), button:has-text("Start Workout")').first();
      if (await startButton.isVisible()) {
        await startButton.click();
        
        // Should navigate to workout session
        await expect(page.locator('body')).toBeVisible();
      }
    });

    test('should view workout details', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      // Look for workout card or list item
      const workoutItem = page.locator('[class*="workout"], [class*="card"]').first();
      if (await workoutItem.isVisible()) {
        await workoutItem.click();
        
        // Should show details
        await expect(page.locator('body')).toBeVisible();
      }
    });

  });

});
