#!/bin/bash
#
# Root Directory Cleanup - Phase 4-5
# Safe, copy-paste ready script for organizing shell scripts and markdown docs
#
# Usage: bash scripts/cleanup_phase4_phase5.sh
#
# This script moves:
# - 30 shell scripts → scripts/ (organized by purpose)
# - 122 markdown docs → docs/ (organized by category)
#

set -e  # Exit on error

echo "========================================="
echo "ROOT DIRECTORY CLEANUP - PHASE 4-5"
echo "========================================="
echo ""

# Get project root (one level up from scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Working directory: $PROJECT_ROOT"
echo ""

# =========================================
# PHASE 4: SHELL SCRIPTS (30 files)
# =========================================

echo "=== PHASE 4: SHELL SCRIPTS RENDEZÉSE ==="
echo ""

# Create directories
mkdir -p scripts/testing/{stability,cypress,ci,e2e}
mkdir -p scripts/monitoring
mkdir -p scripts/deployment

echo "✅ Script directories created"

# Stability test scripts
echo "Moving stability test scripts..."
mv run_stability*.sh scripts/testing/stability/ 2>/dev/null || true
mv run_golden_path*.sh scripts/testing/stability/ 2>/dev/null || true
mv run_true_golden_path*.sh scripts/testing/stability/ 2>/dev/null || true
mv run_production*.sh scripts/testing/stability/ 2>/dev/null || true
mv run_phase1_stability*.sh scripts/testing/stability/ 2>/dev/null || true
echo "Stability scripts: $(ls scripts/testing/stability/*.sh 2>/dev/null | wc -l)"

# Cypress test scripts
echo "Moving cypress test scripts..."
mv run_cypress*.sh scripts/testing/cypress/ 2>/dev/null || true
echo "Cypress scripts: $(ls scripts/testing/cypress/*.sh 2>/dev/null | wc -l)"

# CI simulation scripts
echo "Moving CI test scripts..."
mv run_ci*.sh scripts/testing/ci/ 2>/dev/null || true
mv measure_ci*.sh scripts/testing/ci/ 2>/dev/null || true
echo "CI scripts: $(ls scripts/testing/ci/*.sh 2>/dev/null | wc -l)"

# E2E test scripts
echo "Moving E2E test scripts..."
mv run_all_*.sh scripts/testing/e2e/ 2>/dev/null || true
mv run_master*.sh scripts/testing/e2e/ 2>/dev/null || true
mv run_remaining*.sh scripts/testing/e2e/ 2>/dev/null || true
echo "E2E scripts: $(ls scripts/testing/e2e/*.sh 2>/dev/null | wc -l)"

# Monitoring scripts
echo "Moving monitoring scripts..."
mv monitor*.sh scripts/monitoring/ 2>/dev/null || true
mv analyze*.sh scripts/monitoring/ 2>/dev/null || true
echo "Monitoring scripts: $(ls scripts/monitoring/*.sh 2>/dev/null | wc -l)"

# Deployment scripts
echo "Moving deployment scripts..."
mv run_streamlit.sh scripts/deployment/ 2>/dev/null || true
echo "Deployment scripts: $(ls scripts/deployment/*.sh 2>/dev/null | wc -l)"

# Test helper scripts (remaining test_*.sh)
echo "Moving test helper scripts..."
mv test_*.sh scripts/testing/ 2>/dev/null || true
echo "Test helper scripts: $(ls scripts/testing/test_*.sh 2>/dev/null | wc -l)"

echo ""
echo "✅ PHASE 4 COMPLETE: Shell scripts organized"
echo ""

# =========================================
# PHASE 5: MARKDOWN DOCUMENTATION (122 files)
# =========================================

echo "=== PHASE 5: MARKDOWN DOKUMENTÁCIÓ RENDEZÉSE ==="
echo ""

# Create directories
mkdir -p docs/{planning,baselines,cleanup,summaries,cypress,sandbox,game_config,phase_reports,deprecated,testing,features,performance,refactoring}

echo "✅ Documentation directories created"

