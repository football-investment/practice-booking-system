#!/usr/bin/env bash
# =============================================================================
# Phase 6.3 Load Test Runner
# =============================================================================
# Orchestrates: seed → uvicorn (4 workers) → locust soak+burst → analyze → report
#
# Usage (from project root):
#   bash scripts/run_phase63_load.sh
#
# Environment overrides:
#   LOAD_PEAK_VUS=500   Override peak VU count (default: 1000)
#   PORT=8001           Target port (default: 8001 to avoid conflict with dev server)
#   WORKERS=4           Uvicorn worker count (default: 4)
#   SKIP_SEED=1         Skip user seed if already seeded
#
# Exit codes:
#   0 — all 5 GATES passed (Phase 6.3 VALID)
#   1 — one or more GATES failed
#   2 — infrastructure error (server failed to start, etc.)
# =============================================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
PORT=${PORT:-8001}
WORKERS=${WORKERS:-4}
LOAD_PEAK_VUS=${LOAD_PEAK_VUS:-1000}
RESULTS_DIR="tests/performance/results"
TIMESTAMP=$(date +%Y%m%d_%H%M)
CSV_PREFIX="${RESULTS_DIR}/phase63_${TIMESTAMP}"
HTML_REPORT="${RESULTS_DIR}/phase63_${TIMESTAMP}.html"
LOG_FILE="${RESULTS_DIR}/phase63_${TIMESTAMP}.log"
SEED_OUT=$(mktemp)

export LOAD_PEAK_VUS

# ── Pre-flight checks ────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════"
echo " Phase 6.3 Load Test Runner"
echo " Peak VUs: ${LOAD_PEAK_VUS}  |  Workers: ${WORKERS}  |  Port: ${PORT}"
echo "═══════════════════════════════════════════════════════════════════════"

command -v locust  >/dev/null 2>&1 || { echo "❌ locust not found (pip install locust)"; exit 2; }
command -v uvicorn >/dev/null 2>&1 || { echo "❌ uvicorn not found"; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 not found"; exit 2; }

mkdir -p "${RESULTS_DIR}"

# ── Step 1: Seed test data ────────────────────────────────────────────────────
if [[ "${SKIP_SEED:-0}" != "1" ]]; then
    echo ""
    echo "── Step 1: Seeding 100 load-test student accounts ──────────────────────"
    python3 scripts/seed_load_test_users.py | tee "${SEED_OUT}"
    echo "Seed complete."
else
    echo "── Step 1: Seed SKIPPED (SKIP_SEED=1) ──────────────────────────────────"
    # Still need env vars — try to derive from existing seed output
    echo "LOAD_SEMESTER_IDS=${LOAD_SEMESTER_IDS:-}" >> "${SEED_OUT}"
    echo "LOAD_EVENT_IDS=${LOAD_EVENT_IDS:-1}"     >> "${SEED_OUT}"
fi

# Parse env vars from seed output
SEMESTER_IDS=$(grep "^LOAD_SEMESTER_IDS=" "${SEED_OUT}" | tail -1 | cut -d= -f2 || echo "")
EVENT_IDS=$(grep    "^LOAD_EVENT_IDS="    "${SEED_OUT}" | tail -1 | cut -d= -f2 || echo "1")

if [[ -z "${SEMESTER_IDS}" ]]; then
    echo "⚠️  LOAD_SEMESTER_IDS not set — enroll tasks will be skipped"
fi
echo "   LOAD_SEMESTER_IDS=${SEMESTER_IDS}"
echo "   LOAD_EVENT_IDS=${EVENT_IDS}"
rm -f "${SEED_OUT}"

# ── Step 2: Start uvicorn ─────────────────────────────────────────────────────
echo ""
echo "── Step 2: Starting uvicorn (${WORKERS} workers, ENABLE_RATE_LIMITING=false) ─"

ENABLE_RATE_LIMITING=false \
DB_STATEMENT_TIMEOUT_MS=5000 \
uvicorn app.main:app \
    --host 127.0.0.1 \
    --port "${PORT}" \
    --workers "${WORKERS}" \
    --log-level warning \
    &
SERVER_PID=$!

# Ensure server is killed on exit (even on error)
cleanup() {
    echo ""
    echo "── Cleanup: stopping uvicorn (PID ${SERVER_PID}) ─────────────────────────"
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
}
trap cleanup EXIT

# Wait for server to be ready (up to 15s)
echo -n "   Waiting for server to start"
for i in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 0.5
    if [[ $i -eq 30 ]]; then
        echo ""
        echo "❌ Server failed to start within 15s (check DB connection / migrations)"
        exit 2
    fi
done

# ── Step 3: Run Locust (Phase63LoadShape, headless) ───────────────────────────
echo ""
echo "── Step 3: Running Locust soak+burst (${LOAD_PEAK_VUS} peak VUs, ~10 min) ─────"
echo "   CSV prefix : ${CSV_PREFIX}"
echo "   HTML report: ${HTML_REPORT}"
echo "   Log file   : ${LOG_FILE}"
echo ""

LOAD_SEMESTER_IDS="${SEMESTER_IDS}" \
LOAD_EVENT_IDS="${EVENT_IDS}" \
LOAD_PEAK_VUS="${LOAD_PEAK_VUS}" \
locust \
    -f tests/performance/locustfile.py \
    SoakBurstUser \
    --headless \
    --host "http://127.0.0.1:${PORT}" \
    --run-time 10m \
    --csv "${CSV_PREFIX}" \
    --html "${HTML_REPORT}" \
    --logfile "${LOG_FILE}" \
    2>&1 | tee "${RESULTS_DIR}/phase63_${TIMESTAMP}_stdout.txt"

LOCUST_EXIT=$?
echo ""
if [[ ${LOCUST_EXIT} -ne 0 ]]; then
    echo "⚠️  Locust exited with code ${LOCUST_EXIT}"
fi

# ── Step 4: Analyze results → LOAD_REPORT ─────────────────────────────────────
echo "── Step 4: Analyzing results (GATE-2/3/4) ───────────────────────────────"

ANALYZE_EXIT=0
python3 tests/performance/analyze_load_results.py \
    "${CSV_PREFIX}_stats.csv" \
    "${CSV_PREFIX}_failures.csv" \
    "${CSV_PREFIX}_stats_history.csv" \
    --peak-vus "${LOAD_PEAK_VUS}" \
    --output "tests/performance/LOAD_REPORT_$(date +%Y%m%d).md" \
    || ANALYZE_EXIT=$?

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
if [[ ${ANALYZE_EXIT} -eq 0 ]]; then
    echo " ✅ Phase 6.3 VALID — all GATES passed"
    echo "    Report: tests/performance/LOAD_REPORT_$(date +%Y%m%d).md"
    echo "    HTML  : ${HTML_REPORT}"
else
    echo " ❌ Phase 6.3 NOT COMPLETE — GATE failure (analyze exit=${ANALYZE_EXIT})"
    echo "    Review: tests/performance/LOAD_REPORT_$(date +%Y%m%d).md"
fi
echo "═══════════════════════════════════════════════════════════════════════"

exit ${ANALYZE_EXIT}
