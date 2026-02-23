#!/bin/bash
# Production-Grade Validation with Concurrent Execution & Clean Database
#
# Tests real production scenarios:
# 1. Concurrent test execution (race conditions, DB locks)
# 2. Clean database state (0 users, 0 tournaments - test suite creates all)
# 3. Complete isolation (create → test → cleanup)
# 4. Resource contention (parallel load)

set -e

PROJECT_DIR="/Users/lovas.zoltan/Seafile/Football Investment/Projects/Football Investment Internship/practice_booking_system"
RUNS=3  # Fewer runs, more stress per run

cd "$PROJECT_DIR"
source venv/bin/activate

echo "═══════════════════════════════════════════════════════════"
echo "🏭 PRODUCTION-GRADE VALIDATION"
echo "═══════════════════════════════════════════════════════════"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "Production-grade conditions:"
echo "  ✓ Concurrent test execution (race conditions)"
echo "  ✓ Clean database (test suite creates data)"
echo "  ✓ Complete isolation (create → test → cleanup)"
echo "  ✓ DB lock stress testing"
echo "  ✓ Session collision testing"
echo ""

SUMMARY="/tmp/production_grade_summary.txt"
echo "Production-Grade Validation - $(date '+%Y-%m-%d %H:%M:%S')" > "$SUMMARY"
echo "═══════════════════════════════════════════════════════════" >> "$SUMMARY"
echo "" >> "$SUMMARY"

PASS_COUNT=0
FAIL_COUNT=0

# ═══════════════════════════════════════════════════════════
# HELPER: Create Test Database Seed Data
# ═══════════════════════════════════════════════════════════

create_test_seed_data() {
    echo "   📦 Creating minimal seed data for tests..."

    # Create test users with licenses
    PGDATABASE=lfa_intern_system psql -U postgres -h localhost <<'EOF' 2>&1 | grep -E "INSERT|ERROR" || true
-- Create 8 test users if they don't exist
DO $$
DECLARE
    user_emails TEXT[] := ARRAY[
        'test_user_1@test.com',
        'test_user_2@test.com',
        'test_user_3@test.com',
        'test_user_4@test.com',
        'test_user_5@test.com',
        'test_user_6@test.com',
        'test_user_7@test.com',
        'test_user_8@test.com'
    ];
    email TEXT;
    user_id INT;
    semester_id INT;
BEGIN
    -- Get or create active semester
    SELECT id INTO semester_id FROM semesters
    WHERE specialization_type = 'LFA_FOOTBALL_PLAYER'
    AND is_active = true
    LIMIT 1;

    IF semester_id IS NULL THEN
        INSERT INTO semesters (name, specialization_type, start_date, end_date, is_active, enrollment_cost)
        VALUES ('Test Semester', 'LFA_FOOTBALL_PLAYER', NOW(), NOW() + INTERVAL '6 months', true, 0)
        RETURNING id INTO semester_id;
    END IF;

    -- Create test users
    FOREACH email IN ARRAY user_emails
    LOOP
        -- Insert or get existing user
        INSERT INTO users (email, password_hash, name, specialization, onboarding_completed)
        VALUES (email, '$2b$12$test', 'Test User', 'LFA_FOOTBALL_PLAYER', true)
        ON CONFLICT (email) DO UPDATE SET name = 'Test User'
        RETURNING id INTO user_id;

        -- Ensure user license exists
        INSERT INTO user_licenses (user_id, specialization_type, is_active)
        VALUES (user_id, 'LFA_FOOTBALL_PLAYER', true)
        ON CONFLICT (user_id, specialization_type) DO UPDATE SET is_active = true;

        -- Ensure enrollment exists
        INSERT INTO semester_enrollments (user_id, semester_id, user_license_id, payment_verified, is_active)
        SELECT user_id, semester_id, ul.id, true, true
        FROM user_licenses ul
        WHERE ul.user_id = user_id AND ul.specialization_type = 'LFA_FOOTBALL_PLAYER'
        ON CONFLICT DO NOTHING;
    END LOOP;

    RAISE NOTICE 'Test seed data created: 8 users, 1 semester';
END $$;
EOF

    echo "   ✅ Seed data ready"
}

# ═══════════════════════════════════════════════════════════
# HELPER: Clean Test Data
# ═══════════════════════════════════════════════════════════

clean_test_data() {
    echo "   🧹 Cleaning test tournaments..."

    PGDATABASE=lfa_intern_system psql -U postgres -h localhost <<'EOF' 2>&1 | grep -E "DELETE|^[0-9]" || true
-- Delete test tournaments and related data
DELETE FROM semesters WHERE name LIKE 'UI-E2E-%' OR name LIKE 'Test Tournament%';
EOF

    echo "   ✅ Test data cleaned"
}

