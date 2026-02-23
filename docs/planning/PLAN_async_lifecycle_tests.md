# Plan: Async Lifecycle Production Readiness Tests

## Overview
The sync path (< 128 players) is production-ready. Now we need to prove the async path (>= 128 players) with real Celery workers for 1024p tournaments.

## Architecture Understanding

### Sync Path (< 128 players)
- OPS endpoint runs: session generation + result simulation + ranking calculation
- Everything completes in one HTTP call
- `task_id = "sync-done"`

### Async Path (>= 128 players)
- OPS endpoint: creates tournament + enrolls players + queues Celery task
- Returns immediately with `task_id = UUID`
- **Celery worker** executes `generate_sessions_task`:
  - Only generates sessions (no simulation, no ranking)
  - Worker must be running separately
- **Simulation and ranking** must be called via separate API endpoints:
  - No auto-simulation for async path
  - Need to call `/tournaments/{id}/calculate-rankings` after sessions exist

### Critical Endpoints
1. `POST /tournaments/ops/run-scenario` - launches tournament (async for >= 128p)
2. `GET /tournaments/{id}/generation-status/{task_id}` - polls Celery task status
3. `GET /tournaments/{id}/sessions` - fetches sessions (available after worker completes)
4. `POST /tournaments/{id}/calculate-rankings` - calculates rankings (requires all session results)
5. `POST /tournaments/{id}/complete` - transitions to COMPLETED status

### Missing Components for Async Path
The sync path does:
1. Generate sessions
2. **Simulate results** (`_simulate_tournament_results()`)
3. **Calculate rankings** (RankingStrategyFactory)

But async path (Celery task) only does #1. We need to find/create endpoints for #2 and #3.

## Implementation Plan

### Test File Structure
Create `tests_e2e/test_async_production_readiness.py` with 3 test groups:

#### Group U: TestAsyncFullLifecycle1024 (API, @slow)
**Purpose**: Full async lifecycle with real Celery worker (10 tests)

**Prerequisites**:
- Celery worker running: `celery -A app.celery_app worker -Q tournaments --loglevel=info`
- Redis running (already verified)

**Flow**:
1. Launch 1024p knockout via OPS
2. Poll `/generation-status/{task_id}` until `status=done` (sessions generated)
3. Simulate results (need to find/create endpoint or call directly)
4. Call `/calculate-rankings` to populate rankings
5. Call `/complete` to transition to COMPLETED

**Tests**:
- `test_1024p_worker_generates_sessions_within_timeout` - max 10 minutes for session generation
- `test_1024p_sessions_count_exact` - exactly 1024 sessions
- `test_1024p_no_duplicate_sessions` - all session IDs unique
- `test_1024p_no_orphan_matches` - all bracket matches have proper parent/child relationships
- `test_1024p_bracket_structure_complete` - 10 rounds, correct matches per round, playoff present
- `test_1024p_results_simulation_completes` - all 1024 sessions have `result_submitted=True`
- `test_1024p_rankings_populated_after_calculate` - 1024 rankings exist
- `test_1024p_complete_transition_succeeds` - status becomes COMPLETED
- `test_1024p_comprehensive_metrics` - total runtime, peak memory, DB write count

**Metrics to Capture**:
- `queue_wait_time_ms` - from OPS dispatch to worker pickup (from Celery result)
- `generation_duration_ms` - session generation CPU + DB write (from Celery result)
- `db_write_time_ms` - bulk insert time (from Celery result)
- `total_lifecycle_seconds` - launch to COMPLETED
- `peak_memory_mb` - track via `psutil` before/after (if available)

**Assertions**:
- No duplicate session IDs
- Bracket structure: 10 rounds, each round has correct match count
- Round 1: 512 matches, Round 2: 256, ..., Round 10: 1 match
- Playoff: exactly 1 session with `tournament_match_number=999`
- All sessions have 2 participants (no orphans)
- All sessions have `result_submitted=True` after simulation
- Rankings count == enrolled count (1024)
- Status == COMPLETED after `/complete` call

#### Group V: TestAsyncIdempotency (API, @slow)
**Purpose**: Prove idempotency when Celery task runs twice (3 tests)

**Scenario**:
1. Launch 1024p tournament
2. Wait for Celery task to complete (sessions generated)
3. Manually trigger `generate_sessions_task.apply_async()` again with same tournament_id
4. Wait for second task to complete
5. Verify: session count unchanged, no duplicates, bracket consistent

**Tests**:
- `test_duplicate_task_does_not_create_duplicate_sessions` - session count == 1024 (not 2048)
- `test_duplicate_task_preserves_bracket_structure` - round structure unchanged
- `test_duplicate_task_idempotent_response` - second task returns success but doesn't modify DB

**Key Question**: Does `TournamentSessionGenerator.generate_sessions()` have idempotency checks?
- Need to read the generator code to verify
- If not, this test will FAIL and expose a bug

#### Group W: TestAsyncUIMonitoring1024 (Playwright, @slow)
**Purpose**: UI stability during async generation (2 tests)

**Flow**:
1. Launch 1024p via wizard
2. Leave monitor page open
3. Poll UI every 10 seconds (simulate `@st.fragment(run_every=10)`)
4. Verify UI stable while `sessions=0` (before worker completes)
5. Verify UI updates correctly when sessions appear (after worker completes)
6. Verify UI stable through COMPLETED transition

