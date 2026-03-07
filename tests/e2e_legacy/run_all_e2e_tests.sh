#!/bin/bash

# =============================================================================
# E2E Test Suite Runner
# =============================================================================
# Runs all E2E tests in correct order WITHOUT resetting database between tests
#
# Order:
# 1. Reset database (ONCE at start)
# 2. User registration (creates 3 test users)
# 3. Onboarding workflow (onboard + unlock specialization)
# 4. Instructor assignment workflow (create tournament, assign instructor)
# 5. Tournament enrollment (players enroll)
#
# If any test fails, the script stops and opens debug console
# =============================================================================

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/lfa_intern_system"
export PYTHONPATH="$PROJECT_ROOT"

# Test files in correct order
TESTS=(
    "tests/e2e/test_user_registration_with_invites.py::test_d1_admin_creates_three_invitation_codes"
    "tests/e2e/test_user_registration_with_invites.py::test_d2_first_user_registers_with_invitation"
    "tests/e2e/test_user_registration_with_invites.py::test_d3_second_user_registers_with_invitation"
    "tests/e2e/test_user_registration_with_invites.py::test_d4_third_user_registers_with_invitation"
    "tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user1"
    "tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user2"
    "tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user3"
    "tests/e2e/test_admin_create_tournament_refactored.py::TestAdminCreateTournamentRefactored::test_admin_can_create_tournament_with_type"
    "tests/e2e/test_ui_instructor_application_workflow.py::TestInstructorApplicationWorkflowUI::test_complete_ui_workflow"
)

# Pytest options
# --headed: Show browser window
# --slowmo 500: 500ms delay between actions (so you can see what's happening)
# -v: Verbose output
# --tb=short: Short traceback on failure
# --pdb: Open Python debugger on failure (REMOVED - conflicts with headed mode)
PYTEST_OPTS="--headed --browser firefox --slowmo 500 -v --tb=short"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   E2E TEST SUITE RUNNER                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# =============================================================================
# STEP 1: Reset Database (ONCE)
# =============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📊 STEP 1: Resetting Database${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

if python scripts/reset_database_for_tests.py; then
    echo -e "${GREEN}✅ Database reset successful${NC}"
else
    echo -e "${RED}❌ Database reset FAILED${NC}"
    exit 1
fi

# =============================================================================
# STEP 2: Setup Coupons (required for onboarding test)
# =============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🎫 STEP 2: Setting up coupons${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

if python tests/e2e/setup_onboarding_coupons.py; then
    echo -e "${GREEN}✅ Coupons created${NC}"
else
    echo -e "${RED}❌ Coupon setup FAILED${NC}"
    exit 1
fi

# =============================================================================
# STEP 3: Run Tests (in order, without database reset)
# =============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🧪 STEP 3: Running E2E Tests (in sequence)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

