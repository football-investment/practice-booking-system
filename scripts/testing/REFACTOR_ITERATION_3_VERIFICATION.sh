#!/bin/bash
# ============================================================================
# Iteráció 3 — Teljes E2E Regression Suite
# ============================================================================
# Futtatási útmutató a refaktor validálásához

set -e

PROJECT_ROOT="/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
cd "$PROJECT_ROOT"

echo "════════════════════════════════════════════════════════════════════════"
echo "  ITERÁCIÓ 3 — E2E REGRESSION SUITE"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# ── 1. Import Smoke Test ─────────────────────────────────────────────────────
echo "1️⃣  Import Smoke Test..."
cd streamlit_app
python3 << 'EOFPY'
import sys
sys.dont_write_bytecode = True

# Test all new imports
from components.admin.tournament_monitor import render_tournament_monitor
from components.admin.tournament_card.leaderboard import render_leaderboard
from components.admin.tournament_card.result_entry import render_manual_result_entry
from components.admin.tournament_card.session_grid import render_campus_grid, render_session_card
from components.admin.tournament_card.utils import phase_icon, phase_label_short, phase_label
from components.admin.ops_wizard import init_wizard_state, reset_wizard_state, execute_launch

print("✅ All imports successful")
EOFPY

if [ $? -eq 0 ]; then
    echo "   ✅ Import smoke test PASSED"
else
    echo "   ❌ Import smoke test FAILED"
    exit 1
fi
echo ""

cd ..

# ── 2. Unit Tests ────────────────────────────────────────────────────────────
echo "2️⃣  Unit Tests..."
pytest tests/unit/ -q --tb=line -m unit 2>&1 | tee /tmp/iter3_unit.log
UNIT_EXIT=$?

if [ $UNIT_EXIT -eq 0 ]; then
    echo "   ✅ Unit tests PASSED"
else
    echo "   ⚠️  Unit tests FAILED or WARNINGS (check /tmp/iter3_unit.log)"
fi
echo ""

# ── 3. E2E Smoke Tests ───────────────────────────────────────────────────────
echo "3️⃣  E2E Smoke Tests..."
pytest tests/e2e/test_reward_leaderboard_matrix.py -v -k "8p" --tb=short 2>&1 | tee /tmp/iter3_e2e_smoke.log
E2E_SMOKE_EXIT=$?

if [ $E2E_SMOKE_EXIT -eq 0 ]; then
    echo "   ✅ E2E smoke tests PASSED"
else
    echo "   ❌ E2E smoke tests FAILED (check /tmp/iter3_e2e_smoke.log)"
fi
echo ""

# ── 4. Full E2E Regression Suite ─────────────────────────────────────────────
echo "4️⃣  Full E2E Regression Suite..."
pytest tests/e2e/ -v --tb=short -m "not slow" 2>&1 | tee /tmp/iter3_e2e_full.log
E2E_FULL_EXIT=$?

if [ $E2E_FULL_EXIT -eq 0 ]; then
    echo "   ✅ Full E2E regression PASSED"
else
    echo "   ❌ Full E2E regression FAILED (check /tmp/iter3_e2e_full.log)"
fi
echo ""

# ── 5. Manual UI Verification Checklist ──────────────────────────────────────
echo "5️⃣  Manual UI Verification Checklist"
echo ""
echo "   Start Streamlit app:"
echo "   $ cd streamlit_app && streamlit run 🏠_Home.py"
echo ""
echo "   ✓ Navigate to Tournament Monitor page"
echo "   ✓ Verify OPS Wizard loads (8 steps visible)"
echo "   ✓ Complete full wizard flow (Scenario → Format → Type → Game → Count → Simulation → Reward → Review)"
echo "   ✓ Launch a test tournament (verify auto-tracking starts)"
echo "   ✓ Verify tournament card displays:"
echo "       - Session grid (phase-based rendering)"
echo "       - Manual result entry form"
echo "       - Leaderboard (after completion)"
echo "   ✓ Submit manual results (verify phase grid updates)"
echo "   ✓ Complete tournament → verify leaderboard shows rewards"
echo ""

# ── Summary ──────────────────────────────────────────────────────────────────
echo "════════════════════════════════════════════════════════════════════════"
echo "  REGRESSION SUMMARY"
echo "════════════════════════════════════════════════════════════════════════"
echo ""

TOTAL_FAILURES=0

if [ $UNIT_EXIT -ne 0 ]; then
    echo "❌ Unit tests: FAILED"
    TOTAL_FAILURES=$((TOTAL_FAILURES + 1))
else
    echo "✅ Unit tests: PASSED"
fi

if [ $E2E_SMOKE_EXIT -ne 0 ]; then
    echo "❌ E2E smoke: FAILED"
    TOTAL_FAILURES=$((TOTAL_FAILURES + 1))
else
    echo "✅ E2E smoke: PASSED"
fi

if [ $E2E_FULL_EXIT -ne 0 ]; then
    echo "❌ Full E2E: FAILED"
    TOTAL_FAILURES=$((TOTAL_FAILURES + 1))
else
    echo "✅ Full E2E: PASSED"
fi

echo ""
echo "Logs saved to:"
echo "  - /tmp/iter3_unit.log"
echo "  - /tmp/iter3_e2e_smoke.log"
echo "  - /tmp/iter3_e2e_full.log"
echo ""

if [ $TOTAL_FAILURES -eq 0 ]; then
    echo "🎉 ALL AUTOMATED TESTS PASSED"
    echo ""
    echo "Next step: Complete manual UI verification checklist above"
    exit 0
else
    echo "⚠️  $TOTAL_FAILURES test suite(s) FAILED"
    echo ""
    echo "Review logs and fix issues before considering iteration complete"
    exit 1
fi