**Tests**:
- `test_ui_1024p_monitor_stable_during_async_generation`
  - Launch 1024p
  - Monitor page shows "0 sessions" initially
  - No UI crash/error during 0-sessions state
  - UI refreshes and shows sessions once worker completes
  - Fragment refresh stable throughout

- `test_ui_1024p_monitor_stable_to_completed`
  - Full lifecycle: launch → sessions → results → rankings → COMPLETED
  - UI tracking panel updates at each stage
  - No error text, no crash, stable throughout

**UI Assertions**:
- No "Traceback", "AttributeError", "KeyError", "Exception" text visible
- "LIVE TEST TRACKING" header present
- Session count updates from 0 → 1024
- Status updates: IN_PROGRESS → COMPLETED
- Leaderboard appears after rankings calculated

### Supporting Infrastructure

#### Celery Worker Management
**Option 1**: Require manual worker start
- Document: "Start worker before running: `celery -A app.celery_app worker -Q tournaments`"
- Tests check if worker is available, skip if not (with clear message)

**Option 2**: Auto-start worker in test fixture
- `@pytest.fixture(scope="session")` starts worker subprocess
- Cleaner for CI/CD
- Risk: subprocess management complexity

**Recommendation**: Start with Option 1 (manual), add Option 2 later for CI.

#### Helper: Simulate Results Endpoint
The sync path calls `_simulate_tournament_results()` directly. For async path, we need either:

**Option A**: Create new endpoint `POST /tournaments/{id}/simulate-results` (Admin only)
- Pro: Clean API, testable independently
- Con: New endpoint to implement

**Option B**: Import `_simulate_tournament_results()` directly in test
- Pro: No new endpoint needed
- Con: Test depends on internal implementation

**Recommendation**: Option B for now (faster), document as tech debt for Option A.

#### Helper: Complete Tournament
`POST /tournaments/{id}/complete` already exists. Use it.

#### Helper: Poll Task Status
Create `_poll_task_until_done(api_url, token, tid, task_id, timeout=600)` helper:
- Polls `/generation-status/{task_id}` every 2 seconds
- Returns when `status=done` or `status=error`
- Raises TimeoutError if `timeout` exceeded

### Test Execution Order
1. Run `test_production_readiness.py` (sync path) - already passing
2. **Start Celery worker manually**: `celery -A app.celery_app worker -Q tournaments --loglevel=info`
3. Run `test_async_production_readiness.py` (async path) - new tests

### Risk Mitigation

**Risk 1**: Celery worker not running
- Tests should check if worker is available
- Skip with clear message if worker unavailable: `pytest.skip("Celery worker not running")`

**Risk 2**: 1024p tests take > 10 minutes
- Set realistic timeouts: `@pytest.mark.timeout(900)` (15 minutes)
- Document expected runtime in test docstring

**Risk 3**: Idempotency bug in generator
- If generator doesn't check for existing sessions, tests will expose bug
- This is GOOD - it's a production readiness blocker

**Risk 4**: UI tests flaky due to timing
- Use Playwright's `expect().to_be_visible(timeout=...)` with generous timeouts
- Add explicit waits after state transitions
- Retry logic for network flakiness

### Open Questions for User

1. **Simulate Results Endpoint**: Should we create `POST /tournaments/{id}/simulate-results` or call internal function directly in tests?

2. **Celery Worker**: Manual start (documented) or auto-start in fixture?

3. **Peak Memory**: Should we track memory with `psutil` or just document runtime metrics from Celery?

4. **DB Write Count**: Should we instrument DB session to count write queries, or rely on Celery's `db_write_time_ms`?

5. **Test Timeout**: 15 minutes for 1024p full lifecycle reasonable? Or expect faster?

## Implementation Steps

1. **Read generator code** to understand idempotency behavior
2. **Create test file** `test_async_production_readiness.py`
3. **Implement helpers**: `_poll_task_until_done()`, `_simulate_results()`, `_complete_tournament()`
4. **Implement Group U**: Full lifecycle with worker (10 tests)
5. **Implement Group V**: Idempotency (3 tests)
6. **Implement Group W**: UI monitoring (2 tests)
7. **Document** Celery worker setup in test docstring
8. **Run tests** with worker running, fix failures
9. **Report** metrics: runtime, memory, DB writes

## Success Criteria

- All 15 tests pass with Celery worker running
- 1024p full lifecycle completes in < 15 minutes
- No duplicate sessions created
- Bracket structure valid (no orphans, correct parent/child)
- UI stable during async generation (sessions=0 state)
- UI updates correctly when sessions appear
- Idempotency proven (duplicate task doesn't break state)

## Files to Create/Modify

### New Files
- `tests_e2e/test_async_production_readiness.py` (~1500 lines)

### Files to Read (for understanding)
- `app/services/tournament/session_generation/session_generator.py` - idempotency checks
- `app/api/api_v1/endpoints/tournaments/generator.py` - `_simulate_tournament_results()`

### No Modifications Needed
- Celery task already exists
- All required endpoints already exist
- Just need to orchestrate them correctly in tests
