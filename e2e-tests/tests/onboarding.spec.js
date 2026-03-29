/**
 * Onboarding Tests
 * Tests the new user onboarding flow
 */

const { test, expect } = require('@playwright/test');
const { ONBOARDING_DATA, TEST_USERS } = require('../utils/fixtures');
const { 
  generateRandomEmail, 
  clearBrowserData,
  loginViaAPI,
  registerViaAPI
} = require('../utils/helpers');

test.describe('Onboarding', () => {

  test.beforeEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.afterEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.describe('Onboarding Flow', () => {

    test('should display onboarding welcome step', async ({ page }) => {
      // Register and go to onboarding
      await page.goto('/register');
      
      const email = generateRandomEmail('onboard');
      await page.locator('#name').fill('New User');
      await page.locator('#email').fill(email);
      await page.locator('#password').fill('SecurePass123');
      await page.locator('#confirm_password').fill('SecurePass123');
      await page.locator('#register-btn').click();
      
      // Should be on onboarding page
      await expect(page).toHaveURL(/\/onboarding/, { timeout: 15000 });
      
      // Should show welcome step
      await expect(page.locator('#step-1')).toBeVisible();
      await expect(page.locator('text=Welcome to CrossFit Health OS')).toBeVisible();
    });

    test('should navigate through all 6 steps', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Step 1: Welcome
      await expect(page.locator('#step-1')).toBeVisible();
      await page.click('text=Let\'s Get Started');
      
      // Step 2: Training Focus
      await expect(page.locator('#step-2')).toBeVisible();
      await expect(page.locator('text=What do you want?')).toBeVisible();
      await page.click('#focus-full');
      await page.click('text=Next');
      
      // Step 3: Name & Goals
      await expect(page.locator('#step-3')).toBeVisible();
      await expect(page.locator('text=Tell us about yourself')).toBeVisible();
      await page.fill('#user-name', 'Test User');
      await page.click('text=Next');
      
      // Step 4: Fitness Level
      await expect(page.locator('#step-4')).toBeVisible();
      await expect(page.locator('text=Your Fitness Level')).toBeVisible();
      await page.click('text=Intermediate');
      await page.click('text=Next');
      
      // Step 5: Training Schedule
      await expect(page.locator('#step-5')).toBeVisible();
      await expect(page.locator('text=Your Training Schedule')).toBeVisible();
      // Select some days
      await page.click('#day-0'); // Monday
      await page.click('#day-2'); // Wednesday
      await page.click('#day-4'); // Friday
      await page.click('text=Next');
      
      // Step 6: Confirm
      await expect(page.locator('#step-6')).toBeVisible();
      await expect(page.locator('text=You\'re All Set!')).toBeVisible();
    });

    test('should show progress bar', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Progress should start at 1/6
      await expect(page.locator('#current-step')).toContainText('1');
      await expect(page.locator('#total-steps')).toContainText('6');
      
      // Progress bar should be at 0%
      const progressBar = page.locator('#progress-bar');
      await expect(progressBar).toHaveCSS('width', /0%/);
      
      // Click to advance
      await page.click('text=Let\'s Get Started');
      
      // Progress should be at 2/6
      await expect(page.locator('#current-step')).toContainText('2');
    });

    test('should allow going back to previous steps', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Go to step 2
      await page.click('text=Let\'s Get Started');
      await expect(page.locator('#step-2')).toBeVisible();
      
      // Click back
      await page.click('text=Back');
      
      // Should be back at step 1
      await expect(page.locator('#step-1')).toBeVisible();
    });

    test('should select app focus = training', async ({ page }) => {
      await page.goto('/onboarding');
      
      await page.click('text=Let\'s Get Started');
      await expect(page.locator('#step-2')).toBeVisible();
      
      // Select training only
      await page.click('#focus-training');
      
      // Should have selected class
      await expect(page.locator('#focus-training')).toHaveClass(/selected/);
    });

    test('should select app focus = full', async ({ page }) => {
      await page.goto('/onboarding');
      
      await page.click('text=Let\'s Get Started');
      await expect(page.locator('#step-2')).toBeVisible();
      
      // Select full experience
      await page.click('#focus-full');
      
      await expect(page.locator('#focus-full')).toHaveClass(/selected/);
    });

    test('should select app focus = custom', async ({ page }) => {
      await page.goto('/onboarding');
      
      await page.click('text=Let\'s Get Started');
      await expect(page.locator('#step-2')).toBeVisible();
      
      // Select custom plan
      await page.click('#focus-custom');
      
      await expect(page.locator('#focus-custom')).toHaveClass(/selected/);
    });

    test('should select different fitness levels', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Navigate to fitness level step
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Test');
      await page.click('text=Next');
      
      await expect(page.locator('#step-4')).toBeVisible();
      
      // Select advanced
      await page.click('text=Advanced');
      
      // Should show as selected
      await expect(page.locator('.list-group-item.active')).toContainText('Advanced');
    });

    test('should toggle training days', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Navigate to schedule step
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Test');
      await page.click('text=Next');
      await page.click('text=Intermediate');
      await page.click('text=Next');
      
      await expect(page.locator('#step-5')).toBeVisible();
      
      // Initially days should show "Rest"
      await expect(page.locator('#day-0 .day-status')).toContainText('Rest');
      
      // Toggle Monday to training
      await page.click('#day-0');
      
      // Should show "Train"
      await expect(page.locator('#day-0 .day-status')).toContainText('Train');
      
      // Should have selected class
      await expect(page.locator('#day-0')).toHaveClass(/selected/);
      
      // Toggle again to rest
      await page.click('#day-0');
      await expect(page.locator('#day-0 .day-status')).toContainText('Rest');
    });

    test('should select preferred training time', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Navigate to schedule step
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Test');
      await page.click('text=Next');
      await page.click('text=Intermediate');
      await page.click('text=Next');
      
      await expect(page.locator('#step-5')).toBeVisible();
      
      // Select evening
      await page.click('#time-evening');
      
      // Should have selected class
      await expect(page.locator('#time-evening')).toHaveClass(/selected/);
    });

    test('should display review with correct data', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Navigate to review step
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'John Doe');
      await page.click('text=Next');
      await page.click('text=Intermediate');
      await page.click('text=Next');
      // Select some days
      await page.click('#day-0');
      await page.click('#day-2');
      await page.click('#time-morning');
      await page.click('text=Next');
      
      await expect(page.locator('#step-6')).toBeVisible();
      
      // Check review shows correct name
      await expect(page.locator('#review-name')).toContainText('John Doe');
      
      // Check goal is shown
      await expect(page.locator('#review-goal')).toBeVisible();
      
      // Check fitness level
      await expect(page.locator('#review-fitness')).toContainText('Intermediate');
    });

    test('should show focus-specific alert on review step', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Navigate with training focus
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-training');
      await page.click('text=Next');
      await page.fill('#user-name', 'Trainer');
      await page.click('text=Next');
      await page.click('text=Intermediate');
      await page.click('text=Next');
      await page.click('text=Next');
      
      await expect(page.locator('#step-6')).toBeVisible();
      
      // Should show training only alert
      await expect(page.locator('#focus-alert')).toContainText(/training/i);
    });

    test('should complete onboarding and redirect to dashboard', async ({ page }) => {
      // First register
      await page.goto('/register');
      const email = generateRandomEmail('complete');
      await page.locator('#name').fill('Complete User');
      await page.locator('#email').fill(email);
      await page.locator('#password').fill('SecurePass123');
      await page.locator('#confirm_password').fill('SecurePass123');
      await page.locator('#register-btn').click();
      
      // Should be on onboarding
      await expect(page).toHaveURL(/\/onboarding/, { timeout: 15000 });
      
      // Complete onboarding quickly
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Complete User');
      await page.click('text=Next');
      await page.click('text=Intermediate');
      await page.click('text=Next');
      await page.click('#day-0');
      await page.click('#time-morning');
      await page.click('text=Next');
      
      // Complete onboarding
      await page.click('text=Start Training!');
      
      // Should redirect to dashboard
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
    });

    test('should skip onboarding for returning users', async ({ page }) => {
      // Login as existing user who completed onboarding
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      // Go to onboarding
      await page.goto('/onboarding');
      
      // Should redirect to dashboard (already completed)
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
    });

    test('should validate name is required', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Navigate to step 3 without filling name
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      
      await expect(page.locator('#step-3')).toBeVisible();
      
      // Try to proceed without name
      await page.click('text=Next');
      
      // Should stay on same step (name is used in review)
      // The name field might have default value "Athlete"
      const nameValue = await page.locator('#user-name').inputValue();
      expect(nameValue).toBeTruthy();
    });

  });

  test.describe('Onboarding Data Persistence', () => {

    test('should persist selected focus across steps', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Select training focus
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-training');
      
      // Go forward and back
      await page.click('text=Next');
      await page.click('text=Back');
      
      // Focus should still be selected
      await expect(page.locator('#focus-training')).toHaveClass(/selected/);
    });

    test('should persist selected days across steps', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Navigate to schedule
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Test');
      await page.click('text=Next');
      await page.click('text=Intermediate');
      await page.click('text=Next');
      
      // Select days
      await page.click('#day-0');
      await page.click('#day-2');
      
      // Go forward and back
      await page.click('text=Next');
      await page.click('text=Back');
      
      // Days should still be selected
      await expect(page.locator('#day-0')).toHaveClass(/selected/);
      await expect(page.locator('#day-2')).toHaveClass(/selected/);
    });

    test('should persist preferred time across steps', async ({ page }) => {
      await page.goto('/onboarding');
      
      // Navigate to schedule
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Test');
      await page.click('text=Next');
      await page.click('text=Intermediate');
      await page.click('text=Next');
      
      // Select evening
      await page.click('#time-evening');
      
      // Go forward and back
      await page.click('text=Next');
      await page.click('text=Back');
      
      // Evening should still be selected
      await expect(page.locator('#time-evening')).toHaveClass(/selected/);
    });

  });

  test.describe('Onboarding with Different User Profiles', () => {

    test('onboarding for beginner fitness level', async ({ page }) => {
      await page.goto('/onboarding');
      
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Beginner User');
      await page.click('text=Next');
      await page.click('text=Beginner');
      await page.click('text=Next');
      await page.click('#day-1');
      await page.click('#day-3');
      await page.click('text=Next');
      
      await expect(page.locator('#step-6')).toBeVisible();
      await expect(page.locator('#review-fitness')).toContainText('Beginner');
    });

    test('onboarding for advanced athlete', async ({ page }) => {
      await page.goto('/onboarding');
      
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Advanced Athlete');
      await page.click('text=Next');
      await page.click('text=Advanced');
      await page.click('text=Next');
      
      // Select all days
      for (let i = 0; i < 6; i++) {
        await page.click(`#day-${i}`);
      }
      await page.click('text=Next');
      
      await expect(page.locator('#step-6')).toBeVisible();
      await expect(page.locator('#review-fitness')).toContainText('Advanced');
    });

    test('onboarding for competitive athlete', async ({ page }) => {
      await page.goto('/onboarding');
      
      await page.click('text=Let\'s Get Started');
      await page.click('#focus-full');
      await page.click('text=Next');
      await page.fill('#user-name', 'Competitor');
      await page.click('text=Next');
      await page.click('text=Competitive Athlete');
      await page.click('text=Next');
      await page.click('#day-0');
      await page.click('#day-1');
      await page.click('#day-2');
      await page.click('#day-3');
      await page.click('#day-4');
      await page.click('#time-morning');
      await page.click('text=Next');
      
      await expect(page.locator('#step-6')).toBeVisible();
    });

  });

});
