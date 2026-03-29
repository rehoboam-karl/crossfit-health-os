const { test, expect } = require('@playwright/test');

test('debug validation call', async ({ page }) => {
  await page.goto('http://localhost:8000/login');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
  
  // Directly call validateForm with the form
  const result = await page.evaluate(() => {
    const $form = $('#login-form');
    return FormValidator.validateForm($form);
  });
  console.log('Validation result:', JSON.stringify(result, null, 2));
  
  // Now check if email has is-invalid class
  const emailClass = await page.locator('#email').evaluate(el => el.className);
  console.log('Email class after validateForm:', emailClass);
  
  // Check for invalid-feedback
  const feedbackCount = await page.locator('.invalid-feedback').count();
  console.log('Feedback count:', feedbackCount);
  
  expect(result.valid).toBe(false);
});
