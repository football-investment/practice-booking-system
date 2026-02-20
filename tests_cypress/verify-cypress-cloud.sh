#!/bin/bash

# ═════════════════════════════════════════════════════════════════════════════
# Cypress Cloud Integration Verification Script
# ═════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   ./verify-cypress-cloud.sh
#
# Prerequisites:
#   1. Cypress Cloud project created
#   2. Project ID added to cypress.config.js
#   3. GitHub Secrets configured (CYPRESS_PROJECT_ID, CYPRESS_RECORD_KEY)
#   4. Local environment variable CYPRESS_RECORD_KEY set (for local testing)
#
# This script verifies:
#   - Cypress Cloud configuration is valid
#   - Recording works locally
#   - GitHub Secrets are configured
#   - CI/CD workflow is ready for recording
#
# ═════════════════════════════════════════════════════════════════════════════

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Emoji helpers
CHECK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║       Cypress Cloud Integration Verification                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Check cypress.config.js for projectId
# ─────────────────────────────────────────────────────────────────────────────

echo "${BLUE}Step 1: Checking cypress.config.js for projectId...${NC}"

if grep -q "projectId:" cypress.config.js; then
    PROJECT_ID=$(grep "projectId:" cypress.config.js | grep -v "//" | sed -E "s/.*projectId:.*['\"]([^'\"]+)['\"].*/\1/")

    if [ "$PROJECT_ID" = "your-project-id-here" ] || [ -z "$PROJECT_ID" ]; then
        echo "${CROSS} ${RED}Project ID not configured in cypress.config.js${NC}"
        echo "${INFO} Please follow setup instructions in docs/CYPRESS_CLOUD_SETUP.md"
        echo "${INFO} You need to:"
        echo "   1. Create a Cypress Cloud project at https://cloud.cypress.io"
        echo "   2. Get your Project ID from Project Settings"
        echo "   3. Update cypress.config.js with your Project ID"
        exit 1
    else
        echo "${CHECK} ${GREEN}Project ID found: ${PROJECT_ID}${NC}"
    fi
else
    echo "${CROSS} ${RED}No projectId found in cypress.config.js${NC}"
    echo "${INFO} Please add projectId to cypress.config.js"
    echo "${INFO} See docs/CYPRESS_CLOUD_SETUP.md for instructions"
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Check for CYPRESS_RECORD_KEY environment variable
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "${BLUE}Step 2: Checking for CYPRESS_RECORD_KEY environment variable...${NC}"

if [ -z "$CYPRESS_RECORD_KEY" ]; then
    echo "${WARNING} ${YELLOW}CYPRESS_RECORD_KEY not set in environment${NC}"
    echo "${INFO} To test recording locally, set:"
    echo "   export CYPRESS_RECORD_KEY='your-record-key-here'"
    echo ""
    echo "${INFO} Skipping local recording test..."
    SKIP_LOCAL_TEST=true
else
    echo "${CHECK} ${GREEN}CYPRESS_RECORD_KEY is set${NC}"
    SKIP_LOCAL_TEST=false
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Test local recording (if CYPRESS_RECORD_KEY is set)
# ─────────────────────────────────────────────────────────────────────────────

if [ "$SKIP_LOCAL_TEST" = false ]; then
    echo ""
    echo "${BLUE}Step 3: Testing local recording with Cypress Cloud...${NC}"
    echo "${INFO} Running 1 smoke test to verify recording works..."

    # Run a single smoke test with recording
    if npx cypress run \
        --spec 'cypress/e2e/auth/login.cy.js' \
        --env grepTags=@smoke \
        --record \
        --headless \
        --browser chrome \
        > /tmp/cypress-cloud-test.log 2>&1; then

        echo "${CHECK} ${GREEN}Local recording test passed!${NC}"

        # Extract run URL from logs
        if grep -q "https://cloud.cypress.io/projects" /tmp/cypress-cloud-test.log; then
            RUN_URL=$(grep "https://cloud.cypress.io/projects" /tmp/cypress-cloud-test.log | head -1 | sed -E 's/.*https/https/' | sed 's/[^a-zA-Z0-9:\/._-].*//')
            echo "${INFO} View run: ${RUN_URL}"
        fi
    else
        echo "${CROSS} ${RED}Local recording test failed${NC}"
        echo "${INFO} Check logs at: /tmp/cypress-cloud-test.log"
        echo ""
        echo "Common issues:"
        echo "  - Invalid CYPRESS_RECORD_KEY"
        echo "  - Invalid Project ID in cypress.config.js"
        echo "  - Network connectivity issues"
        exit 1
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Check GitHub repository for required secrets
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "${BLUE}Step 4: Checking GitHub repository secrets...${NC}"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "${WARNING} ${YELLOW}GitHub CLI (gh) not installed${NC}"
    echo "${INFO} Cannot verify GitHub secrets automatically"
    echo "${INFO} Please manually verify at:"
    echo "   https://github.com/footballinvestment/practice-booking-system/settings/secrets/actions"
    echo ""
    echo "Required secrets:"
    echo "   - CYPRESS_PROJECT_ID"
    echo "   - CYPRESS_RECORD_KEY"
