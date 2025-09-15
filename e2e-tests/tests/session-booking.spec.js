// @ts-check  
const { test, expect } = require('@playwright/test');

test.describe('🏃 Session Booking System', () => {
  const TEST_STUDENT = {
    email: 'emma.fresh@student.com',
    password: 'student123'
  };

  test.beforeEach(async ({ page }) => {
    // Login as completed onboarding student
    await page.goto('/login');
    await page.fill('[data-testid="email"]', TEST_STUDENT.email);
    await page.fill('[data-testid="password"]', TEST_STUDENT.password);
    await page.click('[data-testid="login-button"]');
    
    // Skip onboarding if needed, go directly to sessions
    await page.goto('/student/sessions');
  });

  test('📅 Browse available sessions', async ({ page }) => {
    // Should load session list
    await expect(page.locator('[data-testid="session-list"]')).toBeVisible();
    await expect(page.locator('[data-testid="session-card"]')).toHaveCount(1, { timeout: 10000 });
    
    // Check session information is displayed
    const firstSession = page.locator('[data-testid="session-card"]').first();
    await expect(firstSession.locator('[data-testid="session-title"]')).toBeVisible();
    await expect(firstSession.locator('[data-testid="session-date"]')).toBeVisible();
    await expect(firstSession.locator('[data-testid="session-capacity"]')).toBeVisible();
  });

  test('✅ Book an available session', async ({ page }) => {
    // Find bookable session
    const availableSession = page.locator('[data-testid="session-card"]:has([data-testid="book-button"])').first();
    
    await availableSession.locator('[data-testid="book-button"]').click();
    
    // Should show booking confirmation
    await expect(page.locator('[data-testid="booking-success"]')).toBeVisible();
    
    // Verify booking appears in my bookings
    await page.goto('/student/bookings');
    await expect(page.locator('[data-testid="booking-item"]')).toHaveCount(1);
  });

  test('⏳ Join waitlist when session is full', async ({ page }) => {
    // Find full session (from seed data)
    const fullSession = page.locator('[data-testid="session-card"]:has([data-testid="waitlist-button"])').first();
    
    if (await fullSession.count() > 0) {
      await fullSession.locator('[data-testid="waitlist-button"]').click();
      
      // Should show waitlist confirmation
      await expect(page.locator('[data-testid="waitlist-success"]')).toBeVisible();
      
      // Check waitlist position is displayed
      await expect(page.locator('[data-testid="waitlist-position"]')).toContainText('Position');
    }
  });

  test('❌ Cancel a booking', async ({ page }) => {
    // First book a session
    const availableSession = page.locator('[data-testid="session-card"]:has([data-testid="book-button"])').first();
    await availableSession.locator('[data-testid="book-button"]').click();
    await expect(page.locator('[data-testid="booking-success"]')).toBeVisible();
    
    // Go to my bookings
    await page.goto('/student/bookings');
    
    // Cancel the booking
    await page.locator('[data-testid="cancel-booking"]').first().click();
    await page.locator('[data-testid="confirm-cancel"]').click();
    
    // Should show cancellation confirmation
    await expect(page.locator('[data-testid="cancellation-success"]')).toBeVisible();
  });

  test('📱 Mobile session booking', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Test mobile session browsing
    await expect(page.locator('[data-testid="session-list"]')).toBeVisible();
    
    // Test mobile booking flow
    const sessionCard = page.locator('[data-testid="session-card"]').first();
    await sessionCard.scrollIntoViewIfNeeded();
    
    // Tap booking button (mobile interaction)
    await sessionCard.locator('[data-testid="book-button"]').tap();
    
    // Verify mobile booking success
    await expect(page.locator('[data-testid="booking-success"]')).toBeVisible();
  });

  test('🔍 Filter and search sessions', async ({ page }) => {
    // Test date filter
    await page.fill('[data-testid="date-filter"]', '2025-09-20');
    await expect(page.locator('[data-testid="session-card"]')).toHaveCount(1);
    
    // Test sport type filter
    await page.selectOption('[data-testid="sport-filter"]', 'Football');
    // Sessions should be filtered
    
    // Test search by title
    await page.fill('[data-testid="session-search"]', 'Morning');
    // Should show sessions matching search
  });

  test('⚠️ Booking limits and validation', async ({ page }) => {
    // Try to book multiple sessions (test booking limits)
    const sessionCards = page.locator('[data-testid="session-card"]:has([data-testid="book-button"])');
    const count = await sessionCards.count();
    
    // Book maximum allowed sessions
    for (let i = 0; i < Math.min(count, 3); i++) {
      await sessionCards.nth(i).locator('[data-testid="book-button"]').click();
      await page.waitForTimeout(1000); // Wait between bookings
    }
    
    // Next booking attempt should show limit error
    if (count > 3) {
      await sessionCards.nth(3).locator('[data-testid="book-button"]').click();
      await expect(page.locator('[data-testid="booking-limit-error"]')).toBeVisible();
    }
  });

  test('🕒 Time-based booking restrictions', async ({ page }) => {
    // Test booking deadline (24 hours before session)
    // This would require setting up sessions with different start times
    
    // Mock a session that's too close to start time
    await page.route('**/api/v1/sessions/*/book', route => {
      route.fulfill({
        status: 400,
        body: JSON.stringify({
          detail: "Cannot book session less than 24 hours before start time"
        })
      });
    });
    
    const sessionCard = page.locator('[data-testid="session-card"]').first();
    await sessionCard.locator('[data-testid="book-button"]').click();
    
    await expect(page.locator('[data-testid="booking-deadline-error"]')).toBeVisible();
  });
});