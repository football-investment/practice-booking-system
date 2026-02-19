#!/bin/bash

# Champion Badge Regression Test Runner
# =====================================
#
# This script runs the Champion badge regression test locally
# to verify the fix before pushing to CI/CD
#
# Prerequisites:
# - Streamlit app running on http://localhost:8501
# - Database with junior.intern@lfa.com user
# - Playwright installed (pip install playwright && playwright install)
#
# Usage:
#   ./tests_e2e/run_champion_regression.sh
#
# Exit codes:
#   0 - Test passed (Champion badge displays correctly)
#   1 - Test failed (Champion badge shows "No ranking data")

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🏆 Champion Badge Regression Test"
echo "=================================="
echo ""

# Check if Streamlit is running
echo "📡 Checking if Streamlit is running on http://localhost:8501..."
if ! curl -s -f http://localhost:8501 > /dev/null; then
    echo -e "${RED}❌ ERROR: Streamlit is not running on http://localhost:8501${NC}"
    echo ""
    echo "Please start Streamlit first:"
    echo "  DATABASE_URL=\"postgresql://postgres:postgres@localhost:5432/lfa_intern_system\" streamlit run streamlit_app/Home.py"
    echo ""
    exit 1
fi
echo -e "${GREEN}✅ Streamlit is running${NC}"
echo ""

# Activate virtual environment if it exists
if [ -d "venv/bin" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Check if Playwright is installed
echo "🎭 Checking Playwright installation..."
if ! python3 -c "import playwright" 2>/dev/null; then
    echo -e "${RED}❌ ERROR: Playwright is not installed${NC}"
    echo ""
    echo "Install with:"
    echo "  pip install playwright pytest-playwright"
    echo "  playwright install chromium"
    echo ""
    exit 1
fi
echo -e "${GREEN}✅ Playwright is installed${NC}"
echo ""

# Run the test
echo "🧪 Running Champion badge regression test..."
echo ""

cd "$(dirname "$0")/.." || exit

if python3 -m pytest tests_e2e/test_champion_badge_regression.py \
    -v \
    -m "golden_path" \
    --tb=short \
    --maxfail=1; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ TEST PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Champion badge displays correctly!"
    echo "Safe to push to CI/CD."
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ TEST FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${RED}REGRESSION DETECTED:${NC}"
    echo "Champion badge shows 'No ranking data'"
    echo ""
    echo "Check screenshot: tests_e2e/screenshots/champion_badge_regression_FAILED.png"
    echo ""
    echo -e "${YELLOW}DO NOT PUSH TO CI/CD${NC}"
    echo "Fix the issue before committing."
    echo ""
    exit 1
fi
