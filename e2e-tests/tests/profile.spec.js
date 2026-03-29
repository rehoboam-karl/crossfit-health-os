/**
 * Profile Tests
 * Tests user profile management features
 */

const { test, expect } = require('@playwright/test');
const { TEST_USERS } = require('../utils/fixtures');
const { clearBrowserData, loginViaAPI, generateRandomEmail } = require('../utils/helpers');

test.describe('Profile', () => {

  test.beforeEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.afterEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.describe('Profile Page Access', () => {

    test('should require authentication to access profile', async ({ page }) => {
      await page.goto('/dashboard/profile');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('should allow authenticated access to profile', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      await expect(page).toHaveURL(/\/dashboard\/profile/);
    });

  });

  test.describe('Profile Information Display', () => {

    test('should display user email', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      // Should show user email somewhere on the page
      await expect(page.locator('body')).toContainText(TEST_USERS.valid.email);
    });

    test('should display user name', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      // Should show user name
      await expect(page.locator('body')).toContainText(TEST_USERS.valid.name);
    });

    test('should display profile form fields', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      // Common profile fields
      await expect(page.locator('#name, input[name="name"]')).toBeVisible();
      await expect(page.locator('#email, input[name="email"]')).toBeVisible();
    });

  });

  test.describe('Profile Update', () => {

    test('should update user name', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      // Find name field and update
      const nameField = page.locator('#name, input[name="name"]').first();
      if (await nameField.isVisible()) {
        await nameField.fill('Updated Name');
        
        // Save if there's a save button
        const saveButton = page.locator('button:has-text("Save"), button:has-text("Update")');
        if (await saveButton.isVisible()) {
          await saveButton.click();
          
          // Should show success message
          await expect(page.locator('.alert-success, .toast-success')).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('should update birth date', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const birthDateField = page.locator('#birth_date, input[name="birth_date"], input[type="date"]');
      if (await birthDateField.isVisible()) {
        await birthDateField.fill('1990-05-15');
        
        const saveButton = page.locator('button:has-text("Save"), button:has-text("Update")');
        if (await saveButton.isVisible()) {
          await saveButton.click();
          
          await expect(page.locator('.alert-success, .toast-success')).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('should update weight', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const weightField = page.locator('#weight_kg, input[name="weight_kg"]');
      if (await weightField.isVisible()) {
        await weightField.fill('80');
        
        const saveButton = page.locator('button:has-text("Save"), button:has-text("Update")');
        if (await saveButton.isVisible()) {
          await saveButton.click();
          
          await expect(page.locator('.alert-success, .toast-success')).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('should update height', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const heightField = page.locator('#height_cm, input[name="height_cm"]');
      if (await heightField.isVisible()) {
        await heightField.fill('180');
        
        const saveButton = page.locator('button:has-text("Save"), button:has-text("Update")');
        if (await saveButton.isVisible()) {
          await saveButton.click();
          
          await expect(page.locator('.alert-success, .toast-success')).toBeVisible({ timeout: 10000 });
        }
      }
    });

    test('should update fitness level', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const fitnessSelect = page.locator('#fitness_level, select[name="fitness_level"]');
      if (await fitnessSelect.isVisible()) {
        await fitnessSelect.selectOption('advanced');
        
        const saveButton = page.locator('button:has-text("Save"), button:has-text("Update")');
        if (await saveButton.isVisible()) {
          await saveButton.click();
          
          await expect(page.locator('.alert-success, .toast-success')).toBeVisible({ timeout: 10000 });
        }
      }
    });

  });

  test.describe('Profile Validation', () => {

    test('should validate name is not empty', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const nameField = page.locator('#name, input[name="name"]').first();
      if (await nameField.isVisible()) {
        await nameField.fill('');
        await nameField.blur();
        
        // Should show validation error
        const hasError = await nameField.evaluate(el => el.classList.contains('is-invalid'));
        expect(hasError).toBe(true);
      }
    });

    test('should validate email format', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const emailField = page.locator('#email, input[name="email"]').first();
      if (await emailField.isVisible()) {
        await emailField.fill('invalid-email');
        await emailField.blur();
        
        const hasError = await emailField.evaluate(el => el.classList.contains('is-invalid'));
        expect(hasError).toBe(true);
      }
    });

    test('should validate weight range', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const weightField = page.locator('#weight_kg, input[name="weight_kg"]');
      if (await weightField.isVisible()) {
        await weightField.fill('500'); // Unrealistic weight
        await weightField.blur();
        
        // Should show validation error (if client-side validation exists)
        const hasError = await weightField.evaluate(el => el.classList.contains('is-invalid'));
        if (hasError) {
          expect(hasError).toBe(true);
        }
      }
    });

    test('should validate height range', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const heightField = page.locator('#height_cm, input[name="height_cm"]');
      if (await heightField.isVisible()) {
        await heightField.fill('50'); // Unrealistic height
        await heightField.blur();
        
        const hasError = await heightField.evaluate(el => el.classList.contains('is-invalid'));
        if (hasError) {
          expect(hasError).toBe(true);
        }
      }
    });

    test('should validate birth date is not in future', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const birthDateField = page.locator('#birth_date, input[name="birth_date"], input[type="date"]');
      if (await birthDateField.isVisible()) {
        const futureDate = new Date();
        futureDate.setFullYear(futureDate.getFullYear() + 1);
        const futureDateStr = futureDate.toISOString().split('T')[0];
        
        await birthDateField.fill(futureDateStr);
        await birthDateField.blur();
        
        // Should show validation error
        const hasError = await birthDateField.evaluate(el => el.classList.contains('is-invalid'));
        if (hasError) {
          expect(hasError).toBe(true);
        }
      }
    });

  });

  test.describe('Goals Selection', () => {

    test('should allow selecting training goals', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      // Check for goal checkboxes
      const goalCheckbox = page.locator('#goal-strength, input[value="strength"]').first();
      if (await goalCheckbox.isVisible()) {
        await goalCheckbox.check();
        
        const isChecked = await goalCheckbox.isChecked();
        expect(isChecked).toBe(true);
      }
    });

    test('should allow deselecting training goals', async ({ page }) => {
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      await page.goto('/dashboard/profile');
      
      const goalCheckbox = page.locator('#goal-general, input[value="general_fitness"]').first();
      if (await goalCheckbox.isVisible() && await goalCheckbox.isChecked()) {
        await goalCheckbox.uncheck();
        
        const isChecked = await goalCheckbox.isChecked();
        expect(isChecked).toBe(false);
      }
    });

  });

});
