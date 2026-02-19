# DUAL FINALIZATION PATH - Root Cause Analysis

**Date**: 2026-02-01
**Severity**: 🔴 CRITICAL - Core Integrity Bug
**Status**: ANALYSIS COMPLETE, FIX IN PROGRESS

---

## Executive Summary

Tournament 227 "LFA GanFoottennis Euro Cup" demonstrates **DUAL FINALIZATION**: two separate code paths both writing to `tournament_rankings` table, creating **16 ranking rows for 8 players** with conflicting data.

**Live Leaderboard (Correct)**:
- Kylian Mbappé (user_id=13): 11 pts → **SHOULD BE RANK 1**
- Cole Palmer (user_id=15): 8 pts → **SHOULD BE RANK 2 [TIE]**
- Martin Ødegaard (user_id=4): 8 pts → **SHOULD BE RANK 2 [TIE]**

**Distributed Rewards (WRONG - from tournament_rankings table)**:
- Rank 1: Péter Nagy (user_id=5) → **102 pts** ❌
- Rank 2: Cole Palmer (user_id=15) → **94 pts** ❌
- Rank 3: Péter Barna (user_id=6) → **73 pts** ❌
- **Kylian Mbappé got rank 6 (36 pts) instead of rank 1 (11 pts)** ❌

---

## 📊 Database Evidence

```sql
SELECT id, user_id, rank, points
FROM tournament_rankings
WHERE tournament_id = 227
ORDER BY rank;
```

**Result**: 16 rows for 8 players (2x duplication)

| id  | user_id | rank | points |
|-----|---------|------|--------|
| 842 | 5       | 1    | 102.00 | ← HEAD_TO_HEAD scoring?
| 843 | 15      | 2    | 94.00  |
| 844 | 6       | 3    | 73.00  |
| ...  |         |      |        |
| 848 | 4       | 9    | 19.00  | ← INDIVIDUAL scoring?
| 849 | 16      | 12   | 16.00  |
| 850 | 13      | 7    | 32.00  | ← Kylian (should be rank 1)
| 851 | 16      | 8    | 21.00  |
| 852 | 15      | 10   | 17.00  | ← Cole (should be rank 2)
| 853 | 5       | 11   | 16.00  |
| 854 | 14      | 13   | 15.00  |
| 855 | 4       | 14   | 13.00  | ← Martin (should be rank 2)
| 856 | 6       | 15   | 13.00  |
| 857 | 7       | 16   | 9.00   |

**Key Observations**:
- **Two distinct scoring algorithms** writing to same table
- **Points don't match live leaderboard** (11, 8, 8 vs 102, 94, 73)
- **Ranks are completely wrong** for reward distribution

---

## 🔍 DUAL PATH Architecture

### PATH 1: Production Workflow (SessionFinalizer)

**Entry Point**: `POST /api/v1/tournaments/{id}/sessions/{session_id}/finalize`

**Call Stack**:
```
sandbox_workflow.py:784 (Streamlit button)
  ↓
app/api/api_v1/endpoints/tournaments/results/finalization.py:151-214
  ↓
SessionFinalizer.finalize()
  ↓
SessionFinalizer.update_tournament_rankings()
  app/services/tournament/results/finalization/session_finalizer.py:71-101
  ↓
get_or_create_ranking() × N players
  app/services/tournament/leaderboard_service.py:23-78
  ↓
TournamentRanking(...) created (line 64)
  ↓
calculate_ranks()
  app/services/tournament/leaderboard_service.py:118-171
```

**Behavior**:
- ✅ Reads `rounds_data` from session
- ✅ Aggregates by scoring method (ROUNDS_BASED → max score)
- ✅ Creates ONE ranking per player via `get_or_create_ranking()`
- ✅ Assigns ranks via `calculate_ranks()`
- ⚠️ **PROBLEM**: No idempotency check - can be called multiple times

### PATH 2: Sandbox Test Orchestrator (Direct TournamentRanking Creation)

**Entry Point**: `POST /api/v1/sandbox/run-test`

**Call Stack**:
```
streamlit_sandbox_v3_admin_aligned.py:194 (Create Tournament button)
  ↓
app/api/api_v1/endpoints/sandbox/run_test.py:53-167
  ↓
SandboxTestOrchestrator.execute_test()
  app/services/sandbox_test_orchestrator.py:201-270
  ↓
SandboxTestOrchestrator._generate_rankings()
  app/services/sandbox_test_orchestrator.py:489-542
  ↓
TournamentRanking(...) created DIRECTLY (line 526-537)
  ↓
db.add(ranking) × N players
  ↓
db.commit()
```

