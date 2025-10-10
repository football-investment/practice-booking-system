const { test, expect } = require('@playwright/test');

// Timeline Layout Validation Test Suite
test.describe('Timeline Layout Validation', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to student dashboard
    await page.goto('http://localhost:3000/login');
    
    // Login as test student
    await page.fill('[placeholder="Enter your email"]', 'test.student@devstudio.com');
    await page.fill('[placeholder="Enter your password"]', 'testpass123');
    await page.click('button:has-text("Sign In")');
    
    // Wait for dashboard to load
    await page.waitForURL('**/student/dashboard');
    await page.waitForLoadState('networkidle');
  });

  test('Timeline cards have equal widths', async ({ page }) => {
    console.log('🔍 Testing timeline card widths...');
    
    // Wait for timeline to render
    await page.waitForSelector('.semester-timeline', { timeout: 10000 });
    
    // Get all timeline items
    const timelineItems = await page.$$('.timeline-item');
    expect(timelineItems).toHaveLength(3);
    
    // Get widths of all timeline items
    const widths = [];
    for (const item of timelineItems) {
      const box = await item.boundingBox();
      widths.push(box.width);
      console.log(`Timeline item width: ${box.width}px`);
    }
    
    // Check that all widths are equal (within 5px tolerance)
    const [first, second, third] = widths;
    expect(Math.abs(first - second)).toBeLessThanOrEqual(5);
    expect(Math.abs(second - third)).toBeLessThanOrEqual(5);
    expect(Math.abs(first - third)).toBeLessThanOrEqual(5);
    
    console.log('✅ All timeline cards have equal widths');
  });

  test('No overflow detected warnings', async ({ page }) => {
    console.log('🔍 Checking for overflow warnings...');
    
    // Wait for timeline to render
    await page.waitForSelector('.semester-timeline', { timeout: 10000 });
    
    // Check for overflow detected warnings
    const overflowWarnings = await page.$$('text=OVERFLOW DETECTED!');
    expect(overflowWarnings).toHaveLength(0);
    
    console.log('✅ No overflow warnings found');
  });

  test('Timeline uses CSS Grid layout', async ({ page }) => {
    console.log('🔍 Validating CSS Grid implementation...');
    
    // Get timeline container
    const timeline = await page.$('.semester-timeline');
    
    // Check computed styles
    const displayValue = await timeline.evaluate(el => 
      window.getComputedStyle(el).display
    );
    const gridColumns = await timeline.evaluate(el => 
      window.getComputedStyle(el).gridTemplateColumns
    );
    
    expect(displayValue).toBe('grid');
    // Check that we have 3 columns with similar widths (grid is working)
    const columnWidths = gridColumns.split(' ').filter(w => w.includes('px'));
    expect(columnWidths).toHaveLength(3);
    
    console.log(`✅ Display: ${displayValue}, Grid columns: ${gridColumns}`);
  });

  test('Timeline items have proper overflow handling', async ({ page }) => {
    console.log('🔍 Testing overflow handling...');
    
    const timelineItems = await page.$$('.timeline-item');
    
    for (const item of timelineItems) {
      const overflow = await item.evaluate(el => 
        window.getComputedStyle(el).overflow
      );
      expect(overflow).toBe('hidden');
    }
    
    console.log('✅ All timeline items have overflow: hidden');
  });
});

// Responsive Layout Tests
test.describe('Responsive Timeline Layout', () => {
  const viewports = [
    { name: 'Desktop', width: 1280, height: 720 },
    { name: 'Tablet', width: 768, height: 1024 },
    { name: 'Mobile', width: 375, height: 667 }
  ];

  viewports.forEach(({ name, width, height }) => {
    test(`Timeline layout works on ${name} (${width}x${height})`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await page.goto('http://localhost:3000/student/dashboard');
      
      // Login
      await page.fill('[placeholder="Enter your email"]', 'test.student@devstudio.com');
      await page.fill('[placeholder="Enter your password"]', 'testpass123');
      await page.click('button:has-text("Sign In")');
      
      await page.waitForSelector('.semester-timeline', { timeout: 10000 });
      
      // Check timeline is visible and functional
      const timeline = await page.$('.semester-timeline');
      expect(timeline).toBeTruthy();
      
      const timelineItems = await page.$$('.timeline-item');
      expect(timelineItems.length).toBeGreaterThan(0);
      
      // Take screenshot for visual verification
      await page.screenshot({ 
        path: `e2e-tests/screenshots/timeline-${name.toLowerCase()}.png`,
        fullPage: false,
        clip: { x: 0, y: 0, width: width, height: 400 }
      });
      
      console.log(`✅ Timeline layout works on ${name}`);
    });
  });
});

// Visual Regression Tests
test.describe('Visual Regression - Timeline', () => {
  test('Timeline visual consistency', async ({ page }) => {
    await page.goto('http://localhost:3000/student/dashboard');
    
    // Login
    await page.fill('[name="email"]', 'test.student@devstudio.com');
    await page.fill('[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    await page.waitForSelector('.semester-timeline', { timeout: 10000 });
    
    // Wait for all content to load
    await page.waitForTimeout(2000);
    
    // Take screenshot of timeline section only
    const timelineSection = await page.$('.semester-overview');
    expect(timelineSection).toBeTruthy();
    
    await timelineSection.screenshot({ 
      path: 'e2e-tests/screenshots/timeline-baseline.png' 
    });
    
    console.log('✅ Timeline baseline screenshot captured');
  });
});

// Performance Tests
test.describe('Timeline Performance', () => {
  test('Timeline renders within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('http://localhost:3000/student/dashboard');
    
    // Login
    await page.fill('[name="email"]', 'test.student@devstudio.com');
    await page.fill('[name="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Wait for timeline to be visible and stable
    await page.waitForSelector('.semester-timeline', { timeout: 10000 });
    await page.waitForLoadState('networkidle');
    
    const endTime = Date.now();
    const loadTime = endTime - startTime;
    
    // Timeline should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
    
    console.log(`✅ Timeline loaded in ${loadTime}ms`);
  });
});