else
    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        echo "${WARNING} ${YELLOW}Not authenticated with GitHub CLI${NC}"
        echo "${INFO} Run: gh auth login"
        echo "${INFO} Then verify secrets manually at repository settings"
    else
        # Try to list secrets (requires repo access)
        echo "${INFO} Checking for required secrets..."

        # Note: gh secret list only shows secret names, not values
        if gh secret list --repo footballinvestment/practice-booking-system | grep -q "CYPRESS_PROJECT_ID"; then
            echo "${CHECK} ${GREEN}CYPRESS_PROJECT_ID secret exists${NC}"
        else
            echo "${CROSS} ${RED}CYPRESS_PROJECT_ID secret not found${NC}"
            echo "${INFO} Add it at: https://github.com/footballinvestment/practice-booking-system/settings/secrets/actions"
        fi

        if gh secret list --repo footballinvestment/practice-booking-system | grep -q "CYPRESS_RECORD_KEY"; then
            echo "${CHECK} ${GREEN}CYPRESS_RECORD_KEY secret exists${NC}"
        else
            echo "${CROSS} ${RED}CYPRESS_RECORD_KEY secret not found${NC}"
            echo "${INFO} Add it at: https://github.com/footballinvestment/practice-booking-system/settings/secrets/actions"
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Verify workflow configuration
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "${BLUE}Step 5: Verifying GitHub Actions workflow configuration...${NC}"

WORKFLOW_FILE="../.github/workflows/e2e-comprehensive.yml"

if [ -f "$WORKFLOW_FILE" ]; then
    echo "${CHECK} ${GREEN}Workflow file exists: .github/workflows/e2e-comprehensive.yml${NC}"

    # Check for CYPRESS_PROJECT_ID env var
    if grep -q "CYPRESS_PROJECT_ID:" "$WORKFLOW_FILE"; then
        echo "${CHECK} ${GREEN}CYPRESS_PROJECT_ID referenced in workflow${NC}"
    else
        echo "${WARNING} ${YELLOW}CYPRESS_PROJECT_ID not found in workflow${NC}"
    fi

    # Check for recording configuration
    if grep -q "CYPRESS_RECORD_KEY" "$WORKFLOW_FILE"; then
        echo "${CHECK} ${GREEN}CYPRESS_RECORD_KEY referenced in workflow${NC}"
    else
        echo "${WARNING} ${YELLOW}CYPRESS_RECORD_KEY not found in workflow${NC}"
    fi

    # Check for --record flag
    if grep -q "\-\-record" "$WORKFLOW_FILE"; then
        echo "${CHECK} ${GREEN}Recording flag (--record) configured in workflow${NC}"
    else
        echo "${WARNING} ${YELLOW}Recording flag (--record) not found in workflow${NC}"
    fi

    # Check for automatic recording condition
    if grep -q 'if \[ -n "\${{ secrets.CYPRESS_RECORD_KEY }}" \]; then' "$WORKFLOW_FILE"; then
        echo "${CHECK} ${GREEN}Automatic recording enabled when secret is present${NC}"
    else
        echo "${WARNING} ${YELLOW}Automatic recording may not be configured${NC}"
    fi
else
    echo "${CROSS} ${RED}Workflow file not found: $WORKFLOW_FILE${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                   Verification Summary                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

echo "Configuration Status:"
if [ "$PROJECT_ID" != "your-project-id-here" ] && [ -n "$PROJECT_ID" ]; then
    echo "${CHECK} Project ID: ${GREEN}${PROJECT_ID}${NC}"
else
    echo "${CROSS} Project ID: ${RED}Not configured${NC}"
fi

if [ "$SKIP_LOCAL_TEST" = false ]; then
    echo "${CHECK} Local Recording: ${GREEN}Tested and working${NC}"
else
    echo "${INFO} Local Recording: ${YELLOW}Not tested (CYPRESS_RECORD_KEY not set)${NC}"
fi

echo ""
echo "Next Steps:"
echo "1. ${INFO} Verify Cypress Cloud dashboard at:"
echo "   https://cloud.cypress.io/projects/${PROJECT_ID}"
echo ""
echo "2. ${INFO} Trigger a GitHub Actions workflow to test CI recording:"
echo "   - Go to: https://github.com/footballinvestment/practice-booking-system/actions"
echo "   - Select 'E2E Comprehensive' workflow"
echo "   - Click 'Run workflow' → select 'smoke' suite"
echo ""
echo "3. ${INFO} Monitor the run in Cypress Cloud to verify recording works in CI"
echo ""
echo "${CHECK} ${GREEN}Verification complete!${NC}"
echo ""
