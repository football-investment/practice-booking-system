/**
 * Frontend E2E Tests - Health Dashboard
 * ======================================
 *
 * P2 Stabilization - Comprehensive frontend integration testing
 *
 * Test Coverage:
 * - Health dashboard visualization (status badge, gauge, violation table)
 * - Auto-refresh (30 seconds)
 * - Manual "Run Check Now" trigger
 * - API calls and fallback error handling
 * - Responsive design
 *
 * Test Framework: Cypress
 * Author: Claude Code
 * Date: 2025-10-25
 */

describe('Health Dashboard E2E Tests', () => {
  let adminToken;

  // Setup: Login as admin before all tests
  before(() => {
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/api/v1/auth/login',
      body: {
        email: 'admin@example.com',
        password: 'admin_password'
      }
    }).then((response) => {
      adminToken = response.body.access_token;
      // Store token in localStorage for subsequent requests
      window.localStorage.setItem('token', adminToken);
    });
  });

  // Before each test: Visit admin dashboard
  beforeEach(() => {
    // Set token in localStorage
    cy.window().then((win) => {
      win.localStorage.setItem('token', adminToken);
    });

    // Visit admin dashboard
    cy.visit('/admin/dashboard');
  });

  // =========================================================================
  // TEST 1: Health Dashboard Navigation
  // =========================================================================

  it('should navigate to health dashboard from admin dashboard', () => {
    // Find and click "System Health" stat card
    cy.contains('.admin-stat-card', 'System Health')
      .should('be.visible')
      .click();

    // Verify URL changed to /admin/health
    cy.url().should('include', '/admin/health');

    // Verify dashboard header loaded
    cy.contains('h1', 'Progress-License Health Monitor')
      .should('be.visible');
  });

  // =========================================================================
  // TEST 2: Dashboard Components Render
  // =========================================================================

  it('should render all dashboard components correctly', () => {
    // Navigate to health dashboard
    cy.visit('/admin/health');

    // Verify header
    cy.contains('h1', 'Progress-License Health Monitor')
      .should('be.visible');

    cy.contains('Real-time consistency monitoring')
      .should('be.visible');

    // Verify "Run Check Now" button exists
    cy.contains('button', 'Run Check Now')
      .should('be.visible')
      .should('not.be.disabled');

    // Verify status badge exists
    cy.get('.health-status-badge')
      .should('exist');

    // Verify consistency gauge exists
    cy.get('.consistency-rate-gauge')
      .should('exist');

    // Verify metrics card exists
    cy.get('.metrics-card')
      .should('exist');

    // Verify system info section exists
    cy.get('.system-info')
      .should('exist');
  });

  // =========================================================================
  // TEST 3: Status Badge Color-Coding
  // =========================================================================

  it('should display color-coded status badge', () => {
    cy.visit('/admin/health');

    // Wait for data to load
    cy.get('.health-status-badge', { timeout: 10000 })
      .should('exist');

    // Check for one of the status classes
    cy.get('.health-status-badge')
      .should('satisfy', ($el) => {
        const classList = Array.from($el[0].classList);
        return (
          classList.includes('status-healthy') ||
          classList.includes('status-degraded') ||
          classList.includes('status-critical') ||
          classList.includes('status-unknown')
        );
      });

    // Verify status label exists
    cy.get('.status-label')
      .should('exist')
      .should('not.be.empty');
  });

  // =========================================================================
  // TEST 4: Consistency Gauge Visualization
  // =========================================================================

  it('should render consistency gauge with correct data', () => {
    cy.visit('/admin/health');

    // Wait for gauge to load
    cy.get('.consistency-rate-gauge', { timeout: 10000 })
      .should('exist');

    // Verify gauge SVG exists
    cy.get('.gauge-svg')
      .should('exist');

    // Verify gauge value displayed
    cy.get('.rate-number')
      .should('exist')
      .should('not.be.empty');

    cy.get('.rate-percent')
      .should('contain', '%');

    // Verify gauge legend exists
    cy.get('.gauge-legend')
      .should('exist');

    cy.get('.legend-item')
      .should('have.length', 3); // 3 thresholds
  });

  // =========================================================================
  // TEST 5: Metrics Card Data Display
  // =========================================================================

  it('should display metrics card with current data', () => {
    cy.visit('/admin/health');

    // Wait for metrics to load
    cy.get('.metrics-card', { timeout: 10000 })
      .should('exist');

    // Verify metrics grid exists
    cy.get('.metrics-grid')
      .should('exist');

    // Verify metric items exist
    cy.get('.metric-item')
      .should('have.length.at.least', 4);

    // Verify metric values are numbers or "N/A"
    cy.get('.metric-value').each(($el) => {
      const text = $el.text();
      expect(text).to.satisfy((value) => {
        return !isNaN(parseFloat(value)) || value === 'N/A' || value === 'YES' || value === 'NO';
      });
    });
  });

  // =========================================================================
  // TEST 6: Manual Health Check Trigger
  // =========================================================================

  it('should trigger manual health check when button clicked', () => {
    cy.visit('/admin/health');

    // Intercept API call
    cy.intercept('POST', '**/api/v1/health/check-now').as('manualCheck');

    // Click "Run Check Now" button
    cy.contains('button', 'Run Check Now')
      .should('be.visible')
      .click();

    // Verify button shows "Checking..." state
    cy.contains('button', 'Checking...', { timeout: 1000 })
      .should('be.visible');

    // Wait for API call to complete
    cy.wait('@manualCheck', { timeout: 30000 })
      .its('response.statusCode')
      .should('eq', 200);

    // Verify button returns to "Run Check Now" state
    cy.contains('button', 'Run Check Now', { timeout: 5000 })
      .should('be.visible')
      .should('not.be.disabled');
  });

  // =========================================================================
  // TEST 7: Violations Table (if violations exist)
  // =========================================================================

  it('should display violations table or no violations banner', () => {
    cy.visit('/admin/health');

    // Wait for data to load
    cy.wait(2000);

    // Check for either violations table or no violations banner
    cy.get('body').then(($body) => {
      if ($body.find('.violations-table').length > 0) {
        // Violations table exists
        cy.get('.violations-table')
          .should('be.visible');

        // Verify table headers
        cy.get('.violations-table thead th')
          .should('have.length', 6); // 6 columns

        // Verify table has rows
        cy.get('.violations-table tbody tr')
          .should('have.length.at.least', 1);

      } else {
        // No violations banner should exist
        cy.get('.no-violations-banner')
          .should('be.visible');

        cy.contains('System Healthy')
          .should('be.visible');
      }
    });
  });

  // =========================================================================
  // TEST 8: Auto-Refresh Functionality
  // =========================================================================

  it('should auto-refresh data every 30 seconds', () => {
    cy.visit('/admin/health');

    // Intercept API calls
    cy.intercept('GET', '**/api/v1/health/status').as('getStatus');
    cy.intercept('GET', '**/api/v1/health/metrics').as('getMetrics');
    cy.intercept('GET', '**/api/v1/health/violations').as('getViolations');

    // Wait for initial load
    cy.wait(['@getStatus', '@getMetrics', '@getViolations'], { timeout: 10000 });

    // Get initial "Last updated" timestamp
    cy.get('.last-refresh')
      .invoke('text')
      .as('initialTimestamp');

    // Wait 31 seconds for auto-refresh
    cy.wait(31000);

    // Verify API calls made again
    cy.wait(['@getStatus', '@getMetrics', '@getViolations'], { timeout: 10000 });

    // Verify "Last updated" timestamp changed
    cy.get('@initialTimestamp').then((initialTimestamp) => {
      cy.get('.last-refresh')
        .invoke('text')
        .should('not.equal', initialTimestamp);
    });
  });

  // =========================================================================
  // TEST 9: Error Handling - API Failure
  // =========================================================================

  it('should handle API errors gracefully', () => {
    // Intercept API calls and force error
    cy.intercept('GET', '**/api/v1/health/status', {
      statusCode: 500,
      body: { detail: 'Internal Server Error' }
    }).as('getStatusError');

    cy.visit('/admin/health');

    // Wait for error response
    cy.wait('@getStatusError');

    // Verify error banner displayed
    cy.get('.health-error-banner', { timeout: 5000 })
      .should('be.visible')
      .should('contain', 'Failed to load health monitoring data');
  });

  // =========================================================================
  // TEST 10: Responsive Design - Mobile View
  // =========================================================================

  it('should render correctly on mobile devices', () => {
    // Set viewport to mobile size
    cy.viewport('iphone-x');

    cy.visit('/admin/health');

    // Verify header stacks vertically
    cy.get('.health-dashboard-header')
      .should('be.visible');

    // Verify status overview cards stack vertically
    cy.get('.health-status-overview')
      .should('be.visible');

    // Verify "Run Check Now" button is full-width
    cy.contains('button', 'Run Check Now')
      .should('be.visible')
      .should('have.css', 'width', '100%');

    // Verify table is scrollable horizontally
    cy.get('.violations-table-container')
      .should('have.css', 'overflow-x', 'auto');
  });

  // =========================================================================
  // TEST 11: System Info Accuracy
  // =========================================================================

  it('should display accurate system info', () => {
    cy.visit('/admin/health');

    // Wait for data to load
    cy.get('.system-info', { timeout: 10000 })
      .should('exist');

    // Verify system info items
    cy.get('.system-info ul li')
      .should('have.length.at.least', 3);

    // Verify "Total users monitored" exists
    cy.contains('Total users monitored')
      .should('be.visible');

    // Verify "Auto-refresh" mentions 30 seconds
    cy.contains('Auto-refresh: Every 30 seconds')
      .should('be.visible');

    // Verify "Backend checks" mentions 5 minutes
    cy.contains('Backend checks: Every 5 minutes')
      .should('be.visible');
  });

  // =========================================================================
  // TEST 12: Integration Test - Full Workflow
  // =========================================================================

  it('should complete full workflow: navigate → check → verify → refresh', () => {
    // Step 1: Navigate from admin dashboard
    cy.visit('/admin/dashboard');
    cy.contains('.admin-stat-card', 'System Health').click();
    cy.url().should('include', '/admin/health');

    // Step 2: Verify initial state
    cy.get('.health-status-badge', { timeout: 10000 }).should('exist');
    cy.get('.consistency-rate-gauge').should('exist');
    cy.get('.metrics-card').should('exist');

    // Step 3: Trigger manual check
    cy.intercept('POST', '**/api/v1/health/check-now').as('manualCheck');
    cy.contains('button', 'Run Check Now').click();
    cy.wait('@manualCheck', { timeout: 30000 });

    // Step 4: Verify dashboard updates
    cy.get('.status-label')
      .should('exist')
      .should('not.be.empty');

    cy.get('.rate-number')
      .should('exist')
      .should('not.be.empty');

    // Step 5: Wait for auto-refresh
    cy.intercept('GET', '**/api/v1/health/status').as('autoRefresh');
    cy.wait(31000);
    cy.wait('@autoRefresh');

    // Step 6: Verify still functional
    cy.contains('h1', 'Progress-License Health Monitor').should('be.visible');
  });
});