TEST_NUMBER=1
TOTAL_TESTS=${#TESTS[@]}

for TEST in "${TESTS[@]}"; do
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────────${NC}"
    echo -e "${YELLOW}🧪 Test ${TEST_NUMBER}/${TOTAL_TESTS}: ${TEST}${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────────${NC}"
    echo ""

    if pytest "$TEST" $PYTEST_OPTS; then
        echo -e "${GREEN}✅ Test ${TEST_NUMBER} PASSED${NC}"

        # Save snapshot after key test milestones
        if [[ "$TEST" == *"test_d4_third_user_registers_with_invitation"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_registration${NC}"
            ./tests/e2e/snapshot_manager.sh save after_registration
        elif [[ "$TEST" == *"test_complete_onboarding_user3"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_onboarding${NC}"
            ./tests/e2e/snapshot_manager.sh save after_onboarding
        elif [[ "$TEST" == *"test_admin_can_create_tournament_with_type"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_tournament_creation${NC}"
            ./tests/e2e/snapshot_manager.sh save after_tournament_creation
        elif [[ "$TEST" == *"test_complete_ui_workflow"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_application_workflow${NC}"
            ./tests/e2e/snapshot_manager.sh save after_application_workflow
        fi
    else
        echo ""
        echo -e "${RED}╔═══════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║                       ❌ TEST FAILED ❌                            ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${RED}Failed Test: ${TEST}${NC}"
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
        echo ""
        echo -e "${YELLOW}🛠️  Useful Debug Commands:${NC}"
        echo ""
        echo -e "${BLUE}# Check users and credits:${NC}"
        echo -e "  psql \$DATABASE_URL -c \"SELECT id, email, credit_balance, specialization, onboarding_completed FROM users;\""
        echo ""
        echo -e "${BLUE}# Check tournaments:${NC}"
        echo -e "  psql \$DATABASE_URL -c \"SELECT id, name, tournament_status, master_instructor_id FROM semesters;\""
        echo ""
        echo -e "${BLUE}# Check enrollments:${NC}"
        echo -e "  psql \$DATABASE_URL -c \"SELECT se.id, u.email, s.name, se.is_active FROM semester_enrollments se JOIN users u ON se.user_id=u.id JOIN semesters s ON se.semester_id=s.id;\""
        echo ""
        echo -e "${BLUE}# Check licenses:${NC}"
        echo -e "  psql \$DATABASE_URL -c \"SELECT ul.user_id, u.email, ul.specialization_type, ul.current_level FROM user_licenses ul JOIN users u ON ul.user_id=u.id;\""
        echo ""
        echo -e "${BLUE}# Check coupons:${NC}"
        echo -e "  psql \$DATABASE_URL -c \"SELECT code, coupon_type, bonus_credits, times_used, max_uses FROM coupons;\""
        echo ""
        echo -e "${BLUE}# Check screenshots:${NC}"
        echo -e "  ls -lt tests/e2e/screenshots/ | head -10"
        echo ""
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${GREEN}🎯 You are now in an interactive debug shell${NC}"
        echo -e "${GREEN}   - Inspect database state${NC}"
        echo -e "${GREEN}   - Check browser for UI state${NC}"
        echo -e "${GREEN}   - Review test screenshots${NC}"
        echo -e "${GREEN}   - Check backend/frontend logs${NC}"
        echo ""
        echo -e "${YELLOW}Press Ctrl+D to exit debug mode and stop the test suite${NC}"
        echo ""

        # Open interactive shell for debugging
        bash

        echo ""
        echo -e "${RED}Exiting test suite due to failure${NC}"
        echo ""
        exit 1
    fi

    TEST_NUMBER=$((TEST_NUMBER + 1))
done

# =============================================================================
# SUCCESS!
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                   ✅ ALL TESTS PASSED! ✅                          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${GREEN}✅${NC} Database reset successful"
echo -e "  ${GREEN}✅${NC} Coupons created (3 BONUS_CREDITS coupons)"
echo -e "  ${GREEN}✅${NC} ${TOTAL_TESTS} tests passed in sequence"
echo ""
echo -e "${YELLOW}📋 Complete User Journey Validated:${NC}"
echo -e "  1. ✅ Admin created invitation codes (UI)"
echo -e "  2. ✅ 3 users registered with invitations (UI)"
echo -e "  3. ✅ 3 users completed onboarding with coupons (UI)"
echo -e "  4. ✅ Admin created 6 tournaments (3 APPLICATION + 3 OPEN_ASSIGNMENT) (UI)"
echo -e "  5. ✅ Instructor application workflow (UI)"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🗄️  Database State${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Database preserved for manual inspection:${NC}"
echo ""

# Show final database state
psql $DATABASE_URL -c "SELECT id, email, role, credit_balance, specialization, onboarding_completed FROM users ORDER BY id;" 2>/dev/null || echo "  (Unable to query database)"

echo ""
echo -e "${YELLOW}💡 To reset database for next run:${NC}"
echo -e "   ${BLUE}python scripts/reset_database_for_tests.py${NC}"
echo ""
echo -e "${YELLOW}💡 To run tests again:${NC}"
echo -e "   ${BLUE}./tests/e2e/run_all_e2e_tests.sh${NC}"
echo ""
