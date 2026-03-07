#!/usr/bin/env bash
# =============================================================================
# Critical E2E Suite Validation Script
# =============================================================================
#
# PURPOSE:
#   Validates the critical E2E test suite (170 tests) before pushing changes.
#   This serves as the primary quality gate while GitHub Actions is unavailable.
#
# USAGE:
#   ./scripts/validate_critical_e2e.sh
#
# REQUIREMENTS:
#   - Backend running on http://localhost:8000
#   - Streamlit running on http://localhost:8501
#   - Node.js environment (for Cypress)
#
# EXIT CODES:
#   0 - All critical tests passed (170/170)
#   1 - Test failures or infrastructure issues
# =============================================================================

set -eo pipefail

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

err()  { echo -e "${RED}${BOLD}❌  $*${NC}" >&2; }
warn() { echo -e "${YELLOW}⚠️   $*${NC}"; }
info() { echo -e "${CYAN}ℹ️   $*${NC}"; }
ok()   { echo -e "${GREEN}✅  $*${NC}"; }

# ── Config ───────────────────────────────────────────────────────────────────
REPO_ROOT="$(git rev-parse --show-toplevel)"
CYPRESS_DIR="${REPO_ROOT}/cypress"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
STREAMLIT_URL="${STREAMLIT_URL:-http://localhost:8501}"

# ── Banner ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}${BOLD}  Critical E2E Suite Validation (170 tests)${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── 1. Check Backend ─────────────────────────────────────────────────────────
info "Checking FastAPI backend at ${BACKEND_URL}..."
if ! curl -s -f "${BACKEND_URL}/health" > /dev/null 2>&1; then
    err "FastAPI backend not reachable at ${BACKEND_URL}"
    info "Start backend:  uvicorn app.main:app --reload"
    exit 1
fi
ok "Backend reachable"

# ── 2. Check Streamlit ───────────────────────────────────────────────────────
info "Checking Streamlit at ${STREAMLIT_URL}..."
if ! curl -s -f "${STREAMLIT_URL}" > /dev/null 2>&1; then
    err "Streamlit not reachable at ${STREAMLIT_URL}"
    info "Start Streamlit:  streamlit run streamlit_app/🏠_Home.py"
    exit 1
fi
ok "Streamlit reachable"

# ── 3. Run Critical Suite ────────────────────────────────────────────────────
info "Running critical E2E suite (this may take 5-10 minutes)..."
echo ""

cd "${CYPRESS_DIR}"

if npm run cy:run:critical; then
    echo ""
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}${BOLD}  ✅ CRITICAL SUITE PASSED (170/170)${NC}"
    echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    ok "Safe to push to main/develop branches"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}${BOLD}  ❌ CRITICAL SUITE FAILED${NC}"
    echo -e "${RED}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    err "Fix failing tests before pushing"
    info "Review screenshots in: cypress/cypress/screenshots/"
    info "Review videos in: cypress/cypress/videos/"
    echo ""
    exit 1
fi
