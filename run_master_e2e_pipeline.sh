#!/bin/bash
# =============================================================================
# Master E2E Pipeline — LFA Intern System
# =============================================================================
#
# FULL LIFECYCLE PIPELINE RUN ORDER:
# ===================================
#
# Phase 0 — Clean DB Setup (lifecycle prerequisite)
#   tests_e2e/lifecycle/test_00_clean_db.py
#   → Drops and recreates DB, runs migrations, seeds admin + grandmaster + invite code
#   → Saves snapshot: tests_e2e/snapshots/00_clean_db.dump
#   → Requires: PostgreSQL running, DATABASE_URL set
#
# Phase 1 — Auth: Admin Login (smoke check)
#   tests/e2e_frontend/user_lifecycle/auth/test_login_flow.py
#   → Verifies admin@lfa.com / admin123 login works via Streamlit UI
#   → Requires: Streamlit running on :8501, Backend running on :8000
#
# Phase 0b — Star Players Seed (runs after Phase 0 DB setup)
#   scripts/seed_star_players.py
#   → Seeds 12 star players from tests/e2e/test_users.json into DB
#   → Each player gets per-player football_skills (29 skills, 0-99 scale)
#   → Writes db_ids back to test_users.json
#   → Idempotent: existing users skipped
#
# Phase 2 — Registration: 4 Users via UI (D1–D9)
#   tests/e2e_frontend/user_lifecycle/registration/test_registration_with_invite_code.py
#   → D1: Admin creates 4 invitation codes via Admin Dashboard → Financial → Invitation Codes
#   → D2–D5: 4 users register with invite codes via Streamlit registration form
#   → D6–D9: Each user logs in and Specialization Hub loads
#   → D9: DB integrity check (credits, invite code consumed)
#   → Saves generated codes to: tests/e2e/generated_invitation_codes.json
#
# Phase 3 — Onboarding: 4 Users Complete Full Onboarding
#   tests/e2e_frontend/user_lifecycle/onboarding/test_onboarding_with_coupon.py
#   → Prerequisite: Phase 0 already seeds onboarding coupons (from test_users.json)
#   → Each user: applies coupon (+50 credits) → unlocks specialization → 5-step wizard → Player Dashboard
#   → Step 1: position, Steps 2-5: 29 skills across 4 categories (outfield/set_pieces/mental/physical)
#   → Users: pwt.k1sqx1, pwt.p3t1k3, pwt.v4lv3rd3jr, pwt.t1b1k3 (all @f1rstteam.hu)
#
# Phase 4 — Sandbox Tournament: Group+Knockout Full Flow
#   tests/e2e_frontend/test_sandbox_workflow_e2e.py
#   → Creates Group+Knockout tournament (7 players) via sandbox workflow
#   → Submits all group stage matches via UI
#   → Submits semifinals via UI
#   → CRITICAL: Verifies final match auto-populates and appears in UI
#   → Submits final match via UI
#   → Requires: Streamlit sandbox running: streamlit run streamlit_sandbox_v3_admin_aligned.py --server.port 8501
#
# Phase 5 — Tournament Lifecycle E2E: Rankings + Badges + Regression Guard
#   tests_e2e/lifecycle/test_04_tournament_lifecycle.py
#   → Creates league tournament with 4 star players (Mbappé, Haaland, Messi, Vinicius)
#   → Batch enrolls all 4 via admin API
#   → Generates 6 round-robin sessions
#   → Submits all 6 match results (deterministic scores)
#   → Calls calculate-rankings → verifies 4 rows in tournament_rankings
#   → Completes tournament → distributes rewards (v2)
#   → Verifies CHAMPION badge on rank 1 player
#   → CRITICAL: Asserts badge_metadata.total_participants=4 (no "No ranking data" regression)
#   → CRITICAL: Asserts badge_metadata key is "badge_metadata" (not "metadata") — commit 2f38506 guard
#   → Saves snapshot: 04_tournament_complete
#   Phase 5b (determinism): restores 04_tournament_complete → re-asserts same rankings+badges
#   → Requires: Backend running on :8000, Phase 0b star players seeded
#
# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================
#
# DATABASE_URL        — PostgreSQL connection (default: postgresql://postgres:postgres@localhost:5432/lfa_intern_system)
# PYTEST_HEADLESS     — Browser mode: true (CI) | false (debug) (default: true)
# PYTEST_BROWSER      — Browser engine: chromium | firefox | webkit (default: chromium)
# PYTEST_SLOW_MO      — Action delay in ms for debug (default: 0)
# BASE_URL            — Streamlit URL (default: http://localhost:8501)
# API_URL             — FastAPI URL (default: http://localhost:8000)
#
# =============================================================================
# USAGE EXAMPLES
# =============================================================================
#
# Full pipeline (CI/headless):
#   ./run_master_e2e_pipeline.sh
#
# Debug mode (headed browser, slow motion):
#   PYTEST_HEADLESS=false PYTEST_SLOW_MO=1200 ./run_master_e2e_pipeline.sh
#
# Single phase:
#   ./run_master_e2e_pipeline.sh --phase 2
#
# Skip Phase 0 (use existing snapshot):
#   ./run_master_e2e_pipeline.sh --skip-snapshot
#
# Sandbox only:
#   ./run_master_e2e_pipeline.sh --phase 4
#
# Tournament lifecycle only:
#   ./run_master_e2e_pipeline.sh --phase 5
#
# =============================================================================

set -euo pipefail