# Planning docs
echo "Moving planning documents..."
mv ACTION_PLAN*.md docs/planning/ 2>/dev/null || true
mv IMPLEMENTATION_PLAN*.md docs/planning/ 2>/dev/null || true
mv EPIC*.md docs/planning/ 2>/dev/null || true
mv TODO*.md docs/planning/ 2>/dev/null || true
mv PLAN_*.md docs/planning/ 2>/dev/null || true
mv EXECUTION_CHECKLIST*.md docs/planning/ 2>/dev/null || true
mv STABILIZATION*.md docs/planning/ 2>/dev/null || true
mv PRIORITIZED*.md docs/planning/ 2>/dev/null || true
echo "Planning docs: $(ls docs/planning/*.md 2>/dev/null | wc -l)"

# Baseline reports
echo "Moving baseline documents..."
mv BASELINE*.md docs/baselines/ 2>/dev/null || true
mv CRITICAL_UNIT_TEST_STATUS*.md docs/baselines/ 2>/dev/null || true
mv KNOWN_*.md docs/baselines/ 2>/dev/null || true
echo "Baseline docs: $(ls docs/baselines/*.md 2>/dev/null | wc -l)"

# Cleanup reports
echo "Moving cleanup documents..."
mv CLEANUP*.md docs/cleanup/ 2>/dev/null || true
mv DAY1*.md docs/cleanup/ 2>/dev/null || true
mv IMMEDIATE_ACTIONS*.md docs/cleanup/ 2>/dev/null || true
mv FINAL_CLEANUP*.md docs/cleanup/ 2>/dev/null || true
echo "Cleanup docs: $(ls docs/cleanup/*.md 2>/dev/null | wc -l)"

# Summary reports
echo "Moving summary documents..."
mv *_SUMMARY*.md docs/summaries/ 2>/dev/null || true
mv *_FINAL*.md docs/summaries/ 2>/dev/null || true
mv ITERATION*.md docs/summaries/ 2>/dev/null || true
mv SPRINT*.md docs/summaries/ 2>/dev/null || true
mv WEEK_*.md docs/summaries/ 2>/dev/null || true
mv SESSION_SUMMARY*.md docs/summaries/ 2>/dev/null || true
mv TACTICAL*.md docs/summaries/ 2>/dev/null || true
mv KICKOFF*.md docs/summaries/ 2>/dev/null || true
mv TEAM_STATUS*.md docs/summaries/ 2>/dev/null || true
echo "Summary docs: $(ls docs/summaries/*.md 2>/dev/null | wc -l)"

# Cypress documentation
echo "Moving Cypress documents..."
mv CYPRESS*.md docs/cypress/ 2>/dev/null || true
echo "Cypress docs: $(ls docs/cypress/*.md 2>/dev/null | wc -l)"

# Sandbox documentation
echo "Moving Sandbox documents..."
mv SANDBOX*.md docs/sandbox/ 2>/dev/null || true
mv MINIMAL_SANDBOX*.md docs/sandbox/ 2>/dev/null || true
echo "Sandbox docs: $(ls docs/sandbox/*.md 2>/dev/null | wc -l)"

# Game config documentation
echo "Moving Game Config documents..."
mv GAME_*.md docs/game_config/ 2>/dev/null || true
echo "Game config docs: $(ls docs/game_config/*.md 2>/dev/null | wc -l)"

# Phase reports
echo "Moving Phase reports..."
mv PHASE*.md docs/phase_reports/ 2>/dev/null || true
mv P2_*.md docs/phase_reports/ 2>/dev/null || true
mv P3_*.md docs/phase_reports/ 2>/dev/null || true
mv P4_*.md docs/phase_reports/ 2>/dev/null || true
echo "Phase reports: $(ls docs/phase_reports/*.md 2>/dev/null | wc -l)"

# Testing documentation
echo "Moving Testing documents..."
mv TESTING*.md docs/testing/ 2>/dev/null || true
mv TEST_*.md docs/testing/ 2>/dev/null || true
mv MULTI_ROUND_TEST*.md docs/testing/ 2>/dev/null || true
mv GENESIS_TEST*.md docs/testing/ 2>/dev/null || true
mv QUICK_START*.md docs/testing/ 2>/dev/null || true
mv SANITY_CHECK*.md docs/testing/ 2>/dev/null || true
mv REGRESSION_TEST*.md docs/testing/ 2>/dev/null || true
mv LOW_PRIORITY_TESTS*.md docs/testing/ 2>/dev/null || true
echo "Testing docs: $(ls docs/testing/*.md 2>/dev/null | wc -l)"

