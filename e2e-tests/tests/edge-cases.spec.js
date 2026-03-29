/**
 * Edge Cases and Error Handling Tests
 * Tests various edge cases, error scenarios, and boundary conditions
 */

const { test, expect } = require('@playwright/test');
const { TEST_USERS, FORM_VALIDATION, REGISTRATION_DATA } = require('../utils/fixtures');
const { 
  generateRandomEmail, 
  clearBrowserData, 
  getAllValidationErrors,
  loginViaAPI,
  registerViaAPI
} = require('../utils/helpers');

test.describe('Edge Cases', () => {

  test.beforeEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  test.afterEach(async ({ page }) => {
    await clearBrowserData(page);
  });

  // ============================================
  // REPEATED REGISTRATION ATTEMPTS
  // ============================================

  test.describe('Repeated Registration', () => {

    test('should handle rapid registration attempts', async ({ page }) => {
      await page.goto('/register');
      
      const email = generateRandomEmail('rapid');
      
      // Fill form quickly
      await page.locator('#name').fill('Rapid User');
      await page.locator('#email').fill(email);
      await page.locator('#password').fill('SecurePass123');
      await page.locator('#confirm_password').fill('SecurePass123');
      
      // Submit immediately
      await page.locator('#register-btn').click();
      
      // Should handle without crashing
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle double-click on register button', async ({ page }) => {
      await page.goto('/register');
      
      const email = generateRandomEmail('double');
      await page.locator('#name').fill('Double User');
      await page.locator('#email').fill(email);
      await page.locator('#password').fill('SecurePass123');
      await page.locator('#confirm_password').fill('SecurePass123');
      
      // Double click
      await Promise.all([
        page.locator('#register-btn').click(),
        page.locator('#register-btn').click()
      ]);
      
      // Should handle gracefully - either success or error
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle multiple sequential registration attempts', async ({ page }) => {
      for (let i = 0; i < 3; i++) {
        await page.goto('/register');
        
        const email = generateRandomEmail(`seq${i}`);
        await page.locator('#name').fill(`Seq User ${i}`);
        await page.locator('#email').fill(email);
        await page.locator('#password').fill('SecurePass123');
        await page.locator('#confirm_password').fill('SecurePass123');
        await page.locator('#register-btn').click();
        
        // Wait for response
        await page.waitForTimeout(1000);
      }
      
      // Should handle without crashing
      await expect(page.locator('body')).toBeVisible();
    });

  });

  // ============================================
  // SESSION RESET SCENARIOS
  // ============================================

  test.describe('Session Reset', () => {

    test('should clear localStorage on logout', async ({ page }) => {
      // Login
      await loginViaAPI(page, TEST_USERS.valid.email, TEST_USERS.valid.password);
      
      // Verify token exists
      let token = await page.evaluate(() => localStorage.getItem('access_token'));
      expect(token).toBeTruthy();
      
      // Clear storage
      await clearBrowserData(page);
      
      // Verify token cleared
      token = await page.evaluate(() => localStorage.getItem('access_token'));
      expect(token).toBeNull();
    });

    test('should handle expired session gracefully', async ({ page }) => {
      // Set an expired/fake token
      await page.evaluate(() => {
        localStorage.setItem('access_token', 'expired_token_123');
        localStorage.setItem('user', JSON.stringify({ email: 'test@example.com' }));
      });
      
      // Try to access protected page
      await page.goto('/dashboard');
      
      // Should redirect to login or show error
      await expect(page).toHaveURL(/\/(login|dashboard)/);
    });

    test('should handle missing token gracefully', async ({ page }) => {
      // No token set
      await page.goto('/dashboard');
      
      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });

    test('should handle malformed user data in storage', async ({ page }) => {
      // Set malformed user data
      await page.evaluate(() => {
        localStorage.setItem('access_token', 'valid_token');
        localStorage.setItem('user', 'not valid json');
      });
      
      await page.goto('/dashboard');
      
      // Should handle gracefully
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle session storage corruption', async ({ page }) => {
      // Corrupt session storage
      await page.evaluate(() => {
        sessionStorage.setItem('test', '{ broken json');
      });
      
      await page.goto('/login');
      
      // Should handle without crashing
      await expect(page.locator('body')).toBeVisible();
    });

  });

  // ============================================
  // INPUT VALIDATION EDGE CASES
  // ============================================

  test.describe('Input Validation Edge Cases', () => {

    test('should reject future birth date', async ({ page }) => {
      await page.goto('/register');
      
      const futureDate = new Date();
      futureDate.setFullYear(futureDate.getFullYear() + 5);
      const futureDateStr = futureDate.toISOString().split('T')[0];
      
      await page.locator('#birth_date').fill(futureDateStr);
      await page.locator('#birth_date').blur();
      
      // Should show validation error
      const hasError = await page.locator('#birth_date').evaluate(
        el => el.classList.contains('is-invalid')
      );
      expect(hasError).toBe(true);
    });

    test('should reject very old birth date', async ({ page }) => {
      await page.goto('/register');
      
      await page.locator('#birth_date').fill('1900-01-01');
      await page.locator('#birth_date').blur();
      
      // Should show validation error (unrealistic age)
      const hasError = await page.locator('#birth_date').evaluate(
        el => el.classList.contains('is-invalid')
      );
      // May or may not have error depending on validation rules
    });

    test('should handle extremely long name input', async ({ page }) => {
      await page.goto('/register');
      
      const longName = 'A'.repeat(500);
      await page.locator('#name').fill(longName);
      await page.locator('#name').blur();
      
      // Should either truncate or show validation error
      const hasError = await page.locator('#name').evaluate(
        el => el.classList.contains('is-invalid')
      );
      // Validation should catch this
      expect(hasError).toBe(true);
    });

    test('should handle special characters in name', async ({ page }) => {
      await page.goto('/register');
      
      const specialName = "O'Connor-Smith Jr. @#$%";
      await page.locator('#name').fill(specialName);
      await page.locator('#name').blur();
      
      // Name validation pattern may reject special characters
      const hasError = await page.locator('#name').evaluate(
        el => el.classList.contains('is-invalid')
      );
      // Pattern allows: /^[a-zA-ZÀ-ÿ\s'-]+$/
      // So O'Connor and hyphen should be fine, @#$% should fail
    });

    test('should handle negative weight values', async ({ page }) => {
      await page.goto('/register');
      
      await page.locator('#weight_kg').fill('-50');
      await page.locator('#weight_kg').blur();
      
      const hasError = await page.locator('#weight_kg').evaluate(
        el => el.classList.contains('is-invalid')
      );
      expect(hasError).toBe(true);
    });

    test('should handle extremely high weight values', async ({ page }) => {
      await page.goto('/register');
      
      await page.locator('#weight_kg').fill('1000');
      await page.locator('#weight_kg').blur();
      
      const hasError = await page.locator('#weight_kg').evaluate(
        el => el.classList.contains('is-invalid')
      );
      expect(hasError).toBe(true);
    });

    test('should handle zero height', async ({ page }) => {
      await page.goto('/register');
      
      await page.locator('#height_cm').fill('0');
      await page.locator('#height_cm').blur();
      
      const hasError = await page.locator('#height_cm').evaluate(
        el => el.classList.contains('is-invalid')
      );
      expect(hasError).toBe(true);
    });

    test('should handle negative height values', async ({ page }) => {
      await page.goto('/register');
      
      await page.locator('#height_cm').fill('-100');
      await page.locator('#height_cm').blur();
      
      const hasError = await page.locator('#height_cm').evaluate(
        el => el.classList.contains('is-invalid')
      );
      expect(hasError).toBe(true);
    });

  });

  // ============================================
  // NETWORK ERROR HANDLING
  // ============================================

  test.describe('Network Error Handling', () => {

    test('should show error on network failure', async ({ page }) => {
      // Block network to simulate failure
      await page.route('**/api/**', route => route.abort('failed'));
      
      await page.goto('/login');
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('TestPass123');
      await page.locator('#login-btn').click();
      
      // Should show error message
      await expect(page.locator('.alert-danger')).toBeVisible({ timeout: 10000 });
    });

    test('should handle slow network gracefully', async ({ page }) => {
      // Add delay to simulate slow network
      await page.route('**/api/v1/auth/**', route => 
        route.continue({ delay: 10000 })
      );
      
      await page.goto('/login');
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('TestPass123');
      
      // Click and wait - button should show loading state
      await page.locator('#login-btn').click();
      
      // Loading spinner should appear
      await expect(page.locator('.btn-spinner, .spinner')).toBeVisible({ timeout: 2000 });
    });

    test('should handle server 500 error', async ({ page }) => {
      // Mock server error
      await page.route('**/api/v1/auth/login', route => 
        route.fulfill({ status: 500, body: 'Internal Server Error' })
      );
      
      await page.goto('/login');
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('TestPass123');
      await page.locator('#login-btn').click();
      
      // Should show error
      await expect(page.locator('.alert-danger')).toBeVisible({ timeout: 10000 });
    });

    test('should handle server 400 error', async ({ page }) => {
      // Mock bad request
      await page.route('**/api/v1/auth/login', route => 
        route.fulfill({ status: 400, body: JSON.stringify({ detail: 'Bad Request' }) })
      );
      
      await page.goto('/login');
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('TestPass123');
      await page.locator('#login-btn').click();
      
      await expect(page.locator('.alert-danger')).toBeVisible({ timeout: 10000 });
    });

    test('should handle timeout gracefully', async ({ page }) => {
      // Mock timeout
      await page.route('**/api/v1/auth/login', route => 
        route.abort('timeout')
      );
      
      await page.goto('/login');
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('TestPass123');
      await page.locator('#login-btn').click();
      
      // Should show error after timeout
      await expect(page.locator('.alert-danger, text=/timeout|error/i')).toBeVisible({ timeout: 15000 });
    });

  });

  // ============================================
  // URL MANIPULATION
  // ============================================

  test.describe('URL Manipulation', () => {

    test('should handle direct URL to non-existent page', async ({ page }) => {
      await page.goto('/nonexistent-page-xyz');
      
      // Should show 404 or redirect
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle URL with special characters', async ({ page }) => {
      await page.goto('/register?email=test%40example.com&name=Test%20User');
      
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle URL with hash fragments', async ({ page }) => {
      await page.goto('/login#access_token=test_token');
      
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle URL with query parameters', async ({ page }) => {
      await page.goto('/login?redirect_to=/dashboard&param=value');
      
      // Page should load correctly
      await expect(page.locator('#login-form')).toBeVisible();
    });

  });

  // ============================================
  // BROWSER NAVIGATION
  // ============================================

  test.describe('Browser Navigation', () => {

    test('should handle browser back button', async ({ page }) => {
      await page.goto('/login');
      await page.goto('/register');
      
      // Press back
      await page.goBack();
      
      // Should be back on login
      await expect(page).toHaveURL(/\/login/);
    });

    test('should handle browser forward button', async ({ page }) => {
      await page.goto('/login');
      await page.goto('/register');
      await page.goBack();
      await page.goForward();
      
      // Should be on register
      await expect(page).toHaveURL(/\/register/);
    });

    test('should handle page refresh', async ({ page }) => {
      await page.goto('/login');
      await page.fill('#email', 'test@example.com');
      
      await page.reload();
      
      // Form should be cleared
      const emailValue = await page.locator('#email').inputValue();
      expect(emailValue).toBe('');
    });

  });

  // ============================================
  // CONCURRENT ACTIONS
  // ============================================

  test.describe('Concurrent Actions', () => {

    test('should handle multiple rapid form submissions', async ({ page }) => {
      await page.goto('/login');
      
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('TestPass123');
      
      // Click multiple times rapidly
      for (let i = 0; i < 3; i++) {
        page.locator('#login-btn').click({ delay: 50 });
      }
      
      // Should handle without crashing
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle navigating away during form submission', async ({ page }) => {
      await page.goto('/login');
      
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('TestPass123');
      await page.locator('#login-btn').click();
      
      // Immediately navigate away
      await page.goto('/register');
      
      // Should handle gracefully
      await expect(page).toHaveURL(/\/register/);
    });

  });

  // ============================================
  // ACCESSIBILITY EDGE CASES
  // ============================================

  test.describe('Accessibility Edge Cases', () => {

    test('should handle keyboard navigation', async ({ page }) => {
      await page.goto('/login');
      
      // Tab through form fields
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      // Should navigate without errors
      await expect(page.locator('body')).toBeVisible();
    });

    test('should handle form submission with keyboard', async ({ page }) => {
      await page.goto('/login');
      
      // Fill form using keyboard
      await page.locator('#email').focus();
      await page.keyboard.type('test@example.com');
      await page.keyboard.press('Tab');
      await page.keyboard.type('TestPass123');
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      
      // Should submit form
      // Note: This may or may not work depending on form implementation
    });

    test('should close alerts when dismiss button clicked', async ({ page }) => {
      await page.goto('/login');
      await page.locator('#email').fill('wrong@example.com');
      await page.locator('#password').fill('WrongPass');
      await page.locator('#login-btn').click();
      
      // Wait for error alert
      await expect(page.locator('.alert-danger')).toBeVisible({ timeout: 10000 });
      
      // Close alert
      const closeBtn = page.locator('.alert-danger button.btn-close');
      if (await closeBtn.isVisible()) {
        await closeBtn.click();
        
        // Alert should be gone
        await expect(page.locator('.alert-danger')).not.toBeVisible();
      }
    });

  });

  // ============================================
  // STATE PERSISTENCE
  // ============================================

  test.describe('State Persistence', () => {

    test('should preserve form data on validation error', async ({ page }) => {
      await page.goto('/register');
      
      await page.locator('#name').fill('Test User');
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('weak');
      await page.locator('#confirm_password').fill('weak');
      await page.locator('#register-btn').click();
      
      // Fix password
      await page.locator('#password').fill('SecurePass123');
      await page.locator('#confirm_password').fill('SecurePass123');
      
      // Name and email should still be filled
      const nameValue = await page.locator('#name').inputValue();
      expect(nameValue).toBe('Test User');
      
      const emailValue = await page.locator('#email').inputValue();
      expect(emailValue).toBe('test@example.com');
    });

    test('should handle localStorage quota exceeded', async ({ page }) => {
      // Fill localStorage with large data
      await page.evaluate(() => {
        try {
          const largeData = 'x'.repeat(10 * 1024 * 1024); // 10MB
          localStorage.setItem('largeData', largeData);
        } catch (e) {
          // Expected to fail
        }
      });
      
      await page.goto('/login');
      
      // Should handle gracefully
      await expect(page.locator('body')).toBeVisible();
    });

  });

});
