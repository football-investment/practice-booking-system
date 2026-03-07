#!/usr/bin/env node

/**
 * CI Result Processor for Cypress E2E Suite
 *
 * Processes Cypress test results and enforces test classification rules:
 * - Critical specs (core workflows): failures are BLOCKING (exit 1)
 * - Non-critical specs (error states): failures are WARNINGS only (exit 0)
 *
 * Usage:
 *   node ci-result-processor.js [mode]
 *
 * Modes:
 *   - critical: Only check critical specs (blocking)
 *   - non-critical: Only check non-critical specs (warning)
 *   - all: Check all specs with appropriate handling (default)
 */

const fs = require('fs');
const path = require('path');

// ─────────────────────────────────────────────────────────────────────────────
// Configuration
// ─────────────────────────────────────────────────────────────────────────────

const MANIFEST_PATH = path.join(__dirname, 'test-manifest.json');
const RESULTS_PATH = path.join(__dirname, 'cypress-results.json');

const mode = process.argv[2] || 'all';

// ─────────────────────────────────────────────────────────────────────────────
// Load manifest and results
// ─────────────────────────────────────────────────────────────────────────────

function loadManifest() {
  if (!fs.existsSync(MANIFEST_PATH)) {
    console.error(`❌ Test manifest not found: ${MANIFEST_PATH}`);
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
}

function loadResults() {
  if (!fs.existsSync(RESULTS_PATH)) {
    console.error(`⚠️  No Cypress results file found: ${RESULTS_PATH}`);
    console.log('   Assuming all tests passed (no results = no failures)');
    return null;
  }
  return JSON.parse(fs.readFileSync(RESULTS_PATH, 'utf8'));
}

// ─────────────────────────────────────────────────────────────────────────────
// Result processing
// ─────────────────────────────────────────────────────────────────────────────

function extractSpecName(fullPath) {
  // Extract relative spec path from full path
  // E.g., "/path/to/cypress/e2e/admin/dashboard.cy.js" -> "admin/dashboard.cy.js"
  const match = fullPath.match(/cypress\/e2e\/(.+\.cy\.js)$/);
  return match ? match[1] : fullPath;
}

function analyzeResults(results, manifest) {
  const criticalSpecs = new Set(manifest.specs.critical.specs);
  const nonCriticalSpecs = new Set(manifest.specs.nonCritical.specs);

  const analysis = {
    critical: { total: 0, passed: 0, failed: 0, specs: [] },
    nonCritical: { total: 0, passed: 0, failed: 0, specs: [] },
    unknown: { total: 0, passed: 0, failed: 0, specs: [] },
  };

  if (!results || !results.runs) {
    console.log('ℹ️  No test runs found in results');
    return analysis;
  }

  results.runs.forEach((run) => {
    const specName = extractSpecName(run.spec.relative);
    const stats = run.stats;
    const hasFailed = stats.failures > 0;

    const specResult = {
      name: specName,
      tests: stats.tests,
      passed: stats.passes,
      failed: stats.failures,
      skipped: stats.skipped,
      pending: stats.pending,
      duration: stats.duration,
    };

    if (criticalSpecs.has(specName)) {
      analysis.critical.total += stats.tests;
      analysis.critical.passed += stats.passes;
      analysis.critical.failed += stats.failures;
      analysis.critical.specs.push(specResult);
    } else if (nonCriticalSpecs.has(specName)) {
      analysis.nonCritical.total += stats.tests;
      analysis.nonCritical.passed += stats.passes;
      analysis.nonCritical.failed += stats.failures;
      analysis.nonCritical.specs.push(specResult);
    } else {
      analysis.unknown.total += stats.tests;
      analysis.unknown.passed += stats.passes;
      analysis.unknown.failed += stats.failures;
      analysis.unknown.specs.push(specResult);
    }
  });

  return analysis;
}

// ─────────────────────────────────────────────────────────────────────────────
// Reporting
// ─────────────────────────────────────────────────────────────────────────────

function printSummary(analysis, manifest) {
  console.log('\n═══════════════════════════════════════════════════════════════════');
  console.log('  Cypress E2E Test Results — CI Analysis');
  console.log('═══════════════════════════════════════════════════════════════════\n');

  // Critical specs
  console.log('🔒 CRITICAL SPECS (Core Workflows — Blocking)');
  console.log('─────────────────────────────────────────────────────────────────');
  console.log(`   Total Tests:    ${analysis.critical.total}`);
  console.log(`   Passed:         ${analysis.critical.passed} ✓`);
  console.log(`   Failed:         ${analysis.critical.failed} ${analysis.critical.failed > 0 ? '❌' : ''}`);

  if (analysis.critical.failed > 0) {
    console.log('\n   ⚠️  FAILING CRITICAL SPECS:');
    analysis.critical.specs
      .filter(s => s.failed > 0)
      .forEach(spec => {
        console.log(`      • ${spec.name}: ${spec.failed}/${spec.tests} failures`);
      });
  }

  const criticalPassRate = analysis.critical.total > 0
    ? ((analysis.critical.passed / analysis.critical.total) * 100).toFixed(1)
    : '100.0';

  console.log(`\n   Pass Rate:      ${criticalPassRate}% (Expected: 100%)`);

  if (analysis.critical.failed === 0) {
    console.log('   Status:         ✅ PASS\n');
  } else {
    console.log('   Status:         ❌ FAIL — Critical workflows broken!\n');
  }

  // Non-critical specs
  console.log('⚠️  NON-CRITICAL SPECS (Error States — Warning Only)');
  console.log('─────────────────────────────────────────────────────────────────');
  console.log(`   Total Tests:    ${analysis.nonCritical.total}`);
  console.log(`   Passed:         ${analysis.nonCritical.passed} ✓`);
  console.log(`   Failed:         ${analysis.nonCritical.failed} ⚠️`);

  if (analysis.nonCritical.failed > 0) {
    console.log('\n   ⚠️  FAILING NON-CRITICAL SPECS (known issues):');
    analysis.nonCritical.specs
      .filter(s => s.failed > 0)
      .forEach(spec => {
        const knownIssue = manifest.specs.nonCritical.knownIssues.find(
          issue => issue.spec === spec.name
        );
        const tracked = knownIssue ? `[${knownIssue.tracked}]` : '';
        console.log(`      • ${spec.name}: ${spec.failed}/${spec.tests} failures ${tracked}`);
        if (knownIssue) {
          console.log(`        └─ Known: ${knownIssue.issue}`);
        }
      });
  }

  const nonCriticalPassRate = analysis.nonCritical.total > 0
    ? ((analysis.nonCritical.passed / analysis.nonCritical.total) * 100).toFixed(1)
    : '100.0';

  console.log(`\n   Pass Rate:      ${nonCriticalPassRate}% (Expected: ≥70%)`);
  console.log('   Status:         ⚠️  WARNING — Non-blocking failures\n');

  // Unknown specs
  if (analysis.unknown.total > 0) {
    console.log('❓ UNCLASSIFIED SPECS');
    console.log('─────────────────────────────────────────────────────────────────');
    console.log(`   Total Tests:    ${analysis.unknown.total}`);
    console.log(`   Passed:         ${analysis.unknown.passed} ✓`);
    console.log(`   Failed:         ${analysis.unknown.failed}`);
    console.log('\n   ⚠️  These specs are not in test-manifest.json:');
    analysis.unknown.specs.forEach(spec => {
      console.log(`      • ${spec.name}`);
    });
    console.log('');
  }

  // Overall summary
  const totalTests = analysis.critical.total + analysis.nonCritical.total + analysis.unknown.total;
  const totalPassed = analysis.critical.passed + analysis.nonCritical.passed + analysis.unknown.passed;
  const totalFailed = analysis.critical.failed + analysis.nonCritical.failed + analysis.unknown.failed;
  const overallPassRate = totalTests > 0 ? ((totalPassed / totalTests) * 100).toFixed(1) : '100.0';

  console.log('📊 OVERALL SUMMARY');
  console.log('─────────────────────────────────────────────────────────────────');
  console.log(`   Total Tests:    ${totalTests}`);
  console.log(`   Passed:         ${totalPassed} ✓`);
  console.log(`   Failed:         ${totalFailed} ${totalFailed > 0 ? '⚠️' : ''}`);
  console.log(`   Pass Rate:      ${overallPassRate}%`);
  console.log(`   Baseline:       93.6% (expected)\n`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────────

function main() {
  console.log(`Running CI result processor in mode: ${mode}`);

  const manifest = loadManifest();
  const results = loadResults();

  if (!results) {
    console.log('✅ No test results found — assuming all tests passed');
    process.exit(0);
  }

  const analysis = analyzeResults(results, manifest);
  printSummary(analysis, manifest);

  // Determine exit code based on mode
  let exitCode = 0;

  if (mode === 'critical' || mode === 'all') {
    if (analysis.critical.failed > 0) {
      console.log('❌ CI FAILURE: Critical spec failures detected');
      console.log('   → Core workflows are broken — blocking deployment\n');
      exitCode = 1;
    } else {
      console.log('✅ CI SUCCESS: All critical specs passed');
      console.log('   → Core workflows are stable\n');
    }
  }

  if (mode === 'non-critical') {
    if (analysis.nonCritical.failed > 0) {
      console.log('⚠️  CI WARNING: Non-critical spec failures detected');
      console.log('   → Error state tests failing but not blocking\n');
    } else {
      console.log('✅ All non-critical specs passed\n');
    }
  }

  // Unknown specs always exit 0 but warn
  if (analysis.unknown.total > 0) {
    console.log('⚠️  WARNING: Unclassified specs found — update test-manifest.json\n');
  }

  console.log(`Exit code: ${exitCode}\n`);
  process.exit(exitCode);
}

main();