# Feature documentation
echo "Moving Feature documents..."
mv FEATURE_*.md docs/features/ 2>/dev/null || true
mv PRODUCT_*.md docs/features/ 2>/dev/null || true
mv REWARDS_*.md docs/features/ 2>/dev/null || true
mv PLACEMENT_*.md docs/features/ 2>/dev/null || true
mv PLAYER_DASHBOARD*.md docs/features/ 2>/dev/null || true
mv VISUALIZATION*.md docs/features/ 2>/dev/null || true
echo "Feature docs: $(ls docs/features/*.md 2>/dev/null | wc -l)"

# Performance documentation
echo "Moving Performance documents..."
mv PATCH_NOTE*.md docs/performance/ 2>/dev/null || true
mv SCALE_SUITE*.md docs/performance/ 2>/dev/null || true
mv STEP1_RENDER*.md docs/performance/ 2>/dev/null || true
mv TABS_RENDERING*.md docs/performance/ 2>/dev/null || true
mv NULL_RESPONSE*.md docs/performance/ 2>/dev/null || true
echo "Performance docs: $(ls docs/performance/*.md 2>/dev/null | wc -l)"

# Refactoring documentation
echo "Moving Refactoring documents..."
mv REFACTOR*.md docs/refactoring/ 2>/dev/null || true
mv SCHEMA_*.md docs/refactoring/ 2>/dev/null || true
mv CONFIG_CONSOLIDATION*.md docs/refactoring/ 2>/dev/null || true
mv REUSABILITY*.md docs/refactoring/ 2>/dev/null || true
mv MIGRATION*.md docs/refactoring/ 2>/dev/null || true
echo "Refactoring docs: $(ls docs/refactoring/*.md 2>/dev/null | wc -l)"

# Deprecated documentation
echo "Moving Deprecated documents..."
mv *.DEPRECATED docs/deprecated/ 2>/dev/null || true
echo "Deprecated docs: $(ls docs/deprecated/*.md 2>/dev/null | wc -l)"

# Bug fix documentation (catch-all for FIX_*, BUG_* patterns)
echo "Moving Bug Fix documents..."
mv FIX_*.md docs/debugging/ 2>/dev/null || true
mv *_BUG*.md docs/debugging/ 2>/dev/null || true
mv LOGOUT_BUTTON*.md docs/debugging/ 2>/dev/null || true
mv GROUP_STAGE*.md docs/debugging/ 2>/dev/null || true
echo "Debugging docs: $(ls docs/debugging/*.md 2>/dev/null | wc -l)"

# README files (special handling - some stay in root)
echo "Organizing README files..."
# Keep main README.md in root, move others
mv README_*.md docs/ 2>/dev/null || true
echo "Specialized READMEs: $(ls docs/README_*.md 2>/dev/null | wc -l)"

# Hungarian docs
echo "Moving Hungarian documents..."
mv VÉGLEGES*.md docs/summaries/ 2>/dev/null || true
mv TERV_A*.md docs/planning/ 2>/dev/null || true
echo "Hungarian docs moved"

echo ""
echo "✅ PHASE 5 COMPLETE: Markdown documentation organized"
echo ""

# =========================================
# FINAL SUMMARY
# =========================================

echo "========================================="
echo "CLEANUP COMPLETE - PHASE 4-5"
echo "========================================="
echo ""
echo "Remaining files in root directory:"
ROOT_FILES=$(ls -1p | grep -v / | wc -l)
echo "  $ROOT_FILES files"
echo ""
echo "Expected remaining files (~8-10):"
echo "  - README.md"
echo "  - CONTRIBUTING.md"
echo "  - ARCHITECTURE.md"
echo "  - COVERAGE_GAP_RISK_REPORT.md"
echo "  - requirements.txt"
echo "  - requirements-test.txt"
echo "  - streamlit_requirements.txt"
echo "  - alembic.ini"
echo "  - pytest.ini"
echo "  - docker-compose.test.yml"
echo "  - mypy.ini"
echo ""
echo "Files organized:"
echo "  - Shell scripts: scripts/"
echo "  - Markdown docs: docs/"
echo "  - Logs: logs/"
echo "  - Snapshots: snapshots/"
echo ""
echo "✅ Root directory cleanup complete!"
echo ""
echo "Next steps:"
echo "  1. Review remaining files: ls -1"
echo "  2. Update .gitignore if needed"
echo "  3. Commit changes: git add -A && git commit"
echo ""
