/**
 * Helper functions for Playwright tests
 */

const { page } = require('@playwright/test');

/**
 * Generate random email for unique test users
 */
function generateRandomEmail(prefix = 'test') {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 10000);
  return `${prefix}+${timestamp}+${random}@example.com`;
}

/**
 * Generate random password
 */
function generatePassword(length = 12) {
  const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%';
  let password = '';
  for (let i = 0; i < length; i++) {
    password += charset.charAt(Math.floor(Math.random() * charset.length));
  }
  return password;
}

/**
 * Clear all browser storage
 */
async function clearBrowserData(page) {
  try {
    await page.context().clearCookies();
    await page.evaluate(() => {
      try {
        localStorage.clear();
        sessionStorage.clear();
      } catch (e) {
        // Ignore - may not be accessible yet
      }
    });
  } catch (e) {
    // Ignore errors during cleanup
  }
}

/**
 * Wait for network idle
 */
async function waitForNetworkIdle(page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Take screenshot with name
 */
async function takeScreenshot(page, name) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  await page.screenshot({ 
    path: `screenshots/${name}-${timestamp}.png`,
    fullPage: true 
  });
}

/**
 * Check if element is visible
 */
async function isVisible(page, selector) {
  const element = page.locator(selector);
  return await element.isVisible().catch(() => false);
}

/**
 * Get alert message text
 */
async function getAlertText(page) {
  const alert = page.locator('.alert');
  if (await alert.isVisible()) {
    return alert.textContent();
  }
  return null;
}

/**
 * Fill form with data object
 */
async function fillForm(page, data) {
  for (const [field, value] of Object.entries(data)) {
    const input = page.locator(`[name="${field}"], [id="${field}"]`).first();
    if (await input.isVisible()) {
      await input.fill(value);
    }
  }
}

/**
 * Click checkbox by ID
 */
async function checkCheckbox(page, checkboxId) {
  const checkbox = page.locator(`#${checkboxId}`);
  if (await checkbox.isVisible() && !(await checkbox.isChecked())) {
    await checkbox.check();
  }
}

/**
 * Wait for redirect to URL
 */
async function waitForRedirect(page, urlPattern, timeout = 10000) {
  await page.waitForURL(urlPattern, { timeout });
}

/**
 * Get validation error message for a field
 */
async function getFieldError(page, fieldId) {
  const errorLocator = page.locator(`#${fieldId}`).locator('..').locator('.invalid-feedback');
  if (await errorLocator.isVisible()) {
    return errorLocator.textContent();
  }
  return null;
}

/**
 * Check if form has validation error
 */
async function hasValidationError(page, fieldId) {
  const input = page.locator(`#${fieldId}`);
  return await input.evaluate(el => el.classList.contains('is-invalid'));
}

/**
 * Get all form validation errors
 */
async function getAllValidationErrors(page) {
  const errors = [];
  const errorLocators = page.locator('.invalid-feedback:visible');
  const count = await errorLocators.count();
  for (let i = 0; i < count; i++) {
    errors.push(await errorLocators.nth(i).textContent());
  }
  return errors;
}

/**
 * Login via API and set localStorage
 */
async function loginViaAPI(page, email, password) {
  const response = await page.request.post(`${process.env.API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/login`, {
    data: { email, password }
  });
  
  if (response.ok()) {
    const data = await response.json();
    await page.evaluate((tokens) => {
      localStorage.setItem('access_token', tokens.access_token);
      if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token);
      }
    }, data);
    
    return data;
  }
  return null;
}

/**
 * Register via API
 */
async function registerViaAPI(page, userData) {
  const response = await page.request.post(`${process.env.API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/register`, {
    data: userData
  });
  
  if (response.ok()) {
    const data = await response.json();
    return data;
  }
  return null;
}

/**
 * Complete onboarding via API
 */
async function completeOnboardingViaAPI(page, onboardingData) {
  // First login
  await loginViaAPI(page, onboardingData.email, onboardingData.password);
  
  // Then complete onboarding
  const response = await page.request.post(`${process.env.API_BASE_URL || 'http://localhost:8000/api/v1'}/onboarding/complete`, {
    data: {
      name: onboardingData.name,
      app_focus: onboardingData.appFocus || 'full',
      primary_goal: onboardingData.primaryGoal || 'both',
      fitness_level: onboardingData.fitnessLevel || 'intermediate',
      available_days: onboardingData.availableDays || ['monday', 'wednesday', 'friday'],
      preferred_time: onboardingData.preferredTime || 'morning',
      methodologies: onboardingData.methodologies || ['hwpo'],
      nutrition_enabled: onboardingData.appFocus !== 'training'
    }
  });
  
  return response.ok();
}

/**
 * Assert element contains text
 */
async function assertContains(page, selector, text) {
  const element = page.locator(selector);
  await expect(element).toContainText(text);
}

/**
 * Assert URL matches pattern
 */
async function assertURL(page, pattern) {
  await expect(page).toHaveURL(pattern);
}

module.exports = {
  generateRandomEmail,
  generatePassword,
  clearBrowserData,
  waitForNetworkIdle,
  takeScreenshot,
  isVisible,
  getAlertText,
  fillForm,
  checkCheckbox,
  waitForRedirect,
  getFieldError,
  hasValidationError,
  getAllValidationErrors,
  loginViaAPI,
  registerViaAPI,
  completeOnboardingViaAPI,
  assertContains,
  assertURL
};