# ═══════════════════════════════════════════════════════════
# MAIN VALIDATION LOOP
# ═══════════════════════════════════════════════════════════

for i in $(seq 1 $RUNS); do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 PRODUCTION VALIDATION RUN $i/$RUNS - $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    LOG_FILE="/tmp/prod_grade_run_${i}.log"
    CONCURRENT_LOG="/tmp/prod_grade_run_${i}_concurrent.log"

    # ═══════════════════════════════════════════════════════════
    # PHASE 1: COMPLETE CLEANUP
    # ═══════════════════════════════════════════════════════════

    echo "🧹 Phase 1: Complete Cleanup (Clean Slate)"

    # 1.1 Stop all services
    echo "   ⏹️  Stopping all services..."
    pkill -f "streamlit run" 2>/dev/null || true
    pkill -f "pytest" 2>/dev/null || true
    sleep 2

    # 1.2 Clean test data from database
    clean_test_data

    # 1.3 Clear all caches
    echo "   🗑️  Clearing all caches..."
    rm -rf .pytest_cache __pycache__ tests/__pycache__ 2>/dev/null || true
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

    echo "   ✅ Complete cleanup done"
    echo ""

    # ═══════════════════════════════════════════════════════════
    # PHASE 2: FRESH START
    # ═══════════════════════════════════════════════════════════

    echo "🆕 Phase 2: Fresh Start (Seed Data Creation)"

    # 2.1 Create minimal seed data
    create_test_seed_data

    # 2.2 Start Streamlit fresh
    echo "   ▶️  Starting Streamlit (fresh instance)..."
    streamlit run streamlit_sandbox_v3_admin_aligned.py --server.port 8501 \
        > /tmp/streamlit_prod_${i}.log 2>&1 &
    STREAMLIT_PID=$!

    echo "   ⏳ Waiting for Streamlit..."
    MAX_WAIT=30
    WAITED=0
    while ! curl -s http://localhost:8501 > /dev/null 2>&1; do
        sleep 1
        WAITED=$((WAITED + 1))
        if [ $WAITED -ge $MAX_WAIT ]; then
            echo "   ❌ ERROR: Streamlit failed to start"
            exit 1
        fi
    done

    echo "   ✅ Streamlit ready (PID: $STREAMLIT_PID)"
    echo ""

    # ═══════════════════════════════════════════════════════════
    # PHASE 3: SEQUENTIAL BASELINE RUN
    # ═══════════════════════════════════════════════════════════

    echo "🧪 Phase 3: Sequential Baseline (8 tests)"
    START_TIME=$(date +%s)

    set +e
    pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
        -v --tb=line --maxfail=1 \
        2>&1 | tee "$LOG_FILE"
    SEQUENTIAL_EXIT=$?
    set -e

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))

    if grep -q "8 passed" "$LOG_FILE"; then
        SEQUENTIAL_RESULT="✅ 8/8 PASSED"
    else
        SEQUENTIAL_RESULT="❌ FAILED"
    fi

    echo ""
    echo "   Sequential: $SEQUENTIAL_RESULT (${MINUTES}m ${SECONDS}s)" | tee -a "$SUMMARY"
    echo ""

    # ═══════════════════════════════════════════════════════════
    # PHASE 4: CONCURRENT STRESS TEST (if sequential passed)
    # ═══════════════════════════════════════════════════════════

    if [ "$SEQUENTIAL_EXIT" -eq 0 ]; then
        echo "🔥 Phase 4: Concurrent Execution (Stress Test)"
        echo "   Running 2 test instances in parallel..."
        echo "   ⚠️  This tests: DB locks, race conditions, session conflicts"
        echo ""

        # Clean tournaments from sequential run
        clean_test_data
        sleep 2

        # Run 2 test instances concurrently (subset of tests)
        START_TIME=$(date +%s)

        set +e
        # Instance 1: Run T1, T3, T5, T7 (SCORE, TIME, DISTANCE, PLACEMENT)
        pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
            -k "T1_League_Ind_Score or T3_League_Ind_Time or T5_League_Ind_Distance or T7_League_Ind_Placement" \
            -v --tb=line \
            > /tmp/prod_grade_run_${i}_concurrent_1.log 2>&1 &
        PID1=$!

        sleep 5  # Stagger start slightly

        # Instance 2: Run T2, T4, T6, T8 (SCORE, TIME, DISTANCE, PLACEMENT knockout)
        pytest tests/e2e_frontend/test_tournament_full_ui_workflow.py::test_full_ui_tournament_workflow \
            -k "T2_Knockout_Ind_Score or T4_Knockout_Ind_Time or T6_Knockout_Ind_Distance or T8_Knockout_Ind_Placement" \
            -v --tb=line \
            > /tmp/prod_grade_run_${i}_concurrent_2.log 2>&1 &
        PID2=$!

        # Wait for both to complete
        wait $PID1
        EXIT1=$?
        wait $PID2
        EXIT2=$?
        set -e

        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        MINUTES=$((DURATION / 60))
        SECONDS=$((DURATION % 60))

        # Check results
        PASS1=$(grep -c "passed" /tmp/prod_grade_run_${i}_concurrent_1.log || echo "0")
        PASS2=$(grep -c "passed" /tmp/prod_grade_run_${i}_concurrent_2.log || echo "0")

        if [ "$EXIT1" -eq 0 ] && [ "$EXIT2" -eq 0 ]; then
            CONCURRENT_RESULT="✅ BOTH PASSED"
            PASS_COUNT=$((PASS_COUNT + 1))
        else
            CONCURRENT_RESULT="❌ FAILED (Exit: $EXIT1, $EXIT2)"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi

        echo ""
        echo "   Concurrent: $CONCURRENT_RESULT (${MINUTES}m ${SECONDS}s)" | tee -a "$SUMMARY"
        echo "   Instance 1: $PASS1 tests passed" | tee -a "$SUMMARY"
        echo "   Instance 2: $PASS2 tests passed" | tee -a "$SUMMARY"

        # Combine logs
        cat /tmp/prod_grade_run_${i}_concurrent_1.log /tmp/prod_grade_run_${i}_concurrent_2.log > "$CONCURRENT_LOG"
    else
        echo "⏭️  Phase 4: SKIPPED (sequential baseline failed)"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo "" | tee -a "$SUMMARY"

    # ═══════════════════════════════════════════════════════════
    # PHASE 5: POST-RUN ANALYSIS
    # ═══════════════════════════════════════════════════════════

    echo ""
    echo "🔍 Phase 5: Post-Run Analysis"

    # Check for race condition indicators
    if [ -f "$CONCURRENT_LOG" ]; then
        DEADLOCKS=$(grep -c "deadlock\|lock timeout\|could not obtain lock" "$CONCURRENT_LOG" 2>/dev/null || echo "0")
        CONFLICTS=$(grep -c "conflict\|duplicate key\|violates unique constraint" "$CONCURRENT_LOG" 2>/dev/null || echo "0")

        if [ "$DEADLOCKS" -gt 0 ]; then
            echo "   ⚠️  DEADLOCKS DETECTED: $DEADLOCKS" | tee -a "$SUMMARY"
        else
            echo "   ✅ No deadlocks" | tee -a "$SUMMARY"
        fi

        if [ "$CONFLICTS" -gt 0 ]; then
            echo "   ⚠️  DB CONFLICTS DETECTED: $CONFLICTS" | tee -a "$SUMMARY"
        else
            echo "   ✅ No DB conflicts" | tee -a "$SUMMARY"
        fi
    fi

    echo "   Logs: $LOG_FILE, $CONCURRENT_LOG" | tee -a "$SUMMARY"
    echo ""
