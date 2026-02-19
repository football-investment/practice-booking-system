#!/bin/bash

# =============================================================================
# Resume E2E Tests from Checkpoint
# =============================================================================
# Restores database from a saved checkpoint and continues test execution
# from that point forward.
#
# Usage:
#   ./resume_from_checkpoint.sh <checkpoint_name> [test_number]
#
# Available checkpoints:
#   - after_registration  (Resume from test 5: onboarding tests)
#   - after_onboarding    (Resume from test 8: tournament workflow)
#   - after_instructor_workflow (Resume from next test, if any)
#
# Examples:
#   ./resume_from_checkpoint.sh after_registration
#   ./resume_from_checkpoint.sh after_onboarding
#   ./resume_from_checkpoint.sh after_registration 5
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

# Test files (same as run_all_e2e_tests.sh)
TESTS=(
    "tests/e2e/test_user_registration_with_invites.py::test_d1_admin_creates_three_invitation_codes"      # Test 1
    "tests/e2e/test_user_registration_with_invites.py::test_d2_first_user_registers_with_invitation"      # Test 2
    "tests/e2e/test_user_registration_with_invites.py::test_d3_second_user_registers_with_invitation"     # Test 3
    "tests/e2e/test_user_registration_with_invites.py::test_d4_third_user_registers_with_invitation"      # Test 4
    "tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user1"                # Test 5
    "tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user2"                # Test 6
    "tests/e2e/test_complete_onboarding_with_coupon_ui.py::test_complete_onboarding_user3"                # Test 7
    "tests/e2e/test_ui_instructor_application_workflow.py::TestInstructorApplicationWorkflowUI::test_complete_ui_workflow"  # Test 8
)

PYTEST_OPTS="--headed --browser firefox --slowmo 500 -v --tb=short"

# Checkpoint to test mapping
declare -A CHECKPOINT_START_TEST
CHECKPOINT_START_TEST["after_registration"]=5    # Start from test 5 (onboarding_user1)
CHECKPOINT_START_TEST["after_onboarding"]=8      # Start from test 8 (tournament workflow)
CHECKPOINT_START_TEST["after_instructor_workflow"]=9  # No more tests after this

# =============================================================================
# Validate input
# =============================================================================

