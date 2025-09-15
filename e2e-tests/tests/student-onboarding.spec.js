// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('🧑‍🎓 Student Onboarding Flow', () => {
  const TEST_STUDENT = {
    email: 'alex.newcomer@student.com',
    password: 'student123',
    profile: {
      nickname: 'Alex',
      phone: '+36301234567',
      emergencyContact: 'Jane Newcomer', 
      emergencyPhone: '+36309876543',
      medicalNotes: 'No known allergies',
      interests: ['Football', 'Tennis']
    }
  };

  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
  });

  test('🔐 Fresh student can login successfully', async ({ page }) => {
    await page.fill('[data-testid="email"]', TEST_STUDENT.email);
    await page.fill('[data-testid="password"]', TEST_STUDENT.password);
    await page.click('[data-testid="login-button"]');
    
    // Should redirect to onboarding for fresh students
    await expect(page).toHaveURL(/.*onboarding/);
    await expect(page.locator('h1')).toContainText('Welcome');
  });

  test('📝 Complete onboarding form - Core Flow', async ({ page }) => {
    // Login
    await page.fill('[data-testid="email"]', TEST_STUDENT.email);
    await page.fill('[data-testid="password"]', TEST_STUDENT.password);
    await page.click('[data-testid="login-button"]');
    
    // Wait for onboarding page
    await page.waitForURL(/.*onboarding/);
    
    // Fill profile information
    await page.fill('[name="nickname"]', TEST_STUDENT.profile.nickname);
    await page.fill('[name="phone"]', TEST_STUDENT.profile.phone);
    await page.fill('[name="emergencyContact"]', TEST_STUDENT.profile.emergencyContact);
    await page.fill('[name="emergencyPhone"]', TEST_STUDENT.profile.emergencyPhone);
    await page.fill('[name="medicalNotes"]', TEST_STUDENT.profile.medicalNotes);
    
    // Select interests (test the JSON serialization fix)
    for (const interest of TEST_STUDENT.profile.interests) {
      await page.check(`[data-testid="interest-${interest.toLowerCase()}"]`);
    }
    
    // Date of birth
    await page.fill('[name="dateOfBirth"]', '1995-05-15');
    
    // Submit onboarding
    await page.click('[data-testid="complete-onboarding"]');
    
    // Should redirect to dashboard after successful onboarding
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator('[data-testid="welcome-message"]')).toBeVisible();
  });

  test('📱 Mobile-friendly onboarding (iOS Safari simulation)', async ({ page }) => {
    // Set iPhone viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Login
    await page.fill('[data-testid="email"]', TEST_STUDENT.email);
    await page.fill('[data-testid="password"]', TEST_STUDENT.password);
    await page.click('[data-testid="login-button"]');
    
    await page.waitForURL(/.*onboarding/);
    
    // Test mobile form interactions
    await page.fill('[name="nickname"]', TEST_STUDENT.profile.nickname);
    
    // Test iOS date picker (if different behavior)
    await page.click('[name="dateOfBirth"]');
    await page.type('[name="dateOfBirth"]', '05/15/1995');
    
    // Test mobile checkboxes
    await page.tap('[data-testid="interest-football"]');
    
    // Scroll to submit button on mobile
    await page.locator('[data-testid="complete-onboarding"]').scrollIntoViewIfNeeded();
    await page.click('[data-testid="complete-onboarding"]');
    
    // Verify mobile dashboard
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('⚠️ Form validation errors', async ({ page }) => {
    // Login
    await page.fill('[data-testid="email"]', TEST_STUDENT.email);
    await page.fill('[data-testid="password"]', TEST_STUDENT.password);
    await page.click('[data-testid="login-button"]');
    
    await page.waitForURL(/.*onboarding/);
    
    // Try to submit empty form
    await page.click('[data-testid="complete-onboarding"]');
    
    // Should show validation errors
    await expect(page.locator('[data-testid="error-nickname"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-phone"]')).toBeVisible();
  });

  test('🔄 Network error handling', async ({ page }) => {
    // Mock network failure
    await page.route('**/api/v1/users/me', route => {
      route.abort('failed');
    });
    
    // Login attempt
    await page.fill('[data-testid="email"]', TEST_STUDENT.email);
    await page.fill('[data-testid="password"]', TEST_STUDENT.password);
    await page.click('[data-testid="login-button"]');
    
    // Should show network error message
    await expect(page.locator('[data-testid="network-error"]')).toBeVisible();
  });
});