**Behavior**:
- ❌ Does NOT use `get_or_create_ranking()`
- ❌ Does NOT check for existing rankings
- ❌ Creates rankings DIRECTLY in a loop
- ❌ Uses **synthetic point calculation** (100 - i * noise)
- ❌ **BYPASSES all production guards**

**Critical Code** (sandbox_test_orchestrator.py:526-537):
```python
for rank, (user_id, points) in enumerate(ranked_data, start=1):
    ranking = TournamentRanking(  # ❌ DIRECT CREATION - NO GUARDS
        tournament_id=self.tournament_id,
        user_id=user_id,
        participant_type="PLAYER",
        rank=rank,
        points=int(points),
        wins=0,
        losses=0,
        draws=0,
        updated_at=datetime.now()
    )
    self.db.add(ranking)  # ❌ NO IDEMPOTENCY CHECK

self.db.commit()
```

---

## 💥 Divergence Point

The two paths **diverge at tournament creation**:

### Sandbox Path (/sandbox/run-test)
1. Creates tournament via `SandboxTestOrchestrator`
2. **Immediately generates synthetic rankings** (`_generate_rankings()`)
3. **Does NOT finalize sessions** - skips SessionFinalizer entirely
4. Writes to `tournament_rankings` with synthetic points (102, 94, 73...)

### Production Path (Streamlit workflow)
1. Creates tournament via same endpoint (`/sandbox/run-test`)
2. **User manually enters round results** (Step 4)
3. **User clicks "Distribute Rewards"** button (Step 6)
4. **Calls SessionFinalizer.finalize()** → writes REAL rankings (11, 8, 8...)

**Result**: Both paths write to `tournament_rankings` → **16 rows for 8 players**

---

## 🚨 Why This Happened

### Tournament 227 Timeline

1. **14:47:27** - User creates tournament via Streamlit (`/sandbox/run-test`)
2. **Sandbox orchestrator** runs `_generate_rankings()` → **8 synthetic rankings created** (ranks 1-8, points 102, 94, 73...)
3. **User** enters round results manually (Step 4)
4. **User** clicks "Distribute Rewards" (Step 6)
5. **Streamlit** calls `/tournaments/227/sessions/1428/finalize`
6. **SessionFinalizer** runs `update_tournament_rankings()` → **8 MORE rankings created** (ranks 9-16, points 19, 17, 16...)
7. **Reward distribution** uses deduplication logic → picks MIN(rank) per user
8. **Péter Nagy (user_id=5)** has rank 1 (synthetic) AND rank 11 (real) → gets rank 1 reward ❌
9. **Kylian Mbappé (user_id=13)** has rank 6 (synthetic) AND rank 7 (real) → gets rank 6 reward ❌

---

## 🎯 Root Causes

### 1. **Dual Code Paths Writing to Same Table**
- **PATH 1**: `get_or_create_ranking()` (production)
- **PATH 2**: Direct `TournamentRanking()` (sandbox)
- **NO coordination** between paths

### 2. **Sandbox Orchestrator Creates Synthetic Rankings**
- `_generate_rankings()` writes FAKE data (100 - i * noise)
- **Intended for full automated tests** (no human interaction)
- **NOT intended for Streamlit manual workflow**

### 3. **Streamlit Uses Sandbox Endpoint for Creation**
- `sandbox_workflow.py:194` calls `/sandbox/run-test`
- This triggers orchestrator's `_generate_rankings()`
- **Should use dedicated tournament creation endpoint instead**

### 4. **No Idempotency Guards**
- `SessionFinalizer.finalize()` has idempotency check (line 167-187)
- **BUT** `get_or_create_ranking()` does NOT prevent duplicates across DIFFERENT finalization methods
- **Sandbox path** has NO idempotency at all

### 5. **No DB-Level Unique Constraint**
- `tournament_rankings` table allows multiple rows for same (tournament_id, user_id)
- **No unique constraint** to prevent duplicates

---

## ✅ Required Fixes

### FIX 1: Streamlit Must NOT Use /sandbox/run-test ⚡ IMMEDIATE

**Problem**: Streamlit workflow calls sandbox endpoint which generates synthetic rankings

**Solution**: Create dedicated tournament creation endpoint

**File**: `app/api/api_v1/endpoints/tournaments/lifecycle.py` (new endpoint)