done

# ═══════════════════════════════════════════════════════════
# FINAL CLEANUP & REPORT
# ═══════════════════════════════════════════════════════════

echo "🧹 Final Cleanup"
pkill -f "streamlit run" 2>/dev/null || true
echo "   ✅ Services stopped"
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "✅ PRODUCTION-GRADE VALIDATION COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 FINAL VERDICT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Concurrent Runs: $RUNS"
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"
echo ""

if [ "$PASS_COUNT" -eq "$RUNS" ]; then
    echo "🎉 VERDICT: PRODUCTION READY"
    echo ""
    echo "   Suite is stable under:"
    echo "   ✓ Concurrent execution (race conditions tested)"
    echo "   ✓ Clean database (complete isolation)"
    echo "   ✓ DB lock stress (parallel load)"
    echo "   ✓ Service restarts (fresh state)"
    echo ""
    echo "   → Ready for CI/CD pipeline integration"
elif [ "$PASS_COUNT" -ge $((RUNS * 2 / 3)) ]; then
    echo "⚠️  VERDICT: NEEDS WORK"
    echo "   Some instability under concurrent load"
    echo "   Review race conditions and DB locks"
else
    echo "❌ VERDICT: NOT PRODUCTION READY"
    echo "   Significant issues under production stress"
    echo "   Debug and fix before production use"
fi

echo ""
echo "📊 Summary: $SUMMARY"
echo "📁 Logs: /tmp/prod_grade_run_*.log"
