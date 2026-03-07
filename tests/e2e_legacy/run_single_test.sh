#!/bin/bash

# =============================================================================
# Single Test Runner with Snapshot Restore
# =============================================================================
# Run a single E2E test after restoring database to a specific snapshot
# This allows quick iteration on failing tests without rerunning entire suite
#
# Usage:
#   ./run_single_test.sh <snapshot_name> <test_path>
#
# Examples:
#   ./run_single_test.sh after_onboarding tests/e2e/test_ui_instructor_application_workflow.py::TestInstructorApplicationWorkflowUI::test_complete_ui_workflow
#   ./run_single_test.sh after_registration tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user1
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
export PYTHONPATH="$PROJECT_ROOT"

# Pytest options (same as master test runner)
PYTEST_OPTS="--headed --browser firefox --slowmo 500 -v --tb=short"

# Check arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    echo -e "${RED}❌ Error: Missing arguments${NC}"
    echo ""
    echo "Usage:"
    echo -e "  ${GREEN}$0 <snapshot_name> <test_path>${NC}"
    echo ""
    echo "Available snapshots:"
    ./tests/e2e/snapshot_manager.sh list
    echo ""
    echo "Examples:"
    echo -e "  ${BLUE}$0 after_onboarding tests/e2e/test_ui_instructor_application_workflow.py::TestInstructorApplicationWorkflowUI::test_complete_ui_workflow${NC}"
    echo -e "  ${BLUE}$0 after_registration tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user1${NC}"
    echo ""
    exit 1
fi

SNAPSHOT_NAME=$1
TEST_PATH=$2

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              SINGLE TEST RUNNER WITH SNAPSHOT RESTORE              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# =============================================================================
# STEP 1: Restore Database Snapshot
# =============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📂 STEP 1: Restoring database snapshot${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

if ./tests/e2e/snapshot_manager.sh restore "$SNAPSHOT_NAME"; then
    echo -e "${GREEN}✅ Snapshot restored${NC}"
else
    echo -e "${RED}❌ Snapshot restore FAILED${NC}"
    exit 1
fi

# =============================================================================
# STEP 2: Run Single Test
# =============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🧪 STEP 2: Running test${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Test: ${TEST_PATH}${NC}"
echo ""

if pytest "$TEST_PATH" $PYTEST_OPTS; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                      ✅ TEST PASSED! ✅                            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                       ❌ TEST FAILED ❌                            ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🔍 DEBUG MODE${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${GREEN}✅ Firefox browser window is STILL OPEN - inspect the UI state!${NC}"
    echo -e "${GREEN}✅ Backend (FastAPI) is STILL RUNNING on http://localhost:8000${NC}"
    echo -e "${GREEN}✅ Frontend (Streamlit) is STILL RUNNING on http://localhost:8501${NC}"
    echo ""
    echo -e "${BLUE}📊 Database: ${DATABASE_URL}${NC}"
    echo -e "${BLUE}📸 Snapshot used: ${SNAPSHOT_NAME}${NC}"
    echo ""
    echo -e "${YELLOW}🛠️  Useful Debug Commands:${NC}"
    echo ""
    echo -e "${BLUE}# Check users:${NC}"
    echo -e "  psql \$DATABASE_URL -c \"SELECT id, email, credit_balance, specialization, onboarding_completed FROM users;\""
    echo ""
    echo -e "${BLUE}# Check tournaments:${NC}"
    echo -e "  psql \$DATABASE_URL -c \"SELECT id, name, tournament_status, master_instructor_id FROM semesters;\""
    echo ""
    echo -e "${BLUE}# Check enrollments:${NC}"
    echo -e "  psql \$DATABASE_URL -c \"SELECT se.id, u.email, s.name, se.is_active FROM semester_enrollments se JOIN users u ON se.user_id=u.id JOIN semesters s ON se.semester_id=s.id;\""
    echo ""
    echo -e "${BLUE}# Restore snapshot and retry:${NC}"
    echo -e "  $0 $SNAPSHOT_NAME $TEST_PATH"
    echo ""
    echo -e "${BLUE}# Check screenshots:${NC}"
    echo -e "  ls -lt tests/e2e/screenshots/ | head -10"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${GREEN}🎯 You are now in an interactive debug shell${NC}"
    echo -e "${GREEN}   Press Ctrl+D to exit${NC}"
    echo ""

    # Open interactive shell for debugging
    bash

    exit 1
fi