```python
@router.post("/create", response_model=TournamentCreationResponse)
def create_tournament_for_instructor_workflow(
    request: TournamentCreationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create tournament for instructor-led workflow (manual session management).

    DOES NOT:
    - Generate synthetic rankings
    - Auto-finalize sessions
    - Run automated tests

    ONLY creates empty tournament structure.
    """
    # Create tournament
    # Enroll participants
    # Generate sessions
    # Return tournament_id
    # DO NOT call _generate_rankings()
```

**File**: `sandbox_workflow.py:194` (update to use new endpoint)

```python
# OLD (WRONG):
result = api_client.post("/api/v1/sandbox/run-test", data=api_payload)

# NEW (CORRECT):
result = api_client.post("/api/v1/tournaments/create", data=api_payload)
```

### FIX 2: Add DB Unique Constraint ⚡ IMMEDIATE

**File**: `alembic/versions/YYYY_MM_DD_HHMM-add_unique_constraint_tournament_rankings.py`

```python
def upgrade():
    # First, clean up existing duplicates
    op.execute("""
        DELETE FROM tournament_rankings a
        USING tournament_rankings b
        WHERE a.id > b.id
        AND a.tournament_id = b.tournament_id
        AND a.user_id = b.user_id
        AND a.participant_type = b.participant_type;
    """)

    # Add unique constraint
    op.create_unique_constraint(
        'uq_tournament_rankings_tournament_user',
        'tournament_rankings',
        ['tournament_id', 'user_id', 'participant_type']
    )

def downgrade():
    op.drop_constraint(
        'uq_tournament_rankings_tournament_user',
        'tournament_rankings'
    )
```

**Benefits**:
- ✅ Database-level protection
- ✅ Prevents ALL duplicate paths (even future ones)
- ✅ Will raise IntegrityError on duplicate attempts

### FIX 3: Enhanced SessionFinalizer Idempotency

**File**: `app/services/tournament/results/finalization/session_finalizer.py:167-187`

**Current guard** (session-level):
```python
if session.game_results:
    raise ValueError("Session already finalized")
```

**Add tournament_rankings guard** (tournament-level):
```python
# Check if tournament_rankings already exist for this session's participants
existing_rankings = db.query(TournamentRanking).filter(
    TournamentRanking.tournament_id == tournament.id,
    TournamentRanking.user_id.in_([p.user_id for p in session.participants])
).count()

if existing_rankings > 0:
    logger.warning(
        f"🔒 IDEMPOTENCY VIOLATION: Attempted to finalize session {session.id} "
        f"but {existing_rankings} tournament_rankings already exist. "
        f"Rejecting duplicate finalization."
    )
    raise ValueError(
        f"Tournament rankings already exist for this tournament. "
        f"Cannot re-finalize session {session.id}."
    )
```

### FIX 4: Deprecate Sandbox Orchestrator Rankings Generation

**File**: `app/services/sandbox_test_orchestrator.py:489-542`

**Option A**: Remove `_generate_rankings()` entirely
- Sandbox tests should use SessionFinalizer like production

**Option B**: Add guard to prevent use in manual workflows
```python
def _generate_rankings(self, user_ids, performance_variation, ranking_distribution):
    """
    Generate synthetic rankings for AUTOMATED tests only.

    WARNING: This method should ONLY be used for fully automated sandbox tests
    where NO human interaction occurs. For instructor-led workflows, use
    SessionFinalizer.finalize() instead.
    """
    # Check if any sessions have rounds_data (indicates manual workflow)
    sessions = self.db.query(SessionModel).filter(
        SessionModel.semester_id == self.tournament_id
    ).all()

    for session in sessions:
        if session.rounds_data:
            raise ValueError(
                "Cannot generate synthetic rankings: session has manual round data. "
                "Use SessionFinalizer.finalize() for instructor-led workflows."
            )

    # ... existing synthetic ranking logic ...
```

### FIX 5: Comprehensive Audit Logging

**Already implemented** in `leaderboard_service.py:46-62` ✅

**Add to SessionFinalizer** (already done line 207-218) ✅

**Add to all finalization entry points**:
- `finalization.py:202` - Log finalize API call
- `sandbox_test_orchestrator.py:526` - Log synthetic ranking creation

---

## 🧪 Testing Requirements

### Unit Tests

**File**: `tests/unit/services/test_session_finalizer_idempotency.py`