if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Checkpoint name required${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 <checkpoint_name> [test_number]"
    echo ""
    echo -e "${YELLOW}Available checkpoints:${NC}"
    echo "  - after_registration   → Resume from test 5 (onboarding)"
    echo "  - after_onboarding     → Resume from test 8 (tournament workflow)"
    echo ""
    echo -e "${YELLOW}List saved checkpoints:${NC}"
    echo "  ./snapshot_manager.sh list"
    echo ""
    exit 1
fi

CHECKPOINT_NAME=$1
START_TEST=${2:-${CHECKPOINT_START_TEST[$CHECKPOINT_NAME]}}

# Validate checkpoint exists
if [ -z "$START_TEST" ]; then
    echo -e "${RED}❌ Error: Unknown checkpoint '${CHECKPOINT_NAME}'${NC}"
    echo ""
    echo -e "${YELLOW}Available checkpoints:${NC}"
    for cp in "${!CHECKPOINT_START_TEST[@]}"; do
        echo "  - $cp (starts at test ${CHECKPOINT_START_TEST[$cp]})"
    done
    echo ""
    exit 1
fi

# Validate test number
if [ "$START_TEST" -lt 1 ] || [ "$START_TEST" -gt ${#TESTS[@]} ]; then
    echo -e "${RED}❌ Error: Invalid test number ${START_TEST}${NC}"
    echo -e "${YELLOW}Valid range: 1-${#TESTS[@]}${NC}"
    exit 1
fi

# =============================================================================
# Display plan
# =============================================================================

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           RESUME E2E TESTS FROM CHECKPOINT                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📍 Checkpoint:${NC} ${CHECKPOINT_NAME}"
echo -e "${YELLOW}🎯 Starting from:${NC} Test ${START_TEST}/${#TESTS[@]}"
echo ""
echo -e "${BLUE}Tests to run:${NC}"
for i in $(seq $START_TEST ${#TESTS[@]}); do
    echo "  ${i}. ${TESTS[$((i-1))]}"
done
echo ""
echo -e "${RED}⚠️  WARNING:${NC} This will:"
echo "  1. Restore database from snapshot: ${CHECKPOINT_NAME}"
echo "  2. ALL current database changes will be LOST"
echo "  3. Continue test execution from test ${START_TEST}"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cancelled by user${NC}"
    exit 0
fi

# =============================================================================
# Change to project root
# =============================================================================

cd "$PROJECT_ROOT"

# =============================================================================
# Activate virtual environment
# =============================================================================

echo ""
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# =============================================================================
# STEP 1: Restore database from checkpoint
# =============================================================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}📊 STEP 1: Restoring database from checkpoint${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

if ./tests/e2e/snapshot_manager.sh restore "$CHECKPOINT_NAME"; then
    echo -e "${GREEN}✅ Database restored from checkpoint: ${CHECKPOINT_NAME}${NC}"
else
    echo -e "${RED}❌ Failed to restore checkpoint${NC}"
    echo ""
    echo -e "${YELLOW}Available snapshots:${NC}"
    ./tests/e2e/snapshot_manager.sh list
    exit 1
fi

# =============================================================================
# STEP 2: Setup coupons (only if resuming from after_registration)
# =============================================================================

if [ "$CHECKPOINT_NAME" == "after_registration" ]; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}🎫 STEP 2: Setting up coupons (required for onboarding)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""

    if python tests/e2e/setup_onboarding_coupons.py; then
        echo -e "${GREEN}✅ Coupons created${NC}"
    else
        echo -e "${RED}❌ Coupon setup FAILED${NC}"
        exit 1
    fi
fi

# =============================================================================
# STEP 3: Run tests from checkpoint
# =============================================================================

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}🧪 STEP 3: Running tests from test ${START_TEST}${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

TOTAL_TESTS=${#TESTS[@]}

for TEST_NUMBER in $(seq $START_TEST $TOTAL_TESTS); do
    TEST="${TESTS[$((TEST_NUMBER-1))]}"

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
        elif [[ "$TEST" == *"test_complete_ui_workflow"* ]]; then
            echo -e "${BLUE}📸 Saving snapshot: after_instructor_workflow${NC}"
            ./tests/e2e/snapshot_manager.sh save after_instructor_workflow
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
        echo -e "${YELLOW}🛠️  To retry from this checkpoint:${NC}"
        echo -e "   ${BLUE}./tests/e2e/resume_from_checkpoint.sh ${CHECKPOINT_NAME}${NC}"
        echo ""
        echo -e "${YELLOW}🛠️  To retry this specific test:${NC}"
        echo -e "   ${BLUE}pytest ${TEST} ${PYTEST_OPTS}${NC}"
        echo ""
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "${GREEN}🎯 You are now in an interactive debug shell${NC}"
        echo -e "${YELLOW}Press Ctrl+D to exit debug mode${NC}"
        echo ""

        # Open interactive shell for debugging
        bash

        echo ""
        echo -e "${RED}Exiting test suite due to failure${NC}"
        echo ""
        exit 1
    fi
done

# =============================================================================
# SUCCESS!
# =============================================================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ ALL TESTS PASSED FROM CHECKPOINT! ✅               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${GREEN}✅${NC} Resumed from checkpoint: ${CHECKPOINT_NAME}"
echo -e "  ${GREEN}✅${NC} Ran tests ${START_TEST}-${TOTAL_TESTS} (${TOTAL_TESTS - START_TEST + 1} tests)"
echo -e "  ${GREEN}✅${NC} All tests passed!"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
