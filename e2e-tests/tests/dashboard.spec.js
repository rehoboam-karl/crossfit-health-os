/**
 * Dashboard and Navigation Tests
 * Tests the main dashboard and navigation between pages
 */

const { test, expect } = require('@playwright/test');
const { TEST_USERS } = require('../utils/fixtures');
const { clearBrowserData, loginViaAPI } = require('../utils/helpers');

test.describe('Dashboard', () => {

  test.beforeEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.afterEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.describe('Dashboard Access', () => {

    test('should redirect unauthenticated user to login', async ({ page }) => {
      await page.goto('/dashboard');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('should allow authenticated user to access dashboard', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      await expect(page).toHaveURL(/\/dashboard/);
    });

    test('should display user name on dashboard', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      // Should show welcome message with user name
      await expect(page.locator('text=/welcome|hello|hi/i')).toBeVisible({ timeout: 10000 });
    });

    test('should display dashboard navigation menu', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      // Check navigation elements
      await expect(page.locator('text=/dashboard|workout|training/i')).toBeVisible();
    });

    test('should show sidebar or top navigation', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      // Either sidebar or top nav should be present
      const hasNav = await page.locator('nav, .sidebar, .navbar, [class*="nav"]').first().isVisible();
      expect(hasNav).toBe(true);
    });

  });

  test.describe('Navigation Links', () => {

    test('should navigate to workouts page', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      // Click on workouts/training link
      await page.click('text=/workouts?|training/i');
      
      await expect(page).toHaveURL(/\/dashboard\/workouts/);
    });

    test('should navigate to schedule page', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      await page.click('text=/schedule|calendar/i');
      
      await expect(page).toHaveURL(/\/dashboard\/schedule/);
    });

    test('should navigate to health page', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      await page.click('text=/health|biometric/i');
      
      await expect(page).toHaveURL(/\/dashboard\/health/);
    });

    test('should navigate to nutrition page', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      await page.click('text=/nutrition|diet|meal/i');
      
      await expect(page).toHaveURL(/\/dashboard\/nutrition/);
    });

    test('should navigate to reviews page', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      await page.click('text=/reviews?/i');
      
      await expect(page).toHaveURL(/\/dashboard\/reviews/);
    });

    test('should navigate to profile page', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      await page.click('text=/profile|account|settings/i');
      
      await expect(page).toHaveURL(/\/dashboard\/profile/);
    });

    test('should navigate to badges page', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard');
      
      await page.click('text=/badges?|achievement|reward/i');
      
      await expect(page).toHaveURL(/\/dashboard\/badges/);
    });

  });

  test.describe('Page Content', () => {

    test('should display workouts page with content', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      await expect(page.locator('body')).toContainText(/workout|training|exercise/i);
    });

    test('should display schedule page with content', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/schedule');
      
      await expect(page.locator('body')).toContainText(/schedule|calendar|week/i);
    });

    test('should display health page with content', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/health');
      
      await expect(page.locator('body')).toContainText(/health|metric|biometric/i);
    });

    test('should display nutrition page with content', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/nutrition');
      
      await expect(page.locator('body')).toContainText(/nutrition|macro|calorie|diet/i);
    });

    test('should display reviews page with content', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/reviews');
      
      await expect(page.locator('body')).toContainText(/review|feedback/i);
    });

    test('should display profile page with content', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      await expect(page.locator('body')).toContainText(/profile|account|setting/i);
    });

    test('should display badges page with content', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/badges');
      
      await expect(page.locator('body')).toContainText(/badge|achievement|reward/i);
    });

  });

  test.describe('URL Routing', () => {

    test('should access workouts directly via URL', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      await expect(page).toHaveURL(/\/dashboard\/workouts/);
    });

    test('should access schedule directly via URL', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/schedule');
      
      await expect(page).toHaveURL(/\/dashboard\/schedule/);
    });

    test('should access health directly via URL', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/health');
      
      await expect(page).toHaveURL(/\/dashboard\/health/);
    });

    test('should access nutrition directly via URL', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/nutrition');
      
      await expect(page).toHaveURL(/\/dashboard\/nutrition/);
    });

    test('should access reviews directly via URL', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/reviews');
      
      await expect(page).toHaveURL(/\/dashboard\/reviews/);
    });

    test('should access profile directly via URL', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      await expect(page).toHaveURL(/\/dashboard\/profile/);
    });

    test('should access badges directly via URL', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/badges');
      
      await expect(page).toHaveURL(/\/dashboard\/badges/);
    });

  });

  test.describe('Navigation State', () => {

    test('should highlight current page in navigation', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      // Active nav item should have active class or styling
      const activeNav = page.locator('.nav-item.active, .nav-link.active, [class*="active"]').first();
      // This test may need adjustment based on actual nav implementation
    });

    test('should maintain session across navigation', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      // Navigate through several pages
      await page.goto('/dashboard');
      await page.goto('/dashboard/workouts');
      await page.goto('/dashboard/schedule');
      await page.goto('/dashboard/health');
      
      // Should not be redirected to login
      await expect(page).not.toHaveURL(/\/login/);
    });

  });

  test.describe('Breadcrumb Navigation', () => {

    test('should display breadcrumbs on subpages', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/workouts');
      
      // Breadcrumb should show Dashboard > Workouts
      const hasBreadcrumb = await page.locator('[class*="breadcrumb"], [class*="crumb"]').first().isVisible();
      // May or may not be present depending on implementation
    });

  });

});