```python
def test_finalize_session_idempotency(db_session, sample_tournament, sample_session):
    """Test that finalize_session rejects duplicate calls"""
    finalizer = SessionFinalizer(db_session)

    # First call succeeds
    result1 = finalizer.finalize(sample_tournament, sample_session, 1, "Admin")
    assert result1["success"] is True

    # Second call fails
    with pytest.raises(ValueError, match="already finalized"):
        finalizer.finalize(sample_tournament, sample_session, 1, "Admin")

    # Verify only ONE ranking per user
    rankings = db_session.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == sample_tournament.id
    ).all()

    user_ids = [r.user_id for r in rankings]
    assert len(user_ids) == len(set(user_ids)), "Duplicate rankings detected!"
```

### Integration Tests

**File**: `tests/integration/test_dual_path_prevention.py`

```python
def test_sandbox_then_manual_finalization_blocked(db_session):
    """Test that manual finalization is blocked if sandbox rankings exist"""
    # 1. Create tournament via sandbox orchestrator
    orchestrator = SandboxTestOrchestrator(db_session)
    result = orchestrator.execute_test(
        tournament_type_code="league",
        skills_to_test=["shooting"],
        player_count=8
    )
    tournament_id = result["tournament"]["id"]

    # 2. Verify synthetic rankings were created
    rankings = db_session.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).all()
    assert len(rankings) == 8

    # 3. Attempt manual finalization via SessionFinalizer
    session = db_session.query(SessionModel).filter(
        SessionModel.semester_id == tournament_id
    ).first()

    finalizer = SessionFinalizer(db_session)

    # 4. Should be BLOCKED by idempotency guard
    with pytest.raises(ValueError, match="rankings already exist"):
        finalizer.finalize(
            tournament=tournament,
            session=session,
            recorded_by_id=1,
            recorded_by_name="Test User"
        )

    # 5. Verify STILL only 8 rankings (no duplicates)
    rankings_after = db_session.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).all()
    assert len(rankings_after) == 8
```

### E2E Tests

**File**: `tests/e2e/test_streamlit_workflow_no_sandbox.py`

```python
def test_streamlit_workflow_uses_production_endpoint(api_client):
    """Test that Streamlit workflow does NOT call /sandbox/run-test"""
    # 1. Create tournament via Streamlit (should use /tournaments/create)
    response = api_client.post("/api/v1/tournaments/create", json={
        "tournament_name": "Test Tournament",
        "scoring_mode": "INDIVIDUAL",
        "number_of_rounds": 3,
        # ... other config
    })
    assert response.status_code == 200
    tournament_id = response.json()["tournament_id"]

    # 2. Verify NO synthetic rankings were created
    rankings = db.query(TournamentRanking).filter(
        TournamentRanking.tournament_id == tournament_id
    ).all()
    assert len(rankings) == 0, "Synthetic rankings should NOT exist!"

    # 3. Manual round entry...
    # 4. Finalize session...
    # 5. Verify ONLY production rankings exist
```

---

## 📝 Implementation Checklist

- [ ] **FIX 1**: Create `/tournaments/create` endpoint (separate from `/sandbox/run-test`)
- [ ] **FIX 1**: Update `sandbox_workflow.py` to use new endpoint
- [ ] **FIX 2**: Create Alembic migration for unique constraint
- [ ] **FIX 2**: Run migration on database
- [ ] **FIX 3**: Add tournament_rankings check to SessionFinalizer
- [ ] **FIX 4**: Deprecate or guard `_generate_rankings()`
- [ ] **FIX 5**: Add comprehensive logging to all paths
- [ ] **TEST 1**: Write unit tests for idempotency
- [ ] **TEST 2**: Write integration tests for dual path prevention
- [ ] **TEST 3**: Write E2E tests for Streamlit workflow
- [ ] **VERIFY**: Run all tests - must be GREEN
- [ ] **VERIFY**: Manual Streamlit workflow test (no synthetic rankings)
- [ ] **VERIFY**: Sandbox automated test (synthetic rankings OK)

---

## 🚀 Success Criteria

✅ **Streamlit workflow** creates tournaments WITHOUT synthetic rankings
✅ **SessionFinalizer** is idempotent - rejects duplicate calls
✅ **DB constraint** prevents duplicate (tournament_id, user_id, participant_type)
✅ **All tests pass** (unit + integration + E2E)
✅ **Audit logs** show clear single finalization path
✅ **No manual testing required** until all tests GREEN

---

**Generated**: 2026-02-01 by Claude Code