# Default configuration
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/lfa_intern_system}"
PYTEST_HEADLESS="${PYTEST_HEADLESS:-true}"
PYTEST_BROWSER="${PYTEST_BROWSER:-chromium}"
PYTEST_SLOW_MO="${PYTEST_SLOW_MO:-0}"
BASE_URL="${BASE_URL:-http://localhost:8501}"
API_URL="${API_URL:-http://localhost:8000}"

export DATABASE_URL PYTEST_HEADLESS PYTEST_BROWSER PYTEST_SLOW_MO BASE_URL API_URL

# Parse arguments
SKIP_SNAPSHOT=false
PHASE_ONLY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-snapshot)
            SKIP_SNAPSHOT=true
            shift
            ;;
        --phase)
            PHASE_ONLY="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

PASS_COUNT=0
FAIL_COUNT=0

run_phase() {
    local phase_num="$1"
    local phase_name="$2"
    local test_path="$3"
    local extra_args="${4:-}"

    # If phase filter is set, skip other phases
    if [[ -n "$PHASE_ONLY" && "$PHASE_ONLY" != "$phase_num" ]]; then
        return 0
    fi

    echo ""
    echo "============================================================"
    echo "  Phase ${phase_num}: ${phase_name}"
    echo "============================================================"

    if DATABASE_URL="$DATABASE_URL" pytest "$test_path" \
        --tb=short \
        -v \
        $extra_args \
        2>&1; then
        echo "  ✅ Phase ${phase_num} PASSED"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "  ❌ Phase ${phase_num} FAILED"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        if [[ -z "$PHASE_ONLY" ]]; then
            echo ""
            echo "  ⛔ Pipeline halted at Phase ${phase_num}."
            echo "  Run with --phase ${phase_num} to re-run this phase only."
            exit 1
        fi
    fi
}

# =============================================================================
# PRE-FLIGHT CHECKS
# =============================================================================

echo "============================================================"
echo "  LFA Intern System — Master E2E Pipeline"
echo "============================================================"
echo "  Database:    $DATABASE_URL"
echo "  Headless:    $PYTEST_HEADLESS"
echo "  Browser:     $PYTEST_BROWSER"
echo "  Slow Mo:     ${PYTEST_SLOW_MO}ms"
echo "  Base URL:    $BASE_URL"
echo "  API URL:     $API_URL"
echo "============================================================"

# Check backend is running
if ! curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" | grep -q "200"; then
    echo ""
    echo "  ⚠️  WARNING: Backend may not be running at $API_URL"
    echo "     Start it with: DATABASE_URL=... uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    echo ""
fi

# =============================================================================
# PHASE 0: Clean DB Setup (Snapshot)
# =============================================================================

if [[ "$SKIP_SNAPSHOT" == "false" ]]; then
    run_phase "0" "Clean DB Setup + Snapshot" \
        "tests_e2e/lifecycle/test_00_clean_db.py" \
        "-s"

    # Phase 0b: Seed 12 star players (runs immediately after Phase 0)
    if [[ -z "$PHASE_ONLY" || "$PHASE_ONLY" == "0" ]]; then
        echo ""
        echo "============================================================"
        echo "  Phase 0b: Star Players Seed (12 players)"
        echo "============================================================"
        if DATABASE_URL="$DATABASE_URL" python scripts/seed_star_players.py; then
            echo "  ✅ Phase 0b PASSED"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            echo "  ❌ Phase 0b FAILED"
            FAIL_COUNT=$((FAIL_COUNT + 1))
            if [[ -z "$PHASE_ONLY" ]]; then
                echo "  ⛔ Pipeline halted at Phase 0b."
                exit 1
            fi
        fi
    fi
else
    echo ""
    echo "  ⏭️  Phase 0: Skipped (--skip-snapshot)"
fi

# =============================================================================
# PHASE 1: Auth — Admin Login Smoke Check
# =============================================================================

run_phase "1" "Auth: Admin Login" \
    "tests/e2e_frontend/user_lifecycle/auth/test_login_flow.py"

# =============================================================================
# PHASE 2: Registration — 3 Users via UI (D1–D8)
# =============================================================================

run_phase "2" "Registration: 4 Users via Invitation Codes" \
    "tests/e2e_frontend/user_lifecycle/registration/test_registration_with_invite_code.py" \
    "-s"

# =============================================================================
# PHASE 3: Onboarding — 3 Users Complete Full Onboarding
# =============================================================================

run_phase "3" "Onboarding: 4 Users Complete Full Onboarding" \
    "tests/e2e_frontend/user_lifecycle/onboarding/test_onboarding_with_coupon.py" \
    "-s"

# =============================================================================
# PHASE 4: Sandbox Tournament — Group+Knockout Full Flow
# =============================================================================

echo ""
echo "  ℹ️  Phase 4 prerequisite: Streamlit sandbox must be running"
echo "     streamlit run streamlit_sandbox_v3_admin_aligned.py --server.port 8501"
echo ""

run_phase "4" "Sandbox Tournament: Group+Knockout Full Flow" \
    "tests/e2e_frontend/test_sandbox_workflow_e2e.py" \
    "-s"

# =============================================================================
# PHASE 5: Tournament Lifecycle — Rankings + Badges + Regression Guard
# =============================================================================

run_phase "5" "Tournament Lifecycle: Rankings + CHAMPION Badge + No-Regression" \
    "tests_e2e/lifecycle/test_04_tournament_lifecycle.py" \
    "-s"

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "============================================================"
echo "  Pipeline Complete"
echo "============================================================"
echo "  Passed: $PASS_COUNT"
echo "  Failed: $FAIL_COUNT"
echo "============================================================"

if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
fi
