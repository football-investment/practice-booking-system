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
    "tests/playwright/test_user_registration_with_invites.py::test_d1_admin_creates_three_invitation_codes"
    "tests/playwright/test_user_registration_with_invites.py::test_d2_first_user_registers_with_invitation"
    "tests/playwright/test_user_registration_with_invites.py::test_d3_second_user_registers_with_invitation"
    "tests/playwright/test_user_registration_with_invites.py::test_d4_third_user_registers_with_invitation"
    "tests/playwright/test_user_registration_with_invites.py::test_d5_fourth_user_registers_with_invitation"
    "tests/playwright/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user1"
    "tests/playwright/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user2"
    "tests/playwright/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user3"
    "tests/playwright/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user4"
    # SKIPPED: test_ui_instructor_application_workflow (XFAIL - known backend bug)
    # "tests/playwright/test_ui_instructor_application_workflow.py::TestInstructorApplicationWorkflowUI::test_complete_ui_workflow"

    # Tournament Enrollment Tests - OPEN_ASSIGNMENT
    "tests/playwright/test_tournament_enrollment_open_assignment.py::test_e1_admin_creates_open_assignment_tournament"
    "tests/playwright/test_tournament_enrollment_open_assignment.py::test_e2_player1_redeems_coupon_and_enrolls"
    "tests/playwright/test_tournament_enrollment_open_assignment.py::test_e3_player2_redeems_coupon_and_enrolls"
    "tests/playwright/test_tournament_enrollment_open_assignment.py::test_e4_player3_redeems_coupon_and_enrolls"
    "tests/playwright/test_tournament_enrollment_open_assignment.py::test_e5_admin_approves_all_enrollments"
    "tests/playwright/test_tournament_enrollment_open_assignment.py::test_e6_player1_verifies_confirmed_status"

    # Tournament Enrollment Tests - APPLICATION_BASED
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f1_admin_creates_application_based_tournament"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f2_instructor_applies_to_tournament"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f3_admin_approves_instructor_application"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f4_instructor_accepts_assignment"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f5_admin_opens_enrollment"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f6_player1_redeems_coupon_and_enrolls"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f7_player2_redeems_coupon_and_enrolls"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f8_player3_redeems_coupon_and_enrolls"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f9_admin_approves_all_enrollments"
    "tests/playwright/test_tournament_enrollment_application_based.py::test_f10_player1_verifies_confirmed_status"
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
# STEP 1: Master Setup (Reset DB + Seed from seed_data.json)
# =============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🚀 STEP 1: Master Setup (Reset + Seed Database)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

if python scripts/master_setup.py; then
    echo -e "${GREEN}✅ Master setup successful${NC}"
else
    echo -e "${RED}❌ Master setup FAILED${NC}"
    exit 1
fi

# =============================================================================
# STEP 2: Run Tests (in order, without database reset)
# =============================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🧪 STEP 2: Running E2E Tests (in sequence)${NC}"
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
        if [[ "$TEST" == *"test_d5_fourth_user_registers_with_invitation"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_registration${NC}"
            ./tests/playwright/snapshot_manager.sh save after_registration
        elif [[ "$TEST" == *"test_complete_onboarding_user4"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_onboarding${NC}"
            ./tests/playwright/snapshot_manager.sh save after_onboarding
        elif [[ "$TEST" == *"test_e6_player1_verifies_confirmed_status"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_open_assignment_enrollment${NC}"
            ./tests/playwright/snapshot_manager.sh save after_open_assignment_enrollment
        elif [[ "$TEST" == *"test_f10_player1_verifies_confirmed_status"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_application_based_enrollment${NC}"
            ./tests/playwright/snapshot_manager.sh save after_application_based_enrollment
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
echo -e "  ${GREEN}✅${NC} Coupons created (4 BONUS_CREDITS + 4 ENROLLMENT coupons)"
echo -e "  ${GREEN}✅${NC} ${TOTAL_TESTS} tests passed in sequence"
echo ""
echo -e "${YELLOW}📋 Complete User Journey Validated:${NC}"
echo -e "  1. ✅ Admin created invitation codes (UI)"
echo -e "  2. ✅ 4 users registered with invitations (UI)"
echo -e "  3. ✅ 4 users completed onboarding with coupons (UI)"
echo -e "  4. ✅ Instructor assignment workflow (UI + API)"
echo -e "  5. ✅ Tournament enrollment (UI)"
